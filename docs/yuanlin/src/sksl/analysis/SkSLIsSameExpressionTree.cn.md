# SkSL IsSameExpressionTree 分析

> 源文件: `src/sksl/analysis/SkSLIsSameExpressionTree.cpp`

## 概述

`SkSLIsSameExpressionTree.cpp` 实现了 SkSL 编译器中的表达式树等价性判断功能。该模块提供的 `Analysis::IsSameExpressionTree` 函数用于比较两个 SkSL 表达式是否在结构和语义上等价。

该分析的主要用途是编译器优化：当能确认两个表达式产生相同结果时，编译器可以进行公共子表达式消除（CSE）等优化。值得注意的是，该实现并非全面覆盖所有表达式类型——它专注于处理常见的表达式模式，对于无法识别的表达式类型保守地返回 `false`。

## 架构位置

```
Skia
└── src/sksl/
    ├── SkSLAnalysis.h                       // 分析接口声明
    ├── analysis/
    │   ├── SkSLIsSameExpressionTree.cpp     // 本文件
    │   ├── SkSLHasSideEffects.cpp           // 关联：副作用检测
    │   └── ...
    └── ir/                                  // 表达式节点类型
```

该分析服务于 SkSL 编译器的优化阶段，与 `HasSideEffects` 等分析互相配合，共同为优化 pass 提供决策依据。

## 主要类与结构体

本文件没有定义任何类或结构体。功能通过一个递归函数实现。

## 公共 API 函数

### `bool Analysis::IsSameExpressionTree(const Expression& left, const Expression& right)`

- **功能**: 判断两个表达式树是否结构等价
- **参数**:
  - `left`: 第一个表达式
  - `right`: 第二个表达式
- **返回值**: `true` 表示两个表达式语义等价；`false` 表示不等价或无法确认
- **特性**: 纯函数，不修改任何状态

### 支持的表达式类型

| 表达式类型 | 比较方式 |
|-----------|---------|
| `kLiteral` | 比较字面量值 |
| 各种构造器（9 种） | 递归比较所有参数 |
| `kFieldAccess` | 比较字段索引 + 递归比较基础表达式 |
| `kIndex` | 递归比较索引表达式和基础表达式 |
| `kPrefix` | 比较运算符 + 递归比较操作数 |
| `kSwizzle` | 比较分量列表 + 递归比较基础表达式 |
| `kVariableReference` | 比较是否引用同一个变量（指针比较） |

### 不支持的表达式类型

以下类型在 `default` 分支中返回 `false`：
- `BinaryExpression`（如 `x + y`）
- `FunctionCall`（如 `foo(x)`）
- `TernaryExpression`（如 `c ? a : b`）
- `PostfixExpression`（如 `x++`）

## 内部实现细节

### 比较算法

1. **快速拒绝**: 首先检查两个表达式的 `kind()` 是否相同以及类型是否匹配，不同则直接返回 `false`
2. **分派比较**: 根据表达式类型进行 switch 分派，针对每种类型执行特定的比较逻辑
3. **递归下降**: 对于复合表达式（如构造器、字段访问），递归比较子表达式

### 构造器比较

构造器的比较逻辑统一处理了 9 种不同的构造器类型：
- `ConstructorArray` / `ConstructorArrayCast`
- `ConstructorCompound` / `ConstructorCompoundCast`
- `ConstructorDiagonalMatrix` / `ConstructorMatrixResize`
- `ConstructorScalarCast` / `ConstructorStruct` / `ConstructorSplat`

通过 `asAnyConstructor()` 和 `argumentSpan()` 获取统一的参数视图，逐一递归比较。

### 变量引用比较

变量引用通过比较 `Variable*` 指针来判断是否引用同一个变量。这是正确的，因为在 SkSL 的 IR 中，每个变量声明对应唯一的 `Variable` 对象。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLAnalysis.h` | 函数声明 |
| `SkSLOperator.h` | 运算符类型比较 |
| `SkSLConstructor.h` | `AnyConstructor` 基类 |
| `SkSLExpression.h` | 表达式基类 |
| `SkSLFieldAccess.h` | 字段访问节点 |
| `SkSLIndexExpression.h` | 索引表达式节点 |
| `SkSLLiteral.h` | 字面量节点 |
| `SkSLPrefixExpression.h` | 前缀表达式节点 |
| `SkSLSwizzle.h` | Swizzle 节点 |
| `SkSLType.h` | 类型信息（用于类型匹配检查） |
| `SkSLVariableReference.h` | 变量引用节点 |

## 设计模式与设计决策

1. **递归下降比较**: 没有使用访问者模式，而是采用简单的递归 switch 结构，因为比较逻辑需要同时访问两个表达式树
2. **保守策略**: 对未处理的表达式类型返回 `false`，确保不会错误地将不同表达式判定为相同
3. **实用主义**: 注释明确说明这不是穷尽性比较，仅覆盖常见的优化场景——例如不处理 `BinaryExpression`，这意味着 `x[y+1] == x[y+1]` 不会被检测到
4. **快速前置检查**: 先比较 `kind()` 和 `type()`，可以快速排除大部分不匹配的情况
5. **指针相等性**: 变量引用通过指针比较，这依赖于 SkSL IR 中变量的唯一性保证

## 性能考量

- 时间复杂度为 O(n)，其中 n 为较小表达式树的节点数
- 快速拒绝检查（kind 和 type）能在常数时间内排除大部分不匹配的情况
- 构造器参数数量通常很少（1-4 个），递归深度有限
- 无额外内存分配，所有比较在栈上完成
- 短路求值：任何子表达式不匹配立即返回 `false`

## 相关文件

- `src/sksl/SkSLAnalysis.h` — 函数声明
- `src/sksl/analysis/SkSLHasSideEffects.cpp` — 配合使用的副作用检测
- `src/sksl/ir/SkSLExpression.h` — 表达式基类
- `src/sksl/ir/SkSLConstructor.h` — 构造器基类
- `src/sksl/ir/SkSLLiteral.h` — 字面量定义
- `src/sksl/ir/SkSLSwizzle.h` — Swizzle 表达式
- `src/sksl/ir/SkSLVariableReference.h` — 变量引用
