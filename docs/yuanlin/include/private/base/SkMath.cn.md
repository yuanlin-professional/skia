# SkMath 整数数学工具模块

> 源文件: `include/private/base/SkMath.h`

## 概述
SkMath 提供 Skia 中整数运算的基础工具,包括整数常量定义、位运算、饱和运算、2 的幂检测等功能。该模块是 Skia 数值计算的基础,专注于整数和定点数运算。

## 架构位置
位于 Skia 基础工具层 (private/base),为图形库提供底层整数数学支持。与 SkFloatingPoint.h 互补,共同构成 Skia 的数学基础设施。

## 整数常量定义

### 16 位整数边界
```cpp
static constexpr int16_t SK_MaxS16 = INT16_MAX;      // 32767
static constexpr int16_t SK_MinS16 = -SK_MaxS16;     // -32767
```
注意: `SK_MinS16` 不是 `INT16_MIN` (-32768),为对称性设计。

### 32 位整数边界
```cpp
static constexpr int32_t SK_MaxS32 = INT32_MAX;      // 2147483647
static constexpr int32_t SK_MinS32 = -SK_MaxS32;     // -2147483647
static constexpr int32_t SK_NaN32  = INT32_MIN;      // -2147483648
```
- `SK_MaxS32` / `SK_MinS32`: 对称的最大/最小值
- `SK_NaN32`: 特殊标记值,表示无效或未初始化的整数

### 64 位整数边界
```cpp
static constexpr int64_t SK_MaxS64 = INT64_MAX;      // 9223372036854775807
static constexpr int64_t SK_MinS64 = -SK_MaxS64;
```

## 核心工具函数

### 64 位乘法

#### `sk_64_mul`
```cpp
static inline int64_t sk_64_mul(int64_t a, int64_t b)
```
- **功能**: 计算两个 64 位整数的乘积
- **用途**: 便捷函数,自动提升参数类型
- **优势**: 调用者无需显式 cast
- **示例**:
  ```cpp
  int a = 100000, b = 200000;
  int64_t result = sk_64_mul(a, b);  // 自动提升,避免溢出
  ```

### 位移运算

#### `SkLeftShift` (int32 版本)
```cpp
static inline constexpr int32_t SkLeftShift(int32_t value, int32_t shift)
```
- **功能**: 对有符号整数进行左移位
- **实现**: 转为 uint32_t 进行位移,再转回 int32_t
- **原因**: C/C++ 中左移负数是未定义行为
- **返回**: 左移后的结果

#### `SkLeftShift` (int64 版本)
```cpp
static inline constexpr int64_t SkLeftShift(int64_t value, int32_t shift)
```
64 位版本,处理方式相同。

### 2 的幂检测

#### `SkIsPow2`
```cpp
template <typename T> constexpr inline bool SkIsPow2(T value)
```
- **功能**: 检测整数是否为 2 的幂
- **实现**: `(value & (value - 1)) == 0`
- **原理**:
  - 2 的幂的二进制只有一个 1 位
  - `value - 1` 将该位变为 0,低位全变为 1
  - 与运算结果为 0
- **注意**: 不显式检查 `value <= 0`,0 会返回 true
- **示例**:
  ```cpp
  SkIsPow2(16)   // true  (0b10000)
  SkIsPow2(15)   // false (0b01111)
  SkIsPow2(0)    // true  (边界情况)
  SkIsPow2(-4)   // false (负数)
  ```

### 定点数运算辅助

#### `SkMul16ShiftRound`
```cpp
static inline unsigned SkMul16ShiftRound(U16CPU a, U16CPU b, int shift)
```
- **功能**: 计算 `a * b / ((1 << shift) - 1)` 并四舍五入
- **约束**:
  - `a` 和 `b` 必须 <= 32767
  - `shift` 必须在 (0, 8] 范围内
- **用途**: 定点数归一化乘法 (如 alpha 混合)
- **实现**:
  ```cpp
  unsigned prod = a*b + (1 << (shift - 1));  // 加舍入偏移
  return (prod + (prod >> shift)) >> shift;   // 除以 (2^shift - 1)
  ```
- **原理**: `prod >> shift` 近似 `prod / 255` 的余数调整

#### `SkMulDiv255Round`
```cpp
static inline U8CPU SkMulDiv255Round(U16CPU a, U16CPU b)
```
- **功能**: 计算 `a * b / 255` 并四舍五入
- **实现**: 调用 `SkMul16ShiftRound(a, b, 8)`
- **用途**: Alpha 混合的高效计算
- **约束**: `a` 和 `b` 必须 <= 32767
- **示例**:
  ```cpp
  uint8_t alpha = 128;
  uint8_t color = 200;
  uint8_t result = SkMulDiv255Round(alpha, color);  // ≈ 101
  ```

## 内部实现细节

### 对称边界值设计
最小值定义为 `-MaxValue` 而非标准的 `MIN` 常量:
- **优势**: 确保 `abs(SK_MinS32)` 不会溢出
- **对称性**: `SK_MinS32 + SK_MaxS32 = -1` (接近 0)
- **特殊标记**: `INT_MIN` 保留用作 `SK_NaN32`

### 安全位移实现
```cpp
return (int32_t) ((uint32_t) value << shift);
```
- 先转为无符号类型进行位移
- 避免有符号左移的未定义行为
- 结果再转回有符号类型

### 高效的 2 的幂检测
位运算技巧避免循环或对数运算:
```cpp
value & (value - 1) == 0
```
时间复杂度 O(1),无分支。

### 定点乘法的舍入技巧
```cpp
prod = a*b + (1 << (shift - 1));           // 加 0.5 舍入
return (prod + (prod >> shift)) >> shift;  // 快速除法
```
- 第一步加舍入偏移
- 第二步利用位移近似除法,避免除法指令

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkAssert.h` | 提供 SkASSERT 断言宏 |
| `SkCPUTypes.h` | 定义 U16CPU, U8CPU 等类型 |
| `<cstdint>` | 固定宽度整数类型 |
| `<climits>` | 整数极限常量 |

### 被依赖的模块
- `SkFixed.h` - 定点数运算
- `SkFloatingPoint.h` - 浮点转整数
- 颜色混合模块
- Alpha 通道处理
- 位图操作

## 设计模式与设计决策

### constexpr 函数
几乎所有函数声明为 `constexpr`,支持编译期计算:
```cpp
constexpr int32_t maxValue = SK_MaxS32;  // 编译期常量
```

### 模板泛型
`SkIsPow2` 使用模板支持任意整数类型:
```cpp
SkIsPow2(uint8_t)
SkIsPow2(int64_t)
SkIsPow2(size_t)
```

### 内联小函数
所有函数声明为 `inline`,鼓励编译器内联优化,消除函数调用开销。

### 平台无关实现
使用标准 C++ 类型和运算,无平台特定代码。

## 性能考量

### 位运算优于条件分支
`SkIsPow2` 使用位运算而非循环,充分利用 CPU 流水线。

### 避免除法指令
`SkMul16ShiftRound` 使用位移代替除法:
- 现代 CPU: 除法指令 ~20-40 周期
- 位移指令: 1 周期
- 性能提升显著

### 编译期常量折叠
`constexpr` 函数允许编译器在编译期计算:
```cpp
constexpr bool isPow2 = SkIsPow2(1024);  // 编译期确定为 true
```

### 类型提升辅助
`sk_64_mul` 自动提升避免手动 cast,减少代码复杂度和错误。

## 使用示例

### 检测 2 的幂
```cpp
int textureSize = 512;
if (SkIsPow2(textureSize)) {
    // 可以使用 POT (Power-of-Two) 纹理优化
    UsePOTTexture(textureSize);
}
```

### Alpha 混合
```cpp
uint8_t sourceAlpha = 200;
uint8_t sourceColor = 150;
uint8_t destColor = 100;

// 计算混合后的颜色
uint8_t blendedColor = SkMulDiv255Round(sourceAlpha, sourceColor) +
                       SkMulDiv255Round(255 - sourceAlpha, destColor);
```

### 安全的 64 位乘法
```cpp
int width = 4096;
int height = 4096;
int bytesPerPixel = 4;
int64_t totalBytes = sk_64_mul(sk_64_mul(width, height), bytesPerPixel);
```

### 定点数运算
```cpp
// 归一化到 [0, 255]
uint16_t value = 32768;  // 0.5 in 16-bit fixed point
uint8_t normalized = SkMul16ShiftRound(value, 255, 8);
```

### 有符号左移
```cpp
int32_t fixedPoint = -100;
int32_t shifted = SkLeftShift(fixedPoint, 16);  // 安全的负数左移
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkFloatingPoint.h` | 浮点数运算工具 |
| `SkFixed.h` | 定点数类型和运算 |
| `SkCPUTypes.h` | CPU 相关类型定义 |
| `SkSafe32.h` | 32 位饱和运算 |
| `SkBlendMode.h` | 使用 alpha 混合函数 |

## 历史与演进
- 文件历史可追溯到 2006 年 (Android Open Source Project)
- 为 Skia 的高性能渲染提供基础整数运算
- 持续优化以适应现代编译器的优化能力
