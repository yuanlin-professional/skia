# CircularArcRenderStep

> 源文件
> - `src/gpu/graphite/render/CircularArcRenderStep.h`
> - `src/gpu/graphite/render/CircularArcRenderStep.cpp`

## 概述

`CircularArcRenderStep` 是 Skia Graphite 渲染管线中专门用于渲染圆弧的高级渲染步骤类。该类继承自 `RenderStep`，支持填充圆弧（filled arcs）和不包含中心点的描边圆弧（stroked arcs without center）的高质量渲染。当前实现支持平头端点（butt caps）并计划扩展圆头端点（round caps）支持。

该类采用基于实例化渲染的技术，使用预定义的八边形顶点模板结合实例属性动态生成圆弧几何体。通过复杂的着色器逻辑处理圆弧的边缘抗锯齿、裁剪平面计算和可选的圆头端点渲染。每个圆弧实例通过单次绘制调用完成，避免了 CPU 端的复杂曲线细分，充分利用 GPU 的并行计算能力实现高效渲染。

## 架构位置

`CircularArcRenderStep` 位于 Skia Graphite 图形管线的几何渲染层：

```
skia/
├── src/gpu/graphite/
│   ├── Renderer.h                          // RenderStep 基类
│   ├── render/
│   │   ├── CircularArcRenderStep.h        // 圆弧渲染步骤声明
│   │   ├── CircularArcRenderStep.cpp      // 圆弧渲染步骤实现
│   │   └── CommonDepthStencilSettings.h   // 通用深度模板配置
│   ├── geom/
│   │   ├── Shape.h                         // 几何形状抽象
│   │   └── Transform.h                     // 坐标变换
│   ├── BufferManager.h                     // 缓冲区管理器
│   ├── DrawParams.h                        // 绘制参数
│   └── DrawWriter.h                        // 顶点写入器
├── include/core/
│   └── SkArc.h                             // 圆弧数据结构
```

该类是 Skia 圆弧渲染优化策略的核心组件，通过 GPU 加速避免了传统路径细分的开销。

## 主要类与结构体

### CircularArcRenderStep 类

```cpp
class CircularArcRenderStep final : public RenderStep {
public:
    CircularArcRenderStep(Layout, StaticBufferManager*);
    ~CircularArcRenderStep() override;

    std::string vertexSkSL() const override;
    const char* fragmentCoverageSkSL() const override;

    void writeVertices(DrawWriter*, const DrawParams&, uint32_t ssboIndex) const override;
    void writeUniformsAndTextures(const DrawParams&, PipelineDataGatherer*) const override;

private:
    BindBufferInfo fVertexBuffer;   // 静态顶点缓冲区（八边形模板）
    BindBufferInfo fIndexBuffer;    // 索引缓冲区
};
```

**关键特性：**
- **静态顶点模板**：使用预生成的八边形顶点缓冲区
- **实例化渲染**：每个圆弧通过单个实例绘制
- **无 uniform 依赖**：所有数据通过实例属性传递
- **抗锯齿边界扩展**：自动外扩边界框以包含抗锯齿区域

### Vertex 结构体

```cpp
struct Vertex {
    SkV3 fPosition;  // 单位圆局部空间位置 (.xy) 和 AA 偏移 (.z)
};
```

顶点数组包含 18 个顶点，形成外接和内接单位圆的八边形环。

### 顶点几何数据

```cpp
static constexpr int kVertexCount = 18;
static constexpr float kOctOffset = 0.41421356237f;  // sqrt(2) - 1
static constexpr SkScalar kCosPi8 = 0.923579533f;
static constexpr SkScalar kSinPi8 = 0.382683432f;
```

八边形顶点交替排列外环和内环顶点，形成三角形带（triangle strip）拓扑。

### 静态属性

```cpp
{"position", VertexAttribType::kFloat3}  // 来自静态缓冲区的顶点位置
```

### 实例属性（每个圆弧实例）

```cpp
{
    {"centerScales", VertexAttribType::kFloat4},      // 中心位置 (.xy) + 外半径 (.z) + 内半径 (.w)
    {"radiiAndFlags", VertexAttribType::kFloat3},     // 外半径+0.5 (.x) + 归一化内半径 (.y) + 标志 (.z)
    {"geoClipPlane", VertexAttribType::kFloat3},      // 几何裁剪平面（处理尖锐圆弧）
    {"fragClipPlane0", VertexAttribType::kFloat3},    // 片段裁剪平面 0（总是应用）
    {"fragClipPlane1", VertexAttribType::kFloat3},    // 片段裁剪平面 1（交集或并集）
    {"inRoundCapPos", VertexAttribType::kFloat4},     // 圆头端点中心位置
    {"inRoundCapRadius", VertexAttribType::kFloat},   // 圆头端点半径
    {"depth", VertexAttribType::kFloat},              // 深度值
    {"ssboIndex", VertexAttribType::kUInt},           // SSBO 索引
    {"mat0", VertexAttribType::kFloat3},              // 变换矩阵第 0 行
    {"mat1", VertexAttribType::kFloat3},              // 变换矩阵第 1 行
    {"mat2", VertexAttribType::kFloat3}               // 变换矩阵第 2 行
}
```

### Varying 变量

```cpp
{
    {"circleEdge", SkSLType::kFloat4},      // 归一化偏移向量 + 半径信息
    {"clipPlane", SkSLType::kFloat3},       // 主裁剪平面
    {"isectPlane", SkSLType::kFloat3},      // 交集裁剪平面（凸圆弧）
    {"unionPlane", SkSLType::kFloat3},      // 并集裁剪平面（凹圆弧）
    {"roundCapRadius", SkSLType::kFloat},   // 圆头端点半径
    {"roundCapPos", SkSLType::kFloat4}      // 圆头端点位置
}
```

## 公共 API 函数

### 构造与析构

```cpp
CircularArcRenderStep(Layout layout, StaticBufferManager* bufferManager);
```
创建圆弧渲染步骤实例并初始化静态顶点缓冲区。

**配置**：
- 渲染步骤 ID：`RenderStepID::kCircularArc`
- 图元类型：`PrimitiveType::kTriangleStrip`（三角形带）
- 深度模板：`kDirectDepthLessPass`
- 标志：`kPerformsShading | kEmitsCoverage | kOutsetBoundsForAA | kAppendInstances`

**静态缓冲区初始化**：
调用 `write_vertex_buffer()` 生成 18 个八边形顶点。

### vertexSkSL()

```cpp
std::string vertexSkSL() const override;
```
生成顶点着色器的 SkSL 代码主体。

**着色器调用**：
```glsl
float4 devPosition = circular_arc_vertex_fn(
    position,          // 静态顶点位置
    centerScales, radiiAndFlags, geoClipPlane,
    fragClipPlane0, fragClipPlane1,
    inRoundCapPos, inRoundCapRadius, depth,
    float3x3(mat0, mat1, mat2),  // 变换矩阵
    // 输出 varying 变量
    circleEdge, clipPlane, isectPlane, unionPlane,
    roundCapRadius, roundCapPos,
    stepLocalCoords
);
```

**功能**：调用 `circular_arc_vertex_fn` 内置函数处理顶点变换、抗锯齿偏移和 varying 变量计算。

### fragmentCoverageSkSL()

```cpp
const char* fragmentCoverageSkSL() const override;
```
返回片段着色器的覆盖率计算代码。

**着色器代码**：
```glsl
outputCoverage = circular_arc_coverage_fn(
    circleEdge,
    clipPlane,
    isectPlane,
    unionPlane,
    roundCapRadius,
    roundCapPos
);
```

**功能**：调用 `circular_arc_coverage_fn` 内置函数计算圆弧边缘的抗锯齿覆盖率。

### writeVertices()

```cpp
void writeVertices(DrawWriter* writer, const DrawParams& params,
                   uint32_t ssboIndex) const override;
```
为圆弧实例写入实例属性数据。

**实现流程**：
1. 从 `DrawParams` 提取 `SkArc` 几何数据
2. 计算局部空间和设备空间的半径
3. 处理描边宽度（如果是描边圆弧）
4. 计算圆弧起始和结束点的单位向量
5. 确定裁剪平面（使用中心或割线裁剪）
6. 处理圆头端点（如果需要）
7. 将所有计算结果写入实例属性

**关键计算**：

**半径外扩**：
```cpp
outerRadius += SK_ScalarHalf;   // 外扩 0.5 像素用于抗锯齿
innerRadius -= SK_ScalarHalf;
```

**描边半径**：
```cpp
if (isStroke) {
    float localHalfWidth = params.strokeStyle().halfWidth();
    float halfWidth = localHalfWidth * transform.maxScaleFactor();
    outerRadius += halfWidth;
    innerRadius = radius - halfWidth;
}
```

**起始/结束点变换**：
```cpp
SkV2 localPoints[3];
localPoints[0] = {cos(startAngle), sin(startAngle)};
localPoints[1] = {cos(endAngle), sin(endAngle)};
transform.mapPoints(localPoints, devPoints, 3);
startPoint = normalize(devPoints[0] - center);
stopPoint = normalize(devPoints[1] - center);
```

**裁剪平面计算**（凸圆弧，使用中心）：
```cpp
SkV2 norm0 = {startPoint.y, -startPoint.x};  // 垂直于起始向量
SkV2 norm1 = {stopPoint.y, -stopPoint.x};    // 垂直于结束向量
clipPlane0 = {norm0.x, norm0.y, 0.5f};
clipPlane1 = {norm1.x, norm1.y, 0.5f};
```

**圆头端点**：
```cpp
if (isStroke && cap() == kRound_Cap) {
    float midRadius = (innerRadius + outerRadius) / (2 * outerRadius);
    roundCapPos0 = startPoint * midRadius;
    roundCapPos1 = stopPoint * midRadius;
    roundCapRadius = (outerRadius - innerRadius) / (2 * outerRadius);
}
```

### writeUniformsAndTextures()

```cpp
void writeUniformsAndTextures(const DrawParams&,
                              PipelineDataGatherer* gatherer) const override;
```
该渲染步骤不使用 uniform 变量或纹理，所有数据通过实例属性传递。

## 内部实现细节

### 八边形顶点模板

顶点数组形成外接和内接单位圆的八边形环：

```cpp
// 外环顶点：八边形顶点，距离 = 1 + kOctOffset
// 内环顶点：圆上顶点，距离 = 1
// 顶点交替排列：外环、内环、外环、内环...

kOctagonVertices[18] = {
    {-kOctOffset, -1, kOuterAAOffset},   // 外环底部
    {-kSinPi8, -kCosPi8, kInnerAAOffset}, // 内环
    {kOctOffset, -1, kOuterAAOffset},     // 外环
    // ... 以此类推
};
```

**Z 分量含义**：
- `kOuterAAOffset = 0.5`：标记为外环顶点，用于外扩抗锯齿
- `kInnerAAOffset = -0.5`：标记为内环顶点，用于内缩抗锯齿

### 顶点变换逻辑

顶点着色器中根据 Z 分量选择缩放因子：

```glsl
float scale = (position.z > 0) ? centerScales.z : centerScales.w;
vec2 localPos = centerScales.xy + position.xy * scale;
```

- 外环顶点：使用外半径 `centerScales.z`
- 内环顶点：使用内半径 `centerScales.w`（填充圆弧时为 0）

### 裁剪平面策略

**使用中心裁剪**（适用于楔形圆弧和大部分描边圆弧）：
```cpp
bool useCenter = (arc.isWedge() || isStroke) &&
                 !SkScalarNearlyEqual(absSweep, SK_ScalarPI);
```

**交集裁剪**（凸圆弧，扫描角 < 180°）：
```
clipPlane0: 起始点的法向量
clipPlane1: 结束点的法向量
片段必须同时在两个平面的正半空间内
```

**并集裁剪**（凹圆弧，扫描角 > 180°）：
```
片段在任一平面的正半空间内即可
flags 设为负值表示并集模式
```

**割线裁剪**（不使用中心，如半圆或完整圆弧）：
```cpp
SkV2 norm = {startPoint.y - stopPoint.y, stopPoint.x - startPoint.x};
clipPlane0 = {norm.x, norm.y, -norm.dot(startPoint) + 0.5f};
clipPlane1 = {0, 0, 1};  // 不裁剪
```

### 尖锐圆弧几何裁剪

对于非常尖锐的填充圆弧（扫描角 < 45°），额外应用几何裁剪平面防止渲染越过圆心：

```cpp
if (!isStroke && absSweep < 0.5f * SK_ScalarPI) {
    SkV2 clipNorm = {-localNorm0.y - localNorm1.y, localNorm1.x + localNorm0.x};
    clipNorm = clipNorm.normalize();
    float dist = 0.5f / radius / transform.maxScaleFactor();
    geoClipPlane = {clipNorm.x, clipNorm.y, dist};
}
```

### 镜像变换检测

通过检测变换矩阵的行列式判断是否包含镜像：

```cpp
auto upperLeftDet = m.rc(0,0) * m.rc(1,1) - m.rc(0,1) * m.rc(1,0);
if (upperLeftDet < 0) {
    std::swap(startPoint, stopPoint);  // 反转裁剪平面方向
}
```

### 片段覆盖率计算

`circular_arc_coverage_fn` 函数在片段着色器中计算最终覆盖率：

1. **圆边缘距离**：
   ```glsl
   float dist = length(circleEdge.xy) - 1.0;
   float outerCoverage = clamp(circleEdge.x - dist, 0.0, 1.0);
   float innerCoverage = clamp(dist - circleEdge.y, 0.0, 1.0);
   ```

2. **裁剪平面测试**：
   ```glsl
   float clipCoverage = clamp(dot(circleEdge.xy, clipPlane.xy) + clipPlane.z, 0.0, 1.0);
   ```

3. **交集/并集裁剪**：
   ```glsl
   float isectCoverage = clamp(dot(..., isectPlane), 0.0, 1.0);
   float unionCoverage = clamp(dot(..., unionPlane), 0.0, 1.0);
   ```

4. **圆头端点**：
   ```glsl
   float capCoverage0 = clamp(roundCapRadius - length(pos - roundCapPos.xy), 0.0, 1.0);
   float capCoverage1 = clamp(roundCapRadius - length(pos - roundCapPos.zw), 0.0, 1.0);
   ```

5. **合并所有覆盖率**。

## 依赖关系

### 直接依赖

- **RenderStep**：基类
- **DrawParams**：绘制参数
- **DrawWriter**：顶点写入器
- **StaticBufferManager**：静态缓冲区管理器
- **Shape**：几何形状抽象
- **SkArc**：圆弧数据结构
- **Transform**：坐标变换
- **PipelineDataGatherer**：管线数据收集器

### 依赖图

```
CircularArcRenderStep
    ├─> RenderStep (基类)
    ├─> DrawParams
    │   ├─> Geometry (Shape)
    │   │   └─> SkArc
    │   ├─> Transform
    │   ├─> StrokeStyle
    │   └─> DrawOrder
    ├─> DrawWriter
    ├─> StaticBufferManager
    │   └─> BindBufferInfo (静态顶点缓冲区)
    └─> PipelineDataGatherer
```

## 设计模式与设计决策

### 1. 模板方法模式
继承 `RenderStep` 基类，重写关键方法实现圆弧渲染的特定行为。

### 2. 实例化渲染模式
使用静态顶点模板结合动态实例属性，每个圆弧通过单个实例绘制。

### 3. GPU 驱动几何生成
将复杂的圆弧几何计算转移到 GPU 着色器，避免 CPU 端的曲线细分。

### 4. 设计决策

**为什么使用八边形模板？**
- 八边形能够很好地逼近圆形
- 顶点数量适中（18 个），平衡精度和性能
- 外接和内接设计支持填充和描边圆弧

**为什么在着色器中计算覆盖率？**
- 精确的抗锯齿需要亚像素级别的距离计算
- 避免 CPU 端复杂的几何细分
- 支持任意旋转和缩放而不失真

**为什么使用裁剪平面而非模板缓冲区？**
- 裁剪平面在片段着色器中实时计算，无需额外渲染 pass
- 支持平滑的抗锯齿边缘
- 减少内存带宽和状态切换

**为什么将变换矩阵作为实例属性？**
- 避免 uniform 更新的开销
- 支持在单次绘制调用中混合不同变换的圆弧
- 简化管线状态管理

**为什么支持圆头端点？**
- 提供与标准路径渲染一致的描边端点样式
- 通过距离场计算实现高质量抗锯齿

**为什么外扩半径 0.5 像素？**
- 确保抗锯齿区域完全覆盖在渲染边界内
- 简化着色器计算，圆边缘的 alpha 为 0 而非 0.5

## 性能考量

### 1. 实例化渲染
每个圆弧仅需单个实例，最小化绘制调用次数。

### 2. 静态顶点缓冲区
18 个顶点的八边形模板在所有圆弧间共享，一次分配终身使用。

### 3. 无 Uniform 依赖
所有数据通过实例属性传递，避免 uniform 更新和状态同步开销。

### 4. GPU 并行计算
圆弧的复杂几何计算在 GPU 上并行执行，充分利用硬件并行性。

### 5. 紧凑的实例数据
每个实例约 88 字节（11 个 float4），内存占用合理。

### 6. Early-Z 优化
使用 `kDirectDepthLessPass` 深度测试，利用 early-Z 剔除被遮挡的片段。

### 7. 边界框扩展
`kOutsetBoundsForAA` 标志确保边界框包含完整的抗锯齿区域，避免裁剪伪影。

### 8. 避免分支
裁剪平面逻辑通过 flags 参数和默认值设计，最小化着色器分支。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/gpu/graphite/Renderer.h` | RenderStep 基类定义 |
| `src/gpu/graphite/render/CommonDepthStencilSettings.h` | 通用深度模板配置 |
| `src/gpu/graphite/geom/Shape.h` | 几何形状抽象 |
| `include/core/SkArc.h` | 圆弧数据结构 |
| `src/gpu/graphite/geom/Transform.h` | 坐标变换封装 |
| `src/gpu/graphite/DrawParams.h` | 绘制参数封装 |
| `src/gpu/graphite/DrawWriter.h` | 顶点缓冲区写入器 |
| `src/gpu/graphite/BufferManager.h` | 缓冲区管理器 |
| `src/gpu/graphite/PipelineData.h` | 管线数据收集器 |
| `src/gpu/graphite/Attribute.h` | 顶点属性定义 |
| `src/gpu/BufferWriter.h` | 缓冲区写入工具 |
| `include/core/SkPaint.h` | 绘制样式定义 |
