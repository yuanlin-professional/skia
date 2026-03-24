# BitmapTextRenderStep

> 源文件
> - `src/gpu/graphite/render/BitmapTextRenderStep.h`
> - `src/gpu/graphite/render/BitmapTextRenderStep.cpp`

## 概述

`BitmapTextRenderStep` 是 Skia Graphite 渲染管线中专门负责位图文本渲染的渲染步骤类。该类继承自 `RenderStep`，用于处理使用位图字形图集渲染的文本内容。它支持三种不同的遮罩格式：灰度遮罩（A8）、LCD次像素渲染（A565）和彩色表情符号（ARGB），每种格式对应不同的渲染变体，能够高效地将文本字形从图集纹理采样并渲染到目标表面。

该类的核心职责包括生成顶点着色器和片段着色器的 SkSL 代码、管理顶点数据的写入、配置纹理采样器以及处理 uniform 变量。通过实例化渲染（instanced rendering）技术，`BitmapTextRenderStep` 可以在单次绘制调用中渲染大量字形，显著提升文本渲染性能。

## 架构位置

`BitmapTextRenderStep` 位于 Skia Graphite 图形管线的渲染层，具体结构如下：

```
skia/
├── src/gpu/graphite/
│   ├── Renderer.h              // RenderStep 基类
│   ├── render/
│   │   ├── BitmapTextRenderStep.h     // 位图文本渲染步骤声明
│   │   └── BitmapTextRenderStep.cpp   // 位图文本渲染步骤实现
│   ├── text/
│   │   ├── TextAtlasManager.h         // 文本图集管理器
│   │   └── GlyphData.h                // 字形数据
│   ├── DrawParams.h                    // 绘制参数
│   ├── PipelineData.h                  // 管线数据收集器
│   └── AtlasProvider.h                 // 图集提供者
```

该类作为文本渲染子系统的核心组件，与文本图集管理器、字形数据结构和管线数据收集器紧密协作，负责将 CPU 端的字形数据转换为 GPU 可渲染的几何数据。

## 主要类与结构体

### BitmapTextRenderStep 类

```cpp
class BitmapTextRenderStep final : public RenderStep {
public:
    BitmapTextRenderStep(Layout, skgpu::MaskFormat variant);
    ~BitmapTextRenderStep() override;

    // 着色器代码生成
    std::string vertexSkSL() const override;
    std::string texturesAndSamplersSkSL(const ResourceBindingRequirements&,
                                        int* nextBindingIndex) const override;
    const char* fragmentColorSkSL() const override;
    const char* fragmentCoverageSkSL() const override;
    bool usesUniformsInFragmentSkSL() const override;

    // 数据写入
    void writeVertices(DrawWriter*, const DrawParams&, uint32_t ssboIndex) const override;
    void writeUniformsAndTextures(const DrawParams&, PipelineDataGatherer*) const override;

private:
    static SkEnumBitMask<Flags> Flags(skgpu::MaskFormat);
};
```

**关键特性：**
- **变体支持**：通过 `skgpu::MaskFormat` 枚举支持三种渲染变体
- **着色器生成**：动态生成适配不同遮罩格式的 SkSL 着色器代码
- **实例化渲染**：使用附加属性（append attributes）支持实例化绘制
- **纹理管理**：支持最多 4 个文本图集纹理的并发访问

### 渲染变体类型

```cpp
enum class MaskFormat : int {
    kA8,    // 灰度遮罩（单通道 alpha）
    kA565,  // LCD 次像素遮罩（用于 LCD 文本渲染）
    kARGB   // 全彩色遮罩（用于彩色表情符号）
};
```

对应的渲染步骤 ID：
- `kBitmapText_Mask`：灰度文本渲染
- `kBitmapText_LCD`：LCD 次像素文本渲染
- `kBitmapText_Color`：彩色文本/表情符号渲染

### 顶点属性结构

每个字形实例包含以下属性：
```cpp
{
    {"size", VertexAttribType::kUShort2},              // 字形尺寸（像素）
    {"uvPos", VertexAttribType::kUShort2},             // 图集中的 UV 坐标
    {"xyPos", VertexAttribType::kFloat2},              // 屏幕空间位置
    {"indexAndFlags", VertexAttribType::kUShort2},     // 纹理索引和标志位
    {"strikeToSourceScale", VertexAttribType::kFloat}, // 缩放比例
    {"depth", VertexAttribType::kFloat},               // 深度值
    {"ssboIndex", VertexAttribType::kUInt}             // SSBO 索引
}
```

### Uniform 变量

```cpp
{
    {"subRunDeviceMatrix", SkSLType::kFloat4x4},  // 设备空间变换矩阵
    {"deviceToLocal", SkSLType::kFloat4x4},       // 设备到局部坐标变换
    {"atlasSizeInv", SkSLType::kFloat2}           // 图集尺寸倒数（用于纹理坐标归一化）
}
```

## 公共 API 函数

### 构造与析构

```cpp
BitmapTextRenderStep(Layout layout, skgpu::MaskFormat variant);
```
- 创建指定布局和遮罩格式的位图文本渲染步骤
- 根据遮罩格式自动配置渲染标志和管线状态

### 着色器代码生成接口

#### vertexSkSL()
```cpp
std::string vertexSkSL() const override;
```
生成顶点着色器的 SkSL 代码主体。该函数调用 `text_vertex_fn` 内置函数，将字形的实例属性转换为屏幕空间的设备坐标和纹理坐标。

**返回值**：包含顶点变换逻辑的 SkSL 代码字符串。

#### texturesAndSamplersSkSL()
```cpp
std::string texturesAndSamplersSkSL(const ResourceBindingRequirements& bindingReqs,
                                    int* nextBindingIndex) const override;
```
生成纹理和采样器的 SkSL 声明代码。固定生成 4 个纹理采样器（`text_atlas_0` 到 `text_atlas_3`）的声明语句。

**参数**：
- `bindingReqs`：资源绑定需求（平台相关）
- `nextBindingIndex`：下一个可用的绑定索引（输入/输出参数）

#### fragmentColorSkSL()
```cpp
const char* fragmentColorSkSL() const override;
```
返回用于彩色文本（ARGB 遮罩格式）的片段着色器代码。直接从图集纹理采样颜色值并赋给 `primitiveColor`。

#### fragmentCoverageSkSL()
```cpp
const char* fragmentCoverageSkSL() const override;
```
返回用于灰度和 LCD 文本的片段着色器代码。调用 `bitmap_text_coverage_fn` 函数处理采样结果，将遮罩值转换为覆盖率（coverage）。

### 数据写入接口

#### writeVertices()
```cpp
void writeVertices(DrawWriter* dw, const DrawParams& params,
                   uint32_t ssboIndex) const override;
```
将字形的顶点实例数据写入 GPU 缓冲区。

**实现流程**：
1. 从 `DrawParams` 中提取 `SubRunData`（子运行数据）
2. 获取关联的 `GlyphData` 后端数据
3. 调用 `GlyphData::fillInstanceData()` 填充实例缓冲区

**参数**：
- `dw`：绘制写入器（管理顶点缓冲区）
- `params`：绘制参数（包含几何、变换等信息）
- `ssboIndex`：着色器存储缓冲对象索引

#### writeUniformsAndTextures()
```cpp
void writeUniformsAndTextures(const DrawParams& params,
                              PipelineDataGatherer* gatherer) const override;
```
向管线数据收集器写入 uniform 变量和纹理资源。

**实现流程**：
1. 写入三个 uniform 变量：变换矩阵、局部坐标变换、图集尺寸倒数
2. 从 `TextAtlasManager` 获取活跃的图集纹理代理
3. 添加纹理代理及其采样参数到收集器
4. 如果活跃纹理少于 4 个，用第一个纹理填充剩余槽位

## 内部实现细节

### 渲染标志配置

`Flags()` 静态函数根据遮罩格式返回对应的渲染标志：

```cpp
SkEnumBitMask<RenderStep::Flags> BitmapTextRenderStep::Flags(skgpu::MaskFormat variant) {
    switch (variant) {
        case MaskFormat::kA8:
            return Flags::kPerformsShading | Flags::kHasTextures | Flags::kEmitsCoverage;
        case MaskFormat::kA565:
            return Flags::kPerformsShading | Flags::kHasTextures | Flags::kEmitsCoverage |
                   Flags::kLCDCoverage;
        case MaskFormat::kARGB:
            return Flags::kPerformsShading | Flags::kHasTextures | Flags::kEmitsPrimitiveColor;
    }
}
```

**标志含义**：
- `kPerformsShading`：执行着色计算
- `kHasTextures`：使用纹理采样
- `kEmitsCoverage`：输出覆盖率（用于混合）
- `kLCDCoverage`：使用 LCD 次像素覆盖率
- `kEmitsPrimitiveColor`：输出原始颜色（用于彩色表情符号）

### 顶点着色器逻辑

顶点着色器调用 `text_vertex_fn` 内置函数，该函数根据 `sk_VertexID` 生成四边形的四个顶点：

```cpp
float4 devPosition = text_vertex_fn(
    float2(sk_VertexID >> 1, sk_VertexID & 1),  // 顶点在四边形中的位置 (0,0) 到 (1,1)
    subRunDeviceMatrix,                          // 设备空间变换
    deviceToLocal,                               // 逆变换（用于计算局部坐标）
    atlasSizeInv,                                // 纹理坐标归一化系数
    float2(size),                                // 字形尺寸
    float2(uvPos),                               // 图集 UV 起始位置
    xyPos,                                       // 屏幕空间位置
    strikeToSourceScale,                         // 缩放比例
    depth,                                       // 深度值
    textureCoords,                               // 输出：纹理坐标
    unormTexCoords,                              // 输出：未归一化纹理坐标
    stepLocalCoords                              // 输出：局部坐标
);
```

**顶点 ID 编码**：使用 `TriangleStrip` 图元类型，通过位运算从 `sk_VertexID` 解码顶点位置，自动生成四边形的四个角。

### 片段着色器逻辑

#### 彩色文本路径
```cpp
primitiveColor = sample_indexed_atlas(textureCoords, int(texIndex),
                                      text_atlas_0, text_atlas_1,
                                      text_atlas_2, text_atlas_3);
```
直接使用 `sample_indexed_atlas` 函数从指定索引的图集纹理采样 RGBA 颜色值。

#### 遮罩文本路径
```cpp
outputCoverage = bitmap_text_coverage_fn(
    sample_indexed_atlas(textureCoords, int(texIndex),
                         text_atlas_0, text_atlas_1,
                         text_atlas_2, text_atlas_3),
    int(maskFormat)
);
```
采样遮罩值后，调用 `bitmap_text_coverage_fn` 根据遮罩格式处理覆盖率：
- **A8 格式**：直接使用 alpha 通道作为覆盖率
- **A565 格式**：将 RGB 三个通道分别作为 LCD 子像素的覆盖率

### 纹理槽位填充策略

代码确保始终绑定 4 个纹理采样器，即使活跃图集纹理少于 4 个：

```cpp
for (unsigned int i = numProxies; i < kNumTextAtlasTextures; ++i) {
    gatherer->add(proxies[0], {SkFilterMode::kNearest, SkTileMode::kClamp});
}
```

这种设计避免了着色器编译时的分支逻辑，统一使用固定数量的采样器，未使用的槽位复用第一个纹理。

## 依赖关系

### 直接依赖

- **RenderStep**：基类，定义渲染步骤接口
- **DrawParams**：封装绘制参数（几何、变换、绘制顺序）
- **DrawWriter**：管理顶点缓冲区写入
- **PipelineDataGatherer**：收集管线所需的 uniform 和纹理资源
- **SubRunData**：文本子运行数据，包含字形索引范围和变换
- **GlyphData**：字形后端数据，提供实例数据填充接口
- **TextAtlasManager**：管理文本图集纹理的生命周期和分配
- **TextureProxy**：纹理代理对象，延迟纹理资源创建

### 间接依赖

- **AtlasSubRun**：图集子运行容器
- **VertexFiller**：顶点数据填充工具
- **Transform**：变换矩阵封装
- **Recorder**：记录绘制命令的上下文对象

### 依赖图

```
BitmapTextRenderStep
    ├─> RenderStep (基类)
    ├─> DrawParams
    │   ├─> Geometry (SubRunData)
    │   ├─> Transform
    │   └─> DrawOrder
    ├─> DrawWriter
    ├─> PipelineDataGatherer
    ├─> TextAtlasManager
    │   └─> TextureProxy
    └─> GlyphData
        └─> VertexFiller
```

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）
通过 `skgpu::MaskFormat` 枚举实现不同遮罩格式的渲染策略。每种格式对应不同的着色器代码和渲染标志，但共享相同的接口和核心逻辑。

### 2. 模板方法模式（Template Method Pattern）
`RenderStep` 基类定义渲染步骤的执行框架，`BitmapTextRenderStep` 重写关键方法实现特定行为，如 `vertexSkSL()`、`writeVertices()` 等。

### 3. 代码生成模式
动态生成 SkSL 着色器代码而非使用静态着色器文件，提高灵活性和可维护性。着色器代码可根据运行时配置（如纹理数量、绑定索引）动态调整。

### 4. 资源延迟绑定
使用 `TextureProxy` 实现纹理资源的延迟创建和绑定，优化资源管理和内存占用。

### 5. 设计决策

**使用三角形带（TriangleStrip）图元类型**：
- 每个字形实例生成 4 个顶点（通过 `sk_VertexID` 解码）
- 相比三角形列表减少 33% 的顶点数据
- 顶点着色器中使用位运算 `(sk_VertexID >> 1, sk_VertexID & 1)` 高效计算顶点位置

**固定 4 个纹理槽位**：
- 避免着色器动态分支导致的性能损失
- 简化纹理索引逻辑
- 未使用的槽位填充相同纹理不会显著增加内存开销

**分离颜色和覆盖率路径**：
- `fragmentColorSkSL()` 用于彩色文本
- `fragmentCoverageSkSL()` 用于灰度和 LCD 文本
- 允许不同的混合模式和管线状态优化

## 性能考量

### 1. 实例化渲染
使用 `Flags::kAppendInstances` 标志启用实例化渲染，单次绘制调用可渲染大量字形，显著减少 CPU 开销和 GPU 状态切换。

### 2. 图集批处理
将多个字形打包到少量纹理图集中（最多 4 个），减少纹理绑定切换次数。通过 `indexAndFlags` 属性动态索引纹理，无需拆分绘制批次。

### 3. 顶点属性压缩
使用紧凑的数据类型减少内存带宽：
- `UShort2` 存储字形尺寸和 UV 坐标（16 位整数）
- `Float2` 仅用于需要高精度的位置信息

### 4. Uniform 缓存优化
变换矩阵和图集尺寸等 uniform 变量在多个字形间共享，减少 uniform 更新频率。

### 5. 深度测试优化
使用 `kDirectDepthLEqualPass` 深度模板设置，利用 early-Z 测试减少片段着色器执行次数，提升填充率（fill rate）。

### 6. 采样器配置
使用 `kNearest` 过滤模式和 `kClamp` 平铺模式，避免不必要的纹理过滤计算，保证像素级精度的文本渲染。

### 7. 内存布局
顶点属性按照 GPU 对齐要求紧密排列，最小化缓冲区大小和缓存未命中率。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/gpu/graphite/Renderer.h` | RenderStep 基类定义 |
| `src/gpu/graphite/render/CommonDepthStencilSettings.h` | 通用深度模板配置 |
| `src/gpu/graphite/text/TextAtlasManager.h` | 文本图集管理器 |
| `src/gpu/graphite/text/GlyphData.h` | 字形数据结构 |
| `src/gpu/graphite/DrawParams.h` | 绘制参数封装 |
| `src/gpu/graphite/DrawWriter.h` | 顶点缓冲区写入器 |
| `src/gpu/graphite/PipelineData.h` | 管线数据收集器 |
| `src/gpu/graphite/geom/SubRunData.h` | 文本子运行数据 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/gpu/graphite/AtlasProvider.h` | 图集提供者 |
| `src/text/gpu/SubRunContainer.h` | 子运行容器 |
| `src/text/gpu/VertexFiller.h` | 顶点填充工具 |
| `src/gpu/graphite/ContextUtils.h` | 上下文工具函数 |
| `src/gpu/graphite/Attribute.h` | 顶点属性定义 |
| `src/core/SkSLTypeShared.h` | SkSL 类型定义 |
