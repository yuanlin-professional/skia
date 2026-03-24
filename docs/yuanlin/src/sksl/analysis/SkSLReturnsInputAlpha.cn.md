# SkSL ReturnsInputAlpha 分析

> 源文件: `src/sksl/analysis/SkSLReturnsInputAlpha.cpp`

## 概述

`SkSLReturnsInputAlpha.cpp` 实现了 SkSL 编译器中的"返回输入 Alpha"分析功能。该模块的核心目的是判断一个颜色滤镜（color filter）着色器函数是否保证其返回值的 alpha 分量与输入参数的 alpha 分量相同。

这一分析在图形管线优化中非常重要：如果一个颜色滤镜保留了输入的 alpha 值，渲染引擎可以跳过某些 alpha 相关的后处理步骤，从而提升性能。该分析通过模式匹配（pattern matching）的方式检查函数的所有 return 语句，验证返回表达式的最后一个分量（alpha 通道）是否始终来自输入变量。

## 架构位置

```
Skia
└── src/sksl/
    ├── SkSLAnalysis.h                  // 分析接口声明
    ├── analysis/
    │   ├── SkSLReturnsInputAlpha.cpp   // 本文件
    │   ├── SkSLProgramVisitor.h        // 访问者基类
    │   └── SkSLProgramUsage.h          // 变量使用统计
    └── ir/                             // SkSL 中间表示
```

本分析属于 SkSL 编译器分析子系统的一部分，在着色器优化阶段被调用，用于向渲染管线提供颜色滤镜的 alpha 保持特性信息。

## 主要类与结构体

### `ReturnsInputAlphaVisitor`

- **继承关系**: 继承自 `ProgramVisitor`
- **作用域**: 定义在匿名命名空间内，仅文件内可见
- **成员变量**:
  - `fUsage` (`const ProgramUsage&`): 程序变量使用统计信息的引用
  - `fInputVar` (`const Variable*`): 指向颜色滤镜输入参数的指针
- **核心方法**:
  - `visitProgramElement()`: 验证函数签名是否为颜色滤镜格式，并检查输入变量是否被修改
  - `isInputVar()`: 判断表达式是否直接引用输入变量
  - `isInputSwizzleEndingWithAlpha()`: 判断 swizzle 操作的最后分量是否为输入的 alpha（`.a`，即第 4 个分量）
  - `returnsInputAlpha()`: 递归模式匹配，判断表达式是否保留了输入 alpha
  - `visitStatement()`: 拦截 return 语句并进行 alpha 保留检查
  - `visitExpression()`: 空实现，因为表达式内部不包含 return 语句

## 公共 API 函数

### `bool Analysis::ReturnsInputAlpha(const FunctionDefinition& function, const ProgramUsage& usage)`

- **功能**: 判断给定的颜色滤镜函数是否在所有返回路径上保留输入的 alpha 值
- **参数**:
  - `function`: 待分析的函数定义
  - `usage`: 程序变量使用统计信息
- **返回值**: `true` 表示函数保证返回输入的 alpha 值；`false` 表示无法确认
- **前提条件**: 函数必须是颜色滤镜格式（单个 `half4` 参数）

## 内部实现细节

### 分析流程

1. **签名验证**: 检查函数是否接受单个 `half4`（4 分量浮点向量）参数，这是颜色滤镜的标准签名
2. **写入检查**: 通过 `ProgramUsage` 确认输入变量在函数体中未被写入（写入次数为 0）
3. **return 语句遍历**: 遍历函数体中所有 return 语句
4. **模式匹配**: 对每个 return 的表达式递归检查是否保留输入 alpha

### 模式匹配规则

`returnsInputAlpha()` 方法能识别以下保留 alpha 的表达式模式：

| 模式 | 示例 | 说明 |
|------|------|------|
| 直接返回输入 | `return input;` | 输入变量原样返回 |
| Swizzle 以 alpha 结尾 | `return input.rgba;` 或 `input.xxxa` | 最后分量为 `.a`（索引 3） |
| 复合构造器 | `half4(r, g, b, input.a)` | 最后一个参数保留 alpha |
| Splat 构造器 | 展开构造 | 最后一个分量保留 alpha |
| 类型转换 | `float4(half4_expr)` | float/half 之间的转换透传 |
| 三元表达式 | `cond ? exprA : exprB` | 两个分支都必须保留 alpha |

### 短路设计

- `visitExpression()` 返回 `false` 且不递归，因为 return 语句不会出现在表达式内部，这避免了不必要的深度遍历
- 一旦发现某个 return 语句不保留 alpha，立即终止遍历（`visitProgramElement` 返回 `true`）

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLProgramUsage.h` | 获取变量读写次数统计 |
| `SkSLProgramVisitor.h` | AST 访问者基类 |
| `SkSLSwizzle.h` | Swizzle 节点，检查分量重排 |
| `SkSLConstructorCompound.h` | 复合构造器（如 `half4(r, g, b, a)`） |
| `SkSLConstructorSplat.h` | Splat 构造器 |
| `SkSLConstructorCompoundCast.h` | 复合类型转换（如 `float4(half4_expr)`） |
| `SkSLTernaryExpression.h` | 三元表达式 |
| `SkSLReturnStatement.h` | return 语句 |
| `SkSLVariableReference.h` | 变量引用 |
| `SkSLFunctionDefinition.h` | 函数定义 |
| `SkSLFunctionDeclaration.h` | 函数声明（获取参数列表） |

## 设计模式与设计决策

1. **访问者模式（Visitor Pattern）**: 基于 `ProgramVisitor`，与 SkSL 分析框架一致
2. **模式匹配递归**: `returnsInputAlpha()` 通过递归模式匹配来处理嵌套的表达式结构（如三元表达式嵌套构造器）
3. **保守分析**: 无法匹配的表达式模式一律返回 `false`，确保分析结果的安全性
4. **写入检查前置**: 在开始遍历 return 语句之前，先检查输入变量是否被修改，这是一个重要的前提条件——如果输入变量被修改过，即使 return 语句引用了该变量，alpha 值也可能已经改变
5. **匿名命名空间**: 将 visitor 类隐藏在匿名命名空间中，体现良好的封装性

## 性能考量

- 分析仅遍历语句层级，`visitExpression()` 直接返回 `false`，避免深入表达式子树的递归
- 通过 `ProgramUsage` 的变量写入计数实现快速的前置条件检查，若输入变量被写入则立即终止
- 模式匹配按照常见模式的频率排列（先检查简单情况如直接返回输入、swizzle，再处理复杂情况如三元表达式）
- 整体复杂度为 O(n)，其中 n 为函数体中的语句数加上 return 表达式的节点数

## 相关文件

- `src/sksl/SkSLAnalysis.h` — `ReturnsInputAlpha` 函数声明
- `src/sksl/analysis/SkSLProgramUsage.h` — 变量使用统计
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/ir/SkSLSwizzle.h` — Swizzle 表达式定义
- `src/sksl/ir/SkSLReturnStatement.h` — return 语句节点
- `src/sksl/ir/SkSLConstructorCompound.h` — 复合构造器
- `src/sksl/ir/SkSLTernaryExpression.h` — 三元表达式
