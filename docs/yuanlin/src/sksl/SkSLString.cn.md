# SkSL::String - SkSL 字符串工具

> 源文件: `src/sksl/SkSLString.h`, `src/sksl/SkSLString.cpp`

## 概述

`SkSL::String` 命名空间和相关函数提供了 SkSL 编译器所需的字符串处理工具，包括字符串到数值的转换、格式化输出和区域设置无关的浮点数转字符串功能。这些工具确保了 SkSL 在不同平台和区域设置下的一致行为，特别是浮点数的文本表示。

## 架构位置

该模块是 SkSL 编译器的基础工具库，被词法分析器、语法分析器、IR 构建和代码生成等各阶段广泛使用。

## 主要类与结构体

### `SkSL` 命名空间函数
- `stod`: 字符串到双精度浮点数
- `stoi`: 字符串到整数

### `SkSL::String` 命名空间函数
- `printf`: 格式化字符串创建
- `appendf`: 格式化字符串追加
- `vappendf`: va_list 版本的格式化追加
- `Separator()`: 逗号分隔符生成器

### `skstd` 命名空间函数
- `to_string(float)`: 浮点数转字符串
- `to_string(double)`: 双精度浮点数转字符串

## 公共 API 函数

### 字符串到数值
- `bool stod(std::string_view s, SKSL_FLOAT* value)`: 使用经典区域设置解析浮点数，要求结果为有限值。
- `bool stoi(std::string_view s, SKSL_INT* value)`: 解析整数（支持 `u`/`U` 后缀和各种进制），值不超过 32 位。

### 格式化字符串
- `std::string printf(const char* fmt, ...)`: 创建格式化字符串
- `void appendf(std::string* str, const char* fmt, ...)`: 追加格式化内容
- `void vappendf(std::string* str, const char* fmt, va_list va)`: va_list 版本

### 分隔符生成
- `Separator()`: 返回一个 lambda，首次调用返回空字符串，后续调用返回 `", "`。用于生成参数列表等逗号分隔的输出。

### 数值到字符串
- `skstd::to_string(float)`: 区域设置无关的浮点数转字符串（精度 9）
- `skstd::to_string(double)`: 区域设置无关的双精度转字符串（精度 17）

## 内部实现细节

### 浮点数转字符串 (`to_string_impl`)
两阶段精度策略：
1. 使用精度 7 进行初始格式化
2. 往返验证：将结果解析回数值，如果与原始值不同，使用全精度重新格式化
3. 确保输出包含小数点（如果没有小数点且没有科学记数法 'e'，追加 `.0`）

```cpp
buffer.imbue(std::locale::classic());  // 确保使用 '.' 而非 ','
```

### 整数解析 (`stoi`)
- 支持 `u`/`U` 后缀（无符号标识）
- 使用 `strtoull` 解析（支持 `0x`、`0` 前缀等）
- 限制范围为 32 位（`result <= 0xFFFFFFFF`）

### 格式化实现 (`vappendf`)
使用 256 字节的栈缓冲区，超出时动态分配：
```cpp
size_t size = vsnprintf(buffer, BUFFER_SIZE, fmt, args);
if (BUFFER_SIZE >= size + 1) {
    str->append(buffer, size);
} else {
    auto newBuffer = std::unique_ptr<char[]>(new char[size + 1]);
    vsnprintf(newBuffer.get(), size + 1, fmt, reuse);
    str->append(newBuffer.get(), size);
}
```

### Separator 的静态存储
```cpp
static const SkNoDestructor<Output> kOutput(Output{{}, {", "}});
```
使用 `SkNoDestructor` 避免全局析构顺序问题。Lambda 捕获可变的 `firstSeparator` 标志。

## 依赖关系

- `SkSLDefines.h`: `SKSL_FLOAT` 和 `SKSL_INT` 类型定义
- `SkNoDestructor`: 静态对象的生命周期管理
- `SkStringView`: 字符串搜索（`contains`）
- 标准库: `<locale>`, `<sstream>`, `<cstdlib>`, `<cerrno>`

## 设计模式与设计决策

### 区域设置无关
所有数值转换使用 `std::locale::classic()`，确保在不同系统区域设置下浮点数始终使用 '.' 作为小数点。这对着色器代码生成至关重要。

### 往返精度
`to_string` 使用往返验证确保输出的精度足以精确重建原始值，这对着色器常量至关重要。

### 小数点保证
输出始终包含小数点（`1.0` 而非 `1`），确保在着色器语言中被解析为浮点数而非整数。

## 性能考量

- 栈缓冲区优先策略减少大部分场景的堆分配
- `stoi` 使用 `strtoull` 而非 `std::stoi`，避免异常开销
- `to_string` 的往返验证可能导致双重格式化，但仅在精度不足时触发
- `Separator` 的 lambda 是零分配的（捕获仅一个 bool）

## 相关文件

- `src/sksl/SkSLDefines.h`: SKSL 类型定义
- `src/sksl/SkSLLexer.h`: 词法分析器（使用 stod/stoi）
- `src/sksl/codegen/`: 代码生成器（使用 to_string 和 Separator）
- `src/base/SkNoDestructor.h`: 静态对象管理
