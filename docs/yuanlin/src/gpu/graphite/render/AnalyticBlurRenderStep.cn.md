# AnalyticBlurRenderStep

> 源文件: `src/gpu/graphite/render/AnalyticBlurRenderStep.h`, `src/gpu/graphite/render/AnalyticBlurRenderStep.cpp`

## 概述

`AnalyticBlurRenderStep` 是 Skia Graphite 中用于渲染解析模糊效果的 `RenderStep` 实现。它通过 GPU 着色器以解析方式（而非采样卷积）计算模糊覆盖率，支持矩形、圆角矩形和圆形等基本形状的高斯模糊效果。这种方式比传统的多遍纹理采样模糊更高效，特别适用于阴影绘制。

## 架构位置

- **上层**: 由 `RendererProvider` 创建并管理，作为 `fAnalyticBlur` 渲染器的唯一步骤
- **基类**: 继承自 `RenderStep`，实现其顶点、片段着色器生成和数据写入接口
- **用途**: 主要用于 `DrawTypeFlags::kDropShadows`（投影阴影）的渲染

## 主要类与结构体

### `AnalyticBlurRenderStep` 类

继承自 `RenderStep`，配置如下：
- **RenderStepID**: `kAnalyticBlur`
- **标志**: `kPerformsShading | kHasTextures | kEmitsCoverage | kAppendVertices`
- **图元类型**: 三角形（`kTriangles`）
- **深度/模板设置**: `kDirectDepthLessPass`

**Uniform 变量**:
| 名称 | 类型 | 描述 |
|------|------|------|
| `localToDevice` | `float4x4` | 局部到设备空间的变换矩阵 |
| `deviceToScaledShape` | `float3x3` | 设备空间到缩放形状空间的变换 |
| `shapeData` | `float4` | 形状参数数据 |
| `blurData` | `half2` | 模糊参数 |
| `shapeType` | `int` | 形状类型标识 |
| `depth` | `float` | 深度值 |

**追加属性**: `position`（float2）, `ssboIndex`（uint）

**Varying**: `scaledShapeCoords`（float2）— 缩放形状空间中的片段坐标

## 公共 API 函数

- **`AnalyticBlurRenderStep(Layout)`** — 构造函数，接受缓冲区布局
- **`vertexSkSL()`** — 生成顶点着色器 SkSL 代码
- **`texturesAndSamplersSkSL(...)`** — 生成纹理和采样器声明
- **`fragmentCoverageSkSL()`** — 生成片段覆盖率计算代码
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 写入顶点数据（两个三角形组成的四边形）
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 写入 uniform 数据和纹理绑定

## 内部实现细节

### 顶点生成

每个模糊形状生成 6 个顶点（两个三角形），覆盖模糊遮罩的绘制边界。顶点位置直接来自 `AnalyticBlurMask::drawBounds()`。

### 着色器逻辑

- **顶点着色器**: 将顶点变换到设备空间，并通过 `deviceToScaledShape` 矩阵计算缩放形状坐标
- **片段着色器**: 调用 `blur_coverage_fn()` 函数，根据形状类型、形状数据和模糊参数计算覆盖率

### 纹理采样

根据形状类型选择不同的采样模式：
- 矩形模糊使用 **线性过滤**（`kLinear`）
- 其他形状使用 **最近邻过滤**（`kNearest`）
- 统一使用 `kClamp` 平铺模式

## 依赖关系

- `AnalyticBlurMask` — 提供模糊遮罩的几何和参数数据
- `DrawWriter` / `DrawParams` — 顶点和绘制参数写入
- `PipelineDataGatherer` — uniform 和纹理数据收集
- `CommonDepthStencilSettings.h` — 深度/模板配置

## 设计模式与设计决策

### 解析模糊而非卷积

使用数学公式在着色器中直接计算高斯模糊覆盖率，避免了多遍渲染和大量纹理采样。这对于规则形状（矩形、圆角矩形、圆形）特别高效。

### 形状参数统一

所有形状类型共用同一组 uniform（`shapeData`, `blurData`, `shapeType`），通过 `shapeType` 在着色器中分支选择计算路径，减少管线变体数量。

## 性能考量

- **单遍渲染**: 整个模糊效果在一次绘制调用中完成
- **最小顶点开销**: 每个模糊形状仅 6 个顶点
- **纹理查找优化**: 矩形使用预计算的积分表纹理配合线性过滤，其他形状使用最近邻采样

## 相关文件

- `src/gpu/graphite/geom/AnalyticBlurMask.h` — 模糊遮罩数据结构
- `src/gpu/graphite/Renderer.h` — RenderStep 基类
- `src/gpu/graphite/RendererProvider.cpp` — 创建该渲染步骤
- `src/gpu/graphite/render/CommonDepthStencilSettings.h` — 深度模板设置
