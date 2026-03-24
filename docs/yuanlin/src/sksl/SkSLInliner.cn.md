# SkSL Inliner（函数内联器）

> 源文件：[src/sksl/SkSLInliner.h](../../src/sksl/SkSLInliner.h)、[src/sksl/SkSLInliner.cpp](../../src/sksl/SkSLInliner.cpp)

## 概述

`Inliner` 是 SkSL 编译器的函数内联优化器。它将函数调用（`FunctionCall`）转换为一组在调用点注入的语句和替代表达式，从而消除函数调用的开销。内联器能够检测不适合内联的情况（如包含提前返回、循环中的 return、递归调用等），并通过大小阈值和语句计数上限防止代码膨胀。整个内联器在 `SK_ENABLE_OPTIMIZE_SIZE` 编译配置下会被完全禁用。

## 架构位置

`Inliner` 在 SkSL 编译管道的优化阶段运行，由 `Compiler` 调用：

```
解析器 -> IR 树 -> finalize()（验证）
                      |
                      v
                 optimize()
                      |
                      v
              Inliner::analyze()（函数内联）
                      |
                      v
              死代码消除、不可达代码消除
                      |
                      v
                 代码生成器
```

## 主要类与结构体

### `class Inliner`

核心内联器类：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fContext` | `const Context*` | 编译上下文指针 |
| `fMangler` | `Mangler` | 名称修饰器，用于为内联变量生成唯一名称 |
| `fInlinedStatementCounter` | `int` | 已内联的语句计数，防止病态膨胀 |

### `struct InlinedCall`

内联结果结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fInlinedBody` | `std::unique_ptr<Block>` | 内联生成的语句块，插入到调用点之前 |
| `fReplacementExpr` | `std::unique_ptr<Expression>` | 替换原函数调用的表达式 |

### `struct InlineCandidate`（内部）

内联候选项，记录一个潜在可内联的函数调用及其上下文：

| 字段 | 说明 |
|------|------|
| `fSymbols` | 候选项所在的符号表 |
| `fParentStmt` | 外围语句的父语句 |
| `fEnclosingStmt` | 包含候选项的语句 |
| `fCandidateExpr` | 候选的 FunctionCall 表达式 |
| `fEnclosingFunction` | 包含候选项的函数定义 |

### `class InlineCandidateAnalyzer`（内部）

遍历程序 IR 以收集所有内联候选项。维护符号表栈和外围语句栈。

## 公共 API 函数

### `bool analyze(elements, symbols, usage)`

主入口函数。分析程序中所有函数调用，确定可内联的候选项并执行内联。返回 `true` 表示执行了至少一次内联变换。

## 内部实现细节

### 内联流程

`analyze` 方法的完整执行流程：

1. **检查阈值**：如果内联阈值 <= 0 或已超过语句限制，直接返回
2. **构建候选列表**（`buildCandidateList`）：
   - `InlineCandidateAnalyzer` 遍历所有程序元素
   - 过滤不安全的候选项（`candidateCanBeInlined`）
   - 按大小阈值过滤（总内联成本不超过阈值）
3. **执行内联**：对每个候选项调用 `inlineCall`
4. **重写引用**：更新语句映射表以处理多个候选项指向同一外围语句的情况
5. **更新使用量**：维护 `ProgramUsage` 统计

### inlineCall 的实现

`inlineCall` 将一个函数调用转换为内联代码：

1. 为非 void 且有复杂返回的函数创建结果变量
2. 为每个参数创建临时变量（或直接重用表达式）：
   - 如果参数不被写入且是平凡表达式或仅被读取一次，可以直接使用原表达式
   - 否则需要创建临时变量（scratch variable）
3. 递归克隆函数体中的每个语句和表达式，替换所有变量引用
4. 将 `return` 语句转换为对结果变量的赋值
5. 将所有语句包装在无作用域的 Block 中

### 表达式和语句的递归克隆

`inlineExpression` 和 `inlineStatement` 递归遍历整棵 IR 树，通过 `VariableRewriteMap` 将原函数的变量引用替换为内联后的新变量。对于每种 IR 节点类型都有专门的克隆逻辑。

### 安全性检查

`isSafeToInline` 检查以下条件：
- 内联阈值 > 0
- 未超过语句限制（2500）
- 函数有定义（非外部声明）
- 函数未标记 `noinline`
- `out` 参数、数组参数和结构体参数未被写入
- 无提前返回（`ReturnComplexity < kEarlyReturns`）

### 候选项过滤

`buildCandidateList` 按以下顺序过滤候选项：
1. 移除不安全的候选项
2. 移除传递不可复制参数（opaque 类型）的候选项
3. 如果阈值非无限，移除总内联成本超过阈值的候选项
4. `inline` 修饰的函数和仅使用一次的函数跳过大小限制

### 短路求值保护

`InlineCandidateAnalyzer` 不对逻辑 AND/OR 的右侧进行内联候选分析，以保护短路求值语义。类似地，三元表达式的 true/false 分支也不作为候选项。

### 作用域确保

`ensureScopedBlocks` 确保内联体在用作 if/for/do/while 的主体时拥有正确的作用域，避免生成语义错误的代码。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLMangler.h` | 生成唯一变量名 |
| `SkSLAnalysis.h` | 返回复杂度分析、节点计数、副作用检测等 |
| `SkSLProgramUsage.h` | 变量和函数使用量统计 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLTransform.h` | `AddConstToVarModifiers` 等变换工具 |
| 几乎所有 IR 节点头文件 | 克隆各种 IR 节点 |

## 设计模式与设计决策

1. **候选列表模式**：先收集所有候选项，再统一过滤和内联，避免遍历时修改导致的迭代器失效。
2. **变量重写映射**：使用 `THashMap` 将原变量映射到新变量/表达式，支持参数的直接替换优化。
3. **语句计数限制**：硬性限制（2500条语句）防止指数级代码膨胀（如 `ExponentialGrowth.sksl` 测试用例）。
4. **缓存机制**：`InlinabilityCache` 和 `FunctionSizeCache` 避免对同一函数的重复分析。
5. **条件编译**：整个内联器通过 `#ifndef SK_ENABLE_OPTIMIZE_SIZE` 包裹，可在编译时完全移除。
6. **语句重映射表**：当多个候选项指向同一外围语句时，通过 `StatementRemappingTable` 正确处理语句替换链。

## 性能考量

- 内联仅运行一次（由 `Compiler::optimize` 控制），因为多次传递的收益递减
- 模块内联可多次运行直到无变化
- 参数按需创建临时变量，平凡表达式和单次读取的参数直接替换，避免不必要的变量创建
- `InlinabilityCache` 和 `FunctionSizeCache` 避免重复计算
- `overInlineStatementLimit` 提供硬上限，防止编译时间爆炸
- `fInlineThreshold` 为 `INT_MAX` 时跳过大小过滤，用于需要激进内联的场景

## 相关文件

- `src/sksl/SkSLCompiler.h` / `.cpp` —— 编译器调用内联器
- `src/sksl/SkSLMangler.h` / `.cpp` —— 名称修饰器
- `src/sksl/SkSLAnalysis.h` —— 分析工具（返回复杂度、节点计数等）
- `src/sksl/analysis/SkSLProgramUsage.h` —— 使用量统计
- `src/sksl/ir/SkSLFunctionCall.h` —— 被内联替换的函数调用节点
- `src/sksl/ir/SkSLFunctionDefinition.h` —— 被内联的函数定义
