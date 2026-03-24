# SkSL::Position - SkSL 源代码位置

> 源文件: `src/sksl/SkSLPosition.h`, `src/sksl/SkSLPosition.cpp`

## 概述

`SkSL::Position` 是 SkSL 编译器中用于表示源代码位置的轻量级值类型。它记录了源代码中某个标记（token）或语法结构的起始偏移量和长度，用于错误报告和调试信息。该类设计为仅占用 4 字节（32 位），使用位域紧凑存储偏移量和长度信息。

## 架构位置

`Position` 是 SkSL 编译器的基础设施类型，几乎被所有 IR 节点、词法分析器和错误报告器使用。

```
SkSL::Lexer → Token → Position
SkSL::Parser → Position → ErrorReporter
SkSL IR 节点 → Position (用于错误定位)
```

## 主要类与结构体

### `Position`
- 使用 24 位存储起始偏移量（`fStartOffset`），最大值为 `kMaxOffset = 0x7FFFFF`（约 8MB）
- 使用 8 位存储长度（`fLength`），最大值为 255，超长截断
- 无效位置用 `fStartOffset == -1` 表示

### `ForLoopPositions`
包含 for 循环三个组成部分的位置：
- `initPosition`: 初始化语句位置
- `conditionPosition`: 条件表达式位置
- `nextPosition`: 迭代表达式位置

## 公共 API 函数

### 构造与创建
- `Position()`: 创建无效位置（默认构造）
- `static Range(int startOffset, int endOffset)`: 创建指定范围的位置

### 查询
- `valid()`: 检查位置是否有效
- `startOffset()`: 获取起始偏移量
- `endOffset()`: 获取结束偏移量（`startOffset + length`）
- `line(std::string_view source)`: 计算位置对应的行号

### 位置操作
- `rangeThrough(Position end)`: 创建从当前位置到目标位置（包含）的范围
- `after()`: 创建紧随当前位置之后的单字符位置

### 比较运算符
支持完整的比较运算：`==`、`!=`、`>`、`>=`、`<`、`<=`（基于 `fStartOffset`）。

## 内部实现细节

### 紧凑存储
```cpp
int32_t fStartOffset : 24;  // 有符号 24 位
uint32_t fLength : 8;       // 无符号 8 位
```
总共仅 4 字节，适合值语义传递和嵌入到 IR 节点中。

### 行号计算 (`line`)
```cpp
int Position::line(std::string_view source) const {
    int offset = std::min(fStartOffset, (int)source.length());
    int line = 1;
    for (int i = 0; i < offset; i++) {
        if (source[i] == '\n') { ++line; }
    }
    return line;
}
```
通过线性扫描源代码计数换行符。允许偏移量等于源代码长度（用于 EOF 标记）。

### 长度截断
长度超过 255 时截断为 255。这意味着对于特别长的标记/结构，结束位置可能不精确，但起始位置始终准确。

## 依赖关系

- `SkTypes.h`: 断言宏

## 设计模式与设计决策

### 极致的空间效率
4 字节的紧凑表示意味着每个 IR 节点仅增加极小的位置信息开销。8MB 的源代码限制对于着色器程序来说绰绰有余。

### 值语义
Position 按值传递和存储，避免了指针和引用的管理开销。

### 无效状态
通过 `-1` 的起始偏移量表示无效位置，而非使用 `std::optional`，保持了 4 字节的大小。

### 仅限 SkSL 使用
`kMaxOffset` 约为 8MB，这对于着色器源代码足够大，但作为通用源代码位置类型可能不够。这是有意的限制。

## 性能考量

- 4 字节大小使其适合寄存器传递
- 行号计算是 O(n) 的线性扫描，仅在错误报告时使用，不影响正常编译性能
- 比较运算仅比较 `fStartOffset`，是简单的整数比较
- `rangeThrough` 使用简单算术，无分支

## 相关文件

- `src/sksl/SkSLLexer.h`: 词法分析器（生成 Token 和 Position）
- `src/sksl/SkSLErrorReporter.h`: 错误报告器（使用 Position 定位错误）
- `src/sksl/SkSLParser.h`: 语法分析器（使用 Position 构建 IR 位置）
- `src/sksl/ir/SkSLExpression.h`: IR 表达式（持有 Position）
