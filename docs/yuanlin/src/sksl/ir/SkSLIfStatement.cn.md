# SkSL IfStatement (if 语句)

> 源文件:
> - `src/sksl/ir/SkSLIfStatement.h`
> - `src/sksl/ir/SkSLIfStatement.cpp`

## 概述

`IfStatement` 是 SkSL 编译器中间表示（IR）中用于表示 `if` 语句的类。它封装了条件表达式（test）、真分支语句（ifTrue）和可选的假分支语句（ifFalse）。该类不仅提供基本的 IR 表示功能，还内置了编译期优化逻辑：当条件表达式为编译时常量时，可以在构造阶段直接折叠为对应分支，消除死代码。

## 架构位置

`IfStatement` 位于 SkSL IR 层的语句（Statement）层级，继承自 `Statement` 基类。它是程序控制流的基本构建块之一，与其他语句类型（如 `ForStatement`、`SwitchStatement`）一起构成 SkSL 的控制流 IR 表示。

```
Statement (基类)
  |-- IfStatement
  |-- ForStatement
  |-- SwitchStatement
  |-- ReturnStatement
  |-- ...
```

## 主要类与结构体

### `IfStatement`

`final` 类，继承自 `Statement`。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fTest` | `unique_ptr<Expression>` | 条件表达式，类型必须为 `bool` |
| `fIfTrue` | `unique_ptr<Statement>` | 条件为真时执行的语句 |
| `fIfFalse` | `unique_ptr<Statement>` | 条件为假时执行的语句（可为 `nullptr`） |

**IR 节点类型标识：** `Kind::kIf`

## 公共 API 函数

### 构造方法

- **`IfStatement(pos, test, ifTrue, ifFalse)`** -- 直接构造，不进行任何验证或优化。

### 工厂方法

- **`Convert(context, pos, test, ifTrue, ifFalse)`** -- 完整的转换方法。执行以下步骤：
  1. 将条件表达式强制转换为 `bool` 类型
  2. 检测真分支和假分支中不带作用域的变量声明（这是错误的）
  3. 委托给 `Make()` 进行优化和构造

- **`Make(context, pos, test, ifTrue, ifFalse)`** -- 带优化的构造方法。在优化开启时执行以下简化：
  1. 如果真假分支都为空，将整个 if 语句简化为条件表达式语句
  2. 如果条件是布尔常量 `true`，直接返回真分支
  3. 如果条件是布尔常量 `false`，直接返回假分支
  4. 将空的真分支替换为 `Nop`，移除空的假分支

### 访问器

- **`test()` / `test() const`** -- 返回条件表达式的引用
- **`ifTrue()` / `ifTrue() const`** -- 返回真分支语句的引用
- **`ifFalse()` / `ifFalse() const`** -- 返回假分支语句的引用
- **`description()`** -- 返回 if 语句的文本表示

## 内部实现细节

### 编译期常量折叠

`Make()` 方法利用 `ConstantFolder::GetConstantValueForVariable()` 获取条件表达式的常量值。当条件为编译时已知的布尔字面量时：
- `true` 时直接返回 `ifTrue` 分支
- `false` 时直接返回 `ifFalse` 分支（或 `Nop`）

### 空分支处理

辅助函数 `replace_empty_with_nop()` 确保返回的语句不为 `nullptr`。当分支为空（`isEmpty()` 返回 `true`）或为 `nullptr` 时，用 `Nop::Make()` 替代。这简化了后续代码生成阶段的处理。

### 变量声明作用域检查

`Convert()` 方法通过 `Analysis::DetectVarDeclarationWithoutScope()` 检测类似以下的无作用域变量声明：
```glsl
if (cond) int x;  // 错误：变量声明需要大括号作用域
```

### 优化控制

所有优化行为都受 `context.fConfig->fSettings.fOptimize` 控制。当优化关闭时，`Make()` 直接构造 `IfStatement` 而不进行任何简化。

## 依赖关系

**内部依赖：**
- `SkSLExpression` -- 条件表达式基类
- `SkSLStatement` -- 语句基类
- `SkSLContext` -- 编译器上下文
- `SkSLAnalysis` -- 语义分析工具（变量声明检测）
- `SkSLConstantFolder` -- 常量折叠工具
- `SkSLExpressionStatement` -- 表达式语句（用于空分支简化）
- `SkSLLiteral` -- 字面量（用于布尔常量检查）
- `SkSLNop` -- 空操作语句（用于替换空分支）
- `SkSLType` -- 类型系统（用于 bool 类型强制转换）

**外部依赖：**
- `<memory>`, `<string>` -- 标准库

## 设计模式与设计决策

1. **Convert/Make 双层工厂模式**：`Convert` 负责类型检查和错误报告，`Make` 负责优化和最终构造。外部解析器调用 `Convert`，内部信任的代码可直接调用 `Make`。

2. **构造时优化**：将常量折叠优化内嵌到 IR 节点的构造过程中，确保 IR 在构造完成时就已经是优化过的形式。这避免了单独的优化遍历。

3. **Nop 替代 nullptr**：空分支用 `Nop` 代替 `nullptr`，简化了后续的遍历和代码生成逻辑，避免了大量的空指针检查。

4. **不可变 IR 节点**：`IfStatement` 为 `final` 类，不允许被继承，确保 IR 节点的语义一致性。

## 性能考量

- **编译期消除死代码**：当条件为常量时，整个 if 语句在构造阶段即被简化，减少后续处理的 IR 节点数量。
- **空分支优化**：移除空的 else 分支可以减少代码生成输出的大小。
- **分支合并**：当两个分支都为空时，保留条件表达式（可能有副作用）但消除分支结构，减少生成代码中的分支指令。

## 相关文件

- `src/sksl/ir/SkSLStatement.h` -- Statement 基类
- `src/sksl/ir/SkSLExpression.h` -- Expression 基类
- `src/sksl/ir/SkSLNop.h` -- 空操作语句
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具
- `src/sksl/SkSLAnalysis.h` -- 程序分析工具
- `src/sksl/ir/SkSLForStatement.h` -- 循环语句（类似的控制流 IR）
- `src/sksl/ir/SkSLSwitchStatement.h` -- switch 语句（类似的控制流 IR）
