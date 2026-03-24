# SkSLEmptyExpression

> 源文件: src/sksl/ir/SkSLEmptyExpression.h

## 概述

`EmptyExpression` 是 void 类型的空表达式,内部无任何内容。当放在 `ExpressionStatement` 中时,功能上等价于 `Nop`。

## 架构位置

作为特殊的表达式节点,表示无意义的表达式计算,通常是优化或转换的中间产物。

## 主要类与结构体

### EmptyExpression

```cpp
class EmptyExpression : public Expression
```

**构造:**
```cpp
static std::unique_ptr<Expression> Make(Position pos, const Context& context) {
    return std::make_unique<EmptyExpression>(pos, context.fTypes.fVoid.get());
}
```

**类型:** 总是 `void` 类型

**描述:**
```cpp
std::string description(OperatorPrecedence) const override {
    return "false";  // 占位符,void 表达式无法直接表示
}
```

## 设计决策

使用 `false` 作为代码生成的占位符,因为 GLSL 无法直接表示 void 表达式。void 表达式的值从不实际使用,所以任何占位符都可接受。

## 相关文件

- `SkSLExpression.h`: 表达式基类
- `SkSLNop.h`: 语句版本的空操作
- `SkSLExpressionStatement.h`: 包装表达式为语句
