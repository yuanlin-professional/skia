# SkSLSwitchCaseContainsExit — Switch Case 退出分析

> 源文件：[`src/sksl/analysis/SkSLSwitchCaseContainsExit.cpp`](../../src/sksl/analysis/SkSLSwitchCaseContainsExit.cpp)

## 概述

SkSLSwitchCaseContainsExit.cpp 实现了对 switch case 语句块的控制流分析，用于判断某个 case 分支是否包含会导致提前退出（return、break 或 continue）的语句。分析区分了无条件退出和条件退出两种情况，为 SkSL 编译器的优化和代码生成提供控制流信息。

该文件 98 行，包含一个分析访问者类和两个公共分析函数。

## 架构位置

```
SkSL 编译器
  └── 分析（Analysis）模块
        └── 控制流分析
              ├── SwitchCaseContainsExit（本文件）
              ├── GetLoopControlFlowInfo
              └── GetReturnComplexity
```

此分析在 SkSL 的优化器和代码生成阶段使用，帮助确定 switch 语句是否可以安全地转换为其他控制流结构。

## 主要类与结构体

### `SwitchCaseContainsExit`（匿名命名空间内）

```cpp
class SwitchCaseContainsExit : public ProgramVisitor {
public:
    SwitchCaseContainsExit(bool conditionalExits);
    bool visitExpression(const Expression& expr) override;
    bool visitStatement(const Statement& stmt) override;

    bool fConditionalExits = false;
    int fInConditional = 0;
    int fInLoop = 0;
    int fInSwitch = 0;
};
```

- `fConditionalExits`：选择搜索条件退出还是无条件退出
- `fInConditional`：当前嵌套在条件语句中的深度
- `fInLoop`：当前嵌套在循环中的深度
- `fInSwitch`：当前嵌套在 switch 中的深度

## 公共 API 函数

```cpp
bool Analysis::SwitchCaseContainsUnconditionalExit(const Statement& stmt);
```
- 检查 switch case 是否包含无条件退出
- 无条件退出是指不在任何 if/loop 内部的 return/break/continue

```cpp
bool Analysis::SwitchCaseContainsConditionalExit(const Statement& stmt);
```
- 检查 switch case 是否包含条件退出
- 条件退出是指在 if/loop 内部的 return/break/continue

## 内部实现细节

### 语句类型处理逻辑

| 语句类型 | 处理方式 |
|---------|---------|
| `Block` / `SwitchCase` | 递归访问子语句 |
| `Return` | 始终是退出，按条件/无条件模式判断 |
| `Continue` | 对 switch 来说是退出（但对循环不是） |
| `Break` | 不能逃脱 switch 或 loop（只在两者都不嵌套时才是退出） |
| `If` | 增加 `fInConditional` 深度后递归 |
| `For` / `Do` | 增加 `fInConditional` 和 `fInLoop` 深度后递归 |
| `Switch` | 增加 `fInSwitch` 深度后递归 |
| 其他 | 返回 false（不是退出） |

### 条件/无条件退出的判断

```cpp
return fConditionalExits ? fInConditional : !fInConditional;
```

- **无条件退出模式**（`fConditionalExits = false`）：仅当退出语句不在任何条件/循环内部时返回 true
- **条件退出模式**（`fConditionalExits = true`）：仅当退出语句在条件/循环内部时返回 true

### 循环被视为条件

循环体同时增加 `fInConditional` 和 `fInLoop` 计数器，因为循环可能执行零次（编译器没有简单的方法判断循环是否至少执行一次）。

### 表达式跳过

```cpp
bool visitExpression(const Expression& expr) override {
    return false;
}
```

表达式不包含控制流语句，因此完全跳过，提高分析效率。

## 依赖关系

- `src/sksl/SkSLAnalysis.h` — `Analysis` 类声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — `ProgramVisitor` 基类
- `src/sksl/ir/SkSLIRNode.h` — IR 节点基类
- `src/sksl/ir/SkSLStatement.h` — 语句类型

## 设计模式与设计决策

- **访问者模式**：继承 `ProgramVisitor`，通过 `visitStatement` 回调遍历 IR 树。
- **上下文跟踪**：使用 `fInConditional`、`fInLoop`、`fInSwitch` 计数器跟踪嵌套上下文，无需显式的栈结构。
- **双模式复用**：同一个访问者类通过 `fConditionalExits` 标志支持两种分析模式，避免代码重复。
- **保守分析**：将循环视为条件（可能执行零次），确保分析结果在所有情况下都是安全的。

## 性能考量

1. **表达式跳过**：跳过所有表达式访问，大幅减少了遍历的节点数量。
2. **早期终止**：一旦找到退出语句（返回 true），`ProgramVisitor` 会停止遍历。
3. **O(N) 时间复杂度**：遍历一遍 IR 树即可完成分析，N 为语句节点数。

## 相关文件

- `src/sksl/SkSLAnalysis.h` — 分析函数声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/analysis/SkSLGetReturnComplexity.cpp` — 相关的返回复杂度分析
- `src/sksl/analysis/SkSLGetLoopControlFlowInfo.cpp` — 相关的循环控制流分析
