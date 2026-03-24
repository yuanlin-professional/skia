# CoverBoundsRenderStep

> 源文件: `src/gpu/graphite/render/CoverBoundsRenderStep.h`, `src/gpu/graphite/render/CoverBoundsRenderStep.cpp`

## 概述

`CoverBoundsRenderStep` 是 Skia Graphite 中用于绘制边界覆盖四边形的 `RenderStep` 实现。它是模板-覆盖（stencil-and-cover）路径渲染算法中的"覆盖"阶段，在模板阶段已经写入路径形状之后，通过绘制路径的包围盒来触发模板测试并输出颜色。此步骤也被用于无抗锯齿的边界填充。

## 架构位置

- **上层**: 由 `RendererProvider` 创建，用于三种角色：
  - `kCoverBounds_RegularCover` — 正向填充的覆盖步骤
  - `kCoverBounds_InverseCover` — 反向填充的覆盖步骤
  - `kCoverBounds_NonAAFill` — 无抗锯齿边界填充
- **基类**: 继承自 `RenderStep`
- **协同**: 与 `TessellateCurvesRenderStep`、`TessellateWedgesRenderStep`、`MiddleOutFanRenderStep` 配合

## 主要类与结构体

### `CoverBoundsRenderStep` 类

**标志**: `kPerformsShading | kAppendInstances | kInverseFillsScissor`

**图元类型**: 三角形带（`kTriangleStrip`），4 个顶点组成的四边形

**无 uniform** — 所有数据通过实例属性传递

**实例属性**:
| 名称 | 类型 | 描述 |
|------|------|------|
| `bounds` | `float4` | 边界框 LTRB（反向填充时为 RBLT） |
| `depth` | `float` | 深度值 |
| `ssboIndex` | `uint` | SSBO 索引 |
| `mat0/mat1/mat2` | `float3 x3` | 3x3 变换矩阵（压缩自 4x4） |

## 公共 API 函数

- **`CoverBoundsRenderStep(Layout, RenderStepID, DepthStencilSettings)`** — 构造函数
- **`vertexSkSL()`** — 生成调用 `cover_bounds_vertex_fn()` 的着色器代码
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 写入包围盒和变换数据
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 空操作（无 uniform）

## 内部实现细节

### 反向填充编码

通过 `bounds` 的顺序区分正向和反向填充：
- **正向填充**: `bounds = [L, T, R, B]`（正常 LTRB 顺序）
- **反向填充**: `bounds = [R, B, L, T]`（RBLT 顺序），使用裁剪器的整数坐标，着色器中使用逆变换计算局部坐标

### 矩阵压缩

由于局部坐标 Z=0，4x4 变换矩阵可以压缩为 3x3（丢弃第 3 行和第 3 列），节省实例数据带宽。

### 顶点生成

使用 `sk_VertexID` 在着色器中生成四边形的 4 个顶点，避免显式的顶点缓冲区。

## 依赖关系

- `DrawWriter` — GPU 缓冲区写入
- `CommonDepthStencilSettings` — 深度/模板配置（kRegularCoverPass, kInverseCoverPass 等）

## 设计模式与设计决策

### 无 uniform 设计

所有绘制数据通过实例属性传递，避免了每个绘制调用的 uniform 更新开销，提高了批处理效率。

### 多用途复用

同一个类通过不同的 RenderStepID 和 DepthStencilSettings 支持多种使用场景。

## 性能考量

- **最小顶点数**: 每个覆盖只需 4 个顶点的三角形带
- **实例化**: 多个覆盖可以合并到单次绘制调用
- **无 uniform 切换**: 所有变量数据都在实例属性中，减少状态变化

## 相关文件

- `src/gpu/graphite/render/CommonDepthStencilSettings.h` — 深度模板设置常量
- `src/gpu/graphite/render/TessellateCurvesRenderStep.h` — 配合使用的模板步骤
- `src/gpu/graphite/render/TessellateWedgesRenderStep.h` — 配合使用的模板步骤
- `src/gpu/graphite/RendererProvider.cpp` — 创建覆盖步骤
