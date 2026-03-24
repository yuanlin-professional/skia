# TessellateCurvesRenderStep

> 源文件: `src/gpu/graphite/render/TessellateCurvesRenderStep.h`, `src/gpu/graphite/render/TessellateCurvesRenderStep.cpp`

## 概述

`TessellateCurvesRenderStep` 是 Skia Graphite 中用于曲面细分填充路径曲线段的 `RenderStep` 实现。它是模板-覆盖（stencil-and-cover）路径渲染算法的模板阶段组件之一，负责将路径中的二次曲线、圆锥曲线和三次曲线通过 GPU 硬件曲面细分生成三角形网格，并写入模板缓冲区。

该步骤使用固定计数的曲面细分方案（Fixed-Count Tessellation），通过预计算的静态顶点/索引缓冲区和实例化绘制来高效处理曲线段。

## 架构位置

- **上层**: 由 `RendererProvider` 创建，作为 `fStencilTessellatedCurves` 多步渲染器的模板步骤之一
- **基类**: 继承自 `RenderStep`
- **协同**: 与 `MiddleOutFanRenderStep`（处理三角扇）和 `CoverBoundsRenderStep`（覆盖步骤）配合组成完整的模板-覆盖渲染器
- **用途**: `DrawTypeFlags::kNonSimpleShape`

## 主要类与结构体

### `TessellateCurvesRenderStep` 类

有两个变体（奇偶填充和卷绕填充），通过 `evenOdd` 参数区分。

**标志**: `kRequiresMSAA | kAppendDynamicInstances | kIgnoreInverseFill`

**Uniform**: `localToDevice`（float4x4）

**静态属性**: `resolveLevel_and_idx`（float2）— 来自固定计数缓冲区

**实例属性**（取决于无穷大支持）:
- 基础版: `p01`(float4), `p23`(float4), `depth`(float), `curveType`(float), `ssboIndex`(uint)
- 无穷大支持版: `p01`, `p23`, `depth`, `ssboIndex`（省略 curveType，从 p23 推导）

**私有成员**:
- `fVertexBuffer`, `fIndexBuffer` — 固定计数曲面细分的静态缓冲区引用
- `fInfinitySupport` — 是否支持 IEEE 754 无穷大

## 公共 API 函数

- **`TessellateCurvesRenderStep(Layout, bool evenOdd, bool infinitySupport, StaticBufferManager*)`** — 构造函数，初始化静态缓冲区
- **`vertexSkSL()`** — 生成调用 `tessellate_filled_curve()` 的顶点着色器代码
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 使用 PatchWriter 将路径曲线段写入实例缓冲区
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 写入变换矩阵

## 内部实现细节

### PatchWriter 模板系统

使用 `PatchWriter` 模板类，配置为：
- **分配器**: `DynamicInstancesPatchAllocator<FixedCountCurves>` — 动态实例分配
- **必选属性**: `PaintDepth`, `SsboIndex`
- **可选属性**: `ExplicitCurveType`（仅在不支持无穷大时需要）
- **策略**: `AddTrianglesWhenChopping`（细分时添加三角形）, `DiscardFlatCurves`（丢弃平坦曲线）

### 曲线遍历

`writeVertices()` 遍历路径的所有动词（verb），仅处理曲线类型：
- `kQuad` — 二次贝塞尔曲线
- `kConic` — 圆锥曲线（有理二次曲线）
- `kCubic` — 三次贝塞尔曲线
- 直线段和移动命令被忽略（由 MiddleOutFanRenderStep 处理）

### 固定计数曲面细分

静态顶点和索引缓冲区在构造时通过 `StaticBufferManager` 创建，内容由 `FixedCountCurves` 工具类生成。GPU 使用 `resolveLevel_and_idx` 属性在着色器中计算每个三角形的顶点位置。

### Wang 公式

使用 `wangs_formula::VectorXform` 来估算参数化细分层级，确保曲线在屏幕空间中足够平滑。当前不支持透视变换下的逐控制点细分调整。

## 依赖关系

- `PatchWriter` / `DynamicInstancesPatchAllocator` — 曲线细分写入
- `FixedCountCurves` — 固定计数缓冲区生成
- `WangsFormula` — 细分层级估算
- `StaticBufferManager` — 静态 GPU 缓冲区管理
- `CommonDepthStencilSettings` — 模板通道配置

## 设计模式与设计决策

### 固定计数 vs 硬件曲面细分

使用预计算的固定计数方案而非 GPU 硬件曲面细分器（tessellation shader），因为固定计数方案兼容性更广且在 Graphite 的实例化绘制模型中更易集成。

### 无穷大支持

在支持 IEEE 754 无穷大的平台上，曲线类型可以从控制点编码中推导（通过检测特殊值），省略一个显式属性，节省每实例的带宽。

### 模板阶段分离

曲线和扇形（fan）分别由不同的 RenderStep 处理，允许独立优化和缓冲区管理。

## 性能考量

- **实例化绘制**: 所有曲线段作为实例共享同一个静态顶点/索引缓冲区
- **预分配**: 根据路径动词数量预留实例缓冲区空间
- **平坦曲线丢弃**: `DiscardFlatCurves` 策略跳过退化为直线的曲线
- **CPU 变换近似**: 使用 2x2 仿射近似估算细分层级，避免逐控制点的完整变换

## 相关文件

- `src/gpu/tessellate/PatchWriter.h` — 曲线细分写入器
- `src/gpu/tessellate/FixedCountBufferUtils.h` — 固定计数缓冲区工具
- `src/gpu/tessellate/WangsFormula.h` — 细分层级估算
- `src/gpu/graphite/render/DynamicInstancesPatchAllocator.h` — 动态实例分配
- `src/gpu/graphite/render/MiddleOutFanRenderStep.h` — 扇形模板步骤
- `src/gpu/graphite/render/CoverBoundsRenderStep.h` — 覆盖步骤
