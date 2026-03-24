# SkSL::Parser - SkSL 语法分析器

> 源文件: `src/sksl/SkSLParser.h`, `src/sksl/SkSLParser.cpp`

## 概述

`SkSL::Parser` 是 SkSL（Skia 着色语言）编译器的语法分析器，负责将 SkSL 源文本转换为中间表示（IR）树。它使用递归下降分析法解析完整的 SkSL 语法，包括声明、语句、表达式、类型、修饰符和布局限定符。解析器直接与 `SkSL::Compiler` 协作进行语义分析和 IR 构建，解析的结果封装为 `Program` 或 `Module` 对象。

## 架构位置

```
SkSL::Parser
  ├── SkSL::Lexer (词法分析器)
  ├── SkSL::Compiler (语义分析 + IR 构建)
  │     └── SkSL::Context (编译上下文)
  └── 输出: Program / Module
```

Parser 是编译器前端的核心组件，介于词法分析和语义分析之间。

## 主要类与结构体

### `Parser`
- 持有对 `Compiler` 的引用
- 管理词法分析器 (`fLexer`)
- 维护解析深度限制 (`fDepth`, 最大 50 层)
- 支持单 token 的回退 (`fPushback`)
- 收集程序元素 (`fProgramElements`)

### `Parser::AutoDepth` (内部 RAII 类)
递归深度追踪器，防止栈溢出：
- `increase()`: 增加深度，超过限制时报错并标记致命错误
- 析构时自动恢复深度

### `Parser::AutoSymbolTable` (内部 RAII 类)
作用域管理器：
- 创建新的符号表并链接到父表
- 析构时恢复到父符号表

### `Parser::Checkpoint` (内部类)
投机性解析的保存/恢复点：
- `accept()`: 接受解析结果，转发累积的错误
- `rewind()`: 回退到检查点，丢弃所有更改
- 使用 `ForwardingErrorReporter` 临时收集错误

### `VarDeclarationsPrefix` (内部结构体)
变量声明前缀：位置、修饰符、类型和名称。

## 公共 API 函数

### 入口点
- `programInheritingFrom(const Module*)`: 解析程序，返回 `Program`
- `moduleInheritingFrom(const Module*)`: 解析模块，返回 `Module`
- `text(Token)`: 获取 token 的源文本
- `position(Token)`: 获取 token 的源位置

## 内部实现细节

### 词法分析接口
- `nextRawToken()`: 获取下一个 token（含空白），处理保留字和无效八进制
- `nextToken()`: 获取下一个非空白 token
- `peek()`: 预览下一个 token（不消耗）
- `pushback(Token)`: 回退一个 token
- `checkNext(Token::Kind, Token*)`: 条件消耗 token
- `expect(Token::Kind, ...)`: 必须消耗指定类型的 token
- `expectIdentifier(Token*)`: 必须消耗标识符（排除内置类型）
- `expectNewline()`: 消耗换行符

### 声明解析
- `declarations()`: 顶层声明循环（验证 8MB 大小限制）
- `declaration()`: 单个声明（变量/函数/结构体/接口块）
- `functionDeclarationEnd()`: 函数声明的参数列表和返回
- `varDeclarationsOrExpressionStatement()`: 变量声明或表达式语句（使用 Checkpoint 投机解析）
- `structDeclaration()`: 结构体定义
- `interfaceBlock()`: 接口块定义

### 指令解析
- `directive(bool allowVersion)`: `#extension` 和 `#version` 指令
- `extensionDirective(Position)`: 扩展指令
- `versionDirective(Position, bool)`: 版本指令

### 修饰符和布局
- `modifiers()`: 解析修饰符序列（uniform, const, in, out 等）
- `layout()`: 解析 layout 限定符及其参数
- `parse_modifier_token()`: 将 token 映射到修饰符标志

### 语句解析
- `statement()`: 分发到具体语句类型
- `ifStatement()`, `forStatement()`, `whileStatement()`, `doStatement()`: 控制流
- `switchStatement()`: switch 语句
- `returnStatement()`, `breakStatement()`, `continueStatement()`, `discardStatement()`: 跳转语句
- `block()`: 代码块
- `expressionStatement()`: 表达式语句

### 表达式解析（运算符优先级递归下降）
按优先级从低到高：
1. `expression()` -> `assignmentExpression()`
2. `ternaryExpression()`
3. `logicalOrExpression()` -> `logicalXorExpression()` -> `logicalAndExpression()`
4. `bitwiseOrExpression()` -> `bitwiseXorExpression()` -> `bitwiseAndExpression()`
5. `equalityExpression()` -> `relationalExpression()`
6. `shiftExpression()` -> `additiveExpression()` -> `multiplicativeExpression()`
7. `unaryExpression()` -> `postfixExpression()`
8. `term()`: 字面量、标识符、括号表达式

### 后缀操作
- `suffix()`: 处理 `.field`、`[index]`、`(args)` 和 `++`/`--`
- `swizzle()`: 处理向量混洗
- `call()`: 函数调用

### 错误恢复
- `poison(Position)`: 创建毒值表达式
- `expressionOrPoison()`: 表达式为 null 时用毒值替代
- `fEncounteredFatalError`: 致命错误标志，中止解析

### Checkpoint 机制
用于处理语法歧义（如变量声明 vs 表达式语句）：
```cpp
Checkpoint checkpoint(this);
// 尝试解析为变量声明
if (success) {
    checkpoint.accept();
} else {
    checkpoint.rewind();
    // 尝试解析为表达式语句
}
```

## 依赖关系

- `SkSL::Lexer`: 词法分析器
- `SkSL::Compiler`: 语义分析和 IR 构建
- `SkSL::Context`: 编译上下文（符号表、类型系统）
- `SkSL::ErrorReporter`: 错误报告
- 所有 IR 节点类型（Expression, Statement, Declaration 等）
- `SkSL::Operator`: 运算符定义
- `SkSL::Layout` / `SkSL::Modifiers`: 布局和修饰符

## 设计模式与设计决策

### 递归下降分析
经典的手写递归下降解析器，每个语法规则对应一个方法。优点是易于理解、调试和定制错误消息。

### 投机性解析 (Checkpoint)
在语法歧义处使用保存点机制尝试不同的解析路径，失败时回退。比回溯解析器更受控。

### 深度限制
50 层的递归深度限制防止恶意输入导致栈溢出，这对安全性至关重要。

### 毒值传播
解析失败时生成 `Poison` 表达式，允许继续解析以收集更多错误，而不是在第一个错误处停止。

### 私有标识符
`TK_PRIVATE_IDENTIFIER` 仅在允许的程序类型中被识别为标识符，否则报错为保留名称。

### 程序大小限制
源代码不能超过 `Position::kMaxOffset`（约 8MB），因为错误报告系统无法处理更大的偏移。

## 性能考量

- 单 token 预览/回退使用简单的成员变量，O(1) 开销
- 递归下降的调用栈深度受 50 层限制，防止极深的嵌套
- 词法分析器是懒求值的（按需获取 token）
- Checkpoint 的 rewind 操作恢复词法分析器状态，需要 O(1) 时间
- `ForwardingErrorReporter` 使用 `TArray` 收集错误，在大多数路径下无分配（因为 Checkpoint 通常成功）
- 符号表使用链式结构，创建和销毁仅涉及指针操作

## 相关文件

- `src/sksl/SkSLLexer.h` / `.cpp`: 词法分析器
- `src/sksl/SkSLCompiler.h` / `.cpp`: 编译器
- `src/sksl/SkSLContext.h`: 编译上下文
- `src/sksl/SkSLErrorReporter.h`: 错误报告器
- `src/sksl/ir/SkSLProgram.h`: Program IR 根节点
- `src/sksl/SkSLModule.h`: Module 定义
- `src/sksl/ir/`: 所有 IR 节点定义
