# SkPathOpsConic

> 源文件: src/pathops/SkPathOpsConic.h, src/pathops/SkPathOpsConic.cpp

## 概述

`SkPathOpsConic` 是 Skia PathOps 模块中处理有理二次贝塞尔曲线(圆锥曲线)的几何计算模块。圆锥曲线是带权重的二次贝塞尔曲线,可以精确表示圆、椭圆、抛物线和双曲线的弧段,是图形系统中表示圆弧的常用方法。

该模块定义了 `SkDConic` 结构体(双精度圆锥曲线)和 `SkTConic` 类(模板化包装器),提供了圆锥曲线的各种几何操作,包括求值、求导、分割、极值查找等。圆锥曲线的参数形式为:C(t) = [(1-t)²P₀ + 2(1-t)tωP₁ + t²P₂] / [(1-t)² + 2(1-t)tω + t²],其中 ω 是权重,t ∈ [0,1]。当 ω=1 时退化为普通的二次贝塞尔曲线。

## 架构位置

`SkPathOpsConic` 在 PathOps 架构中属于几何计算层,与其他曲线类型并列:

```
操作层 (SkPathOpsOp, SkPathOpsSimplify)
    ↓
协调层 (SkPathOpsCommon)
    ↓
数据结构层 (SkOpContour, SkOpSegment, SkOpSpan)
    ↓
几何计算层
    ├─ SkPathOpsCubic (三次曲线)
    ├─ SkPathOpsQuad (二次曲线)
    ├─ SkPathOpsConic ← 当前模块(圆锥曲线)
    ├─ SkPathOpsLine (直线)
    └─ SkPathOpsCurve (统一曲线接口)
    ↓
基础工具层 (SkPathOpsPoint, SkPathOpsRect)
```

## 主要类与结构体

### SkDConic (双精度圆锥曲线)

表示一个有理二次贝塞尔曲线,包含 3 个控制点和 1 个权重。

**核心常量:**
```cpp
static const int kPointCount = 3;       // 控制点数量
static const int kPointLast = 2;        // 最后一个点的索引
static const int kMaxIntersections = 4; // 最大交点数
```

**成员变量:**
- `SkDQuad fPts`: 3 个控制点(复用二次曲线的点存储)
- `SkScalar fWeight`: 权重值 ω

### SkTConic (模板化曲线包装器)

继承自 `SkTCurve`,提供统一的曲线接口。

**成员变量:**
- `SkDConic fConic`: 包装的圆锥曲线

## 公共 API 函数

### 曲线属性查询

#### collapsed
```cpp
bool collapsed() const
```
检查曲线是否折叠(3 个控制点近似相等)。委托给 `fPts.collapsed()`。

#### controlsInside
```cpp
bool controlsInside() const
```
检查控制点是否在端点之间。委托给 `fPts.controlsInside()`。

#### monotonicInX / monotonicInY
```cpp
bool monotonicInX() const
bool monotonicInY() const
```
检查曲线在 X 或 Y 方向是否单调。委托给 `fPts` 的对应方法。

#### isLinear
```cpp
bool isLinear(int startIndex, int endIndex) const
```
检查曲线是否接近直线。委托给 `fPts.isLinear()`。

#### IsConic (静态)
```cpp
static bool IsConic()
```
返回 true,表示这是圆锥曲线类型。

### 曲线求值与求导

#### ptAtT
```cpp
SkDPoint ptAtT(double t) const
```
计算参数 t 处的点坐标。使用有理贝塞尔曲线公式:
```
C(t) = [分子] / [分母]
分子 = (1-t)²P₀ + 2(1-t)tωP₁ + t²P₂
分母 = (1-t)² + 2(1-t)tω + t²
```
对 t=0 和 t=1 进行特殊优化,直接返回端点。使用 `sk_ieee_double_divide` 处理除零情况。

#### dxdyAtT
```cpp
SkDVector dxdyAtT(double t) const
```
计算参数 t 处的导数(切向量)。使用圆锥曲线的导数公式:
```
C'(t) = t(t·coeff[0] + coeff[1]) + coeff[2]
其中系数通过 conic_deriv_coeff 计算
```
对导数为零的退化情况,使用端点差向量作为替代。

### 曲线分割

#### subDivide
```cpp
SkDConic subDivide(double t1, double t2) const
void subDivide(double t1, double t2, SkDConic* c) const
SkDPoint subDivide(const SkDPoint& a, const SkDPoint& c,
                   double t1, double t2, SkScalar* weight) const
```
提取曲线在 [t1, t2] 区间的子曲线。实现步骤:
1. 计算端点 a 和 c 在齐次坐标系中的坐标(ax/az, ay/az)和(cx/cz, cy/cz)
2. 计算中点 d = C((t1+t2)/2)的齐次坐标(dx/dz, dy/dz)
3. 通过几何关系计算控制点 b 的齐次坐标:bx = 2dx - (ax+cx)/2
4. 计算新的权重:ω' = bz / √(az·cz)
5. 将齐次坐标转换回笛卡尔坐标

第三个版本只返回控制点和权重,用于调整已知端点的子曲线。

### 极值查找

#### FindExtrema (静态)
```cpp
static int FindExtrema(const double src[], SkScalar weight, double t[1])
```
查找曲线在某一坐标(X 或 Y)上的极值点。通过求解导数为零的方程得到。使用 `conic_deriv_coeff` 计算导数系数,然后求解二次方程。

圆锥曲线的导数是一个二次多项式,因此最多有 1 个极值点(在有效区间内)。

### 根查找

#### RootsReal / RootsValidT (静态)
```cpp
static int RootsReal(double A, double B, double C, double t[2])
static int RootsValidT(const double A, const double B, const double C, double s[2])
```
求解二次方程的根。直接委托给 `SkDQuad::RootsReal` 和 `SkDQuad::RootsValidT`,因为圆锥曲线的导数是二次多项式。

#### AddValidTs (静态)
```cpp
static int AddValidTs(double s[], int realRoots, double* t)
```
过滤并添加 [0,1] 区间内的有效根。委托给 `SkDQuad::AddValidTs`。

### 凸包相交检测

#### hullIntersects
```cpp
bool hullIntersects(const SkDQuad& quad, bool* isLinear) const
bool hullIntersects(const SkDConic& conic, bool* isLinear) const
bool hullIntersects(const SkDCubic& cubic, bool* isLinear) const
```
检查与其他曲线的凸包是否相交。大部分实现委托给 `fPts` 或对方曲线的 `hullIntersects` 方法。

### 辅助函数

#### flip
```cpp
SkDConic flip() const
```
翻转曲线方向(交换端点,保持控制点和权重不变)。

#### align
```cpp
void align(int endIndex, SkDPoint* dstPt) const
```
对齐点坐标。委托给 `fPts.align()`。

#### set
```cpp
const SkDConic& set(const SkPoint pts[kPointCount], SkScalar weight)
```
从 SkPoint 数组和权重设置圆锥曲线。

#### otherPts
```cpp
void otherPts(int oddMan, const SkDPoint* endPt[2]) const
```
获取除指定点外的其他点。委托给 `fPts.otherPts()`。

## 内部实现细节

### 齐次坐标表示

圆锥曲线内部使用齐次坐标进行计算:
- 笛卡尔坐标 (x, y) 对应齐次坐标 (x, y, 1)
- 有理点 (x/w, y/w) 对应齐次坐标 (x, y, w)

这种表示避免了除法运算,提高了数值稳定性。

### 导数系数计算

`conic_deriv_coeff` 函数计算导数的系数:
```cpp
static void conic_deriv_coeff(const double src[], SkScalar w, double coeff[3]) {
    const double P20 = src[4] - src[0];
    const double P10 = src[2] - src[0];
    const double wP10 = w * P10;
    coeff[0] = w * P20 - P20;      // (ω-1)P20
    coeff[1] = P20 - 2 * wP10;     // P20 - 2ωP10
    coeff[2] = wP10;               // ωP10
}
```

导数在参数 t 处的值为:C'(t) = t²·coeff[0] + t·coeff[1] + coeff[2]

### 分子和分母求值

有理贝塞尔曲线的求值分为两步:
1. **分子计算**(`conic_eval_numerator`):
   ```cpp
   numerator(t) = C + (B)t + (A)t²
   其中 C = src[0]
        A = src[4] - 2·ω·src[2] + C
        B = 2(ω·src[2] - C)
   ```

2. **分母计算**(`conic_eval_denominator`):
   ```cpp
   denominator(t) = C + (B)t + (A)t²
   其中 C = 1
        A = -(2ω - 2) = 2(1 - ω)
        B = 2(ω - 1)
   ```

最终点坐标为:P(t) = numerator(t) / denominator(t)

### 子曲线权重计算

子曲线的权重计算基于几何关系。设原曲线在 t=0.5 处的点为 d,子曲线的端点为 a 和 c,控制点为 b,则:
```
d = C((t1+t2)/2)
b = 2d - (a+c)/2  (在齐次坐标中)
ω' = bz / √(az·cz)
```

这个公式保证了子曲线在 t=0.5 处的点与原曲线在 (t1+t2)/2 处的点相同。

### 退化处理

当权重接近某些特殊值时:
- ω=1: 退化为普通二次贝塞尔曲线
- ω=0: 控制点无效,曲线退化为直线
- bz=0: 在 `subDivide` 中设置 bz=1,任何值都可以(因为控制点无影响)

## 依赖关系

### 头文件依赖
- `include/core/SkPoint.h`: 点类型
- `include/core/SkScalar.h`: 标量类型
- `src/pathops/SkPathOpsPoint.h`: PathOps 点类型
- `src/pathops/SkPathOpsQuad.h`: 二次曲线(复用点存储和部分方法)
- `src/pathops/SkPathOpsTCurve.h`: 模板曲线基类
- `src/pathops/SkIntersections.h`: 交点计算
- `src/pathops/SkPathOpsCubic.h`: 三次曲线(凸包相交)
- `src/pathops/SkPathOpsRect.h`: 矩形和边界
- `src/pathops/SkPathOpsTypes.h`: PathOps 类型定义

### 类依赖
- **SkDQuad**: 复用点存储、求根方法和部分几何方法
- **SkDCubic**: 凸包相交检测
- **SkIntersections**: 交点存储和计算
- **SkTCurve**: 统一曲线接口基类

## 设计模式与设计决策

### 组合而非继承

`SkDConic` 包含 `SkDQuad fPts` 而非继承自 `SkDQuad`:
- 圆锥曲线和二次曲线在语义上不是 is-a 关系
- 组合允许选择性地委托方法
- 避免了虚函数的开销

### 静态方法委托

许多静态方法直接委托给 `SkDQuad`:
- `RootsReal`, `RootsValidT`, `AddValidTs`
- 避免代码重复
- 利用二次曲线的成熟实现

### 齐次坐标计算

在 `subDivide` 中使用齐次坐标:
- 避免中间结果的除法
- 提高数值稳定性
- 更准确的权重计算

### 权重的特殊处理

权重为 1 时,圆锥曲线退化为二次曲线:
- 分母 = 1,分子 = 二次贝塞尔公式
- 代码自动处理这种退化情况
- 不需要特殊分支

### 极值数量限制

圆锥曲线的 `FindExtrema` 只返回最多 1 个极值点:
- 有理二次曲线的导数是二次多项式
- 二次多项式最多有 2 个根,但通常只有 1 个在 [0,1] 内
- 注释中提到极端情况可能返回 2 个根,但 Pathops 会在后续处理

## 性能考量

### 内联候选

小型访问器和委托方法定义在头文件中,可内联:
- `operator[]`, `collapsed()`, `controlsInside()`
- `monotonicInX()`, `monotonicInY()`
- `IsConic()`, `maxIntersections()`

### 特殊值优化

- `ptAtT`: 对 t=0 和 t=1 特殊处理,避免复杂计算
- `subDivide`: 对 t1=0, t1=1, t2=0, t2=1 进行优化

### IEEE 除法保护

使用 `sk_ieee_double_divide` 而非直接除法:
- 正确处理除零情况
- 返回 IEEE 标准的无穷大或 NaN
- 避免崩溃

### 避免重复计算

- `conic_deriv_coeff`: 预计算导数系数
- `subDivide`: 复用中点和端点的计算结果

### 权重特殊情况处理

```cpp
if (!bz) {
    bz = 1;  // 如果 bz 为 0,权重为 0,控制点无效:任何值都可以
}
```
避免除零,提高鲁棒性。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/pathops/SkPathOpsQuad.h/cpp` | 依赖 | 二次曲线,复用点存储和求根方法 |
| `src/pathops/SkPathOpsCubic.h/cpp` | 相关 | 三次曲线,凸包相交 |
| `src/pathops/SkPathOpsLine.h/cpp` | 相关 | 直线,退化情况 |
| `src/pathops/SkPathOpsCurve.h/cpp` | 被依赖 | 统一曲线接口 |
| `src/pathops/SkPathOpsTCurve.h` | 依赖 | 模板曲线基类 |
| `src/pathops/SkPathOpsPoint.h` | 依赖 | 点和向量类型 |
| `src/pathops/SkPathOpsRect.h` | 依赖 | 矩形和边界 |
| `src/pathops/SkIntersections.h/cpp` | 被依赖 | 交点计算 |
| `src/pathops/SkOpSegment.h/cpp` | 被依赖 | 使用圆锥曲线的线段 |
| `src/pathops/SkPathOpsTypes.h` | 依赖 | PathOps 类型定义 |
| `src/core/SkGeometry.h/cpp` | 相关 | 圆锥曲线的浮点版本 |
| `include/core/SkPoint.h` | 依赖 | Skia 点类型 |
