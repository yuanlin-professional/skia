# SkSL RegexParser（正则表达式解析器）

> 源文件：[src/sksl/lex/RegexParser.h](../../../src/sksl/lex/RegexParser.h)、[src/sksl/lex/RegexParser.cpp](../../../src/sksl/lex/RegexParser.cpp)

## 概述

`RegexParser` 是 SkSL 词法分析器生成工具链的一部分，负责将简单正则表达式字符串解析为 `RegexNode` 解析树。该解析器支持正则表达式的基本语法：量词（`*`、`+`、`?`）、交替（`|`）、字符集（`[a-z]`）和分组（`()`）。它是 `sksllex` 工具的核心组件，用于从正则表达式定义生成高效的词法分析器。

## 架构位置

`RegexParser` 位于 SkSL 词法分析器生成工具链中：

```
正则表达式文本
       |
       v
  RegexParser::parse()  （解析为 RegexNode 树）
       |
       v
  RegexNode::createStates() （生成 NFA 状态）
       |
       v
  NFA -> DFA 转换
       |
       v
  TransitionTable::Write() （生成状态转移表代码）
       |
       v
  SkSLLexer.cpp（自动生成的词法分析器）
```

## 主要类与结构体

### `class RegexParser`

正则表达式解析器类：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fSource` | `std::string` | 源正则表达式字符串 |
| `fIndex` | `size_t` | 当前解析位置 |
| `fStack` | `std::stack<RegexNode>` | 构建中的节点栈 |

## 公共 API 函数

### `RegexNode parse(std::string source)`

将正则表达式字符串解析为 `RegexNode` 解析树。断言在解析完成后栈中恰好有一个节点，且所有输入已被消耗。

## 内部实现细节

### 递归下降解析

解析器使用自顶向下的递归下降方法，语法规则如下：

```
regex       -> sequence ('|' regex)?
sequence    -> quantifiedTerm+
quantifiedTerm -> term ('*' | '+' | '?')?
term        -> literal | group | set | dot
group       -> '(' regex ')'
set         -> '[' '^'? setItem* ']'
setItem     -> literal ('-' literal)?
literal     -> char | '\\' escape
dot         -> '.'
```

### 节点构造

使用栈（`fStack`）来构建解析树。每个非终结符方法将结果推入栈中：
- **序列**：从栈中弹出两个节点，构造 `kConcat_Kind` 节点
- **交替**：从栈中弹出两个节点，构造 `kOr_Kind` 节点
- **量词**：从栈中弹出一个节点，包装为 `kStar_Kind`/`kPlus_Kind`/`kQuestion_Kind`

### 字符集解析

字符集 `[...]` 的解析包括：
- `^` 前缀表示取反（存储在 `fPayload.fBool` 中）
- 字符范围 `a-z` 构造 `kRange_Kind` 节点
- 尾部 `-` 被解析为普通字符

### 转义序列

支持标准转义序列：
| 转义 | 含义 |
|------|------|
| `\n` | 换行符 |
| `\r` | 回车符 |
| `\t` | 制表符 |
| `\s` | 空白字符集（空格、制表符、换行、回车） |
| `\其他` | 原字符 |

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `RegexNode.h` | 解析树节点 |
| `LexUtil.h` | 词法工具（`SkASSERT`） |

## 设计模式与设计决策

1. **递归下降**：使用经典的递归下降方法，代码结构清晰，每个语法规则对应一个方法。
2. **栈式构建**：使用显式栈而非返回值来构建节点树，简化了多子节点的组装逻辑。
3. **最小语法集**：仅支持正则表达式的最基本子集，足以描述编程语言的词法规则。
4. **硬错误处理**：遇到错误时直接 `exit(1)`，因为这是编译时工具而非运行时代码。

## 性能考量

- 解析器仅在编译器构建阶段运行（非运行时），性能不是关键考量
- O(n) 时间复杂度，单遍扫描
- 栈操作为 O(1)

## 相关文件

- `src/sksl/lex/RegexNode.h` / `.cpp` —— 解析树节点
- `src/sksl/lex/NFA.h` —— 非确定性有限自动机
- `src/sksl/lex/DFA.h` —— 确定性有限自动机
- `src/sksl/lex/sksllex.cpp` —— 词法分析器生成工具主程序
- `src/sksl/SkSLLexer.h` / `.cpp` —— 生成的词法分析器
