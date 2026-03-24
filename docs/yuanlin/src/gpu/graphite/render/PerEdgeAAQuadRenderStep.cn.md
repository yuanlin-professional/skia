# PerEdgeAAQuadRenderStep

> 源文件: `src/gpu/graphite/render/PerEdgeAAQuadRenderStep.h`, `src/gpu/graphite/render/PerEdgeAAQuadRenderStep.cpp`

## 概述

`PerEdgeAAQuadRenderStep` 是 Skia Graphite 中用于渲染逐边抗锯齿四边形的 `RenderStep` 实现。它允许每条边独立控制是否应用抗锯齿（AA），支持矩形和任意凸四边形。这种渲染方式广泛用于 UI 框架中需要在相邻元素间避免可见接缝的场景，其中共享边不需要 AA 而外露边需要 AA。

该步骤使用解析距离场方法计算覆盖率，通过在顶点着色器中插值边缘距离并在片段着色器中钳位来实现平滑的 AA 边缘。

## 架构位置

- **上层**: 由 `RendererProvider` 创建为 `fPerEdgeAAQuad` 渲染器
- **基类**: 继承自 `RenderStep`
- **用途**: `DrawTypeFlags::kPerEdgeAAQuad`

## 主要类与结构体

### `PerEdgeAAQuadRenderStep` 类

**RenderStepID**: `kPerEdgeAAQuad`

**标志**: `kPerformsShading | kEmitsCoverage | kOutsetBoundsForAA | kUseNonAAInnerFill | kAppendInstances`

**图元类型**: 三角形带（`kTriangleStrip`），通过索引缓冲区控制

**无 uniform** — 所有数据通过静态和实例属性传递

**静态顶点属性**:
- `cornerID`(uint) — 角落标识 (0-3: TL,TR,BR,BL)
- `normal`(float2) — 法线方向，用于 AA 外扩

**实例属性**:
- `edgeFlags`(ubyte4_norm) — 逐边 AA 标志
- `quadXs`(float4) — 四边形 X 坐标（TL,TR,BR,BL）
- `quadYs`(float4) — 四边形 Y 坐标
- `depth`, `ssboIndex` — 深度和缓冲区索引
- `mat0/mat1/mat2`(float3 x3) — 3x3 变换矩阵

**Varying**: `edgeDistances`(float4) — 到 LTRB 四条边的设备空间距离

### `Vertex` 结构体

每个顶点包含 `fCornerID`（角落标识）和 `fNormal`（法线向量）。

### 几何模板

每个角落有 4 个顶点（`kCornerVertexCount = 4`）：
- 3 个法线方向顶点：(1,0), (sqrt2/2, sqrt2/2), (0,1) — 用于 AA 外扩
- 1 个锚点：(0,0) — 零法线表示不进行外扩

总共 16 个顶点和 29 个索引，使用三角形带绘制。

## 公共 API 函数

- **`PerEdgeAAQuadRenderStep(Layout, StaticBufferManager*)`** — 构造函数，初始化静态顶点/索引缓冲区
- **`vertexSkSL()`** — 生成调用 `per_edge_aa_quad_vertex_fn()` 的着色器代码
- **`fragmentCoverageSkSL()`** — 生成调用 `per_edge_aa_quad_coverage_fn()` 的覆盖率代码
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 写入四边形坐标和边缘 AA 标志
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 空操作（无 uniform）

## 内部实现细节

### 绕序校正

`is_clockwise()` 函数检查四边形顶点的绕序。如果是逆时针，则在写入实例数据时交换左右 AA 位和对应的顶点坐标。

### AA 距离计算

使用泰勒级数近似：给定等值线函数 C(x,y)，在像素点 (px,py) 处计算 C(px,py)/|gradC(px,py)|。对于直线边缘，等值线是线性的，可以在顶点着色器中精确计算并插值。

### 解析导数

使用解析导数而非硬件导数或前向差分，确保在所有硬件和几何配置下的一致性。梯度通过将局部梯度向量与逆 local-to-device 变换的雅可比矩阵相乘来转换到设备空间。

### 索引缓冲区布局

29 个索引组织为：
- 4 组外部 AA 渐变条带（每组 6 个索引，共 24 个）
- 1 个退化三角形索引（分隔外部和内部）
- 4 个内部填充索引（2 个三角形）

## 依赖关系

- `EdgeAAQuad` — 逐边 AA 四边形数据
- `StaticBufferManager` — 预计算顶点/索引缓冲区
- `DrawWriter` — GPU 缓冲区写入

## 设计模式与设计决策

### 无 uniform 设计

与 CoverBoundsRenderStep 类似，所有数据通过实例属性传递，最大化批处理效率。

### 静态几何模板

固定的顶点/索引模板在初始化时创建一次，所有实例共享。每个实例只需提供四边形坐标和 AA 标志。

### 覆盖率渐变

非 AA 边的覆盖率渐变区域塌缩为零面积，使 AA 和非 AA 边在同一着色器中统一处理，无需分支。

## 性能考量

- **单实例绘制**: 每个四边形仅一个实例
- **静态缓冲区共享**: 所有四边形共享预计算的几何模板
- **无 uniform 切换**: 所有变量数据在实例属性中
- **解析 AA**: 避免 MSAA 的多重采样开销
- **非 AA 内部填充**: `kUseNonAAInnerFill` 标志优化大面积四边形的内部像素

## 相关文件

- `src/gpu/graphite/geom/EdgeAAQuad.h` — EdgeAAQuad 数据结构
- `src/gpu/graphite/render/AnalyticRRectRenderStep.h` — 类似的解析距离场渲染步骤
- `src/gpu/graphite/RendererProvider.cpp` — 创建该渲染步骤
- `src/gpu/graphite/render/CommonDepthStencilSettings.h` — 深度模板设置
