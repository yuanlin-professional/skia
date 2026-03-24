# SkSL Lexer（词法分析器）

> 源文件：[src/sksl/SkSLLexer.h](../../src/sksl/SkSLLexer.h)、[src/sksl/SkSLLexer.cpp](../../src/sksl/SkSLLexer.cpp)

## 概述

`SkSLLexer` 是 SkSL 编译器的词法分析器（lexer/tokenizer），负责将 SkSL 源代码文本分解为 Token（词法单元）流。该文件由 `sksllex` 工具自动生成，使用基于状态转移表的 DFA（确定性有限自动机）实现高效的词法扫描。词法分析器能够识别 90+ 种 Token 类型，包括关键字、标识符、字面量、运算符、标点符号和注释。

## 架构位置

`Lexer` 是 SkSL 编译管道的第一阶段，位于 Parser 的底层：

```
SkSL 源代码文本
       |
       v
  Lexer::next()  （词法分析，产生 Token 流）
       |
       v
  Parser         （语法分析，消费 Token 流，构建 IR）
       |
       v
  IR 树
```

## 主要类与结构体

### `struct Token`

词法单元，表示源代码中的一个最小有意义单位：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fKind` | `Token::Kind` | Token 的类型 |
| `fOffset` | `int32_t` | 在源文本中的起始偏移量 |
| `fLength` | `int32_t` | Token 的字符长度 |

### `enum Token::Kind`

Token 类型枚举（90+ 种），主要类别：

| 类别 | Token 示例 |
|------|------------|
| 字面量 | `TK_FLOAT_LITERAL`, `TK_INT_LITERAL`, `TK_TRUE_LITERAL`, `TK_FALSE_LITERAL`, `TK_BAD_OCTAL` |
| 控制流关键字 | `TK_IF`, `TK_ELSE`, `TK_FOR`, `TK_WHILE`, `TK_DO`, `TK_SWITCH`, `TK_CASE`, `TK_DEFAULT`, `TK_BREAK`, `TK_CONTINUE`, `TK_RETURN`, `TK_DISCARD` |
| 修饰符关键字 | `TK_IN`, `TK_OUT`, `TK_INOUT`, `TK_UNIFORM`, `TK_CONST`, `TK_FLAT`, `TK_NOPERSPECTIVE`, `TK_INLINE`, `TK_NOINLINE`, `TK_PURE`, `TK_READONLY`, `TK_WRITEONLY`, `TK_BUFFER` |
| 类型关键字 | `TK_STRUCT`, `TK_LAYOUT`, `TK_HIGHP`, `TK_MEDIUMP`, `TK_LOWP` |
| 标识符 | `TK_IDENTIFIER`, `TK_PRIVATE_IDENTIFIER` |
| 运算符 | `TK_PLUS`, `TK_MINUS`, `TK_STAR`, `TK_SLASH`, `TK_PERCENT`, `TK_EQEQ`, `TK_NEQ` 等 |
| 标点 | `TK_LPAREN`, `TK_RPAREN`, `TK_LBRACE`, `TK_RBRACE`, `TK_SEMICOLON`, `TK_COMMA`, `TK_DOT` |
| 空白/注释 | `TK_WHITESPACE`, `TK_LINE_COMMENT`, `TK_BLOCK_COMMENT` |
| 特殊 | `TK_END_OF_FILE`, `TK_INVALID`, `TK_NONE`, `TK_RESERVED`, `TK_DIRECTIVE`, `TK_ES3`, `TK_EXPORT`, `TK_WORKGROUP`, `TK_PIXELLOCAL` |

### `class Lexer`

词法分析器类：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fText` | `std::string_view` | 源代码文本 |
| `fOffset` | `int32_t` | 当前扫描位置 |

### `struct Lexer::Checkpoint`

检查点结构，用于保存和恢复词法分析器的位置：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fOffset` | `int32_t` | 保存的偏移量 |

## 公共 API 函数

- **`start(text)`** —— 初始化词法分析器，设置源文本和起始偏移量
- **`next()`** —— 返回下一个 Token。到达文本末尾时返回 `TK_END_OF_FILE`
- **`getCheckpoint()`** —— 获取当前位置的检查点
- **`rewindToCheckpoint(checkpoint)`** —— 回退到之前保存的检查点位置

## 内部实现细节

### 自动生成的状态转移表

`SkSLLexer.cpp` 是由 `sksllex` 工具生成的，包含了 DFA 状态转移表的紧凑编码。主要数据结构：

- **`kMappings[118]`** —— 将 ASCII 字符（减去偏移量 9）映射到 75 个字符类别之一
- **`kFull[]`** —— 完整状态转移表，每个条目包含 75 个目标状态
- **`kCompact[]`** —— 紧凑编码的状态转移表，用位图和小数组表示稀疏转移
- **`kAccepts[]`** —— 接受状态到 Token 类型的映射
- **`get_transition()`** —— 根据字符类和当前状态查找下一个状态

### DFA 扫描算法

`Lexer::next()` 的核心逻辑：

```cpp
Token Lexer::next() {
    int32_t startOffset = fOffset;
    State state = 1;
    for (;;) {
        if (fOffset >= fText.length()) {
            // 处理文件结尾
            break;
        }
        uint8_t c = (uint8_t)(fText[fOffset] - 9);  // 字符映射偏移
        State newState = get_transition(kMappings[c], state);
        if (!newState) break;  // 无有效转移，停止
        state = newState;
        ++fOffset;
    }
    Token::Kind kind = (Token::Kind)kAccepts[state];
    return Token(kind, startOffset, fOffset - startOffset);
}
```

该算法利用了 SkSL 语法的特殊性质：所有 Token 的前缀本身也是某种有效 Token（例如 `w` 是标识符，`wh` 也是标识符，`while` 是关键字）。这使得词法分析器可以使用最长匹配策略而无需回溯。

### 紧凑编码

状态转移表使用两种格式以平衡内存和速度：
- `FullEntry`：完整的 75 元素数组，用于高频访问的状态
- `CompactEntry`：使用位图编码的稀疏格式，通过 `popcount` 等位操作查找转移目标

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `<cstdint>` | 固定宽度整数类型 |
| `<string_view>` | 源代码文本的高效表示 |

## 设计模式与设计决策

1. **代码生成**：词法分析器由工具自动生成，确保状态转移表的正确性并优化存储格式。
2. **DFA 而非正则引擎**：使用预编译的 DFA 状态表，避免运行时正则表达式解释的开销。
3. **无回溯设计**：利用 SkSL 语法的无前缀歧义特性，实现 O(n) 时间复杂度的扫描。
4. **检查点机制**：通过 `Checkpoint` 支持 Parser 的前瞻（lookahead），允许在尝试性解析失败后回退。
5. **混合编码格式**：全表和紧凑表混合使用，在内存占用和查找速度之间取得平衡。

## 性能考量

- DFA 状态转移为 O(1) 操作，整体词法分析为 O(n)
- 字符映射表减少了有效字符类别数（从 128 减少到 75），减小状态表大小
- 紧凑编码显著减少了内存占用（相比全展开的状态表）
- 无回溯设计避免了最坏情况下的二次时间复杂度
- `string_view` 避免了源代码的复制
- Token 仅存储偏移量和长度（而非字符串），最小化内存占用

## 相关文件

- `src/sksl/SkSLParser.h` / `.cpp` —— 语法解析器，消费 Lexer 产生的 Token 流
- `src/sksl/lex/` 目录 —— 词法分析器的生成工具源码
- `src/sksl/lex/sksllex.cpp` —— 词法分析器生成工具
