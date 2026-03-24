# SkSL CanExitWithoutReturningValue 分析

> 源文件: `src/sksl/analysis/SkSLCanExitWithoutReturningValue.cpp`

## 概述

`SkSLCanExitWithoutReturningValue.cpp` 实现了 SkSL 编译器中的返回值可达性分析功能。该模块的核心目的是检查一个非 `void` 函数是否存在某条执行路径可以在不执行 `return` 语句的情况下退出函数。

这是编程语言编译器中常见的语义检查——确保声明了返回类型的函数在所有可能的执行路径上都有对应的 `return` 语句。如果存在某条路径缺少返回值，编译器应当报告警告或错误。

该分析需要处理 SkSL 支持的所有控制流结构：`if/else`、`for` 循环、`do-while` 循环、`switch/case` 语句以及代码块。

## 架构位置

```
Skia
└── src/sksl/
    ├── SkSLAnalysis.h                              // 分析接口声明
    ├── analysis/
    │   ├── SkSLCanExitWithoutReturningValue.cpp     // 本文件
    │   ├── SkSLProgramVisitor.h                     // 访问者基类
    │   └── ...
    └── ir/
        ├── SkSLIfStatement.h
        ├── SkSLForStatement.h
        ├── SkSLDoStatement.h
        ├── SkSLSwitchStatement.h
        └── ...
```

本模块属于语义检查阶段的分析，在函数编译完成后被调用，用于验证函数体的返回路径完整性。

## 主要类与结构体

### `ReturnsOnAllPathsVisitor`

- **继承关系**: 继承自 `ProgramVisitor`
- **作用域**: 匿名命名空间内，文件内可见
- **状态标志**:
  - `fFoundReturn` (`bool`): 是否在所有路径上发现了无条件的 `return`
  - `fFoundBreak` (`bool`): 是否发现了 `break` 语句
  - `fFoundContinue` (`bool`): 是否发现了 `continue` 语句
- **设计特点**: 每个控制流分支创建独立的 visitor 实例进行分析，然后合并结果

## 公共 API 函数

### `bool Analysis::CanExitWithoutReturningValue(const FunctionDeclaration& funcDecl, const Statement& body)`

- **功能**: 判断函数是否可能在不返回值的情况下退出
- **参数**:
  - `funcDecl`: 函数声明（用于获取返回类型）
  - `body`: 函数体语句
- **返回值**: `true` 表示函数可能不返回值（存在问题）；`false` 表示所有路径都有返回值（或函数为 void 类型）
- **特殊处理**: 如果函数返回类型为 `void`，直接返回 `false`（void 函数不需要 return 语句）

## 内部实现细节

### 控制流分析策略

每种控制流语句有不同的分析规则：

#### if/else 语句
- 分别用独立的 `ReturnsOnAllPathsVisitor` 分析 `ifTrue` 和 `ifFalse` 分支
- **return**: 两个分支都必须返回，整体才算返回（`&&` 逻辑）
- **break/continue**: 任一分支存在即报告（`||` 逻辑），因为不确定运行时走哪条路径
- 无 `else` 分支时，`falseVisitor` 保持初始状态（未发现返回）

#### for 循环
- 假设循环至少执行一次（这是一个宽松的假设）
- 循环体中的 `break` 和 `continue` 被忽略（它们只影响循环，不影响函数）
- 只关注循环体中是否有无条件 `return`

#### do-while 循环
- 与 for 循环类似，但 do-while 循环保证至少执行一次
- 同样忽略 `break` 和 `continue`

#### switch 语句
- 最复杂的控制流分析
- 必须满足以下条件才算所有路径返回：
  1. 存在 `default` 分支
  2. 每个 `case` 要么无条件返回，要么落入（fall through）到下一个最终返回的 `case`
- 任何 `case` 中存在 `break` 会导致整个 switch 被判定为非完全返回
- `continue` 会传播到外层

#### 其他语句
- `return`: 设置 `fFoundReturn = true`
- `break`: 设置 `fFoundBreak = true`
- `continue`: 设置 `fFoundContinue = true`
- `block`: 直接递归遍历（块不引入新的控制流语义）
- `discard`/`expression`/`nop`/`varDeclaration`: 不影响返回分析

### 表达式处理

`visitExpression()` 直接返回 `false`，跳过所有表达式遍历。表达式中不可能包含 `return` 语句，因此无需处理。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLAnalysis.h` | 函数声明 |
| `SkSLDefines.h` | SkSL 基础定义 |
| `SkSLProgramVisitor.h` | 访问者基类 |
| `SkSLDoStatement.h` | do-while 语句 |
| `SkSLForStatement.h` | for 语句 |
| `SkSLIfStatement.h` | if 语句 |
| `SkSLSwitchCase.h` | switch case 分支 |
| `SkSLSwitchStatement.h` | switch 语句 |
| `SkSLFunctionDeclaration.h` | 函数声明（获取返回类型） |
| `SkSLStatement.h` | 语句基类 |
| `SkSLType.h` | 类型信息（判断 void） |

## 设计模式与设计决策

1. **访问者模式变体**: 虽然继承自 `ProgramVisitor`，但并不是简单的递归遍历。对于带有控制流的语句，创建子 visitor 实例独立分析各分支后再合并结果
2. **三状态追踪**: 使用 `fFoundReturn`、`fFoundBreak`、`fFoundContinue` 三个布尔值追踪退出状态，每种状态在不同控制流结构中的传播规则不同
3. **宽松的循环假设**: 假设 for 循环至少执行一次。注释解释了这是一个有意为之的设计决策——比起对合理代码报误，宁可稍微宽松一些
4. **分层处理 break/continue**: `break` 和 `continue` 在循环中被吸收（不传播到外层），在 switch 中 `break` 被吸收但 `continue` 传播，在 if 中两者都传播
5. **保守分析方向**: 对于 return 采用保守策略（if 的两个分支必须都返回），对于 break/continue 采用宽松策略（任一分支即传播）

## 性能考量

- 每个控制流分支创建独立的 visitor 实例（栈上分配），开销极低
- `visitExpression()` 跳过表达式处理，大幅减少遍历节点数
- 遇到 `return`/`break`/`continue` 立即返回 `true` 终止当前分支遍历
- 整体复杂度为 O(n)，其中 n 为语句节点数
- 作为编译期检查，不影响着色器运行时性能

## 相关文件

- `src/sksl/SkSLAnalysis.h` — 函数声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/ir/SkSLIfStatement.h` — if 语句定义
- `src/sksl/ir/SkSLForStatement.h` — for 语句定义
- `src/sksl/ir/SkSLDoStatement.h` — do-while 语句定义
- `src/sksl/ir/SkSLSwitchStatement.h` — switch 语句定义
- `src/sksl/ir/SkSLSwitchCase.h` — switch case 分支定义
- `src/sksl/ir/SkSLFunctionDeclaration.h` — 函数声明定义
