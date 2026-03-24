# AnalyticRRectRenderStep

> 源文件: `src/gpu/graphite/render/AnalyticRRectRenderStep.h`, `src/gpu/graphite/render/AnalyticRRectRenderStep.cpp`

## 概述

`AnalyticRRectRenderStep` 是 Skia Graphite 中功能最丰富的单步 `RenderStep` 实现，能够以解析方式渲染多种基本几何图元：填充矩形、填充圆角矩形（任意角半径）、逐边 AA 四边形、描边矩形（任意连接）、描边线段（任意线帽）、描边圆角矩形（圆形角）、发丝线矩形/线段/圆角矩形。

这些图元被统一到单个 RenderStep 中，以最大化批处理并减少管线特化数量。这些是最常见的绘制操作，使用解析方法可以避免触发 MSAA。

## 架构位置

- **上层**: 由 `RendererProvider` 创建为 `fAnalyticRRect` 渲染器
- **基类**: 继承自 `RenderStep`
- **用途**: `DrawTypeFlags::kAnalyticRRect`

## 主要类与结构体

### `AnalyticRRectRenderStep` 类

**RenderStepID**: `kAnalyticRRect`

**标志**: `kPerformsShading | kEmitsCoverage | kOutsetBoundsForAA | kUseNonAAInnerFill | kAppendInstances`

**无 uniform** — 所有数据通过静态和实例属性传递

**静态顶点属性**（每角 9 个顶点，共 36 个）:
- `cornerID`(uint), `position`(float2), `normal`(float2), `normalScale`(float), `centerWeight`(float)

**实例属性**:
- `xRadiiOrFlags`(float4) — X 半径或编码标志（区分填充/描边/发丝线/四边形模式）
- `radiiOrQuadXs`(float4) — Y 半径或圆形角半径或四边形 X 坐标
- `ltrbOrQuadYs`(float4) — LTRB 边界或四边形 Y 坐标
- `center`(float4) — 中心坐标、内部填充模式和 AA 内缩尺寸
- `depth`, `ssboIndex`, `mat0/mat1/mat2` — 深度、索引和 3x3 变换

**Varying 变量**:
- `jacobian`(float4) — 逆变换的雅可比矩阵 2x2
- `edgeDistances`(float4) — 到 LTRB 边缘的距离
- `xRadii`(float4), `yRadii`(float4) — 四个角的椭圆半径
- `strokeParams`(float2) — 描边参数
- `perPixelControl`(float2) — 逐像素覆盖率计算控制

### `Vertex` 结构体

每个顶点包含 `fCornerID`、`fPosition`、`fNormal`、`fNormalScale`、`fCenterWeight`。

### 几何模板

每个角落 9 个顶点：
- 4 个外部 AA 外扩顶点（沿法线方向外扩）
- 2 个外部锚点（无外扩）
- 2 个内部曲线顶点（沿法线内缩）
- 1 个中心填充顶点

总共 36 个顶点和 69 个索引。

## 公共 API 函数

- **`AnalyticRRectRenderStep(Layout, StaticBufferManager*)`** — 构造函数
- **`vertexSkSL()`** — 生成调用 `analytic_rrect_vertex_fn()` 的着色器代码
- **`fragmentCoverageSkSL()`** — 生成调用 `analytic_rrect_coverage_fn()` 的覆盖率代码
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 根据形状类型编码实例数据
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 空操作

## 内部实现细节

### 实例数据编码

使用灵活的编码方案，通过 `xRadiiOrFlags` 的值区分不同形状类型：
- **xRadiiOrFlags 全正**: 填充圆角矩形，值为 X 半径
- **xRadiiOrFlags.x < -1**: 描边或发丝线模式
  - `.y < 0`: 发丝线圆角矩形（`-2 - X radii`）
  - `.y == 0`: 描边圆角矩形（`.z` = 描边半径, `.w` = 连接限制）
  - `.y > 0`: 描边或发丝线线段
- **-1 <= xRadiiOrFlags.x <= 0**: 逐边 AA 四边形

### 泰勒级数距离近似

使用 C(px,py)/|nablaC(px,py)| 近似距离到等值线。直线边缘的等值线在顶点着色器中线性计算并精确插值。椭圆角的梯度需要在片段着色器中逐像素计算。

### 解析导数

通过逆变换的雅可比矩阵将局部空间梯度转换到设备空间，避免依赖硬件导数支持。雅可比矩阵在顶点着色器中计算并线性插值（因为每个分量在 (u,v) 中是线性的）。

### 内部交叉检测

`opposite_insets_intersect()` 函数检测 AA 内缩是否会交叉（对于极小或极窄的形状）。当检测到交叉时，`center` 属性的特殊编码通知着色器使用简化的覆盖率计算。

### 绕序校正

对于非矩形的 EdgeAAQuad 输入，`is_clockwise()` 检查绕序，必要时交换顶点以确保着色器的一致性假设。

## 依赖关系

- `EdgeAAQuad` — 逐边 AA 四边形数据
- `Shape` — 矩形、圆角矩形、线段形状
- `StaticBufferManager` — 预计算顶点/索引缓冲区
- `SkRRectPriv` — 圆角矩形半径访问

## 设计模式与设计决策

### 统一渲染器

将所有简单几何图元统一到单个 RenderStep 中，通过实例数据编码区分类型。这种设计的核心优势是最大化批处理——不同类型的形状可以在同一次绘制调用中渲染。

### 四角对称

利用四角旋转对称性，36 个顶点实际上是同一个 9 顶点模板的 4 次重复。着色器中通过 `cornerID` 查找每个角的特定参数。

### perPixelControl 编码

使用紧凑的 float2 编码复杂的逐像素行为决策，避免了着色器中的条件分支和额外的 uniform。

## 性能考量

- **无 MSAA**: 通过解析 AA 避免多重采样开销
- **统一批处理**: 矩形、圆角矩形、线段可以合并到同一绘制调用
- **静态缓冲区共享**: 所有实例共享 36 顶点 + 69 索引的静态模板
- **非 AA 内部填充**: `kUseNonAAInnerFill` 标志允许大面积内部像素跳过覆盖率计算
- **解析导数**: 单一管线支持所有硬件，无需导数支持检测

## 相关文件

- `src/gpu/graphite/render/PerEdgeAAQuadRenderStep.h` — 独立的逐边 AA 四边形渲染
- `src/gpu/graphite/geom/EdgeAAQuad.h` — EdgeAAQuad 数据结构
- `src/gpu/graphite/geom/Shape.h` — 形状定义
- `src/gpu/graphite/RendererProvider.cpp` — 创建该渲染步骤
