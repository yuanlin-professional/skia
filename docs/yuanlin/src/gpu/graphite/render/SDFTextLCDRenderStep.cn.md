# SDFTextLCDRenderStep

> 源文件
> - `src/gpu/graphite/render/SDFTextLCDRenderStep.h`
> - `src/gpu/graphite/render/SDFTextLCDRenderStep.cpp`

## 概述

`SDFTextLCDRenderStep` 是 Skia Graphite 渲染管线中专门用于 LCD 次像素渲染的签名距离场（Signed Distance Field, SDF）文本渲染步骤类。该类继承自 `RenderStep`，实现了基于 SDF 技术的高质量 LCD 文本渲染，能够在保持矢量图形清晰度的同时，利用 LCD 屏幕的 RGB 子像素结构进一步提升文本边缘的锐利度和可读性。

SDF 文本渲染通过将字形轮廓转换为距离场纹理，在着色器中动态计算抗锯齿边缘，支持任意缩放而不失真。结合 LCD 次像素渲染技术，该类能够在水平或垂直方向上提供三倍于标准渲染的分辨率，显著改善文本的视觉质量，特别适用于小字号和高 DPI 显示设备。

## 架构位置

`SDFTextLCDRenderStep` 位于 Skia Graphite 图形管线的高级文本渲染子系统中：

```
skia/
├── src/gpu/graphite/
│   ├── Renderer.h                          // RenderStep 基类
│   ├── render/
│   │   ├── SDFTextLCDRenderStep.h         // SDF LCD 文本渲染步骤声明
│   │   ├── SDFTextLCDRenderStep.cpp       // SDF LCD 文本渲染步骤实现
│   │   ├── SDFTextRenderStep.h            // 标准 SDF 文本渲染
│   │   └── CommonDepthStencilSettings.h   // 通用深度模板配置
│   ├── text/
│   │   ├── TextAtlasManager.h             // 文本图集管理器
│   │   └── GlyphData.h                    // 字形数据
│   ├── PipelineData.h                      // 管线数据收集器
│   └── AtlasProvider.h                     // 图集提供者
├── src/text/gpu/
│   ├── DistanceFieldAdjustTable.h          // 距离场伽马调整表
│   ├── SubRunContainer.h                   // 文本子运行容器
│   └── VertexFiller.h                      // 顶点填充工具
```

该类是 SDF 文本渲染技术链的终端环节，与距离场图集生成、伽马校正和 LCD 子像素几何处理模块协同工作。

## 主要类与结构体

### SDFTextLCDRenderStep 类

```cpp
class SDFTextLCDRenderStep final : public RenderStep {
public:
    SDFTextLCDRenderStep(Layout);
    ~SDFTextLCDRenderStep() override;

    // 着色器代码生成
    std::string vertexSkSL() const override;
    std::string texturesAndSamplersSkSL(const ResourceBindingRequirements&,
                                        int* nextBindingIndex) const override;
    const char* fragmentCoverageSkSL() const override;

    // 数据写入
    void writeVertices(DrawWriter*, const DrawParams&, uint32_t ssboIndex) const override;
    void writeUniformsAndTextures(const DrawParams&, PipelineDataGatherer*) const override;
};
```

**关键特性：**
- **LCD 次像素覆盖率**：使用 `Flags::kLCDCoverage` 标志启用 RGB 子像素分离渲染
- **距离场采样**：使用线性插值从 SDF 图集纹理采样
- **伽马校正**：根据背景亮度动态调整距离场阈值
- **像素几何感知**：支持水平/垂直、RGB/BGR 子像素排列

### 渲染标志

```cpp
Flags::kPerformsShading |     // 执行着色计算
Flags::kHasTextures |         // 使用纹理采样
Flags::kEmitsCoverage |       // 输出覆盖率
Flags::kLCDCoverage |         // LCD 次像素覆盖率
Flags::kAppendInstances       // 实例化渲染
```

### 顶点属性结构

每个字形实例包含以下属性：
```cpp
{
    {"size", VertexAttribType::kUShort2},              // 字形尺寸
    {"uvPos", VertexAttribType::kUShort2},             // 图集 UV 起始位置
    {"xyPos", VertexAttribType::kFloat2},              // 屏幕空间位置
    {"indexAndFlags", VertexAttribType::kUShort2},     // 纹理索引和标志
    {"strikeToSourceScale", VertexAttribType::kFloat}, // 缩放比例
    {"depth", VertexAttribType::kFloat},               // 深度值
    {"ssboIndex", VertexAttribType::kUInt}             // SSBO 索引
}
```

### Uniform 变量

```cpp
{
    {"subRunDeviceMatrix", SkSLType::kFloat4x4},    // 设备空间变换矩阵
    {"deviceToLocal", SkSLType::kFloat4x4},         // 设备到局部坐标变换
    {"atlasSizeInv", SkSLType::kFloat2},            // 图集尺寸倒数
    {"pixelGeometryDelta", SkSLType::kHalf2},       // 子像素偏移量
    {"gammaParams", SkSLType::kHalf4}               // 伽马校正参数
}
```

### Varying 变量

```cpp
{
    {"unormTexCoords", SkSLType::kFloat2},  // 未归一化纹理坐标
    {"textureCoords", SkSLType::kFloat2},   // 归一化纹理坐标
    {"texIndex", SkSLType::kFloat}          // 纹理索引
}
```

## 公共 API 函数

### 构造与析构

```cpp
SDFTextLCDRenderStep(Layout layout);
```
创建 SDF LCD 文本渲染步骤实例。

**配置**：
- 渲染步骤 ID：`RenderStepID::kSDFTextLCD`
- 图元类型：`PrimitiveType::kTriangleStrip`（三角形带）
- 深度模板：`kDirectDepthLEqualPass`（直接深度测试）

### vertexSkSL()

```cpp
std::string vertexSkSL() const override;
```
生成顶点着色器的 SkSL 代码主体。

**着色器逻辑**：
```glsl
texIndex = half(indexAndFlags.x);
float4 devPosition = text_vertex_fn(
    float2(sk_VertexID >> 1, sk_VertexID & 1),  // 顶点位置解码
    subRunDeviceMatrix,                          // 变换矩阵
    deviceToLocal,                               // 逆变换
    atlasSizeInv,                                // 纹理坐标归一化
    float2(size),                                // 字形尺寸
    float2(uvPos),                               // UV 起始位置
    xyPos,                                       // 屏幕位置
    strikeToSourceScale,                         // 缩放因子
    depth,                                       // 深度值
    textureCoords,                               // 输出：归一化纹理坐标
    unormTexCoords,                              // 输出：未归一化纹理坐标
    stepLocalCoords                              // 输出：局部坐标
);
```

**功能**：
1. 提取纹理索引到 `texIndex` varying 变量
2. 调用 `text_vertex_fn` 内置函数生成四边形顶点
3. 同时输出归一化和未归一化纹理坐标（用于不同的片段着色器计算）

### texturesAndSamplersSkSL()

```cpp
std::string texturesAndSamplersSkSL(const ResourceBindingRequirements& bindingReqs,
                                    int* nextBindingIndex) const override;
```
生成 SDF 图集纹理采样器的 SkSL 声明代码。

**生成代码**：
```glsl
layout(...) sampler2D sdf_atlas_0;
layout(...) sampler2D sdf_atlas_1;
layout(...) sampler2D sdf_atlas_2;
layout(...) sampler2D sdf_atlas_3;
```

固定生成 4 个 SDF 图集采样器声明。

### fragmentCoverageSkSL()

```cpp
const char* fragmentCoverageSkSL() const override;
```
返回片段着色器的覆盖率计算代码。

**着色器代码**：
```glsl
outputCoverage = sdf_text_lcd_coverage_fn(
    textureCoords,         // 归一化纹理坐标
    pixelGeometryDelta,    // 子像素偏移
    gammaParams,           // 伽马校正参数
    unormTexCoords,        // 未归一化纹理坐标
    texIndex,              // 纹理索引
    sdf_atlas_0,           // SDF 图集纹理
    sdf_atlas_1,
    sdf_atlas_2,
    sdf_atlas_3
);
```

**功能**：调用 `sdf_text_lcd_coverage_fn` 内置函数计算 LCD 子像素覆盖率。

### writeVertices()

```cpp
void writeVertices(DrawWriter* dw, const DrawParams& params,
                   uint32_t ssboIndex) const override;
```
将字形实例数据写入 GPU 缓冲区。

**实现**：委托给 `GlyphData::fillInstanceData()` 方法，填充顶点属性数据。

**参数**：
- `dw`：绘制写入器
- `params`：绘制参数（包含 `SubRunData`）
- `ssboIndex`：着色器存储缓冲对象索引

### writeUniformsAndTextures()

```cpp
void writeUniformsAndTextures(const DrawParams& params,
                              PipelineDataGatherer* gatherer) const override;
```
向管线数据收集器写入 uniform 变量和纹理资源。

**实现流程**：
1. 写入变换矩阵相关 uniform
2. 计算并写入像素几何偏移量
3. 计算并写入伽马校正参数
4. 添加 SDF 图集纹理和采样器

## 内部实现细节

### 像素几何偏移计算

根据屏幕的子像素排列方式计算偏移向量：

```cpp
SkV2 pixelGeometryDelta = {0, 0};

// 水平子像素排列（RGB 或 BGR）
if (SkPixelGeometryIsH(pixelGeometry)) {
    pixelGeometryDelta = {1.f/(3*atlasWidth), 0};
}
// 垂直子像素排列
else if (SkPixelGeometryIsV(pixelGeometry)) {
    pixelGeometryDelta = {0, 1.f/(3*atlasHeight)};
}

// BGR 排列需要反向偏移
if (SkPixelGeometryIsBGR(pixelGeometry)) {
    pixelGeometryDelta = -pixelGeometryDelta;
}
```

**偏移量含义**：
- 水平排列：在 U 方向偏移 1/3 像素宽度
- 垂直排列：在 V 方向偏移 1/3 像素高度
- BGR 反向：蓝色子像素在左侧，需要负向偏移

**用途**：片段着色器中分别采样 R、G、B 三个子像素位置的距离场值，计算独立的覆盖率。

### 伽马校正参数计算

根据背景亮度调整距离场阈值，补偿人眼对不同亮度的感知差异：

```cpp
auto dfAdjustTable = DistanceFieldAdjustTable::Get();

float redCorrection = dfAdjustTable->getAdjustment(
    SkColorGetR(luminanceColor),
    useGammaCorrectDistanceTable
);
float greenCorrection = dfAdjustTable->getAdjustment(
    SkColorGetG(luminanceColor),
    useGammaCorrectDistanceTable
);
float blueCorrection = dfAdjustTable->getAdjustment(
    SkColorGetB(luminanceColor),
    useGammaCorrectDistanceTable
);

SkV4 gammaParams = {
    redCorrection,
    greenCorrection,
    blueCorrection,
    useGammaCorrectDistanceTable ? 1.f : 0.f  // 标志位
};
```

**原理**：
- 暗色背景：文本需要更粗（较低的距离场阈值）
- 亮色背景：文本需要更细（较高的距离场阈值）
- 每个 RGB 通道独立调整，适配不同的亮度

### SDF 覆盖率计算原理

片段着色器中的 `sdf_text_lcd_coverage_fn` 函数执行以下步骤：

1. **三次子像素采样**：
   ```glsl
   float distR = sample_sdf(texCoords - pixelGeometryDelta);  // 红色子像素
   float distG = sample_sdf(texCoords);                       // 绿色子像素
   float distB = sample_sdf(texCoords + pixelGeometryDelta);  // 蓝色子像素
   ```

2. **距离场转换为覆盖率**：
   ```glsl
   float coverageR = smoothstep(0.5 - gammaR, 0.5 + gammaR, distR);
   float coverageG = smoothstep(0.5 - gammaG, 0.5 + gammaG, distG);
   float coverageB = smoothstep(0.5 - gammaB, 0.5 + gammaG, distB);
   ```

3. **打包为 LCD 覆盖率**：
   ```glsl
   outputCoverage = half4(coverageR, coverageG, coverageB, 1.0);
   ```

### 纹理采样配置

使用线性过滤（`kLinear`）而非最近邻插值：

```cpp
gatherer->add(proxies[i], {SkFilterMode::kLinear, SkTileMode::kClamp});
```

**原因**：
- SDF 纹理存储距离值，需要平滑插值
- 线性插值提供亚像素级别的精度
- 支持任意缩放而不产生阶梯状伪影

### 图集槽位填充策略

确保始终绑定 4 个纹理采样器：

```cpp
for (unsigned int i = numProxies; i < kNumSDFAtlasTextures; ++i) {
    gatherer->add(proxies[0], {SkFilterMode::kLinear, SkTileMode::kClamp});
}
```

未使用的槽位复用第一个纹理，避免着色器动态分支。

## 依赖关系

### 直接依赖

- **RenderStep**：基类，定义渲染步骤接口
- **DrawParams**：封装绘制参数
- **DrawWriter**：管理顶点缓冲区写入
- **PipelineDataGatherer**：收集管线数据
- **SubRunData**：文本子运行数据
- **GlyphData**：字形后端数据
- **TextAtlasManager**：SDF 图集管理器
- **DistanceFieldAdjustTable**：距离场伽马调整表
- **TextureProxy**：纹理代理

### 间接依赖

- **VertexFiller**：顶点数据填充工具
- **Transform**：变换矩阵封装
- **Recorder**：绘制命令记录器
- **AtlasProvider**：图集提供者

### 依赖图

```
SDFTextLCDRenderStep
    ├─> RenderStep (基类)
    ├─> DrawParams
    │   ├─> Geometry (SubRunData)
    │   │   └─> PixelGeometry
    │   ├─> Transform
    │   └─> DrawOrder
    ├─> DrawWriter
    ├─> PipelineDataGatherer
    ├─> TextAtlasManager
    │   └─> TextureProxy (SDF 图集纹理)
    ├─> GlyphData
    │   └─> VertexFiller
    └─> DistanceFieldAdjustTable (伽马校正查找表)
```

## 设计模式与设计决策

### 1. 模板方法模式（Template Method Pattern）
继承 `RenderStep` 基类，重写关键方法实现 SDF LCD 渲染的特定行为。

### 2. 策略模式（Strategy Pattern）
通过 `PixelGeometry` 枚举支持多种子像素排列策略（水平 RGB、水平 BGR、垂直等）。

### 3. 代码生成模式
动态生成 SkSL 着色器代码，根据平台绑定需求调整资源布局。

### 4. 设计决策

**为什么使用 SDF 技术？**
- 传统位图文本在缩放时会模糊或锯齿
- SDF 将字形轮廓编码为距离场，支持任意缩放
- 单一 SDF 纹理可处理多个字号，节省内存

**为什么需要 LCD 次像素渲染？**
- 标准抗锯齿在水平方向分辨率有限
- LCD 屏幕的 RGB 子像素可提供 3 倍水平分辨率
- 显著提升小字号文本的可读性和锐利度

**为什么同时传递归一化和未归一化纹理坐标？**
- 归一化坐标用于标准纹理采样
- 未归一化坐标用于计算子像素偏移（需要以像素为单位）

**为什么需要伽马校正？**
- 人眼对亮度的感知是非线性的
- 未校正的 SDF 渲染在不同背景下会显得过粗或过细
- 查找表提供预计算的校正值，避免复杂的 GPU 计算

**为什么使用线性插值而非最近邻？**
- 距离场是连续的距离值，而非离散的颜色
- 线性插值提供亚像素级精度
- 支持高质量的缩放和旋转

**为什么固定 4 个纹理槽位？**
- 避免着色器动态分支导致的性能损失
- 简化着色器编译和管线状态管理
- 4 个图集足以容纳大部分场景的字形

## 性能考量

### 1. 实例化渲染
使用 `Flags::kAppendInstances` 启用实例化，单次绘制调用可渲染大量字形，最小化 CPU 开销。

### 2. 紧凑的顶点格式
- 使用 `UShort2` 存储尺寸和 UV 坐标（4 字节）
- 每个顶点仅 24 字节，减少内存带宽

### 3. 线性纹理插值
使用 GPU 硬件线性插值，无需在片段着色器中手动计算双线性插值，提升性能。

### 4. 预计算伽马调整表
`DistanceFieldAdjustTable` 提供预计算的伽马校正值，避免复杂的指数运算。

### 5. 子像素偏移优化
偏移量在 CPU 端计算一次并作为 uniform 传递，避免在每个片段中重复计算。

### 6. Half 精度 Uniform
`pixelGeometryDelta` 和 `gammaParams` 使用 `half` 类型（16 位浮点），减少 uniform 缓冲区大小和带宽。

### 7. 图集批处理
将多个字形打包到少量 SDF 图集中，减少纹理切换和状态变更。

### 8. Early-Z 优化
使用 `kDirectDepthLEqualPass` 深度测试模式，利用 early-Z 剔除被遮挡的片段，减少着色器执行次数。

### 9. 内存访问模式
顶点属性按照 GPU 对齐要求排列，最大化缓存命中率。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/gpu/graphite/Renderer.h` | RenderStep 基类定义 |
| `src/gpu/graphite/render/SDFTextRenderStep.h` | 标准 SDF 文本渲染（非 LCD） |
| `src/gpu/graphite/render/BitmapTextRenderStep.h` | 位图文本渲染 |
| `src/gpu/graphite/render/CommonDepthStencilSettings.h` | 通用深度模板配置 |
| `src/gpu/graphite/text/TextAtlasManager.h` | SDF 图集管理器 |
| `src/gpu/graphite/text/GlyphData.h` | 字形数据结构 |
| `src/text/gpu/DistanceFieldAdjustTable.h` | 伽马校正查找表 |
| `src/text/gpu/SubRunContainer.h` | 文本子运行容器 |
| `src/text/gpu/VertexFiller.h` | 顶点填充工具 |
| `src/gpu/graphite/DrawParams.h` | 绘制参数封装 |
| `src/gpu/graphite/DrawWriter.h` | 顶点缓冲区写入器 |
| `src/gpu/graphite/PipelineData.h` | 管线数据收集器 |
| `src/gpu/graphite/geom/SubRunData.h` | 文本子运行数据 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/gpu/graphite/AtlasProvider.h` | 图集提供者 |
| `src/gpu/graphite/ContextUtils.h` | 上下文工具函数 |
| `include/core/SkSurfaceProps.h` | 像素几何定义 |
