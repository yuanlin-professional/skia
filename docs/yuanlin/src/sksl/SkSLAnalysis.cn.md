# SkSL Analysis（静态分析工具集）

> 源文件：[src/sksl/SkSLAnalysis.h](../../src/sksl/SkSLAnalysis.h)、[src/sksl/SkSLAnalysis.cpp](../../src/sksl/SkSLAnalysis.cpp)

## 概述

`SkSLAnalysis` 模块是 SkSL 编译器的静态分析工具集，提供了一系列用于在编译阶段对 SkSL 程序进行语义分析的工具函数。这些函数涵盖了采样用法分析、变量引用检测、副作用判断、可赋值性检查、循环展开信息提取、死代码检测、返回值分析等多个方面。该模块不直接修改 IR（中间表示），而是作为编译器优化和验证阶段的信息提供者。

## 架构位置

`Analysis` 命名空间位于 SkSL 编译器的中间层，在 IR 构建之后、代码生成和优化之前被广泛使用：

```
SkSL 源代码 -> 解析器 -> IR 树
                          |
                    Analysis（静态分析）
                          |
                    优化 / 验证 / 代码生成
```

它为以下阶段提供关键信息：
- **优化阶段**：确定函数是否可以被内联、变量是否可以被消除
- **验证阶段**：检查程序结构正确性、ES2 兼容性
- **代码生成阶段**：确定采样方式、builtin 引用等

## 主要类与结构体

### `namespace Analysis`

所有分析函数都位于 `SkSL::Analysis` 命名空间中，以静态自由函数的形式组织。

### `struct LoopControlFlowInfo`

描述循环体中的控制流信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fHasContinue` | `bool` | 是否包含 `continue` 语句 |
| `fHasBreak` | `bool` | 是否包含 `break` 语句 |
| `fHasReturn` | `bool` | 是否包含 `return` 语句 |

### `struct AssignmentInfo`

赋值分析的结果信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fAssignedVar` | `VariableReference*` | 被赋值的变量引用 |

### `enum class ReturnComplexity`

描述函数返回路径的复杂度：

| 值 | 说明 |
|----|------|
| `kSingleSafeReturn` | 仅有一个安全的返回点 |
| `kScopedReturns` | 在不同作用域中有多个返回 |
| `kEarlyReturns` | 存在提前返回 |

### `class SymbolTableStackBuilder`

与 `ProgramVisitor` 配合使用的 RAII 工具类，自动维护符号表栈。当遍历带有独立符号表的语句时，自动将符号表压入栈，析构时自动弹出。

## 公共 API 函数

### 采样分析

- **`GetSampleUsage(program, child, writesToSampleCoords, elidedSampleCoordCount)`** —— 分析程序如何采样指定的子效果（child effect），返回 `SampleUsage` 枚举（PassThrough / Explicit）
- **`CallsSampleOutsideMain(program)`** —— 检查是否在 `main()` 以外的函数中调用了子效果采样
- **`CallsColorTransformIntrinsics(program)`** —— 检查是否使用了 `toLinearSrgb` / `fromLinearSrgb` 颜色变换内置函数

### 引用检测

- **`ReferencesBuiltin(program, builtin)`** —— 检查程序是否引用了指定的 builtin 变量
- **`ReferencesSampleCoords(program)`** —— 检查程序是否引用了采样坐标
- **`ReferencesFragCoords(program)`** —— 检查程序是否引用了 `sk_FragCoord`
- **`ContainsRTAdjust(expr)`** —— 检查表达式中是否包含 `sk_RTAdjust`
- **`ContainsVariable(expr, var)`** —— 检查表达式中是否包含指定变量

### 表达式分析

- **`HasSideEffects(expr)`** —— 判断表达式是否有副作用
- **`IsCompileTimeConstant(expr)`** —— 判断是否为编译时常量（仅由字面量和构造器组成）
- **`IsDynamicallyUniformExpression(expr)`** —— 判断表达式是否为动态统一表达式
- **`IsTrivialExpression(expr)`** —— 判断表达式是否"平凡"（可安全克隆而无性能损失）
- **`IsSameExpressionTree(left, right)`** —— 判断两棵表达式树是否相同（用于优化器检测自赋值）
- **`IsConstantExpression(expr)`** —— 判断是否符合 GLSL 1.0 的常量表达式定义

### 可赋值性分析

- **`IsAssignable(expr, info, errors)`** —— 判断表达式是否可被赋值
- **`UpdateVariableRefKind(expr, kind, errors)`** —— 更新变量引用的引用类型

### 语句分析

- **`DetectVarDeclarationWithoutScope(stmt, errors)`** —— 检测脱离作用域的变量声明
- **`StatementWritesToVariable(stmt, var)`** —— 检查语句是否写入指定变量
- **`SwitchCaseContainsUnconditionalExit(stmt)`** —— 检测 switch-case 中的无条件退出
- **`SwitchCaseContainsConditionalExit(stmt)`** —— 检测 switch-case 中的条件退出
- **`GetLoopControlFlowInfo(stmt)`** —— 获取循环中的控制流信息

### 函数与程序分析

- **`ReturnsOpaqueColor(function)`** —— 判断函数是否总是返回不透明颜色
- **`ReturnsInputAlpha(function, usage)`** —— 判断颜色过滤器是否保持输入 alpha 不变
- **`NodeCountUpToLimit(function, limit)`** —— 计算函数中的 IR 节点数（上限截止）
- **`GetReturnComplexity(funcDef)`** —— 分析函数的返回路径复杂度
- **`CanExitWithoutReturningValue(funcDecl, body)`** —— 检测可能不返回值的执行路径
- **`CheckProgramStructure(program)`** —— 检查递归和过深的调用链
- **`DoFinalizationChecks(program)`** —— 最终正确性检查
- **`GetComputeShaderMainParams(context, program)`** —— 获取计算着色器的输入输出参数

### 使用量统计

- **`GetUsage(program)` / `GetUsage(module)`** —— 构建程序或模块的使用量统计

### ES2 兼容性

- **`ValidateIndexingForES2(pe, errors)`** —— 验证索引表达式符合 GLSL ES 1.00 规范
- **`GetLoopUnrollInfo(...)`** —— 获取循环展开信息，确保循环终止（可能重写测试条件）

## 内部实现细节

### 访问者模式的广泛使用

实现文件中定义了多个内部访问者类，均继承自 `ProgramVisitor`：

1. **`MergeSampleUsageVisitor`** —— 遍历程序以合并子效果的采样用法。区分 PassThrough（直接传递坐标）和 Explicit（显式采样坐标）两种情况。
2. **`SampleOutsideMainVisitor`** —— 检测非 `main` 函数中的 ChildCall。
3. **`ReturnsNonOpaqueColorVisitor`** —— 检查 return 语句中第四个分量是否为已知的 1.0。
4. **`NodeCountVisitor`** —— 带上限的节点计数器，用于内联决策。
5. **`VariableWriteVisitor`** —— 检测对特定变量的写入引用。
6. **`IsAssignableVisitor`** —— 不继承 ProgramVisitor，仅检查表达式的子集字段以判断可赋值性。

### IsAssignableVisitor 的特殊设计

`IsAssignableVisitor` 没有使用标准的 `ProgramVisitor`，因为对于索引表达式 `x[1]`，只需要检查基础部分 `x` 是否可赋值，而不需要检查索引 `1`。它还特别处理了 swizzle 写入检查，防止对同一分量重复赋值。

### ProgramVisitor 模板实现

文件末尾包含了 `TProgramVisitor<T>` 的模板实现，为表达式、语句和程序元素提供了统一的遍历框架，并为 `ProgramVisitorTypes` 和 `ProgramWriterTypes` 两种类型实例化。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLSampleUsage.h` | 采样用法枚举和合并逻辑 |
| `SkSLCompiler.h` | `RTADJUST_NAME` 等常量 |
| `SkSLConstantFolder` | 常量折叠辅助，获取常量值 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLProgramUsage.h` | 程序使用量统计 |
| `SkSLProgramVisitor.h` | 访问者基类 |
| `SkSLProgramWriter.h` | 可写访问者基类 |
| 各种 IR 节点头文件 | 表达式、语句、类型等 IR 节点 |

## 设计模式与设计决策

1. **访问者模式（Visitor Pattern）**：所有分析均通过继承 `ProgramVisitor` 实现，遵循"返回 true 表示提前终止"的约定。
2. **命名空间级组织**：使用 `Analysis` 命名空间而非类，因为各分析函数之间无共享状态，适合作为独立的自由函数。
3. **保守分析策略**：如 `ReturnsOpaqueColor` 和 `ReturnsInputAlpha` 等函数采用保守分析，宁可误报（返回 false）也不漏报。
4. **ES2 兼容性验证**：通过 `GetLoopUnrollInfo` 在发现潜在无限循环时主动重写循环条件（如将 `!=` 改为 `>`），确保循环终止性。
5. **分离的读/写访问者**：ProgramVisitor（只读）和 ProgramWriter（可写）通过模板参数区分，共享遍历逻辑。

## 性能考量

- `NodeCountVisitor` 使用上限参数提前终止遍历，避免对大型函数进行完整计数
- `IsCompileTimeConstant` 在遇到第一个非常量子表达式时立即终止
- `ReferencesBuiltin` 直接遍历使用量映射而非 IR 树，效率更高
- 大多数访问者在找到目标后立即返回 `true` 终止遍历，避免不必要的递归
- `IsTrivialExpression` 的分析结果被内联器用于决定是否克隆表达式，间接影响生成代码的性能

## 相关文件

- `src/sksl/analysis/SkSLProgramVisitor.h` —— 访问者基类定义
- `src/sksl/analysis/SkSLProgramUsage.h` / `.cpp` —— 程序使用量统计
- `src/sksl/transform/SkSLProgramWriter.h` —— 可写访问者
- `src/sksl/SkSLCompiler.h` / `.cpp` —— 编译器主类，调用各分析函数
- `src/sksl/SkSLInliner.h` / `.cpp` —— 内联器，使用分析结果决策
- `src/sksl/ir/SkSLProgram.h` —— 程序 IR 结构
- `include/private/SkSLSampleUsage.h` —— 采样用法定义
