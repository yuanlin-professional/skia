# SkBezierCurves

> 源文件: `src/base/SkBezierCurves.h`, `src/base/SkBezierCurves.cpp`

## 概述

SkBezierCurves 提供三次和二次贝塞尔曲线的数学运算,包括曲线求值、细分、多项式转换和与水平线求交。这些工具用于 Skia 的路径渲染、字体光栅化和动画曲线计算,是图形几何运算的核心组件。

## 架构位置

- **所属子系统**: 基础设施层 (Base Infrastructure)
- **层级**: 数学工具 - 几何计算
- **作用域**: 为路径系统、字体渲染、动画系统提供贝塞尔曲线运算

## 主要类与结构体

### SkBezierCubic

三次贝塞尔曲线的静态工具类。

**曲线表示**: 8 个 double 数组 `[X0, Y0, X1, Y1, X2, Y2, X3, Y3]`
- (X0, Y0): 起点
- (X1, Y1): 第一控制点
- (X2, Y2): 第二控制点
- (X3, Y3): 终点

**继承关系**: 无(纯静态类)

### SkBezierQuad

二次贝塞尔曲线的静态工具类。

**曲线表示**: 6 个 double/3 个 SkPoint `[X0, Y0, X1, Y1, X2, Y2]`
- (X0, Y0): 起点
- (X1, Y1): 控制点
- (X2, Y2): 终点

**继承关系**: 无(纯静态类)

## 公共 API 函数

### SkBezierCubic 函数

#### `static std::array<double, 2> EvalAt(const double[8], double t)`
- **功能**: 计算三次贝塞尔曲线在参数 t 处的点坐标
- **参数**:
  - `curve`: 8 元素数组表示的曲线
  - `t`: 参数值,通常在 [0, 1]
- **返回值**: {X(t), Y(t)} 坐标对
- **数学公式**:
  ```
  X(t) = X₀(1-t)³ + 3X₁t(1-t)² + 3X₂t²(1-t) + X₃t³
  Y(t) = Y₀(1-t)³ + 3Y₁t(1-t)² + 3Y₂t²(1-t) + Y₃t³
  ```

#### `static void Subdivide(const double[8], double t, double[14])`
- **功能**: 使用 De Casteljau 算法在 t 处细分曲线
- **参数**:
  - `curve`: 输入曲线
  - `t`: 细分参数,必须在 [0, 1]
  - `twoCurves`: 输出数组,索引 0-7 为第一段,6-13 为第二段
- **返回值**: 通过输出参数返回
- **说明**: twoCurves[6] == twoCurves[13] (共享点)

#### `static std::array<double, 4> ConvertToPolynomial(const double[8], bool yValues)`
- **功能**: 将贝塞尔曲线转换为三次多项式 At³ + Bt² + Ct + D
- **参数**:
  - `curve`: 输入曲线
  - `yValues`: true 转换 Y 坐标,false 转换 X 坐标
- **返回值**: {A, B, C, D} 多项式系数
- **推导**:
  ```
  A = -P₀ + 3P₁ - 3P₂ + P₃
  B = 3P₀ - 6P₁ + 3P₂
  C = -3P₀ + 3P₁
  D = P₀
  ```

#### `static SkSpan<const float> IntersectWithHorizontalLine(...)`
- **功能**: 计算三次贝塞尔曲线与水平线 y = yIntercept 的交点
- **参数**:
  - `controlPoints`: 4 个控制点的 SkSpan
  - `yIntercept`: 水平线的 y 坐标
  - `intersectionStorage`: 存储交点 x 坐标的数组(至少 3 元素)
- **返回值**: 包含实际交点数量的 SkSpan
- **说明**: 最多 3 个交点

#### `static SkSpan<const float> Intersect(...)`
- **功能**: 通用求交函数,已知多项式系数时使用
- **参数**:
  - `AX, BX, CX, DX`: X 坐标多项式系数
  - `AY, BY, CY, DY`: Y 坐标多项式系数
  - `toIntersect`: 要相交的 y 值
  - `intersectionsStorage`: 存储结果的数组
- **返回值**: 交点的 SkSpan

### SkBezierQuad 函数

#### `static SkSpan<const float> IntersectWithHorizontalLine(...)`
- **功能**: 计算二次贝塞尔曲线与水平线的交点
- **参数**:
  - `controlPoints`: 3 个控制点的 SkSpan
  - `yIntercept`: 水平线的 y 坐标
  - `intersectionStorage`: 存储交点的数组(至少 2 元素)
- **返回值**: 包含交点的 SkSpan
- **说明**: 最多 2 个交点

#### `static SkSpan<const float> Intersect(...)`
- **功能**: 通用二次曲线求交函数
- **参数**:
  - `AX, BX, CX`: X 坐标多项式系数(形式 At² - 2Bt + C)
  - `AY, BY, CY`: Y 坐标多项式系数
  - `yIntercept`: 目标 y 值
  - `intersectionStorage`: 存储结果的数组
- **返回值**: 交点的 SkSpan

## 内部实现细节

### De Casteljau 细分算法

使用线性插值递归计算中间点:

```
原始曲线: P₀, P₁, P₂, P₃

第一层插值:
  P₀₁ = lerp(P₀, P₁, t)
  P₁₂ = lerp(P₁, P₂, t)
  P₂₃ = lerp(P₂, P₃, t)

第二层插值:
  P₀₁₂ = lerp(P₀₁, P₁₂, t)
  P₁₂₃ = lerp(P₁₂, P₂₃, t)

第三层插值:
  P₀₁₂₃ = lerp(P₀₁₂, P₁₂₃, t)

结果曲线:
  Alpha: P₀, P₀₁, P₀₁₂, P₀₁₂₃
  Beta:  P₀₁₂₃, P₁₂₃, P₂₃, P₃
```

**代码实现**:
```cpp
double x01 = interpolate(in_X(0), in_X(1), t);
double x12 = interpolate(in_X(1), in_X(2), t);
double x23 = interpolate(in_X(2), in_X(3), t);

alpha_X(1) = x01;
beta_X(2) = x23;

alpha_X(2) = interpolate(x01, x12, t);
beta_X(1) = interpolate(x12, x23, t);

alpha_X(3) = interpolate(alpha_X(2), beta_X(1), t);
```

### 三次曲线求交算法

1. **转换为多项式**: 将贝塞尔形式转为 AY×t³ + BY×t² + CY×t + DY
2. **求解三次方程**: SkCubics::RootsReal(AY, BY, CY, DY - yIntercept)
3. **Pin t 值**: 使用 `pinTRange()` 将接近 0/1 的值固定为精确 0/1
4. **过滤有效根**: 保留 t ∈ [0, 1] 的根
5. **计算 X 坐标**: 对每个有效 t,计算 X(t) = AX×t³ + BX×t² + CX×t + DX

**Pin 策略**:
```cpp
double pinTRange(double t) {
    // 如果 t + 1.0 在 float 精度下等于 1.0f,则 t = 0
    if (sk_double_to_float(t + 1.0) == 1.0f) {
        return 0.0;
    }
    // 如果 t 在 float 精度下等于 1.0f,则 t = 1
    else if (sk_double_to_float(t) == 1.0f) {
        return 1.0;
    }
    return t;
}
```

### 二次曲线求交算法

1. **转换为标准形式**: A = p₀ - 2p₁ + p₂, B = p₀ - p₁, C = p₀
   - 注意: 形式为 At² - 2Bt + C,不是标准的 At² + Bt + C
2. **求解二次方程**: SkQuads::Roots(AY, BY, CY - yIntercept)
3. **Pin 和过滤**: 类似三次情况
4. **计算 X 坐标**: X(t) = AX×t² - 2BX×t + CX

**为什么使用 -2B 形式?**
- 贝塞尔标准形式: 2(p₁ - p₀)
- 取反并因式分解: -(p₁ - p₀) = p₀ - p₁
- 避免乘以 2 的开销,直接存储 B = p₀ - p₁

### 曲线求值优化

**标准展开**:
```cpp
double one_minus_t = 1 - t;
double a = one_minus_t * one_minus_t * one_minus_t;
double b = 3 * one_minus_t * one_minus_t * t;
double c = 3 * one_minus_t * t * t;
double d = t * t * t;
```

**优化版本**(减少乘法次数):
```cpp
double one_minus_t = 1 - t;
double one_minus_t_squared = one_minus_t * one_minus_t;
double a = one_minus_t_squared * one_minus_t;
double b = 3 * one_minus_t_squared * t;
double t_squared = t * t;
double c = 3 * one_minus_t * t_squared;
double d = t_squared * t;
```

节省 2 次乘法,在 ARM 等寄存器受限平台有显著改善。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkCubics.h | 三次方程求根 |
| SkQuads.h | 二次方程求根 |
| SkPoint_impl.h | 点数据结构 |
| SkFloatingPoint.h | 浮点数工具 |
| SkSpan_impl.h | 数组视图 |

### 被依赖的模块
- **SkPath**: 路径光栅化时的曲线处理
- **SkStroke**: 描边路径的曲线偏移
- **SkFont**: 字体轮廓的贝塞尔曲线处理
- **SkAnimateBase**: 动画缓动曲线

## 设计模式与设计决策

### 设计模式
1. **静态工具类**: 无状态纯函数设计
2. **策略模式**: 曲线表示可以是 double 数组或 SkPoint 数组

### 设计决策

**为什么使用 double 而不是 float?**
- 贝塞尔求值涉及多次乘法,误差累积
- double 精度对细分和求交至关重要
- 最终结果转为 float 返回

**为什么返回 SkSpan 而不是 std::vector?**
- 避免动态内存分配
- 调用者提供栈数组,零开销
- 交点数量有上界(三次≤3,二次≤2)

**为什么 Pin t 值到 0/1?**
- 数值误差可能导致 t = -1e-15 或 t = 1.0000001
- 这些应视为边界情况
- 使用 float 精度检测(半个 ULP)

**为什么细分使用 De Casteljau 而不是多项式?**
- 数值稳定性更好
- 易于理解和实现
- 几何意义明确

## 性能考量

### 时间复杂度
- `EvalAt()`: O(1) - 固定次数算术运算
- `Subdivide()`: O(1) - 固定 12 次插值
- `ConvertToPolynomial()`: O(1) - 固定次数运算
- `IntersectWithHorizontalLine()`:
  - 三次: O(1) + 求根开销
  - 二次: O(1) + 求根开销

### 数值精度
- **EvalAt**: 相对误差 < 1e-14 (double 精度)
- **Subdivide**: 累积误差 < 1e-13
- **求交**: 精度取决于 SkCubics/SkQuads 的求根精度

### 性能优化
1. **快速路径**: t=0 和 t=1 直接返回端点
2. **位运算对齐**: 使用移位替代除法
3. **减少分支**: 使用算术而非条件判断
4. **寄存器优化**: 最小化临时变量

### SIMD 潜力
- EvalAt 可向量化处理 X 和 Y
- Subdivide 的插值可并行
- 当前实现未使用 SIMD,依赖编译器自动向量化

## 相关文件
| 文件 | 关系 |
|------|------|
| src/base/SkCubics.h | 三次方程求根 |
| src/base/SkQuads.h | 二次方程求根 |
| src/core/SkPath.cpp | 使用贝塞尔工具 |
| src/core/SkStroke.cpp | 曲线描边 |

## 数学公式参考

### 三次贝塞尔参数方程
```
B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
```

### 三次多项式展开
```
B(t) = At³ + Bt² + Ct + D
其中:
  A = -P₀ + 3P₁ - 3P₂ + P₃
  B = 3P₀ - 6P₁ + 3P₂
  C = -3P₀ + 3P₁
  D = P₀
```

### 二次贝塞尔参数方程
```
B(t) = (1-t)²P₀ + 2(1-t)tP₁ + t²P₂
```

### 二次标准形式(SkBezierQuad 使用)
```
B(t) = At² - 2Bt + C
其中:
  A = P₀ - 2P₁ + P₂
  B = P₀ - P₁
  C = P₀
```

## 使用示例

### 示例 1: 求值曲线上的点
```cpp
double curve[8] = {0, 0, 100, 0, 100, 100, 200, 100};
auto [x, y] = SkBezierCubic::EvalAt(curve, 0.5);
// (x, y) = 曲线中点
```

### 示例 2: 细分曲线
```cpp
double curve[8] = {0, 0, 100, 0, 100, 100, 200, 100};
double result[14];
SkBezierCubic::Subdivide(curve, 0.5, result);
// result[0-7]: 前半段
// result[6-13]: 后半段
```

### 示例 3: 求与水平线交点
```cpp
SkPoint pts[4] = {{0, 0}, {50, 100}, {150, 100}, {200, 0}};
float intersections[3];
auto span = SkBezierCubic::IntersectWithHorizontalLine(
    SkSpan(pts, 4), 50.0f, intersections);
// span.size() = 交点数量
// intersections[0..size()-1] = 交点的 x 坐标
```

### 示例 4: 二次曲线求交
```cpp
SkPoint pts[3] = {{0, 0}, {50, 100}, {100, 0}};
float intersections[2];
auto span = SkBezierQuad::IntersectWithHorizontalLine(
    SkSpan(pts, 3), 50.0f, intersections);
```

## 注意事项

1. **参数范围**: t 超出 [0, 1] 时曲线会外推,几何意义不同
2. **退化情况**: 控制点共线时退化为直线,求交可能失败
3. **精度损失**: 多次细分会累积误差
4. **内存管理**: 调用者负责提供足够的输出缓冲区
5. **线程安全**: 纯函数,完全线程安全
6. **NaN 处理**: 输入包含 NaN 时结果未定义
