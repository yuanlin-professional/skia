# SkParseColor — 颜色名称与十六进制解析

> 源文件: `src/utils/SkParseColor.cpp`

## 概述

`SkParseColor.cpp` 实现了 Skia 的颜色字符串解析功能，提供从文本表示（CSS/SVG 命名颜色和十六进制颜色代码）到 `SkColor` 值的转换。该模块包含两个主要功能：

1. **命名颜色查找** (`FindNamedColor`): 支持 148 种 CSS/SVG 标准命名颜色（如 "aliceblue"、"red"、"gold"），通过二分查找在预排序的颜色名称表中进行高效匹配。
2. **颜色字符串解析** (`FindColor`): 支持以 `#` 开头的十六进制颜色代码（3 位、4 位、6 位和 8 位格式），以及命名颜色。

该模块源自 Android Open Source Project（2006 年），是 Skia 中处理颜色文本表示的基础工具。

## 架构位置

```
Skia
├── include/
│   ├── core/SkColor.h          // SkColor 类型定义
│   └── utils/SkParse.h         // SkParse 类声明
└── src/utils/
    └── SkParseColor.cpp        // 本文件：颜色解析实现
```

`SkParse` 是 Skia 的通用文本解析工具类，`SkParseColor.cpp` 是其中专门处理颜色解析的实现文件。该模块在 SVG 解析、调试工具和测试框架中被广泛使用。

## 主要类与结构体

### `ColorRec`（内部结构体）

```cpp
static constexpr struct ColorRec {
    uint8_t r, g, b;
};
```

- **用途**: 存储 RGB 颜色分量（不含 alpha）
- **特点**: `constexpr` 确保编译时初始化，节省运行时开销

### 全局数据表

| 数据表 | 类型 | 元素数 | 说明 |
|--------|------|--------|------|
| `gColorNames` | `const char*[]` | 148 | 按字母序排列的颜色名称字符串 |
| `gColors` | `ColorRec[]` | 148 | 对应的 RGB 值，索引与 `gColorNames` 一一对应 |

颜色名称表严格按照字母顺序排列，这是二分查找正确工作的前提。

## 公共 API 函数

### `const char* SkParse::FindNamedColor(const char* name, size_t len, SkColor* color)`

- **功能**: 在预定义的颜色名称表中查找指定名称对应的颜色
- **参数**:
  - `name`: 待查找的颜色名称字符串
  - `len`: 名称长度（实际未在当前实现中使用）
  - `color`: 输出参数，接收找到的颜色值（可为 `nullptr`）
- **返回值**: 成功时返回指向颜色名称之后的字符的指针；失败时返回 `nullptr`
- **查找算法**: 使用 `std::lower_bound` 进行二分查找

### `const char* SkParse::FindColor(const char* value, SkColor* colorPtr)`

- **功能**: 解析颜色字符串（支持十六进制和命名颜色）
- **参数**:
  - `value`: 颜色字符串
  - `colorPtr`: 输入/输出参数。输入时提供默认 alpha 值，输出时接收解析结果
- **返回值**: 成功时返回解析结束位置的指针；失败时返回 `nullptr`
- **支持格式**:

| 格式 | 示例 | 说明 |
|------|------|------|
| `#RGB` | `#F00` | 3 位十六进制，alpha 保留原值 |
| `#ARGB` | `#FF00` | 4 位十六进制，含 alpha |
| `#RRGGBB` | `#FF0000` | 6 位十六进制，alpha 保留原值 |
| `#AARRGGBB` | `#FFFF0000` | 8 位十六进制，含 alpha |
| 命名颜色 | `red` | CSS/SVG 标准命名颜色 |

### 内部辅助函数

#### `static inline unsigned nib2byte(unsigned n)`

- **功能**: 将 4 位半字节（nibble）扩展为 8 位字节
- **算法**: `(n << 4) | n`，例如 `0xF` 变为 `0xFF`，`0xA` 变为 `0xAA`
- **用途**: 处理 3 位和 4 位十六进制颜色格式时的位扩展

## 内部实现细节

### 二分查找

`FindNamedColor` 使用 `std::lower_bound` 在 `gColorNames` 数组中执行二分查找。由于数组是 `constexpr` 且按字母序排列，查找时间复杂度为 O(log n)，其中 n = 148。

查找完成后还需要用 `strcmp` 进行精确匹配验证，因为 `lower_bound` 只保证找到不小于目标的第一个元素。

### Alpha 通道处理

`FindColor` 中有一个关键设计：对于不包含 alpha 信息的颜色格式（`#RGB` 和 `#RRGGBB`），函数会保留 `colorPtr` 中原有的 alpha 值 (`oldAlpha`)。这允许调用者预设默认 alpha 值。

### 注释掉的代码

文件中包含被注释掉的 CSV 格式颜色解析代码（`count_separators` 函数和 `FindColor` 中的逗号分隔处理），这可能是 RGB 逗号分隔格式（如 `255,0,0`）的早期实现，后来被移除。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `include/utils/SkParse.h` | `SkParse` 类声明，包含 `FindColor`、`FindNamedColor`、`FindHex` 声明 |
| `include/core/SkColor.h` | `SkColor` 类型定义及 `SkColorSetRGB`、`SkColorSetARGB`、`SkColorGetA` 等宏/函数 |
| `include/core/SkTypes.h` | `SkASSERT` 等基础宏 |
| `<algorithm>` | `std::lower_bound` 二分查找 |
| `<cstring>` | `strcmp`、`strlen` 字符串操作 |
| `<iterator>` | `std::begin`、`std::end` |

## 设计模式与设计决策

1. **平行数组设计**: 颜色名称和 RGB 值分别存储在两个数组中，通过索引对应。这种设计比结构体数组更适合二分查找，因为名称字符串的比较不需要加载 RGB 数据
2. **编译时初始化**: 使用 `constexpr` 确保颜色表在编译时初始化，放入只读数据段
3. **Alpha 透传**: 3 位和 6 位格式保留调用者提供的 alpha 值，这是一个灵活的设计，允许上层代码控制默认透明度
4. **解析器返回指针**: 返回解析结束位置的指针而非布尔值，这是一种常见的解析器设计模式，允许调用者继续解析后续内容
5. **仅存储 RGB**: `ColorRec` 不存储 alpha 通道（CSS 命名颜色都是不透明的），节省了 25% 的存储空间

## 性能考量

- **二分查找**: O(log 148) ≈ 8 次比较即可完成命名颜色查找
- **constexpr 数据**: 颜色表存储在只读数据段，避免运行时初始化
- **紧凑存储**: `ColorRec` 仅 3 字节，148 个条目总共不到 500 字节
- **单次遍历**: `FindColor` 是单次解析，没有回溯
- **内联辅助函数**: `nib2byte` 标记为 `inline`，编译器会将其内联展开

## 相关文件

- `include/utils/SkParse.h` — `SkParse` 类声明
- `include/core/SkColor.h` — `SkColor` 类型定义和颜色操作宏
- `src/utils/SkParse.cpp` — `SkParse` 的其他解析功能（如 `FindHex`、`FindScalars`）
- `src/xml/SkDOM.cpp` — XML/SVG 解析中使用颜色解析
