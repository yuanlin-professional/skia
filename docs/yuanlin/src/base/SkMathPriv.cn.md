# SkMathPriv

> 源文件: src/base/SkMathPriv.h, src/base/SkMathPriv.cpp

## 概述

`SkMathPriv` 是 Skia 内部使用的数学工具库，提供了一系列高效的位操作、整数运算和定点数计算函数。这些函数大多利用现代 C++ 标准库的位操作功能（如 `std::countl_zero`, `std::popcount`）以及平台相关的优化技巧，为 Skia 的图形处理提供高性能的数学基础设施。

该模块包含前导零计数、尾随零计数、人口计数、整数平方根、2 的幂运算、Alpha 混合计算等多种实用功能。

## 架构位置

`SkMathPriv` 位于 Skia 基础设施层的数学工具模块中：

- **层级**: src/base（基础工具层）
- **用途**: 为 Skia 提供高性能的整数和位操作工具
- **应用场景**: 图像混合、内存对齐、定点数运算、位掩码操作

在 Skia 架构中，它是底层数学工具，被颜色处理、内存管理、路径计算等模块广泛使用。

## 主要类与结构体

`SkMathPriv` 不是类，而是一组独立的工具函数和宏定义。

## 公共 API 函数

### 位操作函数

#### SkCLZ - 计算前导零

```cpp
static constexpr int SkCLZ(uint32_t x);
```

返回 32 位整数前导零的个数（从最高位开始数）。

**示例**:
- `SkCLZ(0x00000001)` → 31
- `SkCLZ(0x80000000)` → 0
- `SkCLZ(0x00FF0000)` → 8

#### SkCTZ - 计算尾随零

```cpp
static constexpr int SkCTZ(uint32_t x);
```

返回 32 位整数尾随零的个数（从最低位开始数）。

**示例**:
- `SkCTZ(0x00000001)` → 0
- `SkCTZ(0x80000000)` → 31
- `SkCTZ(0x00000100)` → 8

#### SkPopCount - 人口计数

```cpp
static constexpr int SkPopCount(uint32_t x);
```

返回 32 位整数中 1 的个数。

**示例**:
- `SkPopCount(0x00000000)` → 0
- `SkPopCount(0xFFFFFFFF)` → 32
- `SkPopCount(0x0000000F)` → 4

### 整数平方根

#### SkSqrtBits - 通用平方根

```cpp
int32_t SkSqrtBits(int32_t value, int bitBias);
```

计算整数的平方根，带有位偏移参数。

**参数**:
- `value`: 被开方数（≥ 0）
- `bitBias`: 结果的位偏移量（0 < bitBias ≤ 30）

**用途**: 支持定点数平方根计算

#### SkSqrt32 - 定点数平方根

```cpp
static inline int32_t SkSqrt32(int32_t n);
```

计算 SkFixed（16.16 定点数）的平方根。

**实现**: `SkSqrtBits(n, 15)`

### 符号操作

#### SkClampPos - 截断负数

```cpp
static inline int SkClampPos(int value);
```

无分支地将负数变为 0，正数保持不变。

**实现**: `value & ~(value >> 31)`

**原理**: 负数的符号位扩展为全 1 掩码，取反后清零；正数掩码为全 0，不影响结果。

#### SkExtractSign - 提取符号

```cpp
#define SkExtractSign(n) ((int32_t)(n) >> 31)
```

返回 -1（负数）或 0（非负数）。

#### SkApplySign - 应用符号

```cpp
static inline int32_t SkApplySign(int32_t n, int32_t sign);
```

根据 `sign`（0 或 -1）对 `n` 应用符号。

**实现**: `(n ^ sign) - sign`

**原理**:
- `sign = 0`: `(n ^ 0) - 0 = n`
- `sign = -1`: `(n ^ -1) - (-1) = ~n + 1 = -n`

#### SkCopySign32 - 复制符号

```cpp
static inline int32_t SkCopySign32(int32_t x, int32_t y);
```

返回带有 `y` 符号的 `x`。

### 饱和运算

#### SkClampUMax - 无符号限幅

```cpp
static inline unsigned SkClampUMax(unsigned value, unsigned max);
```

将 `value` 限制在 `[0, max]` 范围内。

### 负数转换

#### sk_negate_to_size_t - 安全取负

```cpp
static inline size_t sk_negate_to_size_t(int32_t value);
```

将有符号整数取负并转为 `size_t`，避免编译器警告。

**特殊处理**: 取负 `INT_MIN`（0x80000000）在技术上是未定义行为，但在二进制补码系统中结果仍是 0x80000000。

### Alpha 混合计算

#### SkMulDiv255Trunc - Alpha 乘法（截断）

```cpp
static inline U8CPU SkMulDiv255Trunc(U8CPU a, U8CPU b);
```

计算 `(a * b) / 255`，向下截断。

**实现**: `(prod + (prod >> 8)) >> 8`，其中 `prod = a * b + 1`

**优化**: 避免除法运算，使用位移近似

#### SkMulDiv255Ceiling - Alpha 乘法（向上取整）

```cpp
static inline U8CPU SkMulDiv255Ceiling(U8CPU a, U8CPU b);
```

计算 `(a * b + 254) / 255`，向上取整。

#### SkDiv255Round - 除以 255 舍入

```cpp
static inline unsigned SkDiv255Round(unsigned prod);
```

计算 `round(prod / 255)`。

**实现**: `(prod + 128 + (prod >> 8)) >> 8`

### 字节序操作

#### SkBSwap32 - 字节交换

```cpp
static inline uint32_t SkBSwap32(uint32_t v);
```

交换 32 位整数的字节序（大端 ↔ 小端）。

**示例**: `0xAABBCCDD` → `0xDDCCBBAA`

**实现**:
- MSVC: `_byteswap_ulong(v)`
- GCC/Clang: `__builtin_bswap32(v)`

### 2 的幂运算

#### SkNextLog2 - 向上对数

```cpp
static constexpr int SkNextLog2(uint32_t value);
```

返回大于等于 `value` 的最小 2 的幂的指数。

**示例**:
- `SkNextLog2(1)` → 0
- `SkNextLog2(3)` → 2
- `SkNextLog2(5)` → 3

**实现**: `32 - SkCLZ(value - 1)`

#### SkPrevLog2 - 向下对数

```cpp
static constexpr int SkPrevLog2(uint32_t value);
```

返回小于等于 `value` 的最大 2 的幂的指数。

**示例**:
- `SkPrevLog2(1)` → 0
- `SkPrevLog2(3)` → 1
- `SkPrevLog2(5)` → 2

#### SkNextPow2 - 向上幂

```cpp
static constexpr int SkNextPow2(int value);
```

返回大于等于 `value` 的最小 2 的幂。

**示例**:
- `SkNextPow2(5)` → 8
- `SkNextPow2(16)` → 16

#### SkPrevPow2 - 向下幂

```cpp
static constexpr int SkPrevPow2(int value);
```

返回小于等于 `value` 的最大 2 的幂。

#### SkNextSizePow2 - size_t 向上幂

```cpp
static constexpr size_t SkNextSizePow2(size_t n);
```

返回大于等于 `n` 的最小 2 的幂，若溢出则返回 `n`。

**特殊处理**:
- `n = 0` → 1
- `n >= 最高位置位` → `n`（防止溢出）

### 模板函数

#### SkTDivMod - 除法和取模

```cpp
template <typename In, typename Out>
inline void SkTDivMod(In numer, In denom, Out* div, Out* mod);
```

同时计算除法和取模，存入 `div` 和 `mod`。

### 定点数检查

#### SkFitsInFixed - 检查定点数范围

```cpp
template <typename T>
static inline bool SkFitsInFixed(T x);
```

检查浮点数 `x` 是否能安全转换为 SkFixed（16.16 定点数）。

**范围**: `|x| <= 32767.0`

## 内部实现细节

### SkSqrtBits - 整数平方根算法

实现了经典的"数字平方根"算法（来自《Numerical Recipes in C》）：

```cpp
int32_t SkSqrtBits(int32_t x, int count) {
    uint32_t root = 0;
    uint32_t remHi = 0;
    uint32_t remLo = x;

    do {
        root <<= 1;
        remHi = (remHi << 2) | (remLo >> 30);
        remLo <<= 2;

        uint32_t testDiv = (root << 1) + 1;
        if (remHi >= testDiv) {
            remHi -= testDiv;
            root++;
        }
    } while (--count >= 0);

    return root;
}
```

**原理**:
- 类似长除法，每次迭代处理 2 位
- `count` 参数控制结果的精度（位数）
- 对于 SkFixed（16.16），使用 `count = 15` 得到 16 位整数部分

### Alpha 混合优化

`SkMulDiv255Trunc` 使用快速近似算法：

```cpp
unsigned prod = a * b + 1;
return (prod + (prod >> 8)) >> 8;
```

**数学推导**:

目标: 计算 `⌊(a * b) / 255⌋`

近似: `(prod + (prod >> 8)) >> 8 ≈ prod / 255`

**误差**: 最大 1 个单位，对于 8 位颜色通道可接受

**性能**: 避免昂贵的除法，只需 1 次乘法 + 3 次位移/加法

### 符号操作技巧

`SkClampPos` 利用算术右移的符号扩展：

```cpp
value & ~(value >> 31)
```

- 正数: `value >> 31 = 0x00000000`，`~(value >> 31) = 0xFFFFFFFF`，结果 = `value`
- 负数: `value >> 31 = 0xFFFFFFFF`，`~(value >> 31) = 0x00000000`，结果 = 0

**优势**: 无分支，流水线友好

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<bit>` | C++20 位操作函数（countl_zero, popcount 等） |
| `<cstddef>` | `size_t` 类型定义 |
| `<cstdint>` | 固定宽度整数类型 |
| `SkAssert.h` | 断言宏 |
| `SkCPUTypes.h` | CPU 类型定义（U8CPU 等） |
| `SkTemplates.h` | 模板工具（SkTAbs 等） |

### 被依赖的模块

`SkMathPriv` 作为基础数学工具，被以下模块广泛使用：

| 使用场景 | 说明 |
|---------|------|
| 颜色混合 | Alpha 混合计算（SkMulDiv255 系列） |
| 位图操作 | 2 的幂对齐和大小计算 |
| 内存分配 | 内存大小的 2 的幂舍入 |
| 定点数运算 | SkFixed 类型的数学计算 |
| 路径计算 | 整数平方根用于距离计算 |
| 掩码操作 | 位计数和位操作 |

## 设计模式与设计决策

### 设计模式

1. **内联函数**: 所有函数都声明为 `inline` 或 `constexpr`，确保零开销抽象

2. **模板泛型**: `SkTDivMod`, `SkFitsInFixed` 等使用模板支持多种类型

3. **宏定义**: `SkExtractSign` 使用宏而非函数，确保完全内联

### 设计决策

1. **使用 C++20 标准库位操作**:
   - `std::countl_zero` 替代编译器内建函数
   - 原因: 标准化、可移植、编译器优化

2. **提供快速近似算法**:
   - Alpha 混合使用位移而非除法
   - 原因: 性能优先，误差在图形学中可接受

3. **constexpr 支持**:
   - 大多数函数声明为 `constexpr`
   - 原因: 支持编译时计算，减少运行时开销

4. **平台相关优化**:
   - `SkBSwap32` 使用编译器内建函数
   - 原因: 利用硬件指令（如 x86 的 `BSWAP`）

5. **无分支实现**:
   - `SkClampPos`, `SkApplySign` 等避免分支
   - 原因: 现代 CPU 流水线和分支预测优化

6. **整数平方根而非浮点**:
   - 提供 `SkSqrtBits` 而非直接用 `sqrt`
   - 原因: 定点数系统中避免浮点运算开销

7. **溢出保护**:
   - `SkNextSizePow2` 检测并防止溢出
   - 原因: 安全性，防止内存分配错误

## 性能考量

### 性能特征

| 函数类型 | 典型延迟 | 说明 |
|---------|---------|------|
| 位操作（CLZ, CTZ, PopCount） | 1-2 周期 | 现代 CPU 有专用指令 |
| Alpha 混合（MulDiv255） | 3-5 周期 | 1 次乘法 + 3 次位移/加法 |
| 整数平方根（SkSqrtBits） | 30-60 周期 | 迭代算法，与 `bitBias` 相关 |
| 2 的幂运算（NextPow2） | 2-3 周期 | 基于位操作 |
| 符号操作（ClampPos） | 2-3 周期 | 无分支 |

### 优化策略

1. **利用硬件指令**:
   - 位操作映射到 CPU 指令（`BSF`, `BSR`, `POPCNT`）
   - 字节交换映射到 `BSWAP`

2. **避免除法**:
   - Alpha 混合用位移近似除法
   - 相比真正的除法快约 10 倍

3. **constexpr 计算**:
   - 编译期可确定的值在编译时计算
   - 零运行时开销

4. **内联消除函数调用**:
   - 小函数完全内联
   - 编译器可进一步优化

### 使用建议

1. **选择合适的函数**:
   - 需要精确除法 → 标准除法
   - Alpha 混合 → `SkMulDiv255` 系列
   - 2 的幂运算 → `SkNextPow2` 系列

2. **注意定义域**:
   - `SkCLZ(0)` 和 `SkCTZ(0)` 是未定义行为
   - `SkNextLog2(0)` 会断言失败

3. **理解近似误差**:
   - `SkMulDiv255Trunc` 最大误差 1 个单位
   - 对于颜色计算通常可接受

4. **避免重复计算**:
   - 2 的幂运算结果可缓存
   - 位计数结果可复用

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/base/SkFixed.h` | 定点数类型定义和运算 |
| `include/private/base/SkTemplates.h` | 模板工具函数（SkTAbs 等） |
| `src/core/SkBlendMode.cpp` | 使用 Alpha 混合函数 |
| `src/core/SkBitmap.cpp` | 使用 2 的幂运算进行内存对齐 |
| `src/core/SkMask.cpp` | 使用位操作处理掩码 |
| `src/opts/SkBlitRow_opts.h` | SIMD 优化的混合实现 |
