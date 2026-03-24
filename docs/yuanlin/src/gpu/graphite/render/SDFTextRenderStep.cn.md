# SDFTextRenderStep

> 源文件: `src/gpu/graphite/render/SDFTextRenderStep.h`, `src/gpu/graphite/render/SDFTextRenderStep.cpp`

## 概述

`SDFTextRenderStep` 是 Skia Graphite 中用于渲染有向距离场（Signed Distance Field, SDF）文本的 `RenderStep` 实现。SDF 文本技术允许在任意缩放级别下保持文本边缘的清晰度，相比位图文本具有更好的缩放性能。此步骤处理单通道（非 LCD）SDF 文本渲染，支持最多 4 张图集纹理，并可选地应用伽马校正。

## 架构位置

- **上层**: 由 `RendererProvider` 创建，存储在 `fSDFText[false]`（非 LCD 变体）
- **基类**: 继承自 `RenderStep`
- **协作**: 与 `TextAtlasManager` 协同管理 SDF 图集纹理
- **姊妹类**: `SDFTextLCDRenderStep` 处理 LCD 子像素渲染变体

## 主要类与结构体

### `SDFTextRenderStep` 类

**RenderStepID**: `kSDFText`

**标志**: `kPerformsShading | kHasTextures | kEmitsCoverage | kAppendInstances`

**图元类型**: 三角形带（`kTriangleStrip`），每个字形使用 `sk_VertexID` 生成 4 个顶点

**Uniform 变量**:
| 名称 | 类型 | 描述 |
|------|------|------|
| `subRunDeviceMatrix` | `float4x4` | 子运行的设备变换矩阵 |
| `deviceToLocal` | `float4x4` | 设备到局部空间的逆变换 |
| `atlasSizeInv` | `float2` | 图集纹理尺寸的倒数 |
| `gammaParams` | `half2` | 伽马校正参数 |

**实例属性**:
| 名称 | 类型 | 描述 |
|------|------|------|
| `size` | `ushort2` | 字形尺寸 |
| `uvPos` | `ushort2` | 图集中的纹理坐标 |
| `xyPos` | `float2` | 字形位置 |
| `indexAndFlags` | `ushort2` | 纹理索引和标志 |
| `strikeToSourceScale` | `float` | 字形缩放因子 |
| `depth` | `float` | 深度值 |
| `ssboIndex` | `uint` | SSBO 索引 |

**Varying 变量**: `unormTexCoords`（float2）, `textureCoords`（float2）, `texIndex`（float）

## 公共 API 函数

- **`SDFTextRenderStep(Layout)`** — 构造函数
- **`vertexSkSL()`** — 生成调用 `text_vertex_fn()` 的顶点着色器代码
- **`texturesAndSamplersSkSL(...)`** — 声明 4 个 SDF 图集纹理采样器
- **`fragmentCoverageSkSL()`** — 生成调用 `sdf_text_coverage_fn()` 的片段覆盖率代码
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 通过 GlyphData 写入字形实例数据
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 写入 uniform 和绑定图集纹理

## 内部实现细节

### 顶点生成

使用 `sk_VertexID` 和三角形带图元在顶点着色器中生成字形四边形，避免了显式的顶点缓冲区分配。`text_vertex_fn()` 辅助函数处理从实例数据到设备空间位置的变换。

### 纹理管理

系统支持最多 4 张 SDF 图集纹理（`kNumSDFAtlasTextures = 4`）。每个字形通过 `indexAndFlags.x` 指定其所在的纹理索引。在 `writeUniformsAndTextures()` 中，如果实际图集纹理数少于 4，则用第一张纹理填充剩余的采样器槽位。

### 伽马校正

在定义了 `SK_GAMMA_APPLY_TO_A8` 时，使用 `DistanceFieldAdjustTable` 根据亮度值计算伽马调整系数。这个调整值和伽马校正表标志一起作为 `gammaParams` uniform 传递给着色器。

### 片段着色器

`sdf_text_coverage_fn()` 函数：
1. 从图集纹理中采样距离场值
2. 根据未归一化纹理坐标计算屏幕空间梯度
3. 应用伽马调整后计算覆盖率

使用 `sample_indexed_atlas()` 辅助函数根据纹理索引从 4 个图集纹理之一进行采样。

## 依赖关系

- `TextAtlasManager` — 管理 SDF 图集纹理的创建和分配
- `SubRunData` / `GlyphData` — 提供字形实例数据
- `VertexFiller` — 填充字形顶点数据
- `DistanceFieldAdjustTable`（条件依赖）— 伽马校正查找表
- `AtlasProvider` — 图集提供者

## 设计模式与设计决策

### 实例化渲染

每个字形作为一个实例绘制，共享三角形带的顶点着色器逻辑。这种设计最大化了批处理效率。

### 多纹理图集

支持 4 张图集纹理以容纳大量字形，同时所有采样器始终绑定（不足时复用第一张），避免着色器变体。

### SDF vs 位图

SDF 文本适用于需要缩放的场景。距离场在较大缩放范围内保持质量，而位图文本仅在原始尺寸附近效果最佳。

## 性能考量

- **实例化绘制**: 大量字形通过单次绘制调用处理
- **线性采样**: 图集纹理使用线性过滤，利用双线性插值提升 SDF 采样质量
- **最小顶点数据**: 使用 `sk_VertexID` 替代显式顶点缓冲区
- **伽马预计算**: 伽马调整值在 CPU 侧查表获得，着色器中只需简单的标量运算

## 相关文件

- `src/gpu/graphite/render/SDFTextLCDRenderStep.h` — LCD 变体
- `src/gpu/graphite/text/TextAtlasManager.h` — 文本图集管理
- `src/gpu/graphite/text/GlyphData.h` — 字形数据
- `src/text/gpu/SubRunContainer.h` — 子运行容器
- `src/text/gpu/VertexFiller.h` — 顶点填充器
- `src/text/gpu/DistanceFieldAdjustTable.h` — 距离场调整表
