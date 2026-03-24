# SkSL SwitchStatement (switch 语句)

> 源文件:
> - `src/sksl/ir/SkSLSwitchStatement.h`
> - `src/sksl/ir/SkSLSwitchStatement.cpp`

## 概述

`SwitchStatement` 是 SkSL 编译器中间表示（IR）中用于表示 `switch` 语句的类。它封装了 switch 的值表达式和包含多个 `SwitchCase` 的 case 块。该类提供了完整的编译期优化能力：当 switch 值为常量时，可以将整个 switch 语句折叠为匹配的 case 分支；同时处理了变量声明提升、重复 case 值检测、条件 break 分析等复杂场景。

## 架构位置

`SwitchStatement` 继承自 `Statement`，是 SkSL IR 控制流语句家族的成员。

```
Statement (基类)
  |-- SwitchStatement (switch 语句)
  |-- IfStatement     (if 语句)
  |-- ForStatement    (for 循环)
  |-- ...

SwitchStatement 内部结构:
  SwitchStatement
    |-- fValue: Expression (switch 值)
    |-- fCaseBlock: Block
          |-- SwitchCase (case 1: ...)
          |-- SwitchCase (case 2: ...)
          |-- SwitchCase (default: ...)
```

## 主要类与结构体

### `SwitchStatement`

`final` 类，继承自 `Statement`。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fValue` | `unique_ptr<Expression>` | switch 的值表达式（类型为 `int`） |
| `fCaseBlock` | `unique_ptr<Statement>` | 包含 SwitchCase 语句的 Block |

**IR 节点类型标识：** `Kind::kSwitch`

## 公共 API 函数

### 构造方法

- **`SwitchStatement(pos, value, caseBlock)`** -- 直接构造，不进行验证。

### 工厂方法

- **`Convert(context, pos, value, caseValues, caseStatements, symbolTable)`** -- 完整的转换方法：
  1. 将 switch 值表达式强制转换为 `int` 类型
  2. 将 case 值强制转换为与 switch 值相同的类型
  3. 验证 case 值为常量整数
  4. 检测并报告重复的 case 值
  5. 通过 `Transform::HoistSwitchVarDeclarationsAtTopLevel` 提升变量声明
  6. 委托给 `Make()` 进行优化

- **`Make(context, pos, value, caseBlock)`** -- 带优化的构造方法：
  1. 验证所有子语句都是 `SwitchCase`
  2. 验证没有重复的 case 值
  3. 当 switch 值为常量时，尝试折叠为匹配的 case 分支

### 访问器

- **`value()` / `value() const`** -- 返回 switch 值表达式
- **`caseBlock()` / `caseBlock() const`** -- 返回包含 SwitchCase 的 Block
- **`cases()` / `cases() const`** -- 便捷方法，直接返回 Block 内的 StatementArray
- **`description()`** -- 输出 `switch (value) { cases }` 格式文本

## 内部实现细节

### 重复 case 值检测

`find_duplicate_case_values()` 使用 `THashSet<SKSL_INT>` 跟踪已出现的 case 值，同时用 `foundDefault` 标志检测重复的 default case。返回所有重复的 `SwitchCase` 指针列表。

### 条件 break 移除

`remove_break_statements()` 使用 `ProgramWriter` 访问者模式遍历语句树，将所有 `BreakStatement` 替换为 `Nop`。注意该函数只遍历语句，不进入表达式。

### 静态 switch 折叠（block_for_case）

当 switch 值为编译时常量时，`block_for_case()` 函数尝试将 switch 简化为匹配的 case 语句块。算法如下：

1. **定位匹配 case**：在 case 列表中找到与常量值匹配的 SwitchCase。
2. **分析 fallthrough**：从匹配位置开始向后扫描：
   - 遇到条件退出（conditional exit）-> 放弃优化，返回 false
   - 遇到无条件退出（unconditional exit）-> 标记需要移除 break
   - 到达末尾 -> 包含所有后续 case
3. **重构 Block**：将匹配范围内的 SwitchCase 解包为普通语句，移到数组前端，截断多余部分。
4. **清理 break**：如果存在无条件 break，使用 `remove_break_statements()` 清理。

### 变量声明提升

`Convert()` 通过 `Transform::HoistSwitchVarDeclarationsAtTopLevel` 将 switch-case 顶层的变量声明提升到 switch 外部的包裹 Block 中。这解决了两个问题：
- 后端不支持原生 switch 时的作用域问题
- fallthrough 时变量被后续 case 继承的正确性问题

### Make 方法的常量折叠

当优化开启且 switch 值为常量时：
1. 在 case 列表中搜索匹配值和 default case
2. 如果找到匹配 case，尝试 `block_for_case` 折叠
3. 如果只有 default case，使用 default
4. 如果没有匹配且没有 default，清空 caseBlock 并返回空 Block（保留符号表）

## 依赖关系

**内部依赖：**
- `SkSLExpression` / `SkSLStatement` -- 基类
- `SkSLBlock` -- case 块容器
- `SkSLSwitchCase` -- 单个 case 表示
- `SkSLBreakStatement` -- break 语句
- `SkSLNop` -- 空操作（替换 break）
- `SkSLConstantFolder` -- 常量折叠（获取 switch 值和 case 值）
- `SkSLAnalysis` -- 分析工具（条件/无条件退出检测）
- `SkSLContext` -- 编译器上下文
- `SkSLErrorReporter` -- 错误报告
- `SkSLSymbolTable` -- 符号表
- `SkSLTransform` -- 变换工具（变量声明提升）
- `SkSLProgramWriter` -- 程序遍历器

**外部依赖：**
- `SkTHash` -- 哈希集合（重复检测）
- `<algorithm>`, `<iterator>` -- 标准库

## 设计模式与设计决策

1. **Convert/Make 双层模式**：`Convert` 处理用户输入的验证（类型检查、重复检测、变量提升），`Make` 处理已验证输入的优化。

2. **Block 包装 SwitchCase**：case 列表使用 `Block` 而非独立数组存储。这与 SkSL 的通用语句容器模型一致，且允许 Block 携带 SymbolTable。

3. **保守的 fallthrough 分析**：`block_for_case` 在遇到条件 break 时完全放弃优化，而不是尝试部分优化。这保证了安全性。

4. **变量声明提升**：将 switch 内部的变量声明提升到外部作用域，是为了处理不同 case 间的 fallthrough 共享变量的正确性问题，同时解决了某些后端（如不支持原生 switch 的后端）的代码生成困难。

5. **空 Block 保留符号表**：当 switch 被完全优化掉时，仍保留空的 caseBlock（含符号表），避免了恶意输入代码的作用域解析问题。

## 性能考量

- **编译时 switch 消除**：常量 switch 值在编译期折叠，减少了生成代码中的分支指令，特别有利于 GPU 着色器性能。
- **重复检测使用哈希表**：O(n) 的重复 case 值检测，n 为 case 数量。
- **Fallthrough 分析单遍扫描**：`block_for_case` 只需一次前向扫描即可完成分析。
- **in-place 重构**：case 折叠直接在原有 StatementArray 上操作（移动到数组前端然后截断），避免额外内存分配。

## 相关文件

- `src/sksl/ir/SkSLSwitchCase.h` -- SwitchCase IR 节点
- `src/sksl/ir/SkSLBlock.h` -- Block 语句容器
- `src/sksl/ir/SkSLBreakStatement.h` -- break 语句
- `src/sksl/ir/SkSLStatement.h` -- Statement 基类
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具
- `src/sksl/SkSLAnalysis.h` -- 程序分析工具
- `src/sksl/transform/SkSLTransform.h` -- 变换工具
- `src/sksl/transform/SkSLProgramWriter.h` -- 程序遍历器
