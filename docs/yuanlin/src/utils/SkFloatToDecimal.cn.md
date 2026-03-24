# SkFloatToDecimal - 浮点数到十进制字符串转换

> 源文件:
> - `src/utils/SkFloatToDecimal.h`
> - `src/utils/SkFloatToDecimal.cpp`

## 概述

SkFloatToDecimal 是 Skia 中专门为 PDF 输出设计的浮点数到十进制字符串转换函数。PDF 规范不支持科学计数法（如 `6.02e23`），因此需要一个能够将任意浮点数值转换为标准十进制表示的函数。该函数处理所有可能的浮点输入值（包括 INFINITY、-INFINITY 和 NAN），并以足够的精度保证 round-trip 准确性。

## 架构位置

```
Skia PDF 后端
├── SkPDFDocument / SkPDFDevice
│   └── PDF 数值输出
│       └── SkFloatToDecimal (本模块 - 浮点到十进制转换)
├── SkWStream (字节流输出)
└── PDF 文件格式
```

该函数是 Skia PDF 后端的基础工具，用于将所有浮点数值安全地写入 PDF 文档。

## 主要类与结构体

### 常量
- `kMaximumSkFloatToDecimalLength = 49`: 输出缓冲区的最大长度。该值等于 `3 + 9 - FLT_MIN_10_EXP`（其中 3 为符号、小数点和终止符，9 为有效数字位数，`-FLT_MIN_10_EXP` 为 `-FLT_MIN` 中前导零的数量）。

## 公共 API 函数

### `SkFloatToDecimal`
```cpp
unsigned SkFloatToDecimal(float value, char output[kMaximumSkFloatToDecimalLength]);
```
- **功能**: 将浮点数转换为十进制字符串。
- **输出格式**: `[-]?([0-9]*\.)?[0-9]+`（标准十进制，不使用科学计数法）。
- **参数**:
  - `value`: 任意浮点数值。
  - `output`: 非空输出缓冲区，至少 49 字节。
- **返回值**: `strlen(output)`，即输出字符串的长度。
- **保证**: 对于有限值，`sscanf(output, "%f", &x)` 能恢复原始值。
- **特殊值处理**:
  - `INFINITY` 被舍入为 `FLT_MAX`。
  - `-INFINITY` 被舍入为 `-FLT_MAX`。
  - `NAN` 被转换为 `"0"`。
  - `0.0f` 被转换为 `"0"`。

## 内部实现细节

### 核心算法
1. **特殊值处理**: 首先处理 INFINITY、-INFINITY、NAN 和 0 等特殊情况。
2. **指数计算**: 使用 `std::frexp()` 获取二进制指数，然后通过 `log10(2)` 转换为十进制指数。
3. **有效数字提取**: 将浮点数乘以适当的 10 的幂次，得到整数形式的有效数字。
4. **精度调整**: 对于超过 `167772159`（即 `2^24` 所需的值）的有效数字，减少一位精度以匹配 24 位浮点有效位。
5. **尾零消除**: 循环去除有效数字末尾的零。
6. **字符串构建**: 根据十进制移位量（`decimalShift`），将数字写入缓冲区并在正确位置插入小数点。

### `pow10` 优化函数
```cpp
static double pow10(int e);
```
- 对常用指数（0-15）使用查表法直接返回精确值。
- 对更大的指数使用快速幂算法 (`pow_by_squaring`)。
- 对负指数使用 `0.1` 的快速幂。

### `pow_by_squaring` 快速幂
```cpp
static double pow_by_squaring(double value, double base, int e);
```
- 实现了经典的[二分求幂算法](https://en.wikipedia.org/wiki/Exponentiation_by_squaring)，时间复杂度 O(log n)。

### 最长输出分析
最长的输出是 `-FLT_MIN`，序列化为：
`"-.0000000000000000000000000000000000000117549435"`
包含 48 个字符加上终止符 `'\0'`，总计 49 字节。

## 依赖关系

- `include/core/SkTypes.h`: 基础类型和断言。
- `<cfloat>`: `FLT_MAX`、`FLT_MIN_10_EXP` 等浮点常量。
- `<cmath>`: `std::frexp()`、`std::floor()`、`std::isfinite()`。
- `<limits.h>` (仅 SK_DEBUG): 调试断言中使用。

## 设计模式与设计决策

1. **PDF 规范驱动**: 整个函数的存在和设计都源自 PDF 1.4 规范 C.1 节的要求——PDF 不支持指数格式。

2. **精度优先**: 尽管 PDF 光栅化器（如 pdfium）可能使用定点数运算，该函数仍然以浮点精度输出，确保浮点光栅化器能精确还原。定点光栅化器会优雅地忽略它们无法解析的精度。

3. **24 位精度适配**: 特别处理有效数字超过 `2^24` 对应范围的情况，这与 IEEE 754 单精度浮点数的 24 位尾数精度直接相关。

4. **完备的输入处理**: 函数接受所有可能的 float 值（包括非正常数），保证对任何输入都产生语法正确的输出。

## 性能考量

1. **无动态内存分配**: 所有操作都在栈上缓冲区内完成。

2. **避免 sprintf**: 自行实现转换逻辑而非依赖 `sprintf`，一方面避免 sprintf 可能输出科学计数法，另一方面提供更精确的控制。

3. **查表优化**: `pow10()` 对常见指数使用查表法，避免了昂贵的 `pow()` 调用。

4. **非正规数处理**: 对于非正规数（denormalized numbers），在输出精度足以 round-trip 后提前终止，避免不必要的字符输出。

## 相关文件

- `src/pdf/SkPDFUtils.h` / `.cpp`: PDF 工具函数，调用 `SkFloatToDecimal`。
- `src/pdf/SkPDFTypes.h` / `.cpp`: PDF 类型序列化。
- `tests/SkFloatToDecimalTest.cpp`: 单元测试。
