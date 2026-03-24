# SkSL::ErrorReporter - SkSL 错误报告器

> 源文件: `src/sksl/SkSLErrorReporter.h`, `src/sksl/SkSLErrorReporter.cpp`

## 概述

`SkSL::ErrorReporter` 是 SkSL 编译器中用于收集和报告编译错误的抽象基类。它维护错误计数、源代码引用，并提供基于位置的错误报告接口。具体的错误处理行为由子类实现（例如将错误消息收集到列表中或终止程序）。

## 架构位置

```
SkSL::ErrorReporter (抽象基类)
  ├── Compiler 内部的默认实现
  ├── Parser::Checkpoint::ForwardingErrorReporter (转发实现)
  └── TestingOnly_AbortErrorReporter (测试用, 立即终止)
```

`ErrorReporter` 被 SkSL 编译器的各个阶段使用：词法分析、语法分析、语义分析和代码生成。

## 主要类与结构体

### `ErrorReporter`
- 维护错误计数 (`fErrorCount`)
- 持有源代码引用 (`fSource`)
- 定义 `handleError` 纯虚函数

### `TestingOnly_AbortErrorReporter`
- 继承自 `ErrorReporter`
- 在 `handleError` 中调用 `SK_ABORT`，立即终止程序
- 用于需要 SkSL 上下文但不应产生错误的测试

## 公共 API 函数

### 错误报告
- `void error(Position position, std::string_view msg)`: 报告一个错误。自动过滤包含 `POISON_TAG` 的消息（避免重复报告已知错误值的错误）。

### 源代码管理
- `std::string_view source()`: 获取当前源代码
- `void setSource(std::string_view source)`: 设置当前源代码

### 错误计数
- `int errorCount()`: 获取当前错误数
- `void resetErrorCount()`: 重置错误计数

### 虚函数
- `virtual void handleError(std::string_view msg, Position position) = 0`: 子类实现具体的错误处理逻辑

## 内部实现细节

### Poison 值过滤
```cpp
void ErrorReporter::error(Position position, std::string_view msg) {
    if (skstd::contains(msg, Compiler::POISON_TAG)) {
        return;
    }
    ++fErrorCount;
    this->handleError(msg, position);
}
```
SkSL 使用 "poison" 机制标记因前序错误而无效的值。当后续操作涉及 poison 值时，生成的错误消息包含 `POISON_TAG`，此类错误被自动过滤，避免级联的无用错误消息。

### 测试终止器
```cpp
void TestingOnly_AbortErrorReporter::handleError(std::string_view msg, Position pos) {
    SK_ABORT("%.*s", (int)msg.length(), msg.data());
}
```
使用 `SK_ABORT` 终止程序并输出错误消息，用于测试中断言不应出现错误的场景。

## 依赖关系

- `SkSL::Position`: 源代码位置
- `SkSL::Compiler`: 编译器（提供 `POISON_TAG` 常量）
- `SkStringView`: 字符串搜索（`contains`）

## 设计模式与设计决策

### 模板方法模式
`error` 方法实现了错误过滤和计数的通用逻辑，将具体的错误处理委托给子类的 `handleError`。

### Poison 值模式
通过 `POISON_TAG` 机制避免错误消息的级联爆炸，是编译器中常见的错误恢复策略。

### 可插拔设计
通过切换 ErrorReporter 实现，同一个编译器可以在不同场景下使用不同的错误处理策略（收集、终止、转发等）。

## 性能考量

- 错误过滤使用简单的字符串搜索，开销极小
- 错误计数使用整数递增，无额外开销
- 源代码使用 `string_view` 引用，无拷贝

## 相关文件

- `src/sksl/SkSLCompiler.h` / `.cpp`: 编译器（包含 `POISON_TAG` 定义和默认错误报告器）
- `src/sksl/SkSLPosition.h`: 源代码位置
- `src/sksl/SkSLParser.cpp`: 语法分析器（`ForwardingErrorReporter` 定义于此）
- `src/base/SkStringView.h`: 字符串工具
