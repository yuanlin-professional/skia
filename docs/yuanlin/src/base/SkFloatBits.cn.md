# SkFloatBits - 浮点数位表示转换工具
> 源文件: `src/base/SkFloatBits.h`

## 概述
SkFloatBits 模块提供了浮点数与其位表示之间的安全转换，以及基于位模式的比较工具。该模块通过将浮点数转换为二补码整数表示，使得浮点数可以像整数一样进行比较操作，同时避免了类型双关引起的未定义行为。这在需要对浮点数进行排序、比较或位级操作的场景中非常有用。

## 架构位置
SkFloatBits 位于 Skia 基础数学工具模块（src/base）中，是底层数值处理层的组件。它为浮点数排序、哈希计算、序列化等需要访问浮点数底层位表示的场景提供类型安全的接口。

## 主要函数

### 符号位与二补码转换

#### `int32_t SkSignBitTo2sCompliment(int32_t x)`
- **功能**: 将符号位表示的整数转换为二补码表示
- **参数**: x - 以符号位形式解释的 int32（即 float 的位模式）
- **返回值**: 二补码表示的 int32
- **特殊处理**: -0 (0x80000000) 转换为 0
- **用途**: 使浮点数可以用整数比较运算符比较

#### `int32_t Sk2sComplimentToSignBit(int32_t x)`
- **功能**: 将二补码整数转换回符号位表示
- **参数**: x - 二补码表示的 int32
- **返回值**: 符号位表示的 int32（可解释为 float 的位模式）
- **用途**: SkSignBitTo2sCompliment 的逆操作

### 浮点数与位模式转换

#### `uint32_t SkFloat2Bits(float value)`
- **功能**: 获取 float 的位表示（避免别名警告）
- **参数**: value - 浮点数
- **返回值**: 该浮点数的 32 位位模式
- **实现**: 使用 memcpy 避免类型双关

#### `float SkBits2Float(uint32_t bits)`
- **功能**: 将位模式转换为 float（避免别名警告）
- **参数**: bits - 32 位位模式
- **返回值**: 对应的浮点数
- **实现**: 使用 memcpy 避免类型双关

### 浮点数比较

#### `int32_t SkFloatAs2sCompliment(float x)`
- **功能**: 将 float 转换为可比较的二补码整数
- **参数**: x - 浮点数
- **返回值**: 二补码整数表示
- **用途**: 使用整数比较运算符（<, >, ==）比较浮点数
- **限制**: 仅用于比较，不代表浮点数的整数等价值

#### `float Sk2sComplimentAsFloat(int32_t x)`
- **功能**: 将二补码整数转换回 float
- **参数**: x - 二补码整数
- **返回值**: 对应的浮点数
- **用途**: SkFloatAs2sCompliment 的逆操作

### 宏定义

#### `#define SkScalarAs2sCompliment(x) SkFloatAs2sCompliment(x)`
- **功能**: SkScalar 版本的二补码转换（兼容性宏）
- **说明**: 在 Skia 中 SkScalar 通常就是 float

## 内部实现细节

### 符号位到二补码的转换算法
```cpp
static inline int32_t SkSignBitTo2sCompliment(int32_t x) {
    if (x < 0) {
        x &= 0x7FFFFFFF;  // 清除符号位
        x = -x;            // 取负
    }
    return x;
}
```

**IEEE 754 浮点数位布局**:
```
[符号位][8位指数][23位尾数]
```

**符号位表示特点**:
- 正数：符号位 = 0，值从小到大递增
- 负数：符号位 = 1，绝对值大的反而位模式更大

**转换逻辑**:
1. 如果 x < 0（符号位为 1）：
   - 清除符号位：`x &= 0x7FFFFFFF`
   - 取负：`x = -x`
2. 正数保持不变

**结果**: 负数变为负的二补码，可以与正数一起排序

### 二补码到符号位的转换算法
```cpp
static inline int32_t Sk2sComplimentToSignBit(int32_t x) {
    int sign = x >> 31;      // 获取符号位（全 0 或全 1）
    x = (x ^ sign) - sign;   // 取绝对值（负数翻转后减 1）
    x |= SkLeftShift(sign, 31);  // 设置符号位
    return x;
}
```

**逆向转换逻辑**:
1. 提取符号位：`sign = x >> 31`（算术右移，负数得 -1，正数得 0）
2. 计算绝对值：`x = (x ^ sign) - sign`
   - 正数：`(x ^ 0) - 0 = x`
   - 负数：`(x ^ -1) - (-1) = ~x + 1`（二补码取负）
3. 设置符号位：`x |= sign << 31`

### 使用 memcpy 的类型安全转换
```cpp
static inline uint32_t SkFloat2Bits(float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof(uint32_t));
    return bits;
}
```

**为何使用 memcpy**:
- **类型安全**: 避免违反 C++ 严格别名规则
- **可移植**: 所有平台都正确工作
- **零开销**: 现代编译器优化为直接寄存器操作

**被避免的错误方式**:
```cpp
// 错误：违反严格别名规则
uint32_t bits = *(uint32_t*)&value;

// 错误：C 风格但不安全
union { float f; uint32_t i; } u;
u.f = value;
uint32_t bits = u.i;
```

### -0 的特殊处理
IEEE 754 有两个零：+0 (0x00000000) 和 -0 (0x80000000)

**SkSignBitTo2sCompliment 的处理**:
```cpp
if (x < 0) {
    x &= 0x7FFFFFFF;  // -0 变为 +0
    x = -x;            // 0 的负数还是 0
}
```
结果：+0 和 -0 都映射到 0（二补码）

**意义**: 比较时 +0 和 -0 视为相等

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkMath.h | SkLeftShift 宏 |
| <cstdint> | int32_t, uint32_t 类型 |
| <cstring> | memcpy 函数 |

### 被依赖的模块
- 浮点数排序算法
- 路径边界计算
- 浮点数哈希函数
- 序列化/反序列化
- 几何计算中的特殊值处理
- 浮点数优化和缓存

## 设计模式与设计决策

### 为何需要这些转换
直接比较浮点数的问题：
```cpp
float a = -2.0f, b = -1.0f;
bool less = (a < b);  // true（正确）

// 但如果用位模式直接比较
uint32_t a_bits = SkFloat2Bits(a);  // 0xC0000000
uint32_t b_bits = SkFloat2Bits(b);  // 0xBF800000
bool less_bits = (a_bits < b_bits); // false（错误！）
```

使用二补码转换：
```cpp
int32_t a_cmp = SkFloatAs2sCompliment(a);
int32_t b_cmp = SkFloatAs2sCompliment(b);
bool less = (a_cmp < b_cmp);  // true（正确！）
```

### 内联函数而非宏
所有函数都是 `static inline`：
- **类型安全**: 编译器检查类型
- **调试友好**: 可以设置断点
- **性能**: 内联后与宏相同
- **作用域**: 避免宏污染

### 分离关注点
- **SkFloat2Bits/SkBits2Float**: 纯类型转换
- **SkSignBitTo2sCompliment/Sk2sComplimentToSignBit**: 数学变换
- **SkFloatAs2sCompliment/Sk2sComplimentAsFloat**: 组合操作

清晰的职责分离，易于理解和维护。

### 兼容性宏
```cpp
#define SkScalarAs2sCompliment(x) SkFloatAs2sCompliment(x)
```
- 历史原因：Skia 曾支持 double 作为 SkScalar
- 现在：SkScalar 总是 float
- 保留宏：向后兼容

## 使用场景

### 场景 1: 浮点数排序
```cpp
void sortFloats(float* array, int count) {
    // 转换为可比较的整数
    int32_t* temp = new int32_t[count];
    for (int i = 0; i < count; ++i) {
        temp[i] = SkFloatAs2sCompliment(array[i]);
    }

    // 整数排序（更快）
    std::sort(temp, temp + count);

    // 转换回浮点数
    for (int i = 0; i < count; ++i) {
        array[i] = Sk2sComplimentAsFloat(temp[i]);
    }
    delete[] temp;
}
```

### 场景 2: 浮点数哈希
```cpp
uint32_t hashFloat(float value) {
    uint32_t bits = SkFloat2Bits(value);
    // 处理 +0 和 -0
    if ((bits & 0x7FFFFFFF) == 0) {
        bits = 0;  // 统一为 +0
    }
    return bits;
}
```

### 场景 3: 特殊值检测
```cpp
bool isNegativeZero(float value) {
    return SkFloat2Bits(value) == 0x80000000;
}

bool isPositiveInfinity(float value) {
    return SkFloat2Bits(value) == 0x7F800000;
}
```

### 场景 4: 二进制序列化
```cpp
void serialize(float value, uint8_t* buffer) {
    uint32_t bits = SkFloat2Bits(value);
    memcpy(buffer, &bits, 4);
}

float deserialize(const uint8_t* buffer) {
    uint32_t bits;
    memcpy(&bits, buffer, 4);
    return SkBits2Float(bits);
}
```

## 性能考量

### 转换开销
- **SkFloat2Bits/SkBits2Float**: 零开销（编译器优化为寄存器操作）
- **SkSignBitTo2sCompliment**: 1 次比较 + 1-2 次位运算
- **SkFloatAs2sCompliment**: 组合以上操作

### 排序性能
使用二补码转换的整数排序比直接浮点数排序可能更快：
- **优势**: 整数比较通常更快（无特殊值处理）
- **劣势**: 额外的转换开销
- **适用**: 大量数据排序时有优势

### 内联效果
所有函数都应该被内联：
- 简单操作（几条指令）
- 标记为 `static inline`
- 在头文件中定义

## 陷阱与注意事项

### NaN 的比较
```cpp
float nan = std::numeric_limits<float>::quiet_NaN();
int32_t nan_cmp = SkFloatAs2sCompliment(nan);
// nan_cmp 是某个大的负数
// 排序时 NaN 会排在最前面（最小）
```
**警告**: NaN 的二补码转换不遵循 IEEE 754 的 NaN 比较语义

### 仅用于比较
```cpp
// 错误用法
float x = 3.14f;
int32_t x_cmp = SkFloatAs2sCompliment(x);
int32_t result = x_cmp * 2;  // 错误！不代表 x * 2
```
**限制**: 二补码表示仅用于比较，不能进行算术运算

### +0 和 -0
```cpp
float pos_zero = 0.0f;
float neg_zero = -0.0f;
int32_t pos_cmp = SkFloatAs2sCompliment(pos_zero);  // 0
int32_t neg_cmp = SkFloatAs2sCompliment(neg_zero);  // 0
// 两者相等（在二补码表示中）
```
**行为**: +0 和 -0 在转换后无法区分

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkMath.h | 提供 SkLeftShift |
| src/core/SkGeometry.cpp | 使用位操作检测特殊值 |
| src/pathops/SkPathOpsTypes.cpp | 浮点数排序和比较 |
| include/private/base/SkFloatingPoint.h | 其他浮点数工具 |
| tests/FloatBitsTest.cpp | 单元测试（如果存在） |

## 替代方案

### 直接使用 std::memcpy
对于简单的类型转换：
```cpp
uint32_t bits;
std::memcpy(&bits, &floatValue, sizeof(float));
```

### 使用 std::bit_cast (C++20)
```cpp
#include <bit>
uint32_t bits = std::bit_cast<uint32_t>(floatValue);
```
更现代且类型安全，但需要 C++20。

### 对于比较，考虑 std::sort 的自定义比较器
```cpp
std::sort(array, array + count, [](float a, float b) {
    return a < b;  // 处理 NaN 和特殊值
});
```
