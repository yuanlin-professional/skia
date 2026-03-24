# SkSLBreakStatement

> 源文件: src/sksl/ir/SkSLBreakStatement.h

## 概述

`BreakStatement` 表示 `break` 语句,用于提前退出循环或 switch 语句。这是一个简单的终端语句,不包含子节点或表达式。

## 架构位置

位于 SkSL 控制流语句的一部分,与 `ContinueStatement`、`ReturnStatement` 等并列。

## 主要类与结构体

### BreakStatement

```cpp
class BreakStatement final : public Statement
```

**类型常量:**
```cpp
inline static constexpr Kind kIRNodeKind = Kind::kBreak;
```

**构造:**
```cpp
explicit BreakStatement(Position pos) : INHERITED(pos, kIRNodeKind) {}
```

**工厂方法:**
```cpp
static std::unique_ptr<Statement> Make(Position pos) {
    return std::make_unique<BreakStatement>(pos);
}
```

**描述:**
```cpp
std::string description() const override {
    return "break;";
}
```

## 设计决策

作为 `final` 类,不可进一步派生。没有成员变量,只记录位置信息。极简设计,反映其语义的简单性。

## 相关文件

- `SkSLContinueStatement.h`: 类似的循环控制语句
- `SkSLReturnStatement.h`: 函数返回语句
- `SkSLForStatement.h`, `SkSLDoStatement.h`: 包含 break 的循环结构
