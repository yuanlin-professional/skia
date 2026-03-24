# SkSLPoison

> 源文件: src/sksl/ir/SkSLPoison.h

## 概述

`Poison` 是表示错误或无效值的表达式节点。当编译器遇到错误但需要继续解析时,使用 Poison 节点占位,避免级联错误。

## 主要类与结构体

### Poison
```cpp
class Poison final : public Expression
```

**类型:** `Invalid` 类型
**用途:** 错误恢复,防止后续分析崩溃

**工厂方法:** `Make(Position pos, const Context& context)`

## 设计决策

类似于 LLVM 的 poison 值概念,允许编译器在遇到错误后继续处理,收集更多错误信息。Poison 节点不应出现在有效的最终 IR 中。

## 相关文件

- `SkSLEmptyExpression.h`: 另一种特殊表达式
- `SkSLErrorReporter.h`: 错误报告机制
- 解析器使用 Poison 进行错误恢复
