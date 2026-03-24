# SkSLMethodReference

> 源文件: src/sksl/ir/SkSLMethodReference.h

## 概述

`MethodReference` 表示对方法名的引用,包含调用实例。这是中间值,最终会被替换为 `FunctionCall`。方法调用仅支持 effect-child 类型(如 `shader`, `colorFilter`),并解析为以 `$` 前缀的内置函数。

## 架构位置

用于处理着色器对象的方法调用,如 `child.eval(xy)`,最终转换为 `$eval(xy, child)` 形式的函数调用。

## 主要类与结构体

### MethodReference

```cpp
class MethodReference final : public Expression
```

**成员:**
```cpp
std::unique_ptr<Expression> fSelf;             // 方法调用的对象
const FunctionDeclaration* fOverloadChain;     // 重载链
```

**示例转换:**
```
child.eval(xy)  →  $eval(xy, child)
```

**构造:**
```cpp
MethodReference(const Context& context, Position pos,
                std::unique_ptr<Expression> self,
                const FunctionDeclaration* overloadChain)
```

**访问器:**
```cpp
std::unique_ptr<Expression>& self()
const FunctionDeclaration* overloadChain() const
```

## 设计决策

类型为 `Invalid`,强制在最终 IR 前被处理。将对象表达式存储在 `fSelf` 中,在转换为函数调用时作为最后一个参数传递。只支持特定的内置方法,不是通用的面向对象机制。

## 相关文件

- `SkSLFunctionReference.h`: 普通函数引用
- `SkSLFunctionCall.h`: 最终的函数调用节点
- `SkSLParser.cpp`: 解析方法调用语法
- 着色器内置函数: `$eval`, `$sample` 等
