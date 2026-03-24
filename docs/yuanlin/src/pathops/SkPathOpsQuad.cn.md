# SkPathOpsQuad - 二次贝塞尔曲线数学运算

> 源文件：[src/pathops/SkPathOpsQuad.h](../../../../src/pathops/SkPathOpsQuad.h)、[src/pathops/SkPathOpsQuad.cpp](../../../../src/pathops/SkPathOpsQuad.cpp)

## 概述

`SkPathOpsQuad` 定义了路径操作模块中二次贝塞尔曲线的双精度数学表示和运算。核心结构体 `SkDQuad` 使用 3 个双精度点表示一条二次曲线，提供了点求值、导数计算、子分割、凸包交叉检测、求根、极值查找等完整的几何运算。此外，`SkTQuad` 类作为 `SkTCurve` 多态接口的实现，将 `SkDQuad` 封装为可在通用曲线算法中使用的类型。

## 架构位置

```
PathOps 曲线类型层
  ├── SkDLine    (2 点 - 直线)
  ├── SkDQuad    (3 点 - 二次曲线) ← 本文件
  ├── SkDConic   (3 点 + 权重 - 圆锥曲线)
  └── SkDCubic   (4 点 - 三次曲线)

多态接口层
  └── SkTCurve (基类)
        ├── SkTQuad  ← 本文件
        ├── SkTConic
        └── SkTCubic
```

`SkDQuad` 是 PathOps 中使用最频繁的曲线类型之一。它被 `SkIntersections` 用于交点计算，被 `SkOpSegment` 用于段的数学表示，被 `SkPathOpsTSect` 用于 T-区间细分求交。

## 主要类与结构体

### `SkDQuad`
核心二次曲线结构体。

**常量：**
- `kPointCount = 3`：控制点数量。
- `kPointLast = 2`：最后一个点的索引。
- `kMaxIntersections = 4`：两条二次曲线间的最大交点数。

**成员变量：**
- `fPts[3]`：三个双精度控制点（起点、控制点、终点）。
- `fDebugGlobalState`：调试用的全局状态指针。

### `SkDQuadPair`
二次曲线分割结果，包含 5 个点，可通过 `first()` 和 `second()` 分别获取两条子曲线。利用相邻曲线共享分割点的特性，5 个点表示两条 3 点曲线。

### `SkTQuad`
`SkTCurve` 多态接口的二次曲线实现。包装 `SkDQuad`，提供虚函数实现：点求值、导数、凸包交叉、射线交叉、子分割、边界框计算等。

## 公共 API 函数

### 构造与初始化
- `set(const SkPoint pts[])`：从 SkPoint 数组设置控制点，同时可选择性设置调试全局状态。
- `flip()`：返回控制点顺序反转的副本。
- `debugInit()`：将所有控制点清零。

### 点和导数求值
- `ptAtT(double t)`：使用贝塞尔公式 `(1-t)^2*P0 + 2t(1-t)*P1 + t^2*P2` 计算曲线上参数 t 对应的点。对 t=0 和 t=1 做了快速路径优化。
- `dxdyAtT(double t)`：计算参数 t 处的切线向量（一阶导数）。当导数为零时回退到端点差值。

### 凸包交叉检测
- `hullIntersects(const SkDQuad&, bool*)`：通过旋转所有点到由一对控制点形成的线上来快速判断凸包是否相交。返回 false 表示曲线最多在端点相交。`isLinear` 输出参数表示曲线的凸包是否退化为线段。
- `hullIntersects(const SkDConic&, bool*)` / `hullIntersects(const SkDCubic&, bool*)`：与其他曲线类型的凸包交叉检测（委托给对方实现）。

### 求根
- `RootsReal(double A, double B, double C, double s[2])`：求解一般二次方程 `Ax^2 + Bx + C = 0` 的实根。使用 Numerical Solutions 5.6 建议的方法，通过 `Q = -1/2(B + sgn(B)*sqrt(B^2-4AC))` 避免精度损失。
- `RootsValidT(double A, double B, double C, double t[2])`：求解二次方程并过滤出 [0,1] 范围内的有效根。
- `AddValidTs(double s[], int realRoots, double* t)`：将原始根过滤为有效 t 值，处理边界值钳位和近似相等的去重。

### 交叉检测
- `horizontalIntersect(double y, double roots[2])`：计算与水平线 y 的交点参数值。
- `verticalIntersect(double x, double roots[2])`：计算与垂直线 x 的交点参数值。

### 几何查询
- `collapsed()`：检查三个控制点是否近似重合（退化曲线）。
- `controlsInside()`：检查控制点是否在起止点之间（凸包不自交）。
- `isLinear(int, int)`：使用线参数检查曲线是否近似为直线。
- `monotonicInX()` / `monotonicInY()`：检查曲线是否在 X/Y 方向上单调。
- `otherPts(int oddMan, const SkDPoint* endPt[2])`：给定一个点的索引，返回另外两个点的指针。使用位操作技巧高效计算索引。

### 子分割
- `subDivide(double t1, double t2)`：提取 [t1, t2] 参数范围内的子曲线。使用中点插值法计算新的控制点。
- `subDivide(const SkDPoint& a, const SkDPoint& c, double t1, double t2)`：给定端点约束的子分割，通过射线交叉计算新控制点。
- `chopAt(double t)`：在参数 t 处将曲线切分为两条子曲线，返回 `SkDQuadPair`。

### 其他
- `align(int endIndex, SkDPoint* dstPt)`：如果端点与控制点在某坐标上相等，则对齐结果点以避免浮点误差。
- `FindExtrema(const double src[], double tValue[1])`：求导数为零的极值点参数。
- `SetABC(const double* quad, double* a, double* b, double* c)`：将贝塞尔参数化形式转换为标准多项式系数。

## 内部实现细节

### 凸包交叉的分离轴测试
`hullIntersects` 使用分离轴定理的变体：对于每个"奇数人"（控制点），构造由另外两个点形成的线段，检查第二条曲线的所有点是否在线段的同侧。如果任一方向上所有点都在同侧且与奇数人不同侧，则凸包不相交。

当凸包退化为近线性时，额外执行三角形内点测试（`pointInTriangle`），避免漏检。

### 数值稳定的二次方程求根
`RootsReal` 方法将标准二次方程 `Ax^2 + Bx + C = 0` 转换为正规形式 `x^2 + px + q = 0`，使用 `p^2 - q` 代替标准判别式 `B^2 - 4AC`，减少了大数相减的精度损失。使用 `AlmostDequalUlps` 处理判别式接近零的边界情况。

### 子分割的中点法
`subDivide(t1, t2)` 通过以下步骤计算子曲线：
1. 求 A = 曲线在 t1 处的点。
2. 求 D = 曲线在 (t1+t2)/2 处的中点。
3. 求 C = 曲线在 t2 处的点。
4. 由 D = A/4 + B/2 + C/4 反推 B = 2D - A/2 - C/2。

### 带约束的子分割
`subDivide(a, c, t1, t2)` 方法在给定精确端点时计算控制点，通过构造两条辅助射线并求其交点来确定 B 点。当射线平行时回退为中点。

## 依赖关系

- **SkDPoint / SkDVector**：双精度点和向量。
- **SkPathOpsCubic**：三次曲线类型（用于凸包交叉和 `debugToCubic` 转换）。
- **SkPathOpsConic**：圆锥曲线类型（凸包交叉委托）。
- **SkPathOpsLine**：直线类型。
- **SkPathOpsRect**：边界框计算。
- **SkIntersections**：射线交叉用于约束子分割。
- **SkLineParameters**：线参数化，用于线性度判断。
- **SkTCurve**：多态曲线基类。
- **SkArenaAlloc**：`SkTQuad::make` 使用的内存分配器。

## 设计模式与设计决策

### 值类型结构体
`SkDQuad` 设计为值类型（struct），支持高效复制和栈分配。没有虚函数，没有堆分配，适合在紧密循环中频繁创建和销毁。

### 多态包装
`SkTQuad` 作为 `SkTCurve` 的具体实现提供虚函数接口。这种包装模式允许通用算法（如 T-区间细分）操作不同类型的曲线，同时保持值类型的高效性。

### 静态工厂方法
`SubDivide` 和 `RootsReal` 等静态方法提供了不需要先构造对象的便利接口。

### 双重交叉调度
凸包交叉检测使用双重分发：`SkDQuad::hullIntersects(SkDConic&)` 委托给 `SkDConic::hullIntersects(SkDQuad&)`，确保每种曲线对只需实现一次交叉逻辑。

## 性能考量

- **端点快速路径**：`ptAtT` 对 t=0 和 t=1 直接返回控制点，避免不必要的乘法运算。
- **位操作索引**：`otherPts` 使用异或和移位操作替代分支计算索引。
- **避免归一化**：`isLinear` 中的注释指出可能可以避免归一化操作，暗示这是一个性能敏感的位置。
- **早期返回**：凸包交叉检测在找到分离轴后立即返回 false，避免不必要的计算。

## 相关文件

- `src/pathops/SkPathOpsPoint.h`：`SkDPoint` 和 `SkDVector` 定义。
- `src/pathops/SkPathOpsConic.h`：圆锥曲线类型。
- `src/pathops/SkPathOpsCubic.h`：三次曲线类型。
- `src/pathops/SkPathOpsLine.h`：直线类型。
- `src/pathops/SkPathOpsTCurve.h`：`SkTCurve` 多态基类。
- `src/pathops/SkPathOpsRect.h`：边界框操作。
- `src/pathops/SkLineParameters.h`：线参数化工具。
- `src/pathops/SkPathOpsTSect.h`：使用多态曲线的 T-区间细分算法。
