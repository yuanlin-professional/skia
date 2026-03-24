# SkSLNoOpErrorReporter — 空操作错误报告器

> 源文件：[`src/sksl/analysis/SkSLNoOpErrorReporter.h`](../../src/sksl/analysis/SkSLNoOpErrorReporter.h)

## 概述

SkSLNoOpErrorReporter.h 定义了 `NoOpErrorReporter` 类，它是 SkSL 编译器错误报告系统中的一个空操作（no-op）实现。该类继承自 `ErrorReporter` 并将 `handleError` 方法实现为空操作，用于需要静默忽略编译错误的场景。

该文件仅 24 行，是一个极简的头文件实现。

## 架构位置

```
SkSL 错误报告系统
  └── ErrorReporter (基类, src/sksl/SkSLErrorReporter.h)
        ├── 默认错误报告器 — 收集并报告错误
        └── NoOpErrorReporter — 静默忽略错误（本文件）
```

`NoOpErrorReporter` 在编译器的某些分析和试探性编译路径中使用，当错误是预期的或不需要处理时。

## 主要类与结构体

### `NoOpErrorReporter`

```cpp
class NoOpErrorReporter : public ErrorReporter {
public:
    void handleError(std::string_view, Position) override {}
};
```

- 继承自 `ErrorReporter` 基类
- 唯一的方法 `handleError` 为空实现
- 接收错误消息和位置参数但不做任何处理

## 公共 API 函数

```cpp
void handleError(std::string_view msg, Position pos) override;
```
- 接收错误消息字符串和源码位置
- 不执行任何操作（空函数体）
- 所有传入的错误信息被静默丢弃

## 内部实现细节

`NoOpErrorReporter` 的实现极其简单——只是一个带有空 `handleError` 方法的子类。其价值在于提供了一个类型安全的方式来配置编译器的错误处理行为。

使用场景通常包括：
- 试探性编译：尝试编译某段代码以检查是否有效，但不需要收集具体的错误信息
- 分析阶段：某些分析操作可能触发编译器的错误报告路径，但分析本身不需要处理这些错误
- 测试场景：需要抑制预期的错误输出

## 依赖关系

- `src/sksl/SkSLErrorReporter.h` — `ErrorReporter` 基类
- `src/sksl/SkSLPosition.h` — `Position` 类型

## 设计模式与设计决策

- **空对象模式（Null Object Pattern）**：提供一个"什么都不做"的错误报告器实现，避免在不需要错误报告时使用空指针检查。调用方可以始终安全地调用错误报告方法。
- **策略模式**：通过多态的错误报告器接口，允许在运行时选择不同的错误处理策略（报告、忽略等）。
- **最小化实现**：只重写一个必要的虚方法，保持实现的简洁。

## 性能考量

1. **零开销**：`handleError` 为空函数体，编译器可能将其优化为 no-op。
2. **虚函数调用**：作为虚函数，调用时有一次虚表查找的开销，但这在编译器上下文中完全可忽略。
3. **避免字符串构造**：在某些调用点，如果编译器能推断出错误报告器是 no-op，可能会避免构造错误消息字符串。

## 相关文件

- `src/sksl/SkSLErrorReporter.h` — 错误报告器基类定义
- `src/sksl/SkSLPosition.h` — 源码位置类型
- `src/sksl/SkSLContext.h` — 编译上下文（持有错误报告器引用）
- `src/sksl/SkSLCompiler.h` — 编译器主类（配置错误报告器）
