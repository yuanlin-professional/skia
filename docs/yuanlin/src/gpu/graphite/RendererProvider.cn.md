# RendererProvider

> 源文件: `src/gpu/graphite/RendererProvider.h`, `src/gpu/graphite/RendererProvider.cpp`

## 概述

`RendererProvider` 是 Skia Graphite 渲染后端中的核心管理类，负责创建、持有和提供所有可用的 `Renderer` 单例实例。Graphite 定义了一组有限的渲染器，以最大化绘制调用之间的批处理（batching）机会，同时减少所需的着色器排列数量。这些渲染器是无状态的单例，在 `Context` 和其 `Recorder` 的整个生命周期中保持存活。

由于渲染器是不可变的，且在上下文初始化时创建，`RendererProvider` 天然具备线程安全性。

## 架构位置

`RendererProvider` 位于 Graphite 渲染管线的核心位置：

- **上层**: 由 `Context` 创建并持有，是 `Context` 的友元类
- **下层**: 管理各种 `Renderer` 和 `RenderStep` 实例
- **协作**: 与 `Caps`（能力查询）和 `StaticBufferManager`（静态缓冲区管理）协同工作
- **消费者**: 被 `Recorder`、绘制命令调度器等组件查询以获取合适的渲染器

## 主要类与结构体

### `PathRendererStrategy` 枚举

定义路径渲染策略，由 `Caps` 基于硬件特性和启发式方法确定：

| 策略 | 描述 |
|------|------|
| `kTessellation` | 使用曲面细分和经典的模板-覆盖（stencil-and-cover）算法配合 MSAA |
| `kTessellationAndSmallAtlas` | 在 `kTessellation` 基础上增加纹理图集，小路径使用 CPU 光栅化打包到图集中 |
| `kRasterAtlas` | 所有路径和裁剪都使用 CPU 光栅化并打包到覆盖图集中 |
| `kComputeAnalyticAA` | 实验性：使用 GPU 计算着色器的解析抗锯齿 |
| `kComputeMSAA16` | 实验性：GPU 计算着色器模拟 16 样本 MSAA |
| `kComputeMSAA8` | 实验性：GPU 计算着色器模拟 8 样本 MSAA |
| `kCPUSparseStripsMSAA8` | CPU 上运行 SparseStrips 管线，模拟 8 样本 MSAA |

### `RendererProvider` 类

持有所有渲染器实例并提供按类型查询的接口。

**关键成员变量**:
- `fStrategy`: 当前选定的路径渲染策略
- `fRenderSteps[]`: 拥有所有 `RenderStep` 实例的所有权数组
- `fStencilTessellatedCurves[4]`: 4 种路径填充类型的曲线模板渲染器
- `fStencilTessellatedWedges[4]`: 4 种路径填充类型的楔形模板渲染器
- `fVertices[8]`: 2 种图元模式 × 2 种颜色配置 × 2 种纹理坐标配置
- `fRenderers`: 所有已启用渲染器的聚合列表，用于预编译管线时的遍历

## 公共 API 函数

### 策略查询

- **`IsSupported(PathRendererStrategy, const Caps*)`** — 静态方法，检查指定策略在给定能力下是否受支持
- **`pathRendererStrategy()`** — 返回当前使用的路径渲染策略

### 路径渲染器

- **`stencilTessellatedCurvesAndTris(SkPathFillType)`** — 返回基于曲线+三角形的模板渲染器
- **`stencilTessellatedWedges(SkPathFillType)`** — 返回基于楔形的模板渲染器
- **`convexTessellatedWedges()`** — 返回凸路径楔形渲染器（无需模板）
- **`tessellatedStrokes()`** — 返回描边路径的曲面细分渲染器

### 覆盖遮罩

- **`coverageMask()`** — 返回覆盖遮罩渲染器，用于图集路径渲染和遮罩滤镜

### 文本渲染器

- **`bitmapText(bool useLCDText, MaskFormat format)`** — 返回位图文本渲染器，支持 A8、A565(LCD)、ARGB 格式
- **`sdfText(bool useLCDText)`** — 返回 SDF（有向距离场）文本渲染器

### 图形渲染器

- **`vertices(SkVertices::VertexMode, bool hasColors, bool hasTexCoords)`** — 返回顶点网格渲染器
- **`analyticRRect()`** — 返回解析圆角矩形渲染器
- **`perEdgeAAQuad()`** — 返回逐边抗锯齿四边形渲染器
- **`nonAABounds()`** — 返回无抗锯齿边界填充渲染器
- **`circularArc()`** — 返回圆弧渲染器
- **`analyticBlur()`** — 返回解析模糊渲染器

### 遍历与查找

- **`renderers()`** — 返回所有可用渲染器的 `SkSpan`，用于预编译管线
- **`lookup(RenderStep::RenderStepID)`** — 根据 ID 查找对应的 `RenderStep`

## 内部实现细节

### 构造过程

构造函数接受 `Caps` 和 `StaticBufferManager` 参数，执行以下步骤：

1. **策略选择**: 按优先级选择路径渲染策略（Vello 计算 > 曲面细分+小图集 > 光栅图集），测试模式下可通过 `Caps` 覆盖
2. **布局确定**: 根据是否支持存储缓冲区选择对应的缓冲区布局
3. **单步渲染器初始化**: 使用 `initFromStep` 辅助函数创建只有单个 RenderStep 的渲染器
4. **多步渲染器初始化**: 对于模板+覆盖渲染器，多个 RenderStep 被共享（如 coverFill/coverInverse 步骤在不同填充类型之间共享）

### 所有权管理

`assumeOwnership()` 方法将 `RenderStep` 的所有权转移到 `fRenderSteps` 数组中，通过 `RenderStepID` 作为索引。渲染器本身不持有 RenderStep 的生命周期——它们只保存指针引用。

### 渲染器变体

顶点渲染器有 8 种变体（`kVerticesCount = 8`），通过组合索引 `4*triStrip + 2*hasColors + hasTexCoords` 访问。特别地，三角形+颜色（无纹理坐标）组合额外标记了 `kDropShadows`，因为 Android 使用此组合来绘制阴影。

## 依赖关系

### 上游依赖
- `Caps`: 提供硬件能力信息，决定渲染策略
- `StaticBufferManager`: 用于分配某些 RenderStep 需要的静态缓冲区
- `Context`: 创建并持有 RendererProvider

### 下游依赖（具体的 RenderStep 实现）
- `TessellateCurvesRenderStep`, `TessellateWedgesRenderStep`: 曲面细分
- `TessellateStrokesRenderStep`: 描边
- `MiddleOutFanRenderStep`: 中间扇出
- `CoverBoundsRenderStep`: 边界覆盖
- `CoverageMaskRenderStep`: 覆盖遮罩
- `BitmapTextRenderStep`, `SDFTextRenderStep`, `SDFTextLCDRenderStep`: 文本
- `AnalyticRRectRenderStep`, `PerEdgeAAQuadRenderStep`: 形状
- `CircularArcRenderStep`, `AnalyticBlurRenderStep`: 特殊效果
- `VerticesRenderStep`: 顶点网格

### 条件依赖
- `VelloRenderer`（SK_ENABLE_VELLO_SHADERS 宏启用时）: GPU 计算着色器路径渲染

## 设计模式与设计决策

### 单例工厂模式
所有渲染器作为不可变单例在初始化时一次性创建，后续仅提供查询接口。这种设计确保了线程安全和高效的批处理。

### 策略模式
通过 `PathRendererStrategy` 枚举在初始化时选择路径渲染策略，运行时不再更改。这样可以高效配置共享资源（如图集），并减少因渲染目标特性差异导致的管线变化。

### 渲染步骤共享
多步渲染器之间共享 `RenderStep`（例如 `coverFill` 和 `coverInverse` 在正向/反向填充之间共享），减少内存占用和重复初始化。

### 有限渲染器集合
刻意限制渲染器种类以增加批处理机会——这是 Graphite 架构的核心设计哲学之一。

## 性能考量

- **批处理优化**: 有限的渲染器集合最大化了绘制调用之间的合并机会
- **预编译支持**: `renderers()` 方法允许遍历所有渲染器与绘制组合进行管线预编译，避免运行时编译延迟
- **策略固定**: 每个 Context 只使用一种路径渲染策略，避免运行时分支和资源竞争
- **零运行时分配**: 所有渲染器在初始化时创建完毕，查询操作为 O(1) 的指针返回

## 相关文件

- `src/gpu/graphite/Renderer.h` — `Renderer` 和 `RenderStep` 基类定义
- `src/gpu/graphite/Caps.h` — 硬件能力查询
- `src/gpu/graphite/Context.cpp` — 创建 RendererProvider 的上下文
- `src/gpu/graphite/render/CommonDepthStencilSettings.h` — 深度/模板设置常量
- `src/gpu/graphite/compute/VelloRenderer.h` — Vello 计算着色器渲染器
