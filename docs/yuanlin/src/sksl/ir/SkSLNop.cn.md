# SkSLNop

> 源文件: src/sksl/ir/SkSLNop.h

## 概述

`Nop` 表示空操作语句(no-operation),不执行任何动作。用于占位或优化后删除无用语句的结果。

## 架构位置

作为最简单的语句类型,通常是优化器将无效代码替换为 Nop,随后可能被完全删除。

## 主要类与结构体

### Nop

```cpp
class Nop final : public Statement
```

**特性:**
- 无成员变量
- `isEmpty()` 返回 `true`
- `description()` 返回 `";"`

**工厂方法:**
```cpp
static std::unique_ptr<Statement> Make() {
    return std::make_unique<Nop>();
}
```

## 设计决策

作为 `final` 类,表示其语义完整不可扩展。重写 `isEmpty()` 返回 `true`,允许优化器识别并删除空语句。

## 相关文件

- `SkSLStatement.h`: 语句基类
- `SkSLEmptyExpression.h`: 表达式版本的空操作
- 优化器使用 Nop 替换死代码
