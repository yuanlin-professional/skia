# MiddleOutFanRenderStep

> 源文件
> - `src/gpu/graphite/render/MiddleOutFanRenderStep.h`
> - `src/gpu/graphite/render/MiddleOutFanRenderStep.cpp`

## 概述

`MiddleOutFanRenderStep` 是 Skia Graphite 渲染管线中用于路径填充的渲染步骤类，采用"中间向外扇形三角化"（Middle-Out Fan Triangulation）算法。该类继承自 `RenderStep`，专门处理简单多边形路径的模板缓冲区填充，支持奇偶填充（Even-Odd）和非零环绕（Winding）两种填充规则。

该渲染步骤的核心思想是将路径的轮廓从中间顶点开始向外展开形成三角形扇，并将三角形直接写入模板缓冲区，而不需要在 CPU 端进行复杂的三角剖分预处理。这种方法在处理凸多边形和简单路径时非常高效，可以快速建立路径的模板遮罩，为后续的覆盖渲染（coverage pass）提供基础。

## 架构位置

`MiddleOutFanRenderStep` 位于 Skia Graphite 图形管线的路径渲染子系统中：

```
skia/
├── src/gpu/graphite/
│   ├── Renderer.h                      // RenderStep 基类
│   ├── render/
│   │   ├── MiddleOutFanRenderStep.h   // 中间向外扇形渲染步骤声明
│   │   ├── MiddleOutFanRenderStep.cpp // 中间向外扇形渲染步骤实现
│   │   └── CommonDepthStencilSettings.h // 通用深度模板配置
│   ├── geom/
│   │   ├── Shape.h                     // 几何形状抽象
│   │   └── Transform.h                 // 坐标变换
│   ├── DrawParams.h                    // 绘制参数
│   └── DrawWriter.h                    // 顶点写入器
├── src/gpu/tessellate/
│   └── MiddleOutPolygonTriangulator.h  // 中间向外多边形三角化器
```

该类与路径曲面细分（tessellation）模块紧密配合，利用 `PathMiddleOutFanIter` 迭代器生成三角形数据，是 Graphite 路径渲染策略的重要组成部分。

## 主要类与结构体

### MiddleOutFanRenderStep 类

```cpp
class MiddleOutFanRenderStep final : public RenderStep {
public:
    MiddleOutFanRenderStep(Layout layout, bool evenOdd);
    ~MiddleOutFanRenderStep() override;

    std::string vertexSkSL() const override;
    void writeVertices(DrawWriter*, const DrawParams&, uint32_t ssboIndex) const override;
    void writeUniformsAndTextures(const DrawParams&, PipelineDataGatherer*) const override;
};
```

**关键特性：**
- **双填充规则支持**：通过 `evenOdd` 参数选择奇偶或非零环绕填充规则
- **模板缓冲区渲染**：配置深度模板状态，仅修改模板值而不输出颜色
- **MSAA 支持**：要求多重采样抗锯齿以提升边缘质量
- **动态顶点追加**：使用 `Flags::kAppendVertices` 标志动态生成三角形数据

### 渲染步骤 ID

```cpp
enum RenderStepID {
    kMiddleOutFan_EvenOdd,  // 奇偶填充规则
    kMiddleOutFan_Winding   // 非零环绕填充规则
};
```

### 顶点属性结构

每个顶点包含以下属性：
```cpp
{
    {"position", VertexAttribType::kFloat2},   // 局部坐标系中的 2D 位置
    {"depth", VertexAttribType::kFloat},       // 深度值（用于绘制排序）
    {"ssboIndex", VertexAttribType::kUInt}     // 着色器存储缓冲对象索引
}
```

### Uniform 变量

```cpp
{
    {"localToDevice", SkSLType::kFloat4x4}  // 局部到设备坐标空间的变换矩阵
}
```

### 深度模板配置

根据填充规则选择不同的模板配置：
- **奇偶填充**：`kEvenOddStencilPass` - 每次覆盖切换模板位
- **非零环绕**：`kWindingStencilPass` - 根据覆盖方向递增或递减模板值

## 公共 API 函数

### 构造与析构

```cpp
MiddleOutFanRenderStep(Layout layout, bool evenOdd);
```
创建中间向外扇形渲染步骤实例。

**参数**：
- `layout`：顶点数据布局方式（交错或分离）
- `evenOdd`：`true` 使用奇偶填充规则，`false` 使用非零环绕规则

**实现细节**：
- 自动设置 `Flags::kRequiresMSAA` 和 `Flags::kAppendVertices` 标志
- 根据填充规则选择对应的渲染步骤 ID 和深度模板设置
- 使用 `kTriangles` 图元类型（三角形列表）

### vertexSkSL()

```cpp
std::string vertexSkSL() const override;
```
生成顶点着色器的 SkSL 代码主体。

**返回的着色器逻辑**：
```glsl
float4 devPosition = localToDevice * float4(position, 0.0, 1.0);
devPosition.z = depth;
stepLocalCoords = position;
```

**功能说明**：
1. 将局部坐标 `position` 通过 `localToDevice` 矩阵变换到设备坐标空间
2. 覆盖深度值为顶点属性中的 `depth`（用于绘制排序）
3. 将局部坐标传递给 `stepLocalCoords`（用于后续着色器阶段）

### writeVertices()

```cpp
void writeVertices(DrawWriter* writer, const DrawParams& params,
                   uint32_t ssboIndex) const override;
```
将路径三角化后的顶点数据写入 GPU 缓冲区。

**实现流程**：
1. 从 `DrawParams` 中提取几何形状并转换为 `SkPath`
2. 计算最大可能的三角形数量：`max(顶点数 - 2, 0)`
3. 预留顶点缓冲区空间（三角形数 × 3）
4. 使用 `PathMiddleOutFanIter` 迭代器遍历路径
5. 对于每个三角形栈（stack），逐个输出三角形的三个顶点

**顶点数据格式**：
```cpp
verts.append(3) << p0 << depth << ssboIndex
                << p1 << depth << ssboIndex
                << p2 << depth << ssboIndex;
```
每个顶点包含：2D 位置 + 深度 + SSBO 索引

### writeUniformsAndTextures()

```cpp
void writeUniformsAndTextures(const DrawParams& params,
                              PipelineDataGatherer* gatherer) const override;
```
向管线数据收集器写入 uniform 变量。

**实现**：仅写入一个变换矩阵 uniform：
```cpp
gatherer->write(params.transform().matrix());  // localToDevice 矩阵
```

该渲染步骤不使用纹理资源，因此不添加纹理采样器。

## 内部实现细节

### 中间向外三角化算法

`PathMiddleOutFanIter` 迭代器实现了核心的三角化逻辑：

**算法原理**：
1. 选择路径轮廓的中间顶点作为扇形中心点
2. 从中心点开始，向两侧同时展开形成三角形扇
3. 使用栈结构管理待处理的顶点对
4. 按照"中间向外"的顺序生成三角形

**优势**：
- 避免退化三角形（degenerate triangles）
- 更好的数值稳定性
- 适合 GPU 光栅化的三角形排列顺序
- 减少填充率（fill rate）浪费

### 三角形生成示例

对于一个六边形路径：
```
顶点顺序：V0 -> V1 -> V2 -> V3 -> V4 -> V5

中间向外生成顺序：
选择 V2 或 V3 作为中心
生成三角形：(V2, V3, V4), (V2, V4, V5), (V2, V5, V0), (V2, V0, V1)
```

### 模板缓冲区操作

**奇偶填充模板操作**：
```cpp
stencilOp = Invert  // 切换模板位（0 <-> 1）
```
- 任何被奇数次覆盖的像素：模板值为 1
- 任何被偶数次覆盖的像素：模板值为 0

**非零环绕模板操作**：
```cpp
frontFaceOp = Increment  // 正面三角形：模板值 +1
backFaceOp = Decrement   // 背面三角形：模板值 -1
```
- 模板值为非零的像素被认为在路径内部
- 自然处理路径的环绕方向

### 顶点数据追加

使用 `DrawWriter::Vertices` 接口高效追加顶点：
```cpp
DrawWriter::Vertices verts{*writer};
verts.reserve(maxTrianglesInFans * 3);  // 预分配缓冲区
verts.append(3) << vertex_data;          // 批量写入三角形顶点
```

**性能优化**：
- `reserve()` 避免多次内存重新分配
- 流式写入接口（`operator<<`）减少函数调用开销
- 紧凑的顶点布局提高缓存利用率

## 依赖关系

### 直接依赖

- **RenderStep**：基类，定义渲染步骤接口
- **DrawParams**：封装绘制参数（几何、变换、绘制顺序）
- **DrawWriter**：管理顶点缓冲区写入
- **PipelineDataGatherer**：收集管线所需的 uniform 资源
- **Shape**：几何形状抽象，提供路径转换接口
- **Transform**：封装坐标变换矩阵
- **PathMiddleOutFanIter**：中间向外路径迭代器（来自曲面细分模块）

### 间接依赖

- **SkPath**：Skia 核心路径数据结构
- **Geometry**：几何数据容器
- **DrawOrder**：绘制排序管理
- **CommonDepthStencilSettings**：预定义的深度模板配置

### 依赖图

```
MiddleOutFanRenderStep
    ├─> RenderStep (基类)
    ├─> DrawParams
    │   ├─> Geometry
    │   │   └─> Shape
    │   │       └─> SkPath
    │   ├─> Transform
    │   └─> DrawOrder
    ├─> DrawWriter
    ├─> PipelineDataGatherer
    └─> tess::PathMiddleOutFanIter (曲面细分模块)
```

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）
通过 `evenOdd` 参数选择不同的填充规则策略，每种策略对应不同的渲染步骤 ID 和深度模板配置，但共享相同的三角化和顶点生成逻辑。

### 2. 迭代器模式（Iterator Pattern）
使用 `PathMiddleOutFanIter` 迭代器封装复杂的三角化算法，提供简洁的访问接口。调用者无需了解内部三角形生成细节，只需遍历迭代器即可获取三角形数据。

### 3. 延迟计算模式
三角形数据在 GPU 绘制前才动态生成（`writeVertices()` 阶段），而非在路径创建时预计算。这种设计减少内存占用，适应动态变化的几何数据。

### 4. 设计决策

**为什么使用中间向外算法？**
- 传统的扇形三角化从固定顶点（如第一个顶点）展开，可能产生狭长的退化三角形
- 中间向外算法选择中心位置作为扇形原点，生成更均匀的三角形
- 更好的数值稳定性，减少浮点精度误差

**为什么要求 MSAA？**
- 模板缓冲区渲染依赖精确的边缘覆盖检测
- MSAA 提供子像素级别的覆盖信息，提升路径边缘的抗锯齿质量
- 避免锯齿边缘导致的视觉瑕疵

**为什么使用动态顶点追加？**
- 路径复杂度差异很大（从简单三角形到复杂多边形）
- 静态顶点缓冲区会浪费大量内存
- 动态追加机制按需分配，优化内存使用

**为什么将深度作为顶点属性？**
- 绘制排序需要精确的深度值控制
- 在顶点属性中携带深度值避免管线状态切换
- 允许单次绘制调用中混合不同深度的几何体

## 性能考量

### 1. 顶点缓冲区预分配
```cpp
verts.reserve(maxTrianglesInFans * 3);
```
根据路径顶点数预估最大三角形数量，一次性分配足够的缓冲区空间，避免动态扩容导致的多次内存拷贝。

### 2. 紧凑的顶点格式
- 使用 `Float2` 存储 2D 位置（8 字节）
- 单个 `Float` 存储深度（4 字节）
- 单个 `UInt` 存储 SSBO 索引（4 字节）
- 每个顶点仅 16 字节，最小化内存带宽占用

### 3. 简化的顶点着色器
顶点着色器逻辑极简，仅执行单次矩阵-向量乘法和深度赋值，减少 GPU 计算开销。

### 4. 模板缓冲区优化
- 不输出颜色，禁用颜色写入（隐式配置）
- 仅修改模板值，最小化内存带宽
- 后续覆盖渲染可以直接使用模板遮罩，避免重复计算

### 5. 批处理友好
- 所有三角形使用相同的管线状态和 uniform
- 单次 `writeVertices()` 调用可输出整个路径的三角形
- 减少 GPU 绘制调用次数

### 6. CPU 端三角化开销
虽然三角化算法在 CPU 端执行，但其时间复杂度为 O(n)（n 为顶点数），对于简单路径几乎无开销。相比 GPU 端曲面细分，节省了 GPU 资源。

### 7. 避免路径转换开销
代码注释中提到未来优化方向：
```cpp
// TODO: Have Shape provide a path-like iterator so we don't actually have to convert
// non paths to SkPath just to iterate their pts/verbs
```
当前实现需要将非路径几何转换为 `SkPath`，未来可通过直接迭代器接口避免此开销。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/gpu/graphite/Renderer.h` | RenderStep 基类定义 |
| `src/gpu/graphite/render/CommonDepthStencilSettings.h` | 预定义的深度模板配置（奇偶/环绕） |
| `src/gpu/tessellate/MiddleOutPolygonTriangulator.h` | 中间向外多边形三角化迭代器 |
| `src/gpu/graphite/geom/Shape.h` | 几何形状抽象类 |
| `src/gpu/graphite/geom/Transform.h` | 坐标变换封装 |
| `src/gpu/graphite/DrawParams.h` | 绘制参数容器 |
| `src/gpu/graphite/DrawWriter.h` | 顶点缓冲区写入接口 |
| `src/gpu/graphite/PipelineData.h` | 管线数据收集器 |
| `src/gpu/graphite/Attribute.h` | 顶点属性定义 |
| `src/gpu/BufferWriter.h` | 缓冲区写入工具 |
| `include/core/SkPath.h` | Skia 核心路径类 |
| `src/core/SkSLTypeShared.h` | SkSL 类型定义 |
