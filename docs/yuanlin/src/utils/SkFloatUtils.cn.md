# SkFloatUtils — 浮点数工具与 ULP 比较

> 源文件: `src/utils/SkFloatUtils.h`

## 概述

`SkFloatUtils.h` 提供了基于 ULP（Units in the Last Place，最后一位单位）的浮点数近似相等比较功能，以及一个浮点数插值函数的声明。

浮点数比较是计算机图形学中的一个经典问题——由于浮点运算的固有精度限制，直接使用 `==` 比较两个浮点数通常是不可靠的。该模块实现了一种基于 IEEE 754 浮点表示的精确比较方法：通过计算两个浮点数之间相隔的 ULP 数来判断它们是否"几乎相等"。这种方法比基于固定 epsilon 阈值的比较更为健壮，因为它能根据数值大小自动调整比较精度。

该实现灵感来源于 Google Test 框架的浮点比较实现。

## 架构位置

```
Skia
└── src/utils/
    └── SkFloatUtils.h     // 本文件：浮点工具
```

这是一个内部工具头文件，主要被 Skia 的测试框架和需要高精度浮点比较的模块使用。

## 主要类与结构体

### `SkTypeWithSize<size>`

模板类，将位宽映射到对应的无符号整数类型：

| 特化 | `UInt` 类型 |
|------|------------|
| `SkTypeWithSize<32>` | `uint32_t` |
| `SkTypeWithSize<64>` | `uint64_t` |
| 未特化 | `void`（编译时阻止使用） |

### `SkNumericLimits<RawType>`

模板结构体，提供浮点类型的尾数位数信息：

| 特化 | `digits` |
|------|----------|
| `SkNumericLimits<float>` | `FLT_MANT_DIG`（通常为 24） |
| `SkNumericLimits<double>` | `DBL_MANT_DIG`（通常为 53） |
| 未特化 | 0 |

### `SkFloatingPoint<RawType, ULPs>`

核心模板类，实现 ULP 精度的浮点数比较。

- **模板参数**:
  - `RawType`: 浮点类型（`float` 或 `double`）
  - `ULPs`: 允许的最大 ULP 差距
- **内部类型**:
  - `Bits`: 与浮点数等大的无符号整数类型
  - `FloatingPointUnion`: `union`，用于在浮点值和位表示之间进行类型双关（type punning）
- **编译时常量**:

| 常量 | 含义 |
|------|------|
| `kBitCount` | 总位数（float=32, double=64） |
| `kFractionBitCount` | 尾数位数（float=23, double=52） |
| `kExponentBitCount` | 指数位数（float=8, double=11） |
| `kSignBitMask` | 符号位掩码 |
| `kFractionBitMask` | 尾数位掩码 |
| `kExponentBitMask` | 指数位掩码 |
| `kMaxUlps` | 容忍的最大 ULP 差距 |

## 公共 API 函数

### `SkFloatingPoint<RawType, ULPs>::AlmostEquals(const SkFloatingPoint& rhs) const`

- **功能**: 判断两个浮点数是否在 ULP 容差范围内近似相等
- **语义**:
  - 任一参数为 NaN 时返回 `false`
  - +0.0 和 -0.0 被视为相等（距离为 0 ULP）
  - 极大数被视为与无穷大近似相等

### `SkFloatingPoint<RawType, ULPs>::is_nan() const`

- **功能**: 判断当前浮点数是否为 NaN
- **判断条件**: 指数位全为 1 且尾数位不全为 0

### `SkFloatingPoint<RawType, ULPs>::exponent_bits() const`

- **功能**: 提取指数位

### `SkFloatingPoint<RawType, ULPs>::fraction_bits() const`

- **功能**: 提取尾数位

### `float SkFloatInterpFunc(float searchKey, const float keys[], const float values[], int length)`

- **功能**: 在分段线性函数上进行插值
- **参数**: 搜索键、键数组、值数组、长度
- **特点**:
  - 超出范围的键值会被钳制（clamp）到最小/最大值
  - 使用线性搜索（假设数组较短）
  - 支持重复键以表示不连续函数

## 内部实现细节

### ULP 比较算法

ULP 比较的核心思想是将浮点数的位表示重新解释为整数，然后比较整数差距：

1. **类型双关**: 通过 `union` 将浮点数的位模式读取为无符号整数
2. **符号-幅值转偏置表示**: `SignAndMagnitudeToBiased()` 将 IEEE 754 的符号-幅值表示转换为偏置表示，使得数值顺序与整数顺序一致
   - 负数 `sam`：转换为 `~sam + 1`（补码）
   - 正数 `sam`：转换为 `kSignBitMask | sam`
3. **距离计算**: `DistanceBetweenSignAndMagnitudeNumbers()` 计算两个偏置表示数的绝对差
4. **比较**: 如果距离不超过 `kMaxUlps`，则认为两数近似相等

### 为什么 ULP 比较优于 epsilon 比较

传统的 `|a - b| < epsilon` 方法在不同数量级下表现不一致：
- 对于很大的数（如 1e20），即使 `epsilon = 0.001` 也可能太小
- 对于很小的数（如 1e-20），`epsilon = 0.001` 又太大

ULP 比较通过利用 IEEE 754 浮点数的内在结构，自动适应数值的量级，在任何数量级下都提供一致的精度判断。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `include/core/SkTypes.h` | 基础类型定义 |
| `<limits.h>` | `CHAR_BIT` |
| `<float.h>` | `FLT_MANT_DIG`、`DBL_MANT_DIG` |

## 设计模式与设计决策

1. **模板元编程**: 使用模板特化将浮点类型大小映射到对应的无符号整数类型，实现了对 `float` 和 `double` 的统一处理
2. **编译时常量**: 所有位掩码和位数都是编译时计算的 `static const` 值，零运行时开销
3. **Union 类型双关**: 使用 `union` 在浮点值和整数位表示之间转换，这是 C++ 中常见的底层技巧
4. **参数化 ULP 容差**: ULP 容差作为模板参数，编译时确定，无运行时判断开销
5. **防御性编程**: 未特化的 `SkTypeWithSize` 使用 `void` 作为 `UInt` 类型，确保使用非法大小时在编译时报错
6. **参考资料**: 代码注释引用了 StackOverflow、Google Test 和学术论文作为设计参考

## 性能考量

- 所有关键操作（位掩码、位运算、整数比较）都是常数时间操作
- 模板参数在编译时解析，无运行时多态开销
- `union` 类型双关避免了 `memcpy` 或 `reinterpret_cast` 的开销
- `AlmostEquals` 中的 NaN 检查是快速的位运算，不依赖浮点异常
- 整体比较操作仅需几条 CPU 指令

## 相关文件

- `include/core/SkTypes.h` — 基础类型定义
- `include/private/base/SkFloatingPoint.h` — Skia 浮点数工具（`SkIsFinite`、`SkIsNaN` 等）
- `tests/` — 使用此工具进行精确浮点数比较的测试文件
