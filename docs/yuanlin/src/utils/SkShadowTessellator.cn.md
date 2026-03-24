# SkShadowTessellator - 阴影网格化器

> 源文件:
> - `src/utils/SkShadowTessellator.h`
> - `src/utils/SkShadowTessellator.cpp`

## 概述

SkShadowTessellator 是 Skia 中负责将路径 (SkPath) 转换为阴影三角形网格 (SkVertices) 的核心模块。它实现了两种阴影类型的网格化：**环境光阴影 (Ambient Shadow)** 和 **聚光灯阴影 (Spot Shadow)**。该模块根据路径形状、变换矩阵和光照参数生成带颜色的三角形顶点数据，以供 GPU 或 CPU 渲染器直接使用。

该模块仅在未定义 `SK_ENABLE_OPTIMIZE_SIZE` 时编译，表明它属于非精简构建中的高级渲染功能。

## 架构位置

```
Skia 渲染管线
├── SkCanvas (绘制入口)
│   └── SkShadowUtils (阴影绘制高层 API)
│       └── SkShadowTessellator (本模块 - 阴影几何体生成)
│           ├── SkBaseShadowTessellator (基类)
│           ├── SkAmbientShadowTessellator (环境光阴影)
│           └── SkSpotShadowTessellator (聚光灯阴影)
├── SkVertices (输出的三角形网格)
└── GPU/CPU 渲染后端 (消费 SkVertices)
```

该模块处于阴影渲染管线的中间层，上层由 `SkShadowUtils` 调用，下层输出 `SkVertices` 供渲染后端消费。

## 主要类与结构体

### `SkShadowTessellator` 命名空间
- 定义公共 API，提供 `MakeAmbient` 和 `MakeSpot` 两个工厂函数。
- 定义了 `HeightFunc` 类型：`std::function<SkScalar(SkScalar, SkScalar)>`，用于高度函数回调。

### `SkBaseShadowTessellator` (内部基类)
- 所有阴影网格化器的基类，包含通用的几何处理逻辑。
- **成员变量**：
  - `fZPlaneParams` (SkPoint3): Z 平面参数，定义高度函数 `z = fX*x + fY*y + fZ`。
  - `fPositions` (SkTDArray\<SkPoint\>): 输出顶点位置数组。
  - `fColors` (SkTDArray\<SkColor\>): 输出顶点颜色数组 (umbra 为黑色, penumbra 为透明)。
  - `fIndices` (SkTDArray\<uint16_t\>): 三角形索引数组。
  - `fPathPolygon`: 路径转换后的多边形顶点。
  - `fClipPolygon`/`fClipVectors`: 裁剪多边形和向量 (用于聚光灯阴影)。
  - `fCentroid`: 多边形质心坐标。
  - `fIsConvex`: 凸性标记。
  - `fSucceeded`: 操作成功标记。
  - `fTransparent`: 是否需要填充中心区域。
- **关键常量**：
  - `kMinHeight = 0.1f`: 最小高度限制。
  - `kPenumbraColor = SK_ColorTRANSPARENT`: 半影颜色 (完全透明)。
  - `kUmbraColor = SK_ColorBLACK`: 本影颜色 (完全不透明黑色)。

### `SkAmbientShadowTessellator`
- 继承自 `SkBaseShadowTessellator`，负责环境光阴影网格化。
- 根据 `AmbientBlurRadius` 和 `AmbientRecipAlpha` 计算 outset/inset。
- 私有方法 `computePathPolygon()` 遍历路径生成多边形。

### `SkSpotShadowTessellator`
- 继承自 `SkBaseShadowTessellator`，负责聚光灯阴影网格化。
- 额外处理光源位置、光源半径和方向性参数。
- 生成裁剪多边形和路径多边形。
- 私有方法 `computeClipAndPathPolygons()` 同时生成裁剪和路径多边形。

## 公共 API 函数

### `SkShadowTessellator::MakeAmbient`
```cpp
sk_sp<SkVertices> MakeAmbient(const SkPath& path, const SkMatrix& ctm,
                              const SkPoint3& zPlane, bool transparent);
```
- **功能**: 为路径生成环境光阴影网格。
- **参数**:
  - `path`: 需要生成阴影的路径。
  - `ctm`: 当前变换矩阵 (Current Transform Matrix)。
  - `zPlane`: Z 平面参数向量 (fX, fY, fZ)，用于计算路径上各点的高度。
  - `transparent`: 是否填充阴影中心区域。
- **返回值**: 包含三角形网格的 `SkVertices`，失败时返回 nullptr。
- **输入验证**: 检查变换后的边界矩形和 zPlane 的有限性。

### `SkShadowTessellator::MakeSpot`
```cpp
sk_sp<SkVertices> MakeSpot(const SkPath& path, const SkMatrix& ctm,
                           const SkPoint3& zPlane, const SkPoint3& lightPos,
                           SkScalar lightRadius, bool transparent, bool directional);
```
- **功能**: 为路径生成聚光灯阴影网格。
- **参数**:
  - `path`, `ctm`, `zPlane`: 同上。
  - `lightPos`: 光源位置 (x, y, z)。
  - `lightRadius`: 光源半径。
  - `transparent`: 是否填充阴影中心区域。
  - `directional`: 是否为方向性光源。
- **返回值**: 同上。
- **输入验证**: 额外检查光源位置、高度和半径的有效性。

## 内部实现细节

### 路径到多边形的转换
基类提供了将各种路径元素转换为多边形点的方法：
- `handleLine()`: 处理直线段，进行点坐标规范化（钳制到最近的 1/16 像素）。
- `handleQuad()`: 处理二次贝塞尔曲线。在 Ganesh 后端使用 `GrPathUtils` 进行精确细分；在非 Ganesh 后端则简化为折线段。
- `handleCubic()`: 处理三次贝塞尔曲线，策略同上。
- `handleConic()`: 处理圆锥曲线，先转换为二次曲线再处理。

### 凸性检测与质心计算
- `accumulateCentroid()`: 利用叉积累加面积和质心坐标，同时判断凸性。
- `checkConvexity()`: 通过相邻边的叉积检测凸性。
- `finishPathPolygon()`: 闭合多边形、计算最终质心、确定绕行方向。

### 凸形阴影生成 (`computeConvexShadow`)
1. 计算内缩多边形 (umbra) 和外扩多边形 (penumbra)。
2. 处理内缩多边形坍缩的情况：降低内缩量并调整颜色透明度。
3. 遍历路径多边形，为每条边生成外环四边形。
4. 在相邻边的拐角处生成弧形三角扇形。
5. 处理裁剪 (用于聚光灯阴影)。

### 凹形阴影生成 (`computeConcaveShadow`)
1. 验证多边形简单性 (`SkIsSimplePolygon`)。
2. 使用 `SkOffsetSimplePolygon` 生成内缩和外扩多边形。
3. 通过 `stitchConcaveRings()` 方法将内外环缝合为三角形条带。
4. 对于透明阴影，使用 `SkTriangulateSimplePolygon` 对内环进行三角化。

### 聚光灯阴影的特殊处理
- 使用 `SkDrawShadowMetrics::GetSpotShadowTransform` 计算阴影变换矩阵和模糊半径。
- 同时生成裁剪多边形（基于原始路径在 CTM 下的形状）和路径多边形（在阴影变换下的形状）。
- 在曲线上取额外的中间点以提高裁剪精度。

### 辅助函数
- `compute_normal()`: 计算两点之间的单位法向量。
- `duplicate_pt()`: 判断两点是否"近似重合"（距离小于 1/16 像素）。
- `perp_dot()`: 计算由三点定义的两向量的叉积。
- `sanitize_point()`: 将坐标规范化到最近的 1/16 像素。

## 依赖关系

### 核心依赖
- `include/core/SkPath.h`: 输入路径。
- `include/core/SkVertices.h`: 输出顶点数据。
- `include/core/SkMatrix.h`: 变换矩阵。
- `include/core/SkPoint3.h`: 3D 点（光源位置、Z 平面参数）。

### 内部依赖
- `src/core/SkDrawShadowInfo.h`: 阴影度量计算（模糊半径、缩放比等）。
- `src/core/SkGeometry.h`: 圆锥曲线到二次曲线的转换 (`SkAutoConicToQuads`)。
- `src/core/SkPointPriv.h`: 点距离计算工具。
- `src/utils/SkPolyUtils.h`: 多边形内缩/外扩操作 (`SkInsetConvexPolygon`, `SkOffsetSimplePolygon`, `SkIsSimplePolygon`, `SkTriangulateSimplePolygon`)。
- `src/core/SkColorData.h`: 颜色插值 (`SkPMLerp`)。

### 条件依赖
- `src/gpu/ganesh/geometry/GrPathUtils.h` (SK_GANESH): 更精确的曲线细分。

## 设计模式与设计决策

1. **模板方法模式**: `SkBaseShadowTessellator` 提供算法框架，子类 (`SkAmbientShadowTessellator`, `SkSpotShadowTessellator`) 实现特定的路径遍历和参数计算。

2. **凸/凹分治策略**: 凸形路径使用高效的环形网格生成算法；凹形路径退化为更通用但更复杂的偏移多边形缝合算法。

3. **渐进式降级**: 当内缩多边形坍缩时，不是直接失败，而是减少内缩量并通过颜色插值补偿视觉效果。使用 `fValidUmbra` 标记回退到基于质心的近似方案。

4. **坐标规范化**: 所有输入点被钳制到 1/16 像素精度，避免浮点精度问题导致的拓扑错误。

5. **预分配策略**: 根据路径点数预估并预分配顶点和索引数组的容量。

## 性能考量

1. **条件编译**: 当定义 `SK_ENABLE_OPTIMIZE_SIZE` 时整个模块被跳过，用于嵌入式或体积受限的构建。

2. **曲线细分精度**: Ganesh 后端使用更精确的曲线细分 (`GrPathUtils`)，而非 Ganesh 后端使用粗糙的折线近似，在质量和性能之间做了平衡。

3. **最近点搜索优化**: `getClosestUmbraIndex()` 使用单向遍历策略而非暴力搜索，利用空间相关性减少比较次数。

4. **内存分配模式**: 使用 `SkTDArray` 作为动态数组并调用 `reserve()` 预分配内存，减少重新分配次数。预估公式为顶点 4-5 倍路径点数、索引 12-15 倍路径点数。

5. **弧形步进优化**: `addArc()` 使用旋转矩阵迭代生成弧形点，避免重复的三角函数计算。

## 相关文件

- `src/core/SkDrawShadowInfo.h` / `.cpp`: 阴影度量和参数计算。
- `src/utils/SkPolyUtils.h` / `.cpp`: 多边形几何操作工具。
- `include/core/SkVertices.h`: 输出的顶点网格类。
- `include/core/SkPath.h`: 输入路径类。
- `src/core/SkShadowUtils.cpp`: 阴影绘制入口，调用本模块。
- `src/gpu/ganesh/geometry/GrPathUtils.h`: Ganesh 后端的路径细分工具。
