# SkPathOpsLine - 双精度直线段几何运算

> 源文件：[src/pathops/SkPathOpsLine.h](../../../../src/pathops/SkPathOpsLine.h)、[src/pathops/SkPathOpsLine.cpp](../../../../src/pathops/SkPathOpsLine.cpp)

## 概述

`SkDLine` 是 Skia 路径操作模块中双精度直线段的数学表示。它由两个双精度点（起点和终点）组成，提供了线段上的点求值、精确端点匹配、近似点投影等几何运算。该结构体是 PathOps 曲线类型家族中最简单的成员，主要用于与其他曲线类型的交叉检测和缠绕数计算中的射线测试。

## 架构位置

```
PathOps 曲线类型层
  ├── SkDLine  (2 点 - 直线) ← 本文件
  ├── SkDQuad  (3 点 - 二次曲线)
  ├── SkDConic (3 点 + 权重)
  └── SkDCubic (4 点 - 三次曲线)
```

`SkDLine` 是最基础的曲线类型。它被 `SkIntersections` 用于所有涉及直线的交点计算，被 `SkOpSegment` 表示直线段，也作为射线（ray）传递给各种交叉检测方法。

## 主要类与结构体

### `SkDLine`
双精度直线段。

**成员变量：**
- `fPts[2]`：两个 `SkDPoint` 端点。

## 公共 API 函数

### 点和索引访问
- `operator[](int n)`：按索引访问端点（0 或 1），有边界检查断言。提供 const 和非 const 版本。

### 初始化
- `set(const SkPoint pts[2])`：从 `SkPoint` 数组设置两个端点。返回自身引用以支持链式调用。

### 点求值
- `ptAtT(double t)`：计算参数 t 处的点。使用线性插值公式 `(1-t)*P0 + t*P1`。对 t=0 和 t=1 做快速路径返回。

### 精确点匹配
- `exactPoint(const SkDPoint& xy)`：检查点是否精确等于某个端点。等于 P0 返回 0.0，等于 P1 返回 1.0，否则返回 -1。优先测试更便宜的起点。
- `ExactPointH(xy, left, right, y)`：检查点是否精确匹配水平线段的端点。
- `ExactPointV(xy, top, bottom, x)`：检查点是否精确匹配垂直线段的端点。

### 近似点匹配
- `nearPoint(const SkDPoint& xy, bool* unequal)`：查找点到线段的最近投影。
  1. 先做边界框预检（使用 `AlmostBetweenUlps`）。
  2. 投影点到线段上，计算参数 t。
  3. 计算投影点与原始点的距离。
  4. 使用 ULPS 容差判断距离是否足够小。
  5. `unequal` 输出参数指示单精度下距离是否非零。
- `NearPointH(xy, left, right, y)`：计算点到水平线段的近似匹配参数。
- `NearPointV(xy, top, bottom, x)`：计算点到垂直线段的近似匹配参数。

### 射线近似判断
- `nearRay(const SkDPoint& xy)`：判断点是否近似在射线上（无需点在线段范围内）。与 `nearPoint` 类似但不限制 t 在 [0,1] 范围内，使用更宽松的 `RoughlyEqualUlps` 容差。

## 内部实现细节

### 垂直投影算法
`nearPoint()` 和 `nearRay()` 使用点到直线的垂直投影：
1. 计算线段方向向量 `len = P1 - P0`。
2. 计算分母 `denom = len.x^2 + len.y^2`（线段长度的平方）。
3. 计算分子 `numer = len.x * (xy.x - P0.x) + len.y * (xy.y - P0.y)`（点积）。
4. 参数 `t = numer / denom`。

### ULPS 容差判断
距离容差使用 ULPS（Units in the Last Place）方法：找到坐标中绝对值最大的分量 `largest`，然后检查 `AlmostEqualUlps(largest, largest + dist)`。这种方法使容差与数值的绝对大小成正比，适合处理不同量级的坐标值。

### 水平/垂直线段特化
`NearPointH` 和 `NearPointV` 方法针对轴对齐的线段进行了特化，直接从坐标差计算参数 t，避免了通用投影公式中的除零和精度问题。

## 依赖关系

- **SkDPoint / SkDVector**：双精度点和向量。
- **SkPathOpsTypes**：`AlmostBetweenUlps`、`AlmostBequalUlps`、`AlmostEqualUlps_Pin`、`RoughlyEqualUlps`、`SkPinT`、`between` 等精度比较和工具函数。

## 设计模式与设计决策

### 值类型结构体
与其他 PathOps 曲线类型一致，`SkDLine` 是简单的值类型结构体，无虚函数，支持高效的栈分配和复制。

### 分层匹配策略
精确匹配（`exactPoint`）和近似匹配（`nearPoint`）分为独立方法，允许调用者根据需要选择匹配精度。通常先尝试精确匹配，失败后再尝试近似匹配。

### 返回值约定
匹配函数返回 t 参数值表示成功（0.0 到 1.0），返回 -1 表示失败。这避免了使用 bool 返回值加输出参数的模式。

## 性能考量

- **端点快速路径**：`ptAtT` 对 t=0 和 t=1 直接返回端点。
- **边界框预检**：`nearPoint` 先做快速的范围检查，避免不必要的投影计算。
- **距离平方优化**：代码中多处注释标注了"OPTIMIZATION: can we compare against distSq instead?"，暗示 `sqrt` 调用是潜在的性能改进点。

## 相关文件

- `src/pathops/SkPathOpsPoint.h`：`SkDPoint` 和 `SkDVector` 定义。
- `src/pathops/SkPathOpsTypes.h`：精度比较函数。
- `src/pathops/SkIntersections.h`：使用 `SkDLine` 进行交点计算。
- `src/pathops/SkPathOpsCurve.h`：函数指针分发表中的直线相关条目。
