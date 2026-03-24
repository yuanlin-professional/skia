# SkSLIsDynamicallyUniformExpression — 动态一致性表达式分析

> 源文件：[`src/sksl/analysis/SkSLIsDynamicallyUniformExpression.cpp`](../../src/sksl/analysis/SkSLIsDynamicallyUniformExpression.cpp)

## 概述

SkSLIsDynamicallyUniformExpression.cpp 实现了对 SkSL 表达式的"动态一致性"（dynamically uniform）分析。一个表达式是动态一致的，当且仅当它在单次绘制调用（draw call）的所有着色器调用中具有相同的值。这意味着表达式只能由编译时常量、uniform 变量和纯函数（pure functions）组成。

该文件 86 行，包含一个分析访问者类和一个公共分析函数。

## 架构位置

```
SkSL 编译器
  └── 分析（Analysis）模块
        └── 表达式分析
              └── IsDynamicallyUniformExpression（本文件）
                    └── 判断表达式是否在 GPU 线程间一致
```

此分析在 SkSL 的优化和验证阶段使用，帮助编译器判断表达式是否适用于需要动态一致值的 GPU 操作。

## 主要类与结构体

### `IsDynamicallyUniformExpressionVisitor`（局部类）

```cpp
class IsDynamicallyUniformExpressionVisitor : public ProgramVisitor {
public:
    bool visitExpression(const Expression& expr) override;
    bool fIsDynamicallyUniform = true;
};
```

- 初始假设表达式是动态一致的
- 遇到不满足条件的节点时将 `fIsDynamicallyUniform` 设为 `false`

## 公共 API 函数

```cpp
bool Analysis::IsDynamicallyUniformExpression(const Expression& expr);
```
- 判断给定表达式是否是动态一致的
- 返回 `true` 表示表达式在所有着色器调用中具有相同值

## 内部实现细节

### 表达式分类

访问者将表达式按三类处理：

**可能动态一致的（需递归检查子表达式）**：
- 二元运算（`kBinary`）
- 各种构造函数（Array, Compound, DiagonalMatrix, MatrixResize, ScalarCast, Splat, Struct）
- 字段访问（`kFieldAccess`）
- 索引访问（`kIndex`）
- 前缀/后缀运算（`kPrefix` / `kPostfix`）
- Swizzle 操作
- 三元运算（`kTernary`）

**终端：动态一致的**：
- 字面量（`kLiteral`）— 编译时常量，直接返回 false（无需继续递归）
- `const` 修饰的变量引用 — 常量
- `uniform` 修饰的变量引用 — 在 draw call 内一致

**终端：不是动态一致的**：
- 非 const、非 uniform 的变量引用（如 varying 变量）
- 非 pure 的函数调用
- 其他所有表达式类型

### 变量引用检查

```cpp
case Expression::Kind::kVariableReference: {
    const Variable* var = expr.as<VariableReference>().variable();
    if (var && (var->modifierFlags().isConst() || var->modifierFlags().isUniform())) {
        break;  // 继续递归检查（虽然对变量来说这是终端）
    }
    fIsDynamicallyUniform = false;
    return true;  // 停止遍历
}
```

只有 `const` 和 `uniform` 变量是动态一致的。`varying`、`in`、`out` 等存储类型的变量在不同着色器调用间可能有不同值。

### 函数调用检查

```cpp
case Expression::Kind::kFunctionCall: {
    const FunctionDeclaration& decl = expr.as<FunctionCall>().function();
    if (decl.modifierFlags().isPure()) {
        break;  // pure 函数的返回值取决于输入，继续检查参数
    }
    fIsDynamicallyUniform = false;
    return true;
}
```

`pure` 函数的返回值完全由其参数决定（无副作用、无全局状态访问）。如果参数都是动态一致的，则 pure 函数的返回值也是动态一致的。非 pure 函数可能访问 varying 数据或有副作用。

### 字面量的特殊处理

```cpp
case Expression::Kind::kLiteral:
    return false;
```

字面量直接返回 `false`（不终止遍历的 false，表示"没有发现问题，但也不需要递归"）。由于字面量没有子表达式，这等同于确认它是动态一致的。

## 依赖关系

- `include/core/SkTypes.h` — 基础类型
- `src/sksl/SkSLAnalysis.h` — 分析函数声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/ir/SkSLExpression.h` — 表达式基类
- `src/sksl/ir/SkSLFunctionCall.h` — 函数调用表达式
- `src/sksl/ir/SkSLFunctionDeclaration.h` — 函数声明（检查 pure 修饰符）
- `src/sksl/ir/SkSLModifierFlags.h` — 修饰符标志（const, uniform, pure）
- `src/sksl/ir/SkSLVariable.h` — 变量类型
- `src/sksl/ir/SkSLVariableReference.h` — 变量引用表达式

## 设计模式与设计决策

- **访问者模式**：使用 `ProgramVisitor` 递归遍历表达式树。
- **白名单策略**：明确列出所有可能动态一致的表达式类型，未列出的默认为不一致。这是一种保守的安全策略。
- **早期终止**：一旦发现不一致的节点，设置标志并返回 `true`（终止遍历）。
- **GPU 语义**：分析基于 GPU 编程中"动态一致性"的精确定义，即值在同一 draw call 的所有调用中相同。

## 性能考量

1. **早期终止**：发现不一致表达式后立即停止遍历。
2. **O(N) 时间复杂度**：最坏情况下遍历整个表达式树，N 为表达式节点数。
3. **编译期分析**：在着色器编译阶段执行，不影响运行时性能。

## 相关文件

- `src/sksl/SkSLAnalysis.h` — 分析函数声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/ir/SkSLModifierFlags.h` — 修饰符标志定义
- `src/sksl/ir/SkSLFunctionDeclaration.h` — 函数声明（pure 修饰符检查）
