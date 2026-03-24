# SkPathOpsCubic

> 源文件: src/pathops/SkPathOpsCubic.h, src/pathops/SkPathOpsCubic.cpp

## 概述

`SkPathOpsCubic` 是 Skia PathOps 模块中专门处理三次贝塞尔曲线的几何计算模块。该模块定义了 `SkDCubic` 结构体(双精度三次曲线)、`SkDCubicPair`(曲线分割后的对)以及 `SkTCubic` 类(模板化的曲线包装器),提供了三次贝塞尔曲线的各种几何操作,包括求值、求导、分割、求根、极值计算、拐点查找、曲率分析等。

三次贝塞尔曲线是路径操作中最复杂的曲线类型,其形式为:C(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃,其中 t ∈ [0,1]。该模块提供了计算曲线交点、检测凸包相交、查找拐点、计算最大曲率等关键功能,是路径布尔运算和简化算法的重要基础。

## 架构位置

`SkPathOpsCubic` 在 PathOps 架构中属于几何计算层:

```
操作层 (SkPathOpsOp, SkPathOpsSimplify)
    ↓
协调层 (SkPathOpsCommon)
    ↓
数据结构层 (SkOpContour, SkOpSegment, SkOpSpan)
    ↓
几何计算层
    ├─ SkPathOpsCubic ← 当前模块(三次曲线)
    ├─ SkPathOpsQuad (二次曲线)
    ├─ SkPathOpsConic (圆锥曲线)
    ├─ SkPathOpsLine (直线)
    └─ SkPathOpsCurve (统一曲线接口)
    ↓
基础工具层 (SkPathOpsPoint, SkPathOpsRect)
```

该模块为上层的交点计算、路径追踪等算法提供三次曲线的几何计算支持。

## 主要类与结构体

### SkDCubic (双精度三次曲线)

表示一个三次贝塞尔曲线,使用 double 精度存储 4 个控制点。

**核心常量:**
```cpp
static const int kPointCount = 4;       // 控制点数量
static const int kPointLast = 3;        // 最后一个点的索引
static const int kMaxIntersections = 9; // 最大交点数
static const int gPrecisionUnit = 256;  // 精度单位
```

**成员变量:**
- `SkDPoint fPts[kPointCount]`: 4 个控制点
- `SkOpGlobalState* fDebugGlobalState`: 调试用全局状态(仅 Debug 模式)

**核心枚举:**
```cpp
enum SearchAxis {
    kXAxis,  // 沿 X 轴搜索
    kYAxis   // 沿 Y 轴搜索
};
```

### SkDCubicPair (曲线对)

存储曲线分割后的两条子曲线。

**成员变量:**
- `SkDPoint pts[7]`: 7 个点,前 4 个构成第一条曲线,后 4 个构成第二条曲线(中间点共享)

**关键方法:**
- `SkDCubic first() const`: 返回第一条子曲线(点 0-3)
- `SkDCubic second() const`: 返回第二条子曲线(点 3-6)

### SkTCubic (模板化曲线包装器)

继承自 `SkTCurve`,提供统一的曲线接口,使得不同类型的曲线(直线、二次、三次、圆锥)可以通过相同的接口使用。

**成员变量:**
- `SkDCubic fCubic`: 包装的三次曲线

## 公共 API 函数

### 曲线属性查询

#### collapsed
```cpp
bool collapsed() const
```
检查曲线是否折叠(4 个控制点近似相等)。

#### controlsInside
```cpp
bool controlsInside() const
```
检查两个控制点是否在端点之间。通过计算向量点积判断控制点是否在端点连线的同侧。

#### endsAreExtremaInXOrY
```cpp
bool endsAreExtremaInXOrY() const
```
检查端点是否是 X 或 Y 方向的极值点(控制点在端点之间)。

#### monotonicInX / monotonicInY
```cpp
bool monotonicInX() const
bool monotonicInY() const
```
检查曲线在 X 或 Y 方向是否单调(控制点在端点之间)。

#### isLinear
```cpp
bool isLinear(int startIndex, int endIndex) const
```
检查曲线是否接近直线。计算控制点到端点连线的距离,如果距离相对于曲线尺度足够小则认为是直线。

### 曲线求值与求导

#### ptAtT
```cpp
SkDPoint ptAtT(double t) const
```
计算参数 t 处的点坐标。使用贝塞尔曲线的标准公式:
```
C(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
```
对 t=0 和 t=1 进行特殊优化,直接返回端点。

#### dxdyAtT
```cpp
SkDVector dxdyAtT(double t) const
```
计算参数 t 处的导数(切向量)。使用导数公式:
```
C'(t) = 3(b-a)(1-t)² + 6(c-b)t(1-t) + 3(d-c)t²
```
对于导数为零的退化情况,使用端点差向量作为替代。

### 曲线分割

#### chopAt
```cpp
SkDCubicPair chopAt(double t) const
```
在参数 t 处将曲线分割为两条子曲线。对 t=0.5 进行优化,使用简化公式。一般情况使用递归中点细分算法(De Casteljau 算法)。

#### subDivide
```cpp
SkDCubic subDivide(double t1, double t2) const
void subDivide(double t1, double t2, SkDCubic* c) const
void subDivide(const SkDPoint& a, const SkDPoint& d,
               double t1, double t2, SkDPoint p[2]) const
```
提取曲线在 [t1, t2] 区间的子曲线。第三个版本计算子曲线的控制点,并根据给定的端点 a 和 d 进行调整。

### 极值与拐点

#### FindExtrema (静态)
```cpp
static int FindExtrema(const double src[], double tValue[2])
```
查找曲线在某一坐标(X 或 Y)上的极值点。通过求解导数 C'(t)=0 得到极值参数。导数是二次多项式:
```
C'(t) = At² + Bt + C
其中 A = d - a + 3(b - c)
     B = 2(a - 2b + c)
     C = b - a
```
返回 [0,1] 区间内的有效极值点数量。

#### findInflections
```cpp
int findInflections(double tValues[2]) const
```
查找曲线的拐点(曲率符号改变的点)。通过求解曲线的二阶导数叉积为零的方程得到。拐点是曲线从凹变凸或从凸变凹的位置。

#### findMaxCurvature
```cpp
int findMaxCurvature(double tValues[]) const
```
查找曲线的最大曲率点。曲率表示曲线弯曲的程度,最大曲率点是曲线最弯曲的位置。通过求解 F'·F'' = 0 得到候选点。

### 根查找

#### RootsReal (静态)
```cpp
static int RootsReal(double A, double B, double C, double D, double s[3])
```
求解三次方程 Ax³ + Bx² + Cx + D = 0 的实根。实现了完整的三次方程求根算法:
1. 检查退化情况(A≈0 时退化为二次方程)
2. 检查特殊根(0 或 1)
3. 使用 Cardano 公式求解一般情况
4. 根据判别式 R² - Q³ 判断有 3 个实根还是 1 个实根

#### RootsValidT (静态)
```cpp
static int RootsValidT(const double A, const double B,
                       const double C, double D, double s[3])
```
求解三次方程并过滤出 [0,1] 区间内的有效根。对接近 0 或 1 的根进行容差处理。

#### horizontalIntersect / verticalIntersect
```cpp
int horizontalIntersect(double yIntercept, double roots[3]) const
int verticalIntersect(double xIntercept, double roots[3]) const
```
计算曲线与水平或垂直线的交点参数。返回 [0,1] 区间内的有效交点数。

#### searchRoots
```cpp
int searchRoots(double extremes[6], int extrema, double axisIntercept,
                SearchAxis xAxis, double* validRoots) const
```
在极值点和拐点划分的区间中搜索与坐标轴交点。结合极值点、拐点和二分搜索,提高根查找的鲁棒性。

#### binarySearch
```cpp
double binarySearch(double min, double max, double axisIntercept,
                    SearchAxis xAxis) const
```
使用二分法在 [min, max] 区间内搜索与坐标轴的交点。当其他方法失败时的回退策略。

### 凸包相交检测

#### hullIntersects
```cpp
bool hullIntersects(const SkDCubic& c2, bool* isLinear) const
bool hullIntersects(const SkDQuad& quad, bool* isLinear) const
bool hullIntersects(const SkDConic& conic, bool* isLinear) const
bool hullIntersects(const SkDPoint* pts, int ptCount, bool* isLinear) const
```
检查两条曲线的凸包是否相交。快速剔除不相交的曲线对,避免昂贵的精确交点计算。算法通过旋转坐标系,检查一条曲线的点是否都在另一条曲线凸包的同一侧。

### 辅助函数

#### Coefficients (静态)
```cpp
static void Coefficients(const double* cubic, double* A, double* B,
                        double* C, double* D)
```
将三次贝塞尔曲线转换为多项式系数形式:Ax³ + Bx² + Cx + D。

#### ComplexBreak (静态)
```cpp
static int ComplexBreak(const SkPoint pts[4], SkScalar* t)
```
分析复杂曲线(环、蛇形、尖点等)并找到合适的分割点。用于将复杂曲线分解为更简单的片段:
1. 如果曲线在 X 和 Y 上都单调,无需分割
2. 对于环状曲线,找到环的中心点
3. 对于蛇形、尖点等,查找拐点或最大曲率点

#### calcPrecision
```cpp
double calcPrecision() const
```
计算曲线的粗略尺度。通过计算控制点间的距离之和除以精度单位得到。用于确定曲线是否有极端曲率。

#### convexHull
```cpp
int convexHull(char order[kPointCount]) const
```
计算曲线控制点的凸包(未在头文件中声明,可能在 cpp 文件中实现)。返回凸包顶点的索引顺序。

#### align
```cpp
void align(int endIndex, int ctrlIndex, SkDPoint* dstPt) const
```
对齐点坐标。如果端点和控制点在某一坐标上相等,则将目标点的该坐标设置为端点的值。用于修正浮点误差。

#### toFloatPoints
```cpp
bool toFloatPoints(SkPoint*) const
```
将双精度点转换为单精度 SkPoint。将极小值(小于 FLT_EPSILON_ORDERABLE_ERR)设置为 0,并检查有效性。

#### top
```cpp
double top(const SkDCubic& dCurve, double startT, double endT, SkDPoint* topPt) const
```
在 [startT, endT] 区间内查找最上方(Y 最小)的点。遍历 Y 方向的极值点,找到 Y 值最小的点。

## 内部实现细节

### De Casteljau 算法

`chopAt` 和 `subDivide` 使用递归中点细分算法:

```cpp
static void interp_cubic_coords(const double* src, double* dst, double t) {
    double ab = SkDInterp(src[0], src[2], t);
    double bc = SkDInterp(src[2], src[4], t);
    double cd = SkDInterp(src[4], src[6], t);
    double abc = SkDInterp(ab, bc, t);
    double bcd = SkDInterp(bc, cd, t);
    double abcd = SkDInterp(abc, bcd, t);
    // abcd 是曲线在参数 t 处的点
}
```

该算法对 X 和 Y 坐标分别应用,生成分割后的控制点。

### 三次方程求根

使用 Cardano 公式求解三次方程:
1. 将方程化为标准形式:x³ + ax² + bx + c = 0
2. 计算判别式:Q = (a² - 3b)/9, R = (2a³ - 9ab + 27c)/54
3. 根据 R² - Q³ 的符号判断根的类型:
   - R² < Q³: 3 个不同的实根(使用三角方法)
   - R² ≥ Q³: 1 个实根和 2 个复根(使用代数方法)

### 导数计算

使用公式:C'(t) = 3(b-a)(1-t)² + 6(c-b)t(1-t) + 3(d-c)t²

特殊处理:
- 当导数为 (0,0) 且 t=0 时,使用 P₂ - P₀
- 当导数为 (0,0) 且 t=1 时,使用 P₃ - P₁
- 如果仍为 (0,0) 且 t 为 0 或 1,使用 P₃ - P₀

### 拐点计算

拐点是二阶导数叉积为零的点。设:
```
A = P₁ - P₀
B = P₂ - 2P₁ + P₀
C = P₃ + 3(P₁ - P₂) - P₀
```

求解二次方程:
```
(Bₓ·Cᵧ - Bᵧ·Cₓ)t² + (Aₓ·Cᵧ - Aᵧ·Cₓ)t + (Aₓ·Bᵧ - Aᵧ·Bₓ) = 0
```

### 最大曲率计算

曲率由 F' 和 F'' 的叉积幅值决定。最大曲率点满足 F'·F'' = 0。设:
```
A = P₁ - P₀
B = P₂ - 2P₁ + P₀
C = P₃ - 3P₂ + 3P₁ - P₀
```

导数:F' = 3Ct² + 6Bt + 3A
二阶导数:F'' = 6Ct + 6B

F'·F'' = C·Ct³ + 3B·Ct² + (2B·B + C·A)t + A·B = 0

### 凸包相交算法

1. 计算第一条曲线的凸包(按逆时针顺序排列顶点)
2. 对凸包的每条边:
   - 计算该边对应的直线方程
   - 确定曲线其他点相对于直线的方向(符号)
   - 检查第二条曲线的所有点是否都在直线的同一侧
3. 如果找到一条边使得第二条曲线的所有点都在同侧,则凸包不相交

### 子曲线提取算法

`subDivide(t1, t2)` 使用几何方法:
1. 计算端点 A = C(t1), D = C(t2)
2. 计算两个参考点 E = C((2t1+t2)/3), F = C((t1+2t2)/3)
3. 通过线性方程组求解控制点 B 和 C:
   ```
   B = (M*2 - N)/18
   C = (N*2 - M)/18
   其中 M = E*27 - A*8 - D
        N = F*27 - A - D*8
   ```

## 依赖关系

### 头文件依赖
- `include/core/SkPoint.h`: 点类型
- `include/core/SkScalar.h`: 标量类型
- `include/core/SkTypes.h`: 基础类型
- `src/pathops/SkPathOpsPoint.h`: PathOps 点类型
- `src/pathops/SkPathOpsTCurve.h`: 模板曲线基类
- `src/core/SkGeometry.h`: 几何工具
- `src/pathops/SkIntersections.h`: 交点计算
- `src/pathops/SkLineParameters.h`: 直线参数
- `src/pathops/SkPathOpsQuad.h`: 二次曲线
- `src/pathops/SkPathOpsConic.h`: 圆锥曲线
- `src/pathops/SkPathOpsRect.h`: 矩形

### 算法依赖
- **SkDQuad**: 用于退化情况和求根
- **SkGeometry**: 曲线分类(SkClassifyCubic)
- **SkIntersections**: 交点存储和计算
- **SkLineParameters**: 线性检测

## 设计模式与设计决策

### 值语义设计

`SkDCubic` 是一个 POD 结构体,使用值语义:
- 没有虚函数,可以按值传递和复制
- 所有操作都是 const 方法,不修改原对象
- 返回新对象而不是修改自身

### 静态方法设计

大量使用静态方法(如 `RootsReal`, `FindExtrema`, `ComplexBreak`):
- 不需要实例即可调用
- 清晰地表明方法不依赖对象状态
- 便于作为独立的数学函数使用

### 多态包装器

`SkTCubic` 作为 `SkDCubic` 的多态包装器:
- 继承 `SkTCurve` 基类,提供统一接口
- 允许不同曲线类型通过基类指针使用
- 使用组合而非继承,保持 `SkDCubic` 的简单性

### 精度单位设计

使用 `gPrecisionUnit = 256` 作为精度基准:
- 将曲线尺度归一化到合理范围
- 用于判断数值是否足够小(相对于曲线尺度)
- 常量可以通过测试框架调整

### 特殊情况优化

对常见特殊情况进行优化:
- `ptAtT`: t=0 或 t=1 直接返回端点
- `chopAt`: t=0.5 使用简化公式
- `subDivide`: t1=0 或 t2=1 使用 chopAt

### 退化处理

妥善处理各种退化情况:
- `RootsReal`: A≈0 时退化为二次方程
- `dxdyAtT`: 导数为零时使用端点差向量
- `isLinear`: 端点相同时检查二次曲线

### 容差设计

使用多级容差函数:
- `approximately_zero`: 绝对容差
- `approximately_zero_when_compared_to`: 相对容差
- `precisely_between`: 严格区间判断
- `roughly_between`: 宽松区间判断

## 性能考量

### 内联候选

小型访问器定义在头文件中,可内联:
- `operator[]`: 索引访问
- `collapsed()`: 简单属性检查
- `IsConic()`: 常量返回

### 分支预测

对常见情况优先判断:
- `ptAtT`: 先检查 t=0 和 t=1
- `chopAt`: 先检查 t=0.5

### 缓存友好

数据结构紧凑:
- `fPts[4]` 连续存储,缓存局部性好
- `SkDCubicPair` 的 7 个点连续存储

### 算法选择

根据精度和性能权衡选择算法:
- 一般情况使用 De Casteljau(稳定但较慢)
- t=0.5 使用直接公式(快速)
- 根查找先尝试解析方法,失败时使用二分法

### 避免重复计算

- `searchRoots`: 先计算极值和拐点,在区间内搜索
- `subDivide`: 复用中间计算结果

### 浮点优化

- 将极小值(< FLT_EPSILON_ORDERABLE_ERR)置零
- 对接近 0 或 1 的值进行舍入
- 使用 ULP 比较避免浮点误差

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/pathops/SkPathOpsQuad.h/cpp` | 相关 | 二次曲线,退化情况和求根 |
| `src/pathops/SkPathOpsConic.h/cpp` | 相关 | 圆锥曲线,凸包相交 |
| `src/pathops/SkPathOpsLine.h/cpp` | 相关 | 直线,线性检测 |
| `src/pathops/SkPathOpsCurve.h/cpp` | 被依赖 | 统一曲线接口 |
| `src/pathops/SkPathOpsTCurve.h` | 依赖 | 模板曲线基类 |
| `src/pathops/SkPathOpsPoint.h` | 依赖 | 点和向量类型 |
| `src/pathops/SkPathOpsRect.h` | 依赖 | 矩形和边界 |
| `src/pathops/SkIntersections.h/cpp` | 被依赖 | 交点计算 |
| `src/pathops/SkLineParameters.h` | 依赖 | 直线参数,线性检测 |
| `src/pathops/SkOpSegment.h/cpp` | 被依赖 | 使用三次曲线的线段 |
| `src/core/SkGeometry.h/cpp` | 依赖 | 曲线分类和几何工具 |
| `include/core/SkPoint.h` | 依赖 | Skia 点类型 |
| `src/base/SkTSort.h` | 依赖 | 排序算法 |
