# SkSLFunctionReference

> 源文件: src/sksl/ir/SkSLFunctionReference.h

## 概述

`FunctionReference` 表示对函数名的标识符引用,是解析过程的中间产物。在完整的程序中,所有函数引用最终都会被替换为 `FunctionCall` 节点。

## 架构位置

作为临时表达式节点,存在于解析和类型检查阶段,在完成重载解析后被替换。

## 主要类与结构体

### FunctionReference

```cpp
class FunctionReference final : public Expression
```

**成员:**
```cpp
const FunctionDeclaration* fOverloadChain;  // 重载函数链
```

**类型:** 总是 `Invalid` 类型,表示这不是有效的最终表达式

**构造:**
```cpp
FunctionReference(const Context& context, Position pos,
                  const FunctionDeclaration* overloadChain)
```

**核心方法:**
```cpp
const FunctionDeclaration* overloadChain() const
```
返回可能的重载函数链,用于后续的重载解析。

**描述:**
```cpp
std::string description() const override {
    return "<function>";
}
```

## 设计决策

作为中间节点,类型为 `Invalid` 强制其在最终 IR 前被处理。存储重载链允许在调用点进行参数类型匹配。如果在最终化检查时仍存在 `FunctionReference`,则为编译错误。

## 相关文件

- `SkSLFunctionDeclaration.h`: 函数声明
- `SkSLFunctionCall.h`: 最终的函数调用节点
- `SkSLFinalizationChecks.cpp`: 检测残留的函数引用
- `SkSLParser.cpp`: 创建函数引用,随后解析为函数调用
