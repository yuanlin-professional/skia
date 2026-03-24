# Tessellation

> 源文件:
> - `src/gpu/tessellate/Tessellation.h`
> - `src/gpu/tessellate/Tessellation.cpp`

## 概述

`Tessellation` 模块是 Skia GPU 渲染引擎中路径细分（tessellation）的核心基础设施。它定义了将贝塞尔曲线（二次曲线、圆锥曲线、三次曲线）转换为 GPU 可渲染的线段和三角形所需的常量、数据结构和算法。该模块同时服务于 Ganesh 和 Graphite 两套渲染后端，提供路径预切割（pre-chopping）、凸性分析、笔触参数编码等功能。

## 架构位置

```
Skia GPU 渲染层
  └── tessellate (曲线细分子系统)
        ├── Tessellation.h/cpp (核心常量、类型和算法)
        ├── WangsFormula.h (Wang 公式：计算所需线段数)
        ├── CullTest.h (视口裁剪测试)
        ├── PatchWriter.h (patch 数据写入器)
        └── 各种 Tessellator 实现
```

## 主要类与结构体

### `PatchAttribs`（位域枚举）
定义细分 patch 中可选的顶点属性：
- `kJoinControlPoint`：笔触连接控制点方向（float2）。
- `kFanPoint`：楔形扇中心点（float2）。
- `kStrokeParams`：笔触宽度和连接类型（float2）。
- `kColor`：颜色（ubyte4 或 float4）。
- `kPaintDepth`：Graphite 中的深度值（float）。
- `kExplicitCurveType`：显式曲线类型标识（float）。
- `kSsboIndex`：共享存储缓冲区索引（int）。
- `kWideColorIfEnabled`：标志，将颜色升级为 float4 宽色彩。

### `StrokeParams`
笔触参数数据结构，包含：
- `fRadius`：笔触半径（宽度的一半）。
- `fJoinType`：连接类型编码（负数=圆角、零=斜角、正数=斜接及其限制值）。

### `PathChopper`（内部类）
路径预切割器，使用栈式递归将路径中的曲线切割到可管理的线段数量内：
- 使用 Wang 公式评估曲线复杂度。
- 超出 `kMaxSegmentsPerCurve` 的曲线在 T=0.5 处二分切割。
- 完全在视口外的曲线扁平化为直线。
- 使用堆栈（`STArray`）代替运行时调用栈进行递归。

## 公共 API 函数

### 路径预处理
- **`PreChopPathCurves(float tessellationPrecision, const SkPath&, const SkMatrix&, const SkRect& viewport) -> SkPath`**：将路径中的曲线切割到每条曲线不超过 `kMaxSegmentsPerCurve`（1024）段。视口外的曲线被扁平化为直线。保留原始路径的填充类型。

### 曲线分析
- **`FindCubicConvex180Chops(const SkPoint[], float T[2], bool* areCusps) -> int`**：查找三次曲线的凸 180 度切割点。返回 0、1 或 2 个参数 T 值，确保切割后的曲线段是凸的且旋转不超过 180 度。`areCusps` 指示切割点是否为尖点。

- **`ConicHasCusp(const SkPoint p[3]) -> bool`**：检测圆锥曲线（或二次曲线）是否有尖点。尖点出现在退化的平直线段上，起止切线方向相反。

### 笔触辅助函数
- **`GetJoinType(const SkStrokeRec&) -> float`**：将连接类型编码为单个浮点数（-1=圆角，0=斜角，正数=斜接限制值）。
- **`StrokesHaveEqualParams(const SkStrokeRec&, const SkStrokeRec&) -> bool`**：比较两个笔触是否具有相同的参数。
- **`NumFixedEdgesInJoin(SkPaint::Join / const StrokeParams&) -> int`**：返回给定连接类型的固定边数（不含圆角的可变径向段）。
- **`CalcNumRadialSegmentsPerRadian(float approxDevStrokeRadius) -> float`**：计算每弧度的径向段数，用于笔触细分精度控制。

### 辅助计算
- **`NumCurveTrianglesAtResolveLevel(int resolveLevel) -> int`**：返回给定解析级别（2^resolveLevel 个线段）的三角形数量，为 `(1 << resolveLevel) - 1`。
- **`PatchAttribsStride(PatchAttribs) -> size_t`**：计算 patch 属性部分在 GPU 缓冲区中的字节大小。
- **`PatchStride(PatchAttribs) -> size_t`**：计算整个 patch 的字节步长（4 个控制点 + 属性）。

## 内部实现细节

### 精度常量体系
- `kPrecision = 4`：线性化段与真实曲线的最大偏差为 1/4 像素。
- `kMaxResolveLevel = 5`：固定计数缓冲区支持的最大细分级别。
- `kMaxParametricSegments = 32`（2^5）：单条曲线的最大参数段数。
- `kMaxSegmentsPerCurve = 1024`：允许的绝对最大段数，超过需要预切割。

### FindCubicConvex180Chops 算法
该算法使用三次曲线的幂基表示法：
1. 计算拐点函数 `F' x F'' = aT^2 + bT + c = 0` 的系数。
2. 计算判别式 `discr_over_4`：
   - 判别式 < 0（负值超过尖点阈值）：曲线无拐点，但可能旋转超过 180 度。通过求 `Tangent(T) x tan0 = 0` 找到 180 度旋转点。
   - 判别式接近零（在尖点阈值内）：视为单个尖点，取两根的平均值。如果曲线是完全平直的退化情况，则改为求切线与 tan0 垂直的点。
   - 判别式 > 0：有两个拐点/旋转点，通过二次方程求解。
3. 过滤掉距离端点过近（< kEpsilon = 1/2048）的切割点。

### PathChopper 递归机制
使用 `STArray` 作为显式栈，避免深递归导致的栈溢出：
- 二次曲线：每次切割产生 5 个点（2 段 x 3 点，共享中间点）。
- 圆锥曲线：除控制点外，还需要维护权重栈。
- 三次曲线：每次切割产生 7 个点（2 段 x 4 点，共享中间点）。
- 最大切割次数 `kMaxChopsPerCurve = 128 * 6 * 6 = 4608`，防止浮点精度问题导致的无限递归。

## 依赖关系

- **Skia 核心**: `SkPath`、`SkPathBuilder`、`SkMatrix`、`SkPoint`、`SkStrokeRec`、`SkPaint`
- **Skia 几何**: `SkGeometry`（曲线切割函数）、`SkConic`
- **GPU 细分**: `WangsFormula`（复杂度评估）、`CullTest`（视口裁剪）
- **SIMD 工具**: `SkVx`（skvx::float2/float4 向量运算）

## 设计模式与设计决策

1. **编译期常量体系**：精度、解析级别、最大段数等通过 `constexpr` 定义，编译器可进行常量折叠优化。
2. **位域属性系统**：`PatchAttribs` 使用位域枚举允许灵活组合不同的 patch 属性，编译期计算步长。
3. **栈式递归**：`PathChopper` 使用显式栈代替函数递归，避免大型路径的栈溢出风险。
4. **浮点精度防护**：`FindCubicConvex180Chops` 中使用精心选择的 epsilon 值和 IEEE 754 位运算进行范围检查，确保数值稳定性。
5. **连接类型编码**：将连接类型和斜接限制编码到单个 float 值中，减少 GPU 缓冲区中的属性数量。

## 性能考量

- **Wang 公式**：使用 Wang 公式的 p4/p2 变体（4 次方/2 次方形式）避免开方运算，与阈值比较时使用对应次方的阈值。
- **视口裁剪**：完全在视口外的曲线直接扁平化为直线，大幅减少不可见区域的细分开销。
- **二分切割**：在 T=0.5 处切割可使用 `SkChopQuadAtHalf` / `SkChopCubicAtHalf` 等优化版本。
- **SIMD 向量运算**：`FindCubicConvex180Chops` 使用 `skvx::float2` 进行并行的 2D 向量计算。
- **constexpr 步长计算**：`PatchAttribsStride` 和 `PatchStride` 为编译期函数，零运行时开销。

## 相关文件

- `src/gpu/tessellate/WangsFormula.h` - Wang 公式实现
- `src/gpu/tessellate/CullTest.h` - 视口裁剪测试
- `src/gpu/tessellate/PatchWriter.h` - Patch 数据写入
- `src/core/SkGeometry.h` - 曲线切割函数
- `src/base/SkVx.h` - SIMD 向量运算
