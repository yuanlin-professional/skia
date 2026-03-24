# Int96.h - 96 位整数运算

> 源文件: `modules/bentleyottmann/include/Int96.h`

## 概述

`Int96.h` 定义了 96 位有符号整数结构体 `Int96` 及其基本运算。该类型用于 Bentley-Ottmann 算法中需要超过 64 位精度的整数运算场景，特别是在线段比较时将 64 位中间结果乘以 32 位整数产生 96 位结果的情况。

## 架构位置

`Int96` 是 Bentley-Ottmann 模块的底层数学工具：

- **使用者**：`Segment.cpp` 中的 `less_than_at` 函数、`Myers.cpp` 中的 `s0_less_than_s1_at_y` 函数
- **无模块内依赖**：仅依赖标准库 `<cstdint>`
- **实现文件**：`Segment.cpp` 或独立的实现文件中

## 主要类与结构体

### `Int96`
```cpp
struct Int96 {
    int64_t hi;
    uint32_t lo;
    static Int96 Make(int32_t a);
    static Int96 Make(int64_t a);
};
```
- `hi`：高 64 位（有符号）
- `lo`：低 32 位（无符号）
- 总计表示 96 位有符号整数

## 公共 API 函数

### `Int96::Make(int32_t a)` / `Int96::Make(int64_t a)`
从 32 位或 64 位整数构造 `Int96`。

### `operator==(a, b)` / `operator<(a, b)`
96 位整数的相等和小于比较。

### `operator+(a, b)`
96 位整数加法。

### `multiply(int64_t a, int32_t b)` / `multiply(int32_t a, int64_t b)`
将 64 位整数与 32 位整数相乘，产生 96 位结果。这是该类型存在的核心原因。

## 内部实现细节

### 96 位表示方式
`Int96` 使用 `{int64_t hi, uint32_t lo}` 表示。`hi` 为有符号高 64 位，`lo` 为无符号低 32 位。总值等于 `hi * 2^32 + lo`。注意 `lo` 为无符号类型，因为它始终表示非负的低位部分。

### 乘法实现
96 位乘法将 64 位操作数拆分为高 32 位和低 32 位两部分，分别与 32 位操作数相乘后组合结果，处理进位。这类似于小学的竖式乘法，但基数为 2^32。

### Make 构造
`Make(int32_t a)` 和 `Make(int64_t a)` 将较小的整数扩展到 96 位表示。对于正数，`lo` 部分接收低 32 位，`hi` 部分接收高 32 位（或零）。对于负数，需要正确处理符号扩展。

### 比较运算
`operator<` 先比较 `hi` 部分，若相等再比较 `lo` 部分。由于 `hi` 为有符号类型，负数的高位自然排在正数前面。

### 加法实现
`operator+` 先将 `lo` 部分相加，检测是否产生进位（通过比较结果是否小于任一操作数），然后将 `hi` 部分相加并加上进位。

## 依赖关系

- `<cstdint>` - 基本整数类型

## 设计模式与设计决策

### 最小必要精度
仅提供算法所需的运算（比较、加法、乘法），不实现完整的大整数库。

### 固定精度
使用固定的 96 位而非任意精度，因为线段比较的精度需求可以精确预计算。

## 性能考量

- 结构体仅 12 字节（加上填充可能 16 字节），适合值传递
- 乘法运算需要多次 64 位操作，但比使用通用大整数库更高效
- 比较运算先比较高位，高位不等时可提前返回

## 相关文件

- `modules/bentleyottmann/src/Segment.cpp` - `less_than_at` 使用 `Int96` 进行精确比较
- `modules/bentleyottmann/src/Myers.cpp` - `s0_less_than_s1_at_y` 使用 `Int96`
- `modules/bentleyottmann/include/Segment.h` - 声明使用 96 位比较的函数
