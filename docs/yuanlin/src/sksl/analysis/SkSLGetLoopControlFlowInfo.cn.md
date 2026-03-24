# SkSLGetLoopControlFlowInfo — 循环控制流分析

> 源文件：[`src/sksl/analysis/SkSLGetLoopControlFlowInfo.cpp`](../../src/sksl/analysis/SkSLGetLoopControlFlowInfo.cpp)

## 概述

SkSLGetLoopControlFlowInfo.cpp 实现了对循环语句体的控制流分析，检测循环中是否包含 `continue`、`break` 和 `return` 语句。分析结果以 `LoopControlFlowInfo` 结构体返回，为 SkSL 编译器的循环优化（如循环展开）提供必要的控制流信息。

该文件 79 行，包含一个分析访问者类和一个公共分析函数。

## 架构位置

```
SkSL 编译器
  └── 分析（Analysis）模块
        └── 控制流分析
              ├── GetLoopControlFlowInfo（本文件）
              ├── SwitchCaseContainsExit
              └── GetReturnComplexity
```

此分析在 SkSL 的优化阶段使用，帮助决定循环是否可以安全展开以及如何处理循环中的控制流跳转。

## 主要类与结构体

### `LoopControlFlowInfo`（定义在 SkSLAnalysis.h）

```cpp
struct LoopControlFlowInfo {
    bool fHasContinue = false;
    bool fHasBreak = false;
    bool fHasReturn = false;
};
```

### `LoopControlFlowVisitor`（匿名命名空间内）

```cpp
class LoopControlFlowVisitor : public ProgramVisitor {
public:
    bool visitExpression(const Expression& expr) override;
    bool visitStatement(const Statement& stmt) override;
    LoopControlFlowInfo fResult;
    int fDepth = 0;
};
```

- `fResult`：累积的分析结果
- `fDepth`：当前嵌套在内部循环/switch 中的深度

## 公共 API 函数

```cpp
LoopControlFlowInfo Analysis::GetLoopControlFlowInfo(const Statement& stmt);
```
- 分析给定语句（通常是循环体）中的控制流
- 返回 `LoopControlFlowInfo` 指示是否存在 continue、break 和 return

## 内部实现细节

### 语句处理逻辑

| 语句类型 | 处理方式 |
|---------|---------|
| `Continue` | 仅当 `fDepth == 0`（不在内层循环中）时标记 `fHasContinue` |
| `Break` | 仅当 `fDepth == 0`（不在内层循环/switch中）时标记 `fHasBreak` |
| `Return` | 无论嵌套深度如何都标记 `fHasReturn`（return 会中止所有层级） |
| `For` / `Do` / `Switch` | 增加 `fDepth` 后递归访问 |
| 其他 | 递归访问子节点 |

### 深度跟踪与语义区别

- **continue**：只影响直接外层循环。在内层循环中的 continue 不影响外层循环的控制流。SkSL 禁止在 switch 中使用 continue。
- **break**：只影响直接外层的循环或 switch。内层的 break 不传播到外层。
- **return**：无论嵌套深度如何都会中止外层循环（return 退出整个函数）。

### 早期终止优化

```cpp
return fResult.fHasContinue && fResult.fHasBreak && fResult.fHasReturn;
```

当三个标志都已被设置时，无需继续遍历，可以提前终止。

### 表达式跳过

与其他分析一样，完全跳过表达式节点的遍历，因为控制流语句只出现在语句层级。

## 依赖关系

- `src/sksl/SkSLAnalysis.h` — 分析函数和 `LoopControlFlowInfo` 声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/ir/SkSLIRNode.h` — IR 节点基类
- `src/sksl/ir/SkSLStatement.h` — 语句类型

## 设计模式与设计决策

- **访问者模式**：继承 `ProgramVisitor` 遍历语句树。
- **深度跟踪**：使用单一的 `fDepth` 计数器而非分离的循环/switch 计数器，因为 break 和 continue 对两者的行为一致（不传播到外层）。
- **累积结果**：使用三个布尔标志累积分析结果，简洁且易于理解。
- **早期终止**：所有信息收集完毕后立即停止遍历。

## 性能考量

1. **O(N) 时间复杂度**：最多遍历一遍语句树。
2. **早期终止**：通常在找到所有控制流语句后提前返回，避免不必要的遍历。
3. **表达式跳过**：减少访问节点数量。

## 相关文件

- `src/sksl/SkSLAnalysis.h` — 分析函数声明和 `LoopControlFlowInfo` 定义
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/analysis/SkSLSwitchCaseContainsExit.cpp` — 相关的 switch 退出分析
- `src/sksl/transform/SkSLTransform.h` — 优化变换（使用此分析结果）
