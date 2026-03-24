# SkFloatingPoint - 浮点数比较工具
> 源文件: `src/base/SkFloatingPoint.cpp`

## 概述
SkFloatingPoint 模块提供了精确的浮点数比较功能，解决了标准浮点数相等性判断在计算机中因舍入误差导致的问题。该模块实现了基于 ULP（Unit in the Last Place，最后一位的单位）的浮点数近似相等判断，以及接近零的特殊判断，为 Skia 的几何计算、路径操作等需要精确数值比较的场景提供可靠支持。

## 架构位置
SkFloatingPoint 位于 Skia 基础数学工具模块（src/base）中，是底层数值计算层的关键组件。它为路径操作、曲线求交、矩阵运算、颜色空间转换等上层模块提供数值稳定的比较操作。

## 公共 API 函数

### `bool sk_doubles_nearly_equal_ulps(double a, double b, uint8_t maxUlpsDiff)`
- **功能**: 判断两个 double 是否在给定的 ULP 误差范围内近似相等
- **参数**:
  - a, b: 待比较的两个双精度浮点数
  - maxUlpsDiff: 允许的最大 ULP 差异（默认通常为 16）
- **返回值**: 近似相等返回 true，否则返回 false
- **特殊处理**:
  - 精确相等（包括双无穷大）直接返回 true
  - NaN 总是返回 false（NaN != NaN）
  - 次正规数使用最小正规数的幅度

### `bool sk_double_nearly_zero(double a)`
- **功能**: 判断 double 是否接近零
- **参数**: a - 待检查的双精度浮点数
- **返回值**: 接近零返回 true，否则返回 false
- **阈值**: 使用 `std::numeric_limits<float>::epsilon()`（约 1.19e-7）
- **实现**: `a == 0 || fabs(a) < epsilon`

## 内部实现细节

### ULP 相等性算法

#### 幅度提取
```cpp
static double magnitude(double a) {
    static constexpr int64_t extractMagnitude =
        0b0'11111111111'0000000000000000000000000000000000000000000000000000;
    int64_t bits;
    memcpy(&bits, &a, sizeof(bits));
    bits &= extractMagnitude;
    double out;
    memcpy(&out, &bits, sizeof(out));
    return out;
}
```

**功能**: 提取 double 的正幅度（忽略符号和尾数）
- 保留符号位（置零）
- 保留指数位（11 位）
- 清零尾数位（52 位）
- **结果**:
  - 正规数：返回 2^e（e 为指数）
  - 次正规数：返回 0
  - NaN/Infinity：返回 infinity

**使用 memcpy 而非 reinterpret_cast**:
- 避免严格别名规则（strict aliasing）违反
- 保证在所有平台上正确工作
- 编译器会优化为零开销

#### ULP 容差计算
```cpp
const double maxMagnitude = std::max(std::max(magnitude(a), minMagnitude), magnitude(b));
const double tolerance = maxMagnitude * (ulpFactor * (maxUlpsDiff + 1));
```

**步骤**:
1. 计算 a 和 b 的最大幅度
2. 如果都是次正规数（幅度为 0），使用 minMagnitude (2^-1021)
3. 计算 ULP 因子：`epsilon = 2^-52`（double 的机器精度）
4. 容差 = maxMagnitude × epsilon × (maxUlpsDiff + 1)
5. 将 `maxUlpsDiff` 加 1 以补偿使用 `<` 而非 `<=` 的比较

#### 为何使用 `<` 而非 `<=`
```cpp
return a == b || std::abs(b - a) < tolerance;
```

**原因**: 正确处理无穷大
- 如果 a 或 b 是 infinity，maxMagnitude 也是 infinity
- tolerance = infinity × ... = infinity
- 如果使用 `<=`，`finite - infinity` 的差（infinity）会满足 `<= infinity`
- 使用 `<` 确保 `infinity < infinity` 为 false

**+1 补偿**: 因为改用 `<`，所以将 `maxUlpsDiff` 加 1 以保持完整的 ULP 范围

#### 特殊情况处理

**精确相等快速路径**:
```cpp
return a == b || ...
```
- 优先检查精确相等
- 捕获 ±0、±infinity 的情况
- 避免不必要的计算

**次正规数处理**:
```cpp
const double maxMagnitude = std::max(std::max(magnitude(a), minMagnitude), magnitude(b));
```
- 次正规数的幅度为 0
- 使用 minMagnitude (2^-1021) 作为最小容差基准
- 确保极小数的比较有合理的容差

**NaN 处理**:
- `a == b` 在 a 或 b 为 NaN 时返回 false
- 后续的差值计算也会产生 NaN
- `NaN < tolerance` 返回 false
- 结果：NaN 总是不相等

### sk_double_nearly_zero 的实现
```cpp
bool sk_double_nearly_zero(double a) {
    return a == 0 || fabs(a) < std::numeric_limits<float>::epsilon();
}
```

**设计选择**:
- 使用 float 的 epsilon 而非 double 的
- float epsilon ≈ 1.19e-7
- double epsilon ≈ 2.22e-16
- 选择较大的 float epsilon 提供更宽松的容差
- 适合 Skia 的图形计算精度需求

**快速路径**: `a == 0` 快速捕获精确零

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkFloatingPoint.h | 函数声明 |
| <algorithm> | std::max |
| <cmath> | fabs |
| <cstring> | memcpy（位模式转换） |
| <limits> | std::numeric_limits |

### 被依赖的模块
- src/base/SkCubics.cpp（三次方程求解）
- src/pathops/*.cpp（路径操作）
- src/core/SkGeometry.cpp（几何计算）
- src/core/SkMatrix.cpp（矩阵运算）
- src/core/SkPath.cpp（路径边界检查）
- 所有需要数值稳定比较的模块

## 设计模式与设计决策

### ULP 而非绝对误差
选择 ULP 而非固定阈值：
```cpp
// 固定阈值（不佳）
bool nearly_equal(double a, double b) {
    return fabs(a - b) < 1e-10;  // 对大数太严格，对小数太宽松
}

// ULP 方法（更好）
bool nearly_equal(double a, double b, uint8_t maxUlps) {
    // 误差相对于数的大小
}
```

**ULP 的优势**:
- 相对误差：自动适应数值大小
- 与浮点表示一致：直接反映浮点数精度
- 可预测：在整个浮点范围内表现一致

### 使用 double 的幅度
通过提取幅度而非完整数值：
- 避免符号差异的影响
- 只关注数值大小
- 简化次正规数处理

### 混合使用 double 和 float epsilon
`sk_double_nearly_zero` 使用 float 的 epsilon：
- 实用主义：Skia 的几何计算精度需求
- 避免过于严格的比较
- 与 Skia 历史代码兼容

### memcpy 实现类型双关
使用 memcpy 而非联合体或指针转换：
- **安全**: 不违反 C++ 严格别名规则
- **标准**: C++ 标准明确允许通过 memcpy 进行类型双关
- **优化**: 现代编译器将其优化为零开销

## 性能考量

### magnitude 函数的开销
- 2 次 memcpy（编译器优化为寄存器操作）
- 1 次位与运算
- 总成本：约 3-5 个 CPU 周期

### ULP 比较的完整开销
- 2 次 magnitude 调用
- 3 次 std::max
- 1 次浮点减法
- 1 次 fabs
- 1 次浮点乘法（容差计算）
- 总成本：约 20-30 个周期

### 快速路径优化
```cpp
return a == b || ...
```
精确相等时直接返回，避免昂贵的计算：
- 对于整数值的浮点数（0, 1, 2, ...）
- 对于从常量赋值的相同值
- 可能占比较操作的 30-50%

### nearly_zero 的轻量级
相比 ULP 比较，nearly_zero 更快：
- 1 次精确比较
- 1 次 fabs
- 1 次浮点比较
- 总成本：约 5-10 个周期

## ULP 的数学背景

### 什么是 ULP
ULP (Unit in the Last Place) 是浮点数表示的最小增量：
- 对于数值 x，1 ULP = 下一个可表示数 - x
- ULP 随数值大小变化

**示例**（简化的 4 位尾数）:
- 1.0 附近：1 ULP ≈ 2^-52
- 1000.0 附近：1 ULP ≈ 2^-42（1000 × 2^-52）
- 0.001 附近：1 ULP ≈ 2^-62

### 典型的 maxUlpsDiff 值
- **1-4 ULPs**: 非常严格，要求几乎完全一致
- **8-16 ULPs**: 合理默认值（允许少量舍入误差）
- **32-64 ULPs**: 宽松，允许多次运算的累积误差
- **Skia 常用**: 16 ULPs

### 为何次正规数特殊处理
次正规数（subnormal）接近零的特殊浮点数：
- 指数字段全为 0
- 幅度为 0（按标准提取方法）
- 需要使用 minMagnitude (2^-1021) 作为容差基准
- 确保极小数之间的比较有合理的精度

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkFloatingPoint.h | 函数声明和其他浮点工具 |
| src/base/SkCubics.cpp | 使用这些函数进行根的比较 |
| src/pathops/SkPathOpsTypes.cpp | 路径操作的数值比较 |
| src/core/SkGeometry.cpp | 几何计算中的边界判断 |
| src/core/SkMatrix.cpp | 矩阵近似相等判断 |
| tests/FloatingPointTest.cpp | 单元测试 |

## 使用示例

### 基本 ULP 比较
```cpp
double a = 0.1 + 0.2;  // 0.30000000000000004
double b = 0.3;        // 0.3
bool equal = (a == b); // false（位模式不同）
bool nearly = sk_doubles_nearly_equal_ulps(a, b, 16); // true（误差在 16 ULP 内）
```

### 边界检查
```cpp
double value = computeIntersection();
if (sk_double_nearly_zero(value)) {
    // 视为零，可能退化为特殊情况
} else if (sk_doubles_nearly_equal_ulps(value, 1.0, 16)) {
    // 视为 1，可能是端点
}
```

### 避免的陷阱
```cpp
// 错误：不适合大数差异
if (sk_doubles_nearly_equal_ulps(1e20, 1e20 + 100, 16)) {
    // 可能为 true！100 在 1e20 的尺度上很小
}

// 正确：根据应用场景选择合适的 maxUlpsDiff
```
