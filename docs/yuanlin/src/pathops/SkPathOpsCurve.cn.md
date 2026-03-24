# SkPathOpsCurve - 曲线类型统一接口与函数表

> 源文件：[src/pathops/SkPathOpsCurve.h](../../../../src/pathops/SkPathOpsCurve.h)、[src/pathops/SkPathOpsCurve.cpp](../../../../src/pathops/SkPathOpsCurve.cpp)

## 概述

`SkPathOpsCurve` 提供了 PathOps 模块中不同曲线类型（直线、二次、圆锥、三次曲线）的统一联合体表示和函数指针分发表。通过 `SkDCurve` 联合体和一系列以 `SkPath::Verb` 为索引的函数指针数组，实现了对不同曲线类型的运行时多态调用，包括点求值、导数计算、垂直性判断、射线交叉和水平/垂直截距计算等操作。

## 架构位置

```
PathOps 模块
  ├── 具体曲线类型 (SkDLine, SkDQuad, SkDConic, SkDCubic)
  ├── SkPathOpsCurve (统一接口层) ← 本文件
  │     ├── SkOpCurve   (SkPoint 精度的曲线存储)
  │     ├── SkDCurve    (SkDPoint 精度的曲线联合体)
  │     ├── SkDCurveSweep (曲线扫掠方向)
  │     └── 函数指针分发表 (CurvePointAtT, CurveSlopeAtT, ...)
  └── 上层调用者 (SkOpSegment, SkOpAngle, SkOpCoincidence, ...)
```

该文件是 PathOps 模块的"胶水层"，让上层代码能够以统一的方式处理不同类型的曲线，而不需要到处编写 `switch(verb)` 分支。

## 主要类与结构体

### `SkOpCurve`
单精度（SkPoint）存储的曲线。

**成员变量：**
- `fPts[4]`：最多 4 个控制点（覆盖三次曲线）。
- `fWeight`：圆锥曲线权重。
- `fVerb`（仅调试）：记录实际曲线类型。

提供从 `SkDQuad` 和 `SkDCubic` 的转换方法 `set()`。

### `SkDCurve`
双精度联合体，能存储任意类型的曲线。

**联合体成员：**
- `fLine`：`SkDLine` - 2 点直线。
- `fQuad`：`SkDQuad` - 3 点二次曲线。
- `fConic`：`SkDConic` - 3 点圆锥曲线（带权重）。
- `fCubic`：`SkDCubic` - 4 点三次曲线。

**方法：**
- `operator[](int n)`：统一的控制点访问（始终通过 fCubic 成员访问，因为它有最多的点）。
- `nearPoint(verb, xy, opp)`：查找曲线上距离给定点最近的位置。
- `conicTop/cubicTop/lineTop/quadTop`：查找曲线在指定参数范围内的最高点。
- `setConicBounds/setCubicBounds/setQuadBounds`：计算曲线子段的边界框。

### `SkDCurveSweep`
曲线扫掠方向分析。

**成员：**
- `fCurve`：`SkDCurve` 联合体。
- `fSweep[2]`：两个扫掠向量。
- `fIsCurve`：是否为真正的曲线（非退化线段）。
- `fOrdered`：控制点是否在扫掠向量之间有序排列。

`setCurveHullSweep(verb)` 方法计算曲线的凸包扫掠方向，用于角度排序算法。对三次曲线有特殊处理：检查第三个扫掠向量是否在前两个之间。

## 公共 API 函数

### 函数指针分发表
以 `SkPath::Verb` 枚举值为索引的函数指针数组（索引 0=none, 1=line, 2=quad, 3=conic, 4=cubic）：

**双精度点求值：**
- `CurveDPointAtT[verb](pts, weight, t)`：计算 SkPoint 曲线在参数 t 处的 SkDPoint。
- `CurveDDPointAtT[verb](curve, t)`：计算 SkDCurve 在参数 t 处的 SkDPoint。

**单精度点求值：**
- `CurvePointAtT[verb](pts, weight, t)`：计算 SkPoint 曲线在参数 t 处的 SkPoint。

**导数（斜率）计算：**
- `CurveDSlopeAtT[verb](pts, weight, t)`：返回 SkDVector 导数。
- `CurveDDSlopeAtT[verb](curve, t)`：从 SkDCurve 计算 SkDVector 导数。
- `CurveSlopeAtT[verb](pts, weight, t)`：返回 SkVector 导数。

**垂直性判断：**
- `CurveIsVertical[verb](pts, weight, startT, endT)`：判断曲线子段是否垂直。

**射线交叉：**
- `CurveIntersectRay[verb](pts, weight, ray, intersections)`：计算 SkPoint 曲线与射线的交点。
- `CurveDIntersectRay[verb](curve, ray, intersections)`：计算 SkDCurve 与射线的交点。

**水平/垂直截距：**
- `CurveIntercept[verb*2+h/v](pts, weight, coord, roots)`：计算曲线与水平线或垂直线的截距参数。

### `SkDCurve` 方法
- `nearPoint(verb, xy, opp)`：通过构造垂线射线并与曲线求交，找到最近点。先做边界框快速排除，然后选择距离最小的交点。使用 ULPS 容差判断距离是否足够小。
- `setConicBounds/setCubicBounds/setQuadBounds`：通过双精度边界框计算后转换为单精度 `SkPathOpsBounds`。

### `Top[]` 函数指针数组
`extern` 声明的函数指针数组，用于查找曲线最高点（最小 Y 值）。

## 内部实现细节

### 函数指针分发模式
所有函数指针数组在头文件中声明为 `static`（在每个包含该头文件的编译单元中创建一份副本）。每个数组的第 0 个元素为 `nullptr`（对应 `SkPath::kMove_Verb`），后续元素依次对应 line、quad、conic、cubic。

每个分发包装函数的实现非常简洁：
```cpp
static SkDPoint dquad_xy_at_t(const SkPoint a[3], SkScalar, double t) {
    SkDQuad quad;
    quad.set(a);
    return quad.ptAtT(t);
}
```
创建临时对象、设置数据、调用方法，然后返回结果。`SkScalar` 参数（权重）仅在圆锥曲线中使用。

### nearPoint 垂线射线法
`SkDCurve::nearPoint` 通过以下步骤找到曲线上最近点：
1. 边界框检查：如果点不在曲线边界框内（带 ULPS 容差），直接返回 -1。
2. 构造垂线射线：以目标点为起点，方向为 `(opp.y-xy.y, xy.x-opp.x)`（垂直于 xy-opp 方向）。
3. 与曲线求交：使用 `CurveDIntersectRay` 获取所有交点。
4. 选择最近交点：遍历交点找距离最小的。
5. 容差检查：使用 `AlmostEqualUlps_Pin` 判断距离是否在 ULPS 容差内。
6. 返回交点参数 t（经 `SkPinT` 钳位到 [0,1]）。

### 凸包扫掠分析
`setCurveHullSweep` 计算曲线从起点出发的两个扫掠向量：
- 对线段：两个扫掠向量相同，`fIsCurve = false`。
- 对二次/圆锥曲线：`fSweep[0] = P1-P0`，`fSweep[1] = P2-P0`。
- 对三次曲线：还需考虑第三个向量 `P3-P0`。如果第三个向量不在前两个之间，需要调整扫掠方向并标记 `fOrdered = false`。

当扫掠向量近似为零时（与曲线最大坐标值相比），使用后续的扫掠向量替代，确保不出现零向量。

### 截距计算
`CurveIntercept` 数组使用交错索引（verb*2 + h/v）来同时存储水平和垂直截距函数。这种设计允许通过计算索引直接选择正确的函数。

## 依赖关系

- **SkDLine / SkDQuad / SkDConic / SkDCubic**：具体的曲线类型实现。
- **SkIntersections**：射线交叉计算和水平/垂直截距。
- **SkPathOpsTypes**：精度比较函数和辅助工具。
- **SkPathOpsBounds**：单精度边界框。
- **SkPathOpsRect**：双精度边界框。

## 设计模式与设计决策

### 函数指针分发 vs 虚函数
选择函数指针数组而非虚函数，因为：
1. 曲线类型是值类型（struct），不应有虚函数表。
2. 函数指针表提供了基于 `SkPath::Verb` 枚举的直接索引访问。
3. 避免了虚函数调用的间接性，同时保持了灵活性。

### 联合体存储
`SkDCurve` 使用 C++ union 而非继承体系来存储不同类型的曲线。这保证了内存布局的紧凑性（最大成员的大小），且所有成员的控制点数组具有相同的起始偏移，允许通过 `fCubic[n]` 统一访问。

### 双精度和单精度的双版本
为每种操作提供双精度（`SkDPoint`）和单精度（`SkPoint`）两套接口，满足不同精度需求。核心计算使用双精度避免精度损失，最终输出转换为单精度。

## 性能考量

- **函数指针分发零分支**：通过数组索引直接跳转到目标函数，无需 switch/case 分支。
- **内联静态函数**：分发包装函数声明为 `static`，编译器可进行内联优化。
- **边界框预检**：`nearPoint` 先做快速的边界框排除，避免不必要的射线交叉计算。
- **临时对象开销**：每次调用创建临时曲线对象并设置数据，对于频繁调用的场景可能有一定开销。

## 相关文件

- `src/pathops/SkPathOpsLine.h`：直线类型。
- `src/pathops/SkPathOpsQuad.h`：二次曲线类型。
- `src/pathops/SkPathOpsConic.h`：圆锥曲线类型。
- `src/pathops/SkPathOpsCubic.h`：三次曲线类型。
- `src/pathops/SkPathOpsPoint.h`：双精度点和向量。
- `src/pathops/SkPathOpsBounds.h`：单精度边界框。
- `src/pathops/SkPathOpsRect.h`：双精度边界框。
- `src/pathops/SkIntersections.h`：交点计算。
