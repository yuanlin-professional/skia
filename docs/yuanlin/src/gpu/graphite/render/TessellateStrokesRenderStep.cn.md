# TessellateStrokesRenderStep

> 源文件: `src/gpu/graphite/render/TessellateStrokesRenderStep.h`, `src/gpu/graphite/render/TessellateStrokesRenderStep.cpp`

## 概述

`TessellateStrokesRenderStep` 是 Skia Graphite 中用于通过 GPU 曲面细分渲染描边路径（stroked paths）的 `RenderStep` 实现。它将路径的各种曲线段（直线、二次曲线、圆锥曲线、三次曲线）转换为描边三角形带，支持各种线帽（cap）和连接（join）样式。该步骤能处理描边中的特殊情况，如尖点（cusp）和 180 度转折。

## 架构位置

- **上层**: 由 `RendererProvider` 创建，作为 `fTessellatedStrokes` 渲染器的唯一步骤
- **基类**: 继承自 `RenderStep`
- **用途**: `DrawTypeFlags::kNonSimpleShape`（描边路径）

## 主要类与结构体

### `TessellateStrokesRenderStep` 类

**RenderStepID**: `kTessellateStrokes`

**标志**: `kRequiresMSAA | kPerformsShading | kAppendDynamicInstances`

**图元类型**: 三角形带（`kTriangleStrip`），使用 `sk_VertexID` 生成

**Uniform 变量**:
| 名称 | 类型 | 描述 |
|------|------|------|
| `affineMatrix` | `float4` | 2x2 仿射变换矩阵（列主序） |
| `translate` | `float2` | 平移分量 |
| `maxScale` | `float` | 最大缩放因子 |

**实例属性**:
- `p01`(float4), `p23`(float4) — 曲线控制点
- `prevPoint`(float2) — 前一段的连接控制点
- `stroke`(float2) — 描边参数（半宽度和连接限制）
- `depth`(float), `ssboIndex`(uint)
- `curveType`(float)（仅在不支持无穷大时）

## 公共 API 函数

- **`TessellateStrokesRenderStep(Layout, bool infinitySupport)`** — 构造函数
- **`vertexSkSL()`** — 生成调用 `tessellate_stroked_curve()` 的顶点着色器代码
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 使用 StrokeIterator 遍历路径并写入描边补丁
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 写入仿射变换参数

## 内部实现细节

### PatchWriter 配置

描边 PatchWriter 配置了描边特有的属性和策略：
- **`Required<kJoinControlPoint>`** — 连接控制点（`prevPoint`），用于计算连接样式
- **`Required<kStrokeParams>`** — 描边参数（半宽度和连接限制）
- **`ReplicateLineEndPoints`** — 直线端点复制，匹配 Ganesh 着色器行为
- **`TrackJoinControlPoints`** — 自动追踪连接控制点

### 路径遍历和特殊情况处理

`writeVertices()` 遍历路径的所有动词，并处理以下特殊情况：

**尖点（Cusp）处理**:
- 二次曲线和圆锥曲线的尖点通过 `ConicHasCusp()` 检测
- 三次曲线的 180 度转折通过 `FindCubicConvex180Chops()` 检测
- 尖点处插入圆形补丁（`writeCircle()`），并将曲线分解为直线段

**三次曲线分割**:
- 通过 `FindCubicConvex180Chops()` 找到最多 2 个分割点
- 使用 `SkChopCubicAt()` 在分割点处细分曲线
- 每段确保转角不超过 180 度（凸 180 约束）

**轮廓关闭**:
- `writeDeferredStrokePatch()` 处理轮廓的开始和结束线帽
- `closeDeferredStrokePatch()` 处理闭合轮廓的连接

### Uniform 编码

变换矩阵以分离的仿射矩阵（2x2）和平移（float2）形式传递，而非完整的 4x4 矩阵。这是因为描边细分不支持透视变换，使用紧凑的仿射表示更高效。

### 顶点着色器

使用 `sk_VertexID` 驱动三角形带生成，最大边数为 16383（`2^14 - 1`）。`tessellate_stroked_curve()` 函数输出设备坐标和局部坐标（`devAndLocalCoords`）。

## 依赖关系

- `PatchWriter` — 描边补丁写入
- `FixedCountStrokes` — 固定计数描边缓冲区
- `StrokeIterator` — 描边路径迭代器
- `WangsFormula` — 细分层级估算
- `SkGeometry` — 曲线几何操作（`SkChopCubicAt`, `FindCubicConvex180Chops` 等）

## 设计模式与设计决策

### 仿射变换限制

当前实现仅支持仿射变换（不支持透视），这简化了描边宽度的计算。透视描边需要更复杂的逐点变换逻辑。

### 凸 180 约束

三次曲线被分割确保每段转角不超过 180 度，这是曲面细分着色器正确工作的必要条件。

### 延迟描边补丁

使用延迟写入机制处理线帽和连接：轮廓的第一段被延迟写入，直到知道轮廓是否闭合（影响使用线帽还是连接）。

### 无静态缓冲区

与填充细分步骤不同，描边细分不使用预计算的静态顶点/索引缓冲区，而是完全依赖 `sk_VertexID` 驱动的三角形带。

## 性能考量

- **三角形带**: 使用三角形带而非三角形列表，减少顶点数量
- **`sk_VertexID`**: 避免显式顶点缓冲区分配
- **预分配**: 根据路径动词数量预留补丁缓冲空间
- **仿射近似**: 使用简化的仿射变换避免完整矩阵运算

## 相关文件

- `src/gpu/tessellate/PatchWriter.h` — 补丁写入器
- `src/gpu/tessellate/StrokeIterator.h` — 描边迭代器
- `src/gpu/tessellate/FixedCountBufferUtils.h` — 固定计数缓冲区
- `src/core/SkGeometry.h` — 曲线几何操作
- `src/gpu/graphite/RendererProvider.cpp` — 创建描边渲染步骤
