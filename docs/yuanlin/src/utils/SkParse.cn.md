# SkParse

> 源文件: include/utils/SkParse.h, src/utils/SkParse.cpp

## 概述

`SkParse` 是 Skia 图形库中的字符串解析工具类,提供了一组静态方法用于从字符串中提取和解析各种数据类型。该模块专注于解析数值、颜色、布尔值等常见数据格式,广泛用于配置文件读取、SVG 解析、文本数据处理等场景。

核心功能包括:解析整数(int32_t)、浮点数(SkScalar)、十六进制数、颜色值、布尔值,以及统计字符串中的数值数量和在列表中查找匹配项。所有解析方法都采用健壮的错误处理机制,能够正确处理空格、分隔符和非法输入。

## 架构位置

`SkParse` 位于 Skia 的实用工具层(utils),作为底层字符串解析工具,为多个上层模块提供基础解析能力:

```
应用层 / SVG 解析器 / 配置读取器
   ↓
SkParse (工具层 - include/utils, src/utils)
   ↓
标准 C++ 库 (strtod, strcmp, memcmp)
```

相关的解析工具:
- `SkParsePath`: 使用 `SkParse` 解析 SVG 路径字符串
- `SkParseColor`: 使用 `SkParse` 解析颜色名称
- 配置文件解析器等

## 主要类与结构体

### SkParse

纯静态工具类,提供字符串解析方法集合。

**继承关系**: 无继承关系,纯静态工具类

**关键成员变量**: 无(所有方法为静态方法)

## 公共 API 函数

### Count - 统计数值数量

```cpp
static int Count(const char str[]);
static int Count(const char str[], char separator);
```

统计字符串中由空格或指定分隔符分隔的数值数量。第一个版本使用空格、逗号、分号作为分隔符;第二个版本使用指定的单一分隔符。

**返回值**: 数值的数量

**示例**:
- `Count("1 2 3")` 返回 3
- `Count("1,2,3", ',')` 返回 3

### FindHex - 解析十六进制数

```cpp
static const char* FindHex(const char str[], uint32_t* value);
```

从字符串中解析十六进制数(最多8位),跳过前导空格。

**参数**:
- `str`: 输入字符串
- `value`: 输出解析结果(可为 nullptr,仅验证格式)

**返回值**: 解析成功返回下一个待读取位置的指针,失败返回 nullptr

### FindColor - 解析颜色值

```cpp
static const char* FindColor(const char str[], SkColor* value);
```

解析颜色字符串,支持十六进制格式(#RGB、#RRGGBB)和命名颜色。

**返回值**: 解析成功返回下一个位置指针,失败返回 nullptr

### FindNamedColor - 解析命名颜色

```cpp
static const char* FindNamedColor(const char str[], size_t len, SkColor* color);
```

根据颜色名称(如 "red", "blue" 等)查找对应的 `SkColor` 值。

**参数**:
- `str`: 颜色名称字符串
- `len`: 字符串长度
- `color`: 输出颜色值

### FindS32 - 解析有符号32位整数

```cpp
static const char* FindS32(const char str[], int32_t* value);
```

从字符串解析有符号32位整数,支持负号。实现了溢出检测,超出 `int32_t` 范围时返回 nullptr。

**内部实现**:
- 使用 `int64_t` 作为中间类型检测溢出
- 正数最大值: `INT_MAX`
- 负数最小值: `INT_MIN`

### FindScalar - 解析浮点数

```cpp
static const char* FindScalar(const char str[], SkScalar* value);
```

解析浮点数(SkScalar,通常为 float)。内部使用标准库 `strtod` 进行解析,转换为 float 类型。

### FindScalars - 解析浮点数数组

```cpp
static const char* FindScalars(const char str[], SkScalar value[], int count);
```

连续解析多个浮点数,自动跳过分隔符。

**参数**:
- `str`: 输入字符串
- `value`: 输出数组(可为 nullptr,仅验证格式)
- `count`: 要解析的数量

**返回值**: 全部解析成功返回最后位置指针,失败返回 nullptr

### FindBool - 解析布尔值

```cpp
static bool FindBool(const char str[], bool* value);
```

解析布尔值,支持多种表示形式:
- true: "yes", "1", "true"
- false: "no", "0", "false"

**返回值**: 匹配成功返回 true,否则返回 false

### FindList - 在列表中查找

```cpp
static int FindList(const char target[], const char list[]);
```

在逗号分隔的列表中查找目标字符串的索引。

**参数**:
- `target`: 要查找的字符串
- `list`: 逗号分隔的列表(如 "red,green,blue")

**返回值**: 找到返回索引(从0开始),未找到返回 -1

## 内部实现细节

### 字符分类辅助函数

```cpp
static inline bool is_between(int c, int min, int max)
static inline bool is_ws(int c)        // 空白字符 [1, 32]
static inline bool is_digit(int c)     // 数字 [0-9]
static inline bool is_sep(int c)       // 分隔符(空格、逗号、分号)
static inline bool is_hex(int c)       // 十六进制字符
static int to_hex(int c)               // 转换为十六进制值
```

这些内联函数提供高效的字符分类,避免使用标准库 `ctype.h` 函数的本地化开销。

### 跳过空白与分隔符

```cpp
static const char* skip_ws(const char str[])   // 跳过空白
static const char* skip_sep(const char str[])  // 跳过分隔符
```

解析器的基础功能,在每次读取数值前后调用,确保正确处理格式化的输入。

### 整数解析的溢出保护

`FindS32` 实现了严格的溢出检测:

```cpp
int64_t maxAbsValue = std::numeric_limits<int>::max();
if (*str == '-') {
    maxAbsValue = -static_cast<int64_t>(std::numeric_limits<int>::min());
}
// ... 解析过程中检查 n > maxAbsValue
```

这确保了即使在边界情况下也不会产生未定义行为。

### 计数算法

`Count` 方法使用状态机实现:

```cpp
goto skipLeading;  // 跳过前导分隔符
do {
    count++;
    // 跳过非分隔符
skipLeading:
    // 跳过分隔符
} while (true);
```

使用 `goto` 优化代码结构,避免在首次迭代时递增计数。

### 浮点数解析

直接使用 C 标准库 `strtod`:

```cpp
char* stop;
float v = (float)strtod(str, &stop);
if (str == stop) {
    return nullptr;  // 未解析任何字符
}
```

`stop` 指针用于判断是否成功解析,并返回下一个位置。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkScalar.h | SkScalar 类型定义 |
| include/core/SkColor.h | SkColor 类型定义 |
| include/private/base/SkTo.h | 类型转换工具(SkToS32) |
| 标准 C++ 库 | strtod, strcmp, memcmp 等 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| SkParsePath | 解析 SVG 路径坐标和参数 |
| SVG 解析器 | 解析 SVG 属性值 |
| 配置文件读取器 | 解析数值配置项 |
| 测试工具 | 从文本输入构造图形对象 |

## 设计模式与设计决策

### 返回指针而非布尔值

大多数解析方法返回 `const char*` 而非 `bool`:

**优点**:
- 一次调用同时完成验证和定位
- 支持链式解析:`str = FindScalar(FindScalar(str, &x), &y)`
- 失败时返回 nullptr,自然融入后续检查

**示例**:
```cpp
str = FindScalar(str, &x);
if (!str) return error;
str = FindScalar(str, &y);
if (!str) return error;
```

### 可选的输出参数

所有 `Find*` 方法的输出参数都可以为 nullptr:

```cpp
if (FindScalar(str, nullptr)) {
    // 格式验证,不获取值
}
```

这种设计允许方法既用于解析也用于验证。

### 分离的分隔符处理

解析器不自动跳过尾部分隔符,调用者需要在解析多个值时手动调用 `skip_sep`:

```cpp
str = FindScalar(str, &x);
str = skip_sep(str);
str = FindScalar(str, &y);
```

这种设计给予调用者更多控制权,适应不同的分隔符规则。`FindScalars` 内部封装了这一模式。

### 本地化无关的字符分类

自定义 `is_digit`、`is_ws` 等函数,不使用 `isdigit`、`isspace`:

**原因**:
- 避免受本地化设置影响
- 确保跨平台一致性
- 性能更优(内联+简单比较)

### 严格的错误处理

所有解析方法遵循"全或无"原则:
- 成功:返回有效指针,输出参数被设置
- 失败:返回 nullptr,输出参数不变

没有部分解析或"尽力而为"的行为,保证调用者能够准确判断状态。

## 性能考量

### 内联字符检查

所有字符分类函数都声明为 `static inline`,编译器可以将其展开到调用点,避免函数调用开销。

### 最小化字符串扫描

解析器采用单次扫描策略:
- 每个字符最多被检查一次
- 不回溯或重新扫描
- 立即返回错误,避免无效输入的持续处理

### 整数解析的优化

`FindS32` 使用整数运算实现解析,避免浮点数转换:

```cpp
n = 10*n + *str - '0';  // 纯整数运算
```

相比 `atoi` 或 `strtol`,这种方式提供更精确的溢出控制。

### Count 方法的 goto 优化

使用 `goto` 避免首次迭代的额外检查:

```cpp
goto skipLeading;  // 直接跳过前导分隔符
do {
    count++;
    // ...
skipLeading:
    // ...
} while (true);
```

虽然使用 `goto`,但在这种状态机场景下提高了代码效率和清晰度。

### 缓存友好的访问模式

解析器顺序访问字符串,没有随机跳转,符合 CPU 缓存行的预取模式。

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| include/utils/SkParse.h | 公共 API 头文件 |
| src/utils/SkParse.cpp | 实现文件 |
| include/utils/SkParsePath.h | SVG 路径解析器 |
| include/utils/SkParseColor.h | 颜色解析器 |
| include/core/SkScalar.h | 标量类型定义 |
| include/core/SkColor.h | 颜色类型定义 |
| include/private/base/SkTo.h | 类型转换工具 |
