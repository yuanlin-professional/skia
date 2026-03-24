# CoverageMaskRenderStep

> 源文件: `src/gpu/graphite/render/CoverageMaskRenderStep.h`, `src/gpu/graphite/render/CoverageMaskRenderStep.cpp`

## 概述

`CoverageMaskRenderStep` 是 Skia Graphite 中用于渲染覆盖遮罩（Coverage Mask）的 `RenderStep` 实现。覆盖遮罩是预先光栅化到图集纹理中的路径形状的 alpha 覆盖数据。此步骤从图集中采样遮罩纹理，将其作为覆盖率应用到绘制中，支持正向和反向填充。

该步骤被用于图集路径渲染策略（`kRasterAtlas`、`kTessellationAndSmallAtlas` 等）以及遮罩滤镜结果的渲染。

## 架构位置

- **上层**: 由 `RendererProvider` 创建为 `fCoverageMask` 渲染器
- **基类**: 继承自 `RenderStep`
- **协作**: 与图集系统（`AtlasProvider`）和计算着色器路径渲染器（Vello）协同工作
- **用途**: `DrawTypeFlags::kNonSimpleShape` 和 `InternalDrawTypeFlags::kCoverageMask`

## 主要类与结构体

### `CoverageMaskRenderStep` 类

**RenderStepID**: `kCoverageMask`

**标志**: `kPerformsShading | kHasTextures | kEmitsCoverage | kOutsetBoundsForAA | kInverseFillsScissor | kAppendInstances`

**Uniform**: `maskToDeviceRemainder`（float3x3）— 遮罩到设备空间的剩余变换

**实例属性**:
| 名称 | 类型 | 描述 |
|------|------|------|
| `drawBounds` | `float4` | 绘制边界（归一化纹理坐标） |
| `maskBoundsIn` | `ushort4_norm` | 遮罩边界（归一化，反向填充时为 RBLT） |
| `deviceOrigin` | `float2` | 设备空间原点偏移 |
| `depth` | `float` | 深度值 |
| `ssboIndex` | `uint` | SSBO 索引 |
| `mat0/mat1/mat2` | `float3 x3` | deviceToLocal 矩阵 |

**Varying 变量**: `maskBounds`(float4), `textureCoords`(float2), `invert`(half)

## 公共 API 函数

- **`CoverageMaskRenderStep(Layout)`** — 构造函数
- **`vertexSkSL()`** — 生成调用 `coverage_mask_vertex_fn()` 的着色器代码
- **`texturesAndSamplersSkSL(...)`** — 声明 `pathAtlas` 纹理采样器
- **`fragmentCoverageSkSL()`** — 从图集采样并应用反转
- **`usesUniformsInFragmentSkSL()`** — 返回 false（片段着色器不使用 uniform）
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 写入归一化的遮罩和绘制边界
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 写入变换矩阵和纹理绑定

## 内部实现细节

### 设备平移提取

`get_device_translation()` 函数从 `localToDevice` 矩阵中提取平移分量，通过计算 `inv(upper 2x2) * translation` 得到。这个平移被分离为实例属性 `deviceOrigin`，使得 `maskToDeviceRemainder` uniform 在多数绘制间保持不变（因为大多数遮罩是像素对齐的）。

### 坐标归一化

所有坐标在写入前被归一化到 [0,1] 范围（除以纹理尺寸），节省 GPU 带宽。`maskBounds` 进一步编码为 `ushort_norm`（16 位归一化无符号整数）以进一步压缩。

### 反向填充处理

反向填充通过以下方式实现：
- `maskBoundsIn` 存储为 RBLT 顺序（xy > zw），在着色器中检测
- `drawBounds` 使用裁剪后的绘制边界（在遮罩空间中）
- 空遮罩的特殊处理：使用 (0,0,0.5,0.5) 边界，采样左上角像素的零值
- 着色器中通过 `invert` varying 执行 `1 - coverage` 反转

### 采样过滤模式

根据遮罩是否像素对齐选择过滤模式：
- **像素对齐**（简单矩阵 + 整数平移 + 1x 缩放）→ 最近邻采样
- **非像素对齐**（复杂变换或遮罩滤镜）→ 线性采样

### 遮罩边界钳位

- 正向填充：遮罩边界内缩 0.5px，确保钳位到外围纹素中心
- 反向填充：遮罩边界外扩 0.5px，钳位到填充区域的纹素中心

## 依赖关系

- `CoverageMaskShape` — 覆盖遮罩形状数据
- `TextureProxy` — 图集纹理代理
- `DrawWriter` — GPU 缓冲区写入
- `CommonDepthStencilSettings` — `kDirectDepthLessPass`

## 设计模式与设计决策

### 平移分离优化

将设备平移从变换矩阵中分离，使得多数绘制共享同一个 `maskToDeviceRemainder` uniform，减少 uniform 更新频率。

### ushort_norm 压缩

遮罩边界使用 16 位归一化格式存储，对于归一化坐标这提供了足够的精度（每图集纹素约 0.0015% 误差），同时将实例数据大小减少了 8 字节。

## 性能考量

- **实例化四边形**: 每个遮罩仅 4 个顶点
- **uniform 频率降低**: 平移分离使大多数绘制共享相同的 uniform
- **像素对齐最近邻**: 避免不必要的双线性过滤
- **带宽优化**: ushort_norm 编码减少实例数据传输量

## 相关文件

- `src/gpu/graphite/geom/CoverageMaskShape.h` — 覆盖遮罩形状
- `src/gpu/graphite/AtlasProvider.h` — 图集提供者
- `src/gpu/graphite/RendererProvider.cpp` — 创建覆盖遮罩渲染步骤
- `src/gpu/graphite/render/CommonDepthStencilSettings.h` — 深度模板设置
