# SkFloatingPoint 浮点数工具模块

> 源文件: `include/private/base/SkFloatingPoint.h`

## 概述
SkFloatingPoint 提供了 Skia 中所有浮点数相关的数学工具函数和常量,包括浮点数验证、类型转换、饱和运算、角度转换等功能。该模块是 Skia 数值计算的基础,确保跨平台的数值稳定性和正确性。

## 架构位置
位于 Skia 基础工具层 (private/base),为整个图形库提供底层浮点数运算支持。被渲染管线、几何计算、变换矩阵等模块广泛使用。

## 数学常量定义

### 常用常量
| 常量名称 | 类型 | 值 | 说明 |
|----------|------|-----|------|
| `SK_FloatSqrt2` | float | 1.41421356f | √2 的单精度值 |
| `SK_FloatPI` | float | 3.14159265f | π 的单精度值 |
| `SK_DoublePI` | double | 3.14159265358979... | π 的双精度值 |
| `SK_FloatNaN` | float | quiet_NaN | 静默 NaN 值 |
| `SK_FloatInfinity` | float | infinity | 正无穷大 |
| `SK_FloatNegativeInfinity` | float | -infinity | 负无穷大 |
| `SK_DoubleNaN` | double | quiet_NaN | 双精度 NaN |

### 整数边界常量
```cpp
inline constexpr int SK_MaxS32FitsInFloat = 2147483520;
inline constexpr int SK_MinS32FitsInFloat = -SK_MaxS32FitsInFloat;

inline constexpr int64_t SK_MaxS64FitsInFloat = SK_MaxS64 >> (63-24) << (63-24);
inline constexpr int64_t SK_MinS64FitsInFloat = -SK_MaxS64FitsInFloat;
```
这些常量定义了能精确表示为 float 的最大/最小整数值 (基于 float 的 23 位尾数精度)。

## 核心工具函数

### 浮点数状态检测

#### `SkIsNaN`
```cpp
template <typename T>
static inline constexpr bool SkIsNaN(T x)
```
- **功能**: 检测浮点数是否为 NaN
- **实现**: 利用 NaN != NaN 的特性
- **返回**: 如果 x 是 NaN 返回 true

#### `SkIsFinite`
```cpp
template <typename T, typename... Pack>
static inline bool SkIsFinite(T x, Pack... values)
```
- **功能**: 检测一组浮点数是否都是有限数 (非 NaN 且非无穷大)
- **参数**: 支持可变参数,检测多个值
- **实现技巧**:
  ```cpp
  T prod = x - x;  // NaN 或 ±Inf 会产生 NaN,有限数产生 0
  prod = (prod * ... * values);  // 折叠表达式累乘
  return prod == prod;  // 仅当所有值都有限时 prod 为 0
  ```
- **优势**: 在 clang-cl 上生成比 `std::isfinite` 更优的代码

#### 数组版本
```cpp
template <typename T>
static inline bool SkIsFinite(const T array[], int count)
```
检测数组中所有元素是否都是有限数。

### 角度与弧度转换

#### `sk_float_degrees_to_radians`
```cpp
static constexpr float sk_float_degrees_to_radians(float degrees)
```
- **功能**: 角度转弧度
- **公式**: `degrees * (π / 180)`

#### `sk_float_radians_to_degrees`
```cpp
static constexpr float sk_float_radians_to_degrees(float radians)
```
- **功能**: 弧度转角度
- **公式**: `radians * (180 / π)`

### 符号函数

#### `sk_float_sgn`
```cpp
static constexpr int sk_float_sgn(float x)
```
- **功能**: 返回浮点数的符号
- **返回**:
  - `1` 如果 x > 0
  - `-1` 如果 x < 0
  - `0` 如果 x == 0

### 饱和转换函数

#### `sk_float_saturate2int`
```cpp
static constexpr int sk_float_saturate2int(float x)
```
- **功能**: 将 float 饱和转换为 int
- **范围**: 限制在 `[SK_MinS32FitsInFloat, SK_MaxS32FitsInFloat]`
- **NaN 处理**: 返回 `SK_MaxS32FitsInFloat`
- **用途**: 防止浮点数转整数时的溢出未定义行为

#### `sk_double_saturate2int`
```cpp
static constexpr int sk_double_saturate2int(double x)
```
双精度版本,范围限制在完整的 int32 范围。

#### `sk_float_saturate2int64`
```cpp
static constexpr int64_t sk_float_saturate2int64(float x)
```
转换为 int64_t 的版本。

### 舍入转换宏

#### Floor/Round/Ceil 系列
| 宏名称 | 功能 | 饱和处理 |
|--------|------|----------|
| `sk_float_floor2int(x)` | 向下取整转 int | 是 |
| `sk_float_round2int(x)` | 四舍五入转 int | 是 |
| `sk_float_ceil2int(x)` | 向上取整转 int | 是 |
| `sk_float_floor2int_no_saturate(x)` | 向下取整 | 否 |
| `sk_float_round2int_no_saturate(x)` | 四舍五入 | 否 |
| `sk_float_ceil2int_no_saturate(x)` | 向上取整 | 否 |

#### Double 版本
```cpp
#define sk_double_round(x)          (std::floor((x) + 0.5))
#define sk_double_floor2int(x)      ((int)std::floor(x))
#define sk_double_round2int(x)      ((int)std::round(x))
#define sk_double_ceil2int(x)       ((int)std::ceil(x))
```

### 浮点数舍入

#### `sk_float_round`
```cpp
#define sk_float_round(x) (float)sk_double_round((double)(x))
```
- **实现**: 先转为 double 再舍入
- **优势**: 处理边界值更准确
  - `0.49999997f` 正确舍入为 0 而非 1
  - `2^24` 正确处理 (float 精度边界)

### 安全类型转换

#### `sk_double_to_float`
```cpp
SK_NO_SANITIZE("float-cast-overflow")
static constexpr float sk_double_to_float(double x)
```
- **功能**: 将 double 转换为 float,忽略溢出警告
- **行为**: 超出范围的值转为最大 float 或无穷大 (实现定义行为)
- **特性**: 禁用 UBSan 的 float-cast-overflow 检查

### 其他工具函数

#### `sk_float_midpoint`
```cpp
static constexpr float sk_float_midpoint(float a, float b)
```
- **功能**: 计算两个浮点数的中点
- **实现**: `0.5 * (double(a) + b)` - 使用 double 防止溢出/下溢
- **类似**: C++20 的 `std::midpoint`

#### `sk_float_rsqrt`
```cpp
static inline float sk_float_rsqrt(float x)
```
- **功能**: 计算平方根倒数 `1.0f / sqrt(x)`

#### IEEE 除法函数
```cpp
SK_NO_SANITIZE("float-divide-by-zero")
static constexpr float sk_ieee_float_divide(float numer, float denom)
SK_NO_SANITIZE("float-divide-by-zero")
static constexpr double sk_ieee_double_divide(double numer, double denom)
```
- **功能**: 执行 IEEE 754 标准的除法
- **特性**:
  - 禁用除零警告
  - 正确处理无穷大和 NaN
  - Windows 需要禁用特定警告 (C4723)

### 高精度比较函数

#### `sk_double_nearly_zero`
```cpp
bool sk_double_nearly_zero(double a);
```
检测 double 值是否接近零 (在小 epsilon 范围内)。

#### `sk_doubles_nearly_equal_ulps`
```cpp
bool sk_doubles_nearly_equal_ulps(double a, double b, uint8_t maxUlpsDiff = 16);
```
- **功能**: 使用 ULP (Units in Last Place) 方法比较两个 double
- **参数**: `maxUlpsDiff` - 最大允许的 ULP 差异,默认 16
- **特殊处理**:
  - NaN 与任何值比较都返回 false
  - 同号无穷大返回 true
  - 无穷大与有限数返回 false

## 内部实现细节

### MSVC NaN 处理 Bug 解决方案
```cpp
#if defined(_MSC_VER) && !defined(__clang__)
    #define SK_CHECK_NAN(resultVal) if (SkIsNaN(x)) { return resultVal; }
#else
    #define SK_CHECK_NAN(resultVal)
#endif
```
- **问题**: MSVC 19.38+ 优化器错误处理 NaN 到整数转换
- **解决**: 注入显式 NaN 检查
- **参考**: https://developercommunity.visualstudio.com/t/10654403

### 饱和转换的边界计算
```cpp
// 0x7fffff8000000000
inline constexpr int64_t SK_MaxS64FitsInFloat = SK_MaxS64 >> (63-24) << (63-24);
```
计算可精确表示为 float 的最大 int64 值:
- float 有 23 位尾数 + 1 位隐含位 = 24 位精度
- 将高 24 位保留,低位清零

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkAttributes.h` | 提供 SK_NO_SANITIZE 宏 |
| `SkMath.h` | 基础数学常量和函数 |
| `<cmath>` | 标准数学函数 |
| `<cstdint>` | 固定宽度整数类型 |
| `<limits>` | 数值极限值 |
| `<type_traits>` | 类型特性检查 |

### 被依赖的模块
- 几何模块 (SkPoint, SkRect, SkPath)
- 矩阵变换 (SkMatrix)
- 颜色处理
- 渲染管线
- 着色器系统

## 设计模式与设计决策

### constexpr 优先
尽可能使用 `constexpr` 函数允许编译期计算,提升性能。

### 模板泛型设计
```cpp
template <typename T, std::enable_if_t<std::is_floating_point_v<T>, bool> = true>
static inline constexpr bool SkIsNaN(T x)
```
使用 SFINAE 限制只接受浮点类型,避免误用。

### 禁用 Sanitizer 检查
对于已知安全的实现定义行为,使用 `SK_NO_SANITIZE` 避免误报:
- 浮点数类型转换溢出
- IEEE 除零操作

### 平台特定优化
通过条件编译和宏定义支持不同平台的最优实现。

## 性能考量

### double 中间精度
在需要精度的场合 (如 `sk_float_round`, `sk_float_midpoint`) 使用 double 作为中间类型,避免浮点误差累积。

### 内联小函数
大多数函数声明为 `inline` 或 `constexpr`,鼓励编译器内联优化。

### 避免分支的 SkIsFinite 实现
通过数学运算而非条件判断检测有限性,利用现代 CPU 的流水线特性。

### ULP 比较的精度控制
`sk_doubles_nearly_equal_ulps` 允许调整容差,在精度和鲁棒性间平衡。

## 平台相关说明

### Windows 特定处理
- 禁用警告 C4723 (除零警告)
- MSVC 优化器 Bug 的特殊处理

### 不同编译器的 NaN 语义
- Clang: 严格 undefined behavior 检查
- GCC: 较宽松的处理
- MSVC: 需要显式 NaN 测试

## 使用示例

### 安全的浮点转整数
```cpp
float value = 2147483648.0f;  // 超出 int32 范围
int result = sk_float_saturate2int(value);  // 安全:返回 SK_MaxS32FitsInFloat
```

### 检测有效坐标
```cpp
SkPoint points[4] = {...};
if (SkIsFinite(points[0].fX, points[0].fY,
               points[1].fX, points[1].fY)) {
    // 所有坐标都有效,可以渲染
}
```

### 角度转换
```cpp
float degrees = 180.0f;
float radians = sk_float_degrees_to_radians(degrees);  // π
```

### 高精度比较
```cpp
double a = 0.1 + 0.2;
double b = 0.3;
if (sk_doubles_nearly_equal_ulps(a, b)) {
    // 认为相等,容忍浮点误差
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkMath.h` | 提供整数数学工具 |
| `SkFixed.h` | 定点数运算 |
| `SkScalar.h` | 标量类型定义 |
| `SkPoint_impl.h` | 使用浮点运算的几何类型 |

## 历史与演进
- 文件历史可追溯到 2006 年 (Android Open Source Project)
- 持续改进以适应新编译器和平台
- 2024 年改进 `SkIsFinite` 以在 clang-cl 上生成更好的代码
