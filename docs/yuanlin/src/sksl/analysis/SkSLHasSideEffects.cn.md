# SkSL HasSideEffects 分析

> 源文件: `src/sksl/analysis/SkSLHasSideEffects.cpp`

## 概述

`SkSLHasSideEffects.cpp` 实现了 SkSL（Skia Shading Language）编译器中的副作用检测分析功能。该模块提供了 `Analysis::HasSideEffects` 函数，用于判断一个给定的 SkSL 表达式是否具有副作用（side effects）。副作用指的是表达式在求值过程中除了返回值之外，还会修改程序状态的行为，例如赋值操作、自增/自减操作以及调用非纯函数等。

此分析在编译器优化阶段（如死代码消除、常量折叠）中至关重要，因为只有不含副作用的表达式才能被安全地移除或重排。

## 架构位置

该文件位于 SkSL 编译器的分析（analysis）子系统中：

```
Skia
└── src/sksl/
    ├── SkSLAnalysis.h          // 分析接口声明
    ├── analysis/
    │   ├── SkSLHasSideEffects.cpp   // 本文件：副作用检测
    │   ├── SkSLProgramVisitor.h     // 访问者基类
    │   └── ...                      // 其他分析 pass
    └── ir/                          // SkSL 中间表示节点
```

`HasSideEffects` 是 `SkSL::Analysis` 命名空间中众多静态分析函数之一，服务于编译器的语义分析和优化流程。

## 主要类与结构体

### `HasSideEffectsVisitor`（局部类）

- **继承关系**: 继承自 `ProgramVisitor`
- **作用域**: 定义在 `HasSideEffects` 函数体内部，作为局部类使用
- **职责**: 递归遍历表达式树，检测是否存在具有副作用的节点
- **核心方法**: `visitExpression(const Expression& expr)` — 重写基类的虚函数，对不同类型的表达式节点进行副作用判定

## 公共 API 函数

### `bool Analysis::HasSideEffects(const Expression& expr)`

- **功能**: 判断给定表达式是否包含副作用
- **参数**: `expr` — 待分析的 SkSL 表达式节点（`const` 引用）
- **返回值**: `true` 表示存在副作用，`false` 表示表达式是纯计算
- **检测的副作用类型**:
  1. **非纯函数调用** (`kFunctionCall`): 调用未标记为 `pure` 的函数
  2. **前缀自增/自减** (`kPrefix`): `++x` 或 `--x`
  3. **赋值操作** (`kBinary`): 包括 `=`、`+=`、`-=` 等所有赋值运算符
  4. **后缀表达式** (`kPostfix`): `x++` 或 `x--`（后缀表达式一律视为有副作用）

## 内部实现细节

实现采用了**访问者模式**（Visitor Pattern），通过 `ProgramVisitor` 基类提供的递归遍历机制来检查表达式树中的每个节点：

1. **入口**: 创建 `HasSideEffectsVisitor` 实例并调用 `visitExpression`
2. **递归**: 对当前节点进行 `switch` 匹配，若匹配到有副作用的模式则立即返回 `true`
3. **回退**: 若当前节点无副作用，则调用 `INHERITED::visitExpression(expr)` 递归检查子表达式
4. **短路求值**: 一旦发现副作用即返回 `true`，不再继续遍历

关键设计点：后缀表达式（`kPostfix`）直接返回 `true`，无需进一步判断运算符类型，因为 SkSL 中所有后缀表达式（`x++` 和 `x--`）都具有副作用。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkTypes.h` | Skia 基础类型定义 |
| `SkSLAnalysis.h` | 分析函数接口声明 |
| `SkSLOperator.h` | 运算符类型定义与查询 |
| `SkSLProgramVisitor.h` | 访问者基类 |
| `SkSLBinaryExpression.h` | 二元表达式 IR 节点 |
| `SkSLExpression.h` | 表达式基类 |
| `SkSLFunctionCall.h` | 函数调用 IR 节点 |
| `SkSLFunctionDeclaration.h` | 函数声明（用于检查 `pure` 修饰符） |
| `SkSLIRNode.h` | IR 节点基类 |
| `SkSLModifierFlags.h` | 修饰符标志（如 `isPure()`） |
| `SkSLPrefixExpression.h` | 前缀表达式 IR 节点 |

## 设计模式与设计决策

1. **访问者模式（Visitor Pattern）**: 继承 `ProgramVisitor` 遍历 AST，与 SkSL 分析子系统的整体设计保持一致
2. **局部类**: 将 `HasSideEffectsVisitor` 定义在函数内部，限制其可见性，体现了封装原则
3. **纯函数标记**: 依赖 SkSL 函数声明上的 `pure` 修饰符来判断函数调用是否有副作用，这是一种声明式的副作用管理策略
4. **保守策略**: 对于后缀表达式采取保守判定（一律有副作用），确保分析结果的正确性（宁可误报也不遗漏）

## 性能考量

- 该分析为**单次遍历**，时间复杂度为 O(n)，其中 n 为表达式树的节点数
- 采用**短路返回**策略，在发现第一个副作用节点时立即终止遍历
- 无额外内存分配，访问者对象在栈上创建
- 作为编译期分析，不影响运行时着色器执行性能

## 相关文件

- `src/sksl/SkSLAnalysis.h` — `HasSideEffects` 的函数声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类定义
- `src/sksl/ir/SkSLExpression.h` — 表达式节点基类
- `src/sksl/ir/SkSLBinaryExpression.h` — 二元表达式定义
- `src/sksl/ir/SkSLPrefixExpression.h` — 前缀表达式定义
- `src/sksl/ir/SkSLFunctionCall.h` — 函数调用节点定义
- `src/sksl/analysis/SkSLIsSameExpressionTree.cpp` — 另一个表达式分析 pass
