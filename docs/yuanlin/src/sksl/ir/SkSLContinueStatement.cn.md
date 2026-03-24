# SkSLContinueStatement

> 源文件: src/sksl/ir/SkSLContinueStatement.h

## 概述

`ContinueStatement` 表示 `continue` 语句,用于跳过当前循环迭代的剩余部分并开始下一次迭代。

## 主要类与结构体

### ContinueStatement
```cpp
class ContinueStatement final : public Statement
```

**工厂方法:** `Make(Position pos)`
**描述:** 返回 `"continue;"`

## 设计决策

与 `BreakStatement` 类似的简单设计,无成员变量,只记录位置。

## 相关文件

- `SkSLBreakStatement.h`: 类似的控制流语句
- `SkSLForStatement.h`, `SkSLDoStatement.h`: 包含 continue 的循环
