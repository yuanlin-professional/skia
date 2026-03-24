# Renderer (渲染器)

> 源文件：[src/gpu/graphite/Renderer.h](../../../../src/gpu/graphite/Renderer.h)、[src/gpu/graphite/Renderer.cpp](../../../../src/gpu/graphite/Renderer.cpp)

## 概述

`Renderer` 和 `RenderStep` 是 Graphite 中将高层绘制操作分解为 GPU 可执行步骤的核心抽象。每种渲染技术（如解析圆角矩形、曲面细分路径、文本位图等）对应一个单例 `Renderer`，它由一系列有序的 `RenderStep` 组成。`RenderStep` 是实际的渲染步骤，定义了顶点布局、着色器代码、深度/模板设置和绘制方式。

不同绘制的同一 `RenderStep` 可以在 `DrawPass` 中被批量重排执行，依赖于 `DisjointStencilIndex` 和 `CompressedPaintersOrder` 保证正确性。

## 架构位置

`Renderer` / `RenderStep` 位于渲染管线的执行层：

- **上游**：`Device::chooseRenderer()` 为每个绘制选择合适的 `Renderer`。
- **下游**：`DrawPass::Make()` 使用 `RenderStep` 生成绘制命令和管线描述。
- **管理**：`RendererProvider` 持有所有 Renderer 单例。

## 主要类与结构体

### `RenderStep` (虚基类)
定义单个渲染步骤。

**标志位 (Flags)：**
- `kRequiresMSAA`：需要 MSAA。
- `kPerformsShading`：执行着色/颜色输出。
- `kHasTextures`：使用纹理和采样器。
- `kEmitsCoverage / kLCDCoverage`：输出覆盖率。
- `kEmitsPrimitiveColor`：输出原始颜色。
- `kOutsetBoundsForAA`：AA 需要扩展边界。
- `kUseNonAAInnerFill`：支持非 AA 内部填充优化。
- `kFixed / kAppendVertices / kAppendInstances / kAppendDynamicInstances`：数据写入模式。

**关键虚方法：**
- `writeVertices(DrawWriter*, DrawParams*, ssboIndex)`：写入顶点/实例数据。
- `writeUniformsAndTextures(DrawParams*, PipelineDataGatherer*)`：写入 uniform 和纹理。
- `vertexSkSL() -> string`：返回顶点着色器 SkSL 代码。
- `texturesAndSamplersSkSL(...) -> string`：纹理和采样器 SkSL 代码。
- `fragmentCoverageSkSL() / fragmentColorSkSL()`：片段着色器覆盖率/颜色代码。

**RenderStepID 枚举（通过宏生成）：**
包括 CircularArc、AnalyticRRect、PerEdgeAAQuad、CoverBounds、CoverageMask、BitmapText、SDFText、TessellateCurves、TessellateWedges、TessellateStrokes、Vertices 等。

### `Renderer` (非虚)
渲染器，持有最多 4 个 `RenderStep` 指针。

**关键属性：**
- `fSteps`：最多 `kMaxRenderSteps`(4) 个步骤。
- `fName`：渲染器名称。
- `fDrawTypes`：支持的绘制类型。
- `fStepFlags`：所有步骤标志的并集。
- `fDepthStencilFlags`：所有步骤的深度/模板标志并集。

**查询方法：**
- `requiresMSAA() / emitsPrimitiveColor() / outsetBoundsForAA() / useNonAAInnerFill()`。
- `coverage() -> Coverage`：覆盖率类型（None、SingleChannel、LCD）。
- `depthStencilFlags()`：深度/模板标志。

## 公共 API 函数

### RenderStep
- `name()`：格式为 "Subclass[variant]" 的名称。
- `getScissor(DrawParams, ...) -> optional<SkIRect>`：计算剪裁矩形。
- `primitiveType() / staticDataStride() / appendDataStride()`：几何属性。
- `uniforms() / staticAttributes() / appendAttributes() / varyings()`：着色器数据描述。
- `depthStencilSettings()`：深度模板配置。

### Renderer
- `step(i) / steps()`：访问渲染步骤。
- `numRenderSteps()`：步骤数量。

## 内部实现细节

### 静态数据与追加数据
每个 `RenderStep` 区分两种数据类型：
- **静态数据**：固定数量，Context 生命周期内不变，由 `StaticBufferManager` 一次性上传（如细分索引表）。
- **追加数据**：每次绘制可变，由 `DrawBufferManager` 在 DrawPass 期间上传（如顶点位置、实例数据）。

### 多步骤渲染器
如 Stencil-then-Cover 路径渲染需要多个步骤（stencil 步骤 + cover 步骤）。DrawPass 可以将多个绘制的同类步骤批量执行，依赖 `DisjointStencilIndex` 避免 stencil 冲突。

### 非 AA 内部填充优化
标记了 `kUseNonAAInnerFill` 的单步骤渲染器允许 Device 记录额外的非 AA 内部填充绘制，利用 early-Z 减少过度绘制。约束条件：必须是单步骤且使用 LESS 深度测试。

## 依赖关系

- `DrawWriter`：顶点和实例数据写入。
- `DrawParams`：绘制参数。
- `PipelineDataGatherer`：管线数据收集。
- `RendererProvider`：渲染器注册和查找。
- `DrawPass`：绘制批量处理。

## 设计模式与设计决策

1. **单例渲染器**：每种技术只有一个 Renderer 实例，通过 RendererProvider 全局共享。
2. **步骤分离**：将多步骤渲染（如 stencil+cover）的步骤可独立排序，提高 GPU 利用率。
3. **标志位驱动**：通过位标志描述步骤特性，支持编译时和运行时的灵活查询。
4. **序列化稳定的 ID**：`RenderStepID` 用于管线序列化，版本变更时通过 `kRenderStepIDVersion` 信号废弃旧数据。

## 性能考量

- 步骤排序批量执行减少管线切换。
- 静态数据一次性上传避免重复传输。
- 非 AA 内部填充利用 early-Z 减少着色器执行。
- 最多 4 步的限制保证渲染器数组内联存储。

## 相关文件

- `src/gpu/graphite/RendererProvider.h/.cpp`：渲染器注册。
- `src/gpu/graphite/DrawPass.h/.cpp`：绘制批量处理。
- `src/gpu/graphite/DrawWriter.h/.cpp`：顶点数据写入。
- `src/gpu/graphite/render/`：各种具体 RenderStep 实现。
