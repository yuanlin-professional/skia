# TessellateWedgesRenderStep

> 源文件: `src/gpu/graphite/render/TessellateWedgesRenderStep.h`, `src/gpu/graphite/render/TessellateWedgesRenderStep.cpp`

## 概述

`TessellateWedgesRenderStep` 是 Skia Graphite 中用于通过楔形（wedge）方式曲面细分填充路径的 `RenderStep` 实现。楔形是由路径曲线段与轮廓中心点（fan point）组成的三角形扇区。与 `TessellateCurvesRenderStep` 不同，楔形方法将每条曲线段与轮廓的中点相连，形成完整的填充覆盖。

该步骤被用于两种场景：作为模板-覆盖算法的模板阶段（非凸路径），以及作为凸路径的直接渲染步骤。

## 架构位置

- **上层**: 由 `RendererProvider` 创建，用于 `fStencilTessellatedWedges`（模板变体）和 `fConvexTessellatedWedges`（凸路径直接渲染变体）
- **基类**: 继承自 `RenderStep`
- **多变体**: 支持 Winding、EvenOdd 和 Convex 三种 RenderStepID

## 主要类与结构体

### `TessellateWedgesRenderStep` 类

**标志**: `kRequiresMSAA | kAppendDynamicInstances | kIgnoreInverseFill`，凸路径变体额外包含 `kPerformsShading`

**Uniform**: `localToDevice`（float4x4）

**实例属性**（比曲线多一个 `fanPointAttrib`）:
- 基础版: `p01`(float4), `p23`(float4), `fanPointAttrib`(float2), `depth`(float), `ssboIndex`(uint)
- 带曲线类型版: 额外包含 `curveType`(float)

**私有成员**:
- `fVertexBuffer`, `fIndexBuffer` — 固定计数楔形的静态缓冲区
- `fInfinitySupport` — IEEE 754 无穷大支持

## 公共 API 函数

- **`TessellateWedgesRenderStep(Layout, RenderStepID, bool infinitySupport, DepthStencilSettings, StaticBufferManager*)`** — 构造函数，接受深度/模板设置以支持不同的渲染模式
- **`CreateVertexTemplate(StaticBufferManager*)`** — 静态方法，创建可共享的顶点模板缓冲区
- **`vertexSkSL()`** — 生成顶点着色器代码，处理扇点和曲线细分两种情况
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 使用 MidpointContourParser 遍历路径轮廓并写入楔形实例
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 写入变换矩阵

## 内部实现细节

### 楔形 vs 曲线

楔形方法与纯曲线细分的关键区别：
1. 每个曲线段都连接到轮廓的中心点（`fanPointAttrib`），形成完整的三角形扇
2. 直线段也需要处理（生成单个三角形）
3. 需要显式关闭轮廓（`writeLine(lastPoint, startPoint)`）
4. 不需要额外的 `MiddleOutFanRenderStep`

### 轮廓遍历

使用 `MidpointContourParser` 逐轮廓遍历路径：
- 计算每个轮廓的中点作为扇点
- 处理所有路径动词（包括直线段）
- 显式关闭未闭合的轮廓

### 顶点着色器分支

着色器中通过 `resolveLevel_and_idx.x` 的符号区分两种顶点：
- **负值**: 表示扇点，直接使用 `fanPointAttrib` 作为位置
- **非负值**: 表示曲线上的点，通过 `tessellate_filled_curve()` 计算

### 深度/模板配置

通过构造函数参数接受不同的 `DepthStencilSettings`：
- **模板变体**: 使用 `kWindingStencilPass` 或 `kEvenOddStencilPass`
- **凸路径变体**: 使用 `kDirectDepthLessPass`，并启用 `kPerformsShading`

## 依赖关系

- `PatchWriter` / `DynamicInstancesPatchAllocator<FixedCountWedges>` — 楔形细分写入
- `FixedCountWedges` — 固定计数楔形缓冲区工具
- `MidpointContourParser` — 轮廓遍历和中点计算
- `WangsFormula` — 细分层级估算
- `StaticBufferManager` — 静态缓冲区管理

## 设计模式与设计决策

### 凸/非凸复用

同一个类通过不同的构造参数（RenderStepID、DepthStencilSettings）支持两种使用模式：
- 凸路径：单步直接渲染，写入颜色和深度
- 非凸路径：多步渲染中的模板阶段，只写入模板缓冲区

### 中点扇形策略

选择轮廓的中点（而非第一个点）作为扇点，可以减少退化三角形的数量，提高覆盖质量。

### 显式轮廓关闭

楔形方法需要显式关闭轮廓（添加从最后一个点到起始点的线段），因为与纯曲线方法不同，它没有隐式的三角形扇步骤来关闭间隙。

## 性能考量

- **实例化绘制**: 所有楔形共享固定计数顶点/索引缓冲区
- **轮廓预分配**: 根据路径动词数量预留实例缓冲区
- **单步凸路径**: 凸路径避免了模板-覆盖的多遍开销
- **CPU 变换近似**: 与曲线步骤相同，使用 2x2 仿射近似

## 相关文件

- `src/gpu/graphite/render/TessellateCurvesRenderStep.h` — 曲线细分步骤
- `src/gpu/graphite/render/CoverBoundsRenderStep.h` — 覆盖步骤
- `src/gpu/tessellate/MidpointContourParser.h` — 中点轮廓解析器
- `src/gpu/tessellate/FixedCountBufferUtils.h` — 固定计数缓冲区
- `src/gpu/tessellate/PatchWriter.h` — 补丁写入器
