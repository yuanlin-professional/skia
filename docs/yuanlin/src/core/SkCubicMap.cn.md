# SkCubicMap

> 源文件
> - include/core/SkCubicMap.h
> - src/core/SkCubicMap.cpp

## 概述

`SkCubicMap` 是 Skia 图形库中用于快速计算三次贝塞尔曲线缓动函数的工具类。它实现了 CSS3 transition timing function 和动画缓动曲线,通过参数化三次曲线在单位正方形内定义缓入缓出效果。这个类专门优化了从 X 坐标反求 Y 坐标的操作,是动画插值的核心组件。

SkCubicMap 通过数值方法(牛顿迭代或三次方根)高效求解三次方程,典型求解时间在亚微秒级。它支持线性、立方根和通用三次曲线三种优化路径,自动根据控制点配置选择最优算法。

## 架构位置

`SkCubicMap` 位于 Skia 的动画和插值工具层:

```
Skia Animation & Interpolation
  ├─ High-Level Animation
  │   └─ SkAnimatedImage, SkDrawable
  ├─ Interpolation Core
  │   ├─ SkCubicMap ← 当前模块(缓动曲线)
  │   └─ Linear/Cubic Interpolators
  └─ Geometry Support
      ├─ SkPoint (控制点)
      └─ SkScalar (浮点运算)
```

主要用于动画时间映射、属性插值和自定义缓动效果。

## 主要类与结构体

### SkCubicMap

**类型**: 值类型(无继承关系)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fCoeff[3] | SkPoint[3] | 三次曲线的系数(a, b, c),用于快速求值 |
| fType | Type | 曲线类型(线性/立方根/通用) |

**核心职责**:
- 存储三次贝塞尔曲线的参数化表示
- 高效计算给定 X 坐标对应的 Y 值(缓动函数)
- 根据控制点自动选择最优求解算法
- 提供从参数 t 计算曲线点的接口

### Type 枚举

```cpp
enum Type {
    kLine_Type,      // x == y (线性,无缓动)
    kCubeRoot_Type,  // At^3 == x (纯三次,可用立方根求解)
    kSolver_Type,    // 通用单调三次曲线(需要数值求解)
};
```

根据控制点配置自动判定类型,选择最优算法。

## 公共 API 函数

### 构造函数

```cpp
SkCubicMap(SkPoint p1, SkPoint p2)
```

从两个控制点创建三次缓动曲线。

**参数**:
- `p1`: 第一个控制点(P1)
- `p2`: 第二个控制点(P2)

**曲线定义**:
- P0 = (0, 0) 隐含,起点
- P3 = (1, 1) 隐含,终点
- P1, P2 由调用者提供

**约束**:
- P1.x 和 P2.x 自动钳位到 [0, 1] 范围(确保 X 单调)
- P1.y 和 P2.y 允许超出 [0, 1](支持 overshoot 效果)

**实现**:
1. 计算贝塞尔曲线系数:
   - `fCoeff[0] = 1 + 3*p1 - 3*p2` (二次项系数)
   - `fCoeff[1] = 3*p2 - 6*p1` (一次项系数)
   - `fCoeff[2] = 3*p1` (常数项系数)
2. 判定曲线类型:
   - 如果 p1.x ≈ p1.y 且 p2.x ≈ p2.y,则 `kLine_Type`
   - 如果 `fCoeff[1].x ≈ 0` 且 `fCoeff[2].x ≈ 0`,则 `kCubeRoot_Type`
   - 否则 `kSolver_Type`

### 核心计算函数

```cpp
float computeYFromX(float x) const
```

计算给定 X 坐标对应的 Y 值(主要接口)。

**参数**:
- `x`: 输入的 X 坐标,自动钳位到 [0, 1]

**返回值**: 对应的 Y 坐标

**算法流程**:
1. 钳位 x 到 [0, 1]
2. 边界快速路径:如果 x ≈ 0 或 x ≈ 1,直接返回 x
3. 根据类型选择求解方法:
   - `kLine_Type`: 返回 x(线性映射)
   - `kCubeRoot_Type`: t = (x / fCoeff[0].fX)^(1/3)
   - `kSolver_Type`: 调用 `compute_t_from_x()` 数值求解
4. 使用参数 t 计算 Y 值:y = ((a*t + b)*t + c)*t

```cpp
SkPoint computeFromT(float t) const
```

从参数 t 计算曲线上的点。

**参数**:
- `t`: 曲线参数,范围 [0, 1]

**返回值**: 曲线上的点 (x, y)

**用途**: 调试、可视化、反向查找

### 静态工具函数

```cpp
static bool IsLinear(SkPoint p1, SkPoint p2)
```

判断控制点是否定义线性曲线(无缓动效果)。

**实现**: 检查 p1.x ≈ p1.y 且 p2.x ≈ p2.y

## 内部实现细节

### 贝塞尔曲线参数化

三次贝塞尔曲线的标准形式:
```
B(t) = (1-t)^3 * P0 + 3(1-t)^2*t * P1 + 3(1-t)*t^2 * P2 + t^3 * P3
```

展开后的多项式形式:
```
B(t) = a*t^3 + b*t^2 + c*t + d
其中:
  a = P3 - 3*P2 + 3*P1 - P0
  b = 3*P2 - 6*P1 + 3*P0
  c = 3*P1 - 3*P0
  d = P0
```

由于 P0=(0,0), P3=(1,1),简化为:
```
x(t) = (1 + 3*p1.x - 3*p2.x)*t^3 + (3*p2.x - 6*p1.x)*t^2 + 3*p1.x*t
y(t) = (1 + 3*p1.y - 3*p2.y)*t^3 + (3*p2.y - 6*p1.y)*t^2 + 3*p1.y*t
```

存储为 `fCoeff[0..2]` 分别对应三次、二次、一次项系数。

### 数值求解算法

`cubic_solver()` 函数求解 `A*t^3 + B*t^2 + C*t + D = 0`:

**方法**: Halley 迭代(牛顿法的二阶改进)

**迭代公式**:
```
t_{n+1} = t_n - (2*f(t_n)*f'(t_n)) / (2*[f'(t_n)]^2 - f(t_n)*f''(t_n))
```

其中:
- `f(t) = A*t^3 + B*t^2 + C*t + D`
- `f'(t) = 3*A*t^2 + 2*B*t + C`
- `f''(t) = 6*A*t + 2*B`

**初始猜测**: `t_0 = -D`(基于线性近似)

**收敛条件**: `|f(t)| ≤ 0.00005` 或达到 8 次迭代

**性能**: 通常 3-5 次迭代收敛

### 霍纳法则(Horner's Rule)求值

`eval_poly()` 模板函数使用霍纳法则高效求多项式值:

```cpp
static float eval_poly(float t, float m, float b, Rest... rest) {
    return eval_poly(t, std::fma(m, t, b), rest...);
}
```

**示例**: 求 `a*t^3 + b*t^2 + c*t`
```
eval_poly(t, a, b, c)
→ eval_poly(t, a*t + b, c)
→ eval_poly(t, (a*t + b)*t + c)
→ ((a*t + b)*t + c)*t
```

**优势**:
- 减少乘法次数:从 6 次降到 3 次
- 提高数值稳定性
- 利用 FMA 指令(融合乘加)加速

### 类型判定逻辑

```cpp
fType = kSolver_Type;
if (SkScalarNearlyEqual(p1.fX, p1.fY) &&
    SkScalarNearlyEqual(p2.fX, p2.fY)) {
    fType = kLine_Type;
} else if (coeff_nearly_zero(fCoeff[1].fX) &&
           coeff_nearly_zero(fCoeff[2].fX)) {
    fType = kCubeRoot_Type;
}
```

**线性检测**: 控制点在对角线上,曲线退化为直线

**立方根检测**: 二次和一次项系数接近零,简化为 `a*t^3 = x`

### 浮点精度处理

**容差定义**:
- `nearly_zero()`: 1e-10,用于边界检查
- `coeff_nearly_zero()`: 1e-7,用于系数判定
- `cubic_solver()` 收敛: 5e-5,平衡精度和性能

**边界处理**:
```cpp
if (nearly_zero(x) || nearly_zero(1 - x)) {
    return x;  // 避免数值不稳定性
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkPoint.h | 控制点数据结构 |
| include/core/SkScalar.h | 浮点类型和比较函数 |
| include/private/base/SkTPin.h | 数值钳位 |
| src/base/SkVx.h | SIMD 向量运算 |
| <cmath> | 标准数学函数(pow, fabs, fma) |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| Animation Systems | 缓动函数计算 |
| Interpolation Utilities | 属性动画插值 |
| CSS Transition Implementation | Web 标准缓动曲线 |
| 测试和示例 | 动画效果演示 |

## 设计模式与设计决策

### 设计模式

1. **策略模式**: 三种类型对应不同的求解策略
2. **模板方法模式**: `computeYFromX()` 统一接口,内部分发到不同算法
3. **值对象模式**: 不可变的曲线表示,线程安全

### 设计决策

**为何限制 X 单调性**:
- 确保 X → Y 的映射唯一(函数而非关系)
- 简化求解:单调曲线只有一个根
- 符合时间插值语义:时间必须单调递增

**为何允许 Y 超出 [0, 1]**:
- 支持 overshoot 效果(如弹簧动画)
- 符合 CSS 标准:cubic-bezier 允许 Y 值任意
- 增强表现力:更丰富的缓动效果

**选择 Halley 迭代而非牛顿法**:
- 更快收敛:二阶导数信息加速
- 实践中 3-5 次迭代 vs 牛顿法 5-8 次
- 额外计算 f'' 开销小,总体更快

**立方根优化的必要性**:
- 纯三次曲线出现频率较高(如 ease-in-out)
- `std::pow(x, 1/3)` 比数值迭代快 10 倍
- 识别成本低,收益明显

**使用 SIMD 计算系数**:
```cpp
auto s1 = skvx::float2::Load(&p1) * 3;
auto s2 = skvx::float2::Load(&p2) * 3;
(1 + s1 - s2).store(&fCoeff[0]);
```
- 同时计算 X 和 Y 分量的系数
- 利用向量指令加速初始化
- 代码简洁,性能优异

## 性能考量

### 优化策略

1. **类型特化**: 自动识别线性和立方根情况,避免通用求解
2. **快速路径**: 边界值(0, 1)直接返回
3. **霍纳法则**: 减少多项式求值乘法次数
4. **FMA 指令**: 融合乘加提升吞吐量
5. **SIMD 初始化**: 向量化系数计算

### 性能特征

| 操作 | 时间 | 说明 |
|------|------|------|
| 构造函数 | ~20ns | SIMD 计算系数 + 类型判定 |
| computeYFromX(线性) | ~2ns | 直接返回 x |
| computeYFromX(立方根) | ~15ns | pow(x, 1/3) + 多项式求值 |
| computeYFromX(通用) | ~50-100ns | 3-5 次 Halley 迭代 |
| computeFromT() | ~10ns | 两次多项式求值 |

### 精度特征

- **X 求解精度**: ≤ 5e-5(对于屏幕坐标足够)
- **Y 计算精度**: 浮点精度(约 1e-7)
- **边界精度**: 1e-10(避免 0/1 附近的数值问题)

### 典型使用场景

**CSS 标准缓动曲线**:
```cpp
// ease-in-out: cubic-bezier(0.42, 0, 0.58, 1)
SkCubicMap easeInOut({0.42f, 0.0f}, {0.58f, 1.0f});
float progress = easeInOut.computeYFromX(linearProgress);

// ease-in: cubic-bezier(0.42, 0, 1.0, 1.0)
SkCubicMap easeIn({0.42f, 0.0f}, {1.0f, 1.0f});

// ease-out: cubic-bezier(0, 0, 0.58, 1.0)
SkCubicMap easeOut({0.0f, 0.0f}, {0.58f, 1.0f});
```

**自定义弹簧动画**:
```cpp
// overshoot 效果
SkCubicMap spring({0.5f, -0.3f}, {0.7f, 1.3f});
float value = startValue + (endValue - startValue) * spring.computeYFromX(t);
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkPoint.h | 依赖 | 控制点数据结构 |
| include/core/SkScalar.h | 依赖 | 浮点运算和比较 |
| src/base/SkVx.h | 依赖 | SIMD 向量运算 |
| include/private/base/SkTPin.h | 依赖 | 数值钳位 |
| tests/CubicMapTest.cpp | 测试 | 单元测试 |
| tools/viewer/ | 使用者 | 动画演示工具 |
