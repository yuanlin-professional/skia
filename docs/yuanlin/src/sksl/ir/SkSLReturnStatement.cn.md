# SkSLReturnStatement

> 源文件: src/sksl/ir/SkSLReturnStatement.h

## 概述

`ReturnStatement` 表示 `return` 语句,用于从函数返回值或提前退出。可以包含返回表达式(有返回值的函数)或为空(void 函数或提前返回)。

## 架构位置

作为控制流语句,终止当前函数的执行并可选地返回值。

## 主要类与结构体

### ReturnStatement

```cpp
class ReturnStatement final : public Statement
```

**成员:**
```cpp
std::unique_ptr<Expression> fExpression;  // 返回值表达式(可为空)
```

**构造:**
```cpp
ReturnStatement(Position pos, std::unique_ptr<Expression> expression)
```

**工厂方法:**
```cpp
static std::unique_ptr<Statement> Make(Position pos,
                                       std::unique_ptr<Expression> expression)
```

**访问器:**
```cpp
std::unique_ptr<Expression>& expression()
const std::unique_ptr<Expression>& expression() const
void setExpression(std::unique_ptr<Expression> expr)
```

**描述:**
```cpp
std::string description() const override {
    if (this->expression()) {
        return "return " + this->expression()->description() + ";";
    } else {
        return "return;";
    }
}
```

## 设计决策

允许表达式为空,表示 void 返回或无返回值的提前返回。提供 `setExpression` 允许优化器修改返回表达式。

## 相关文件

- `SkSLStatement.h`: 语句基类
- `SkSLBreakStatement.h`, `SkSLContinueStatement.h`: 其他控制流语句
- `SkSLFunctionDefinition.h`: 包含 return 语句的函数
- 类型检查: 验证返回类型与函数签名匹配
