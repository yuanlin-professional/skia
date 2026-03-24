# SkSL PostfixExpression（后缀表达式）

> 源文件：[src/sksl/ir/SkSLPostfixExpression.h](../../../src/sksl/ir/SkSLPostfixExpression.h)、[src/sksl/ir/SkSLPostfixExpression.cpp](../../../src/sksl/ir/SkSLPostfixExpression.cpp)

## 概述

`PostfixExpression` 是 SkSL 中间表示（IR）中的后缀一元表达式节点，表示后缀递增（`i++`）和后缀递减（`i--`）运算。该类在构造时验证操作数必须是数值类型且可赋值，并将操作数的变量引用标记为读写（`kReadWrite`），因为后缀运算既读取又修改变量的值。

## 架构位置

`PostfixExpression` 位于 SkSL IR 的表达式节点层：

```
SkSL 源代码: i++
       |
       v
  Parser -> PostfixExpression::Convert()（类型检查和可赋值性检查）
       |
       v
  PostfixExpression（IR 节点）
       |
       v
  Inliner（克隆）/ CodeGen（代码生成）
```

## 主要类与结构体

### `class PostfixExpression`

继承自 `Expression`，final 类：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fOperand` | `std::unique_ptr<Expression>` | 操作数表达式 |
| `fOperator` | `Operator` | 运算符（`++` 或 `--`） |

静态常量：
| 常量 | 值 | 说明 |
|------|----|------|
| `kIRNodeKind` | `Kind::kPostfix` | IR 节点类型标识 |

## 公共 API 函数

### 工厂方法

- **`static Convert(context, pos, base, op)`** —— 创建后缀表达式，执行完整的类型检查：
  - 验证操作数不是数组类型
  - 验证操作数的组件类型是数值类型
  - 验证操作数可赋值（通过 `UpdateVariableRefKind` 标记为 `kReadWrite`）
  - 错误通过 `ErrorReporter` 报告

- **`static Make(context, pos, base, op)`** —— 创建后缀表达式，仅通过断言验证（用于已知安全的构造）

### 访问器

- **`getOperator()`** —— 获取运算符
- **`operand()` / `operand() const`** —— 获取操作数（可变/不可变引用）
- **`clone(pos)`** —— 克隆表达式
- **`description(parentPrecedence)`** —— 生成带优先级感知的文本描述

## 内部实现细节

### Convert 的验证逻辑

```cpp
if (base->type().isArray() || !base->type().componentType().isNumber()) {
    // 错误：后缀运算符不能应用于此类型
}
if (!Analysis::UpdateVariableRefKind(base.get(), VariableRefKind::kReadWrite, ...)) {
    // 错误：操作数不可赋值
}
```

`UpdateVariableRefKind` 将操作数的变量引用类型从默认的 `kRead` 更新为 `kReadWrite`，这对于 `ProgramUsage` 的正确统计至关重要。

### description 的优先级处理

后缀运算符的优先级是 `kPostfix`（第 2 级，非常高）。当父表达式的优先级更高时，需要添加括号：

```cpp
bool needsParens = (OperatorPrecedence::kPostfix >= parentPrecedence);
```

### 类型推导

后缀表达式的类型与操作数相同（构造函数中通过 `&operand->type()` 直接获取）。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLExpression.h` | 表达式基类 |
| `SkSLOperator.h` | 运算符定义 |
| `SkSLAnalysis.h` | `IsAssignable`、`UpdateVariableRefKind` |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLType.h` | 类型检查 |
| `SkSLVariableReference.h` | 变量引用类型 |

## 设计模式与设计决策

1. **Convert/Make 双入口**：`Convert` 用于用户代码（完整错误检查），`Make` 用于编译器内部（断言检查），遵循 SkSL IR 的标准模式。
2. **变量引用类型更新**：后缀表达式在创建时立即将操作数标记为读写，确保使用量统计的正确性。
3. **不可变运算符**：`Operator` 按值存储（仅 1 字节），轻量且高效。
4. **内联克隆**：`clone` 在头文件中内联实现，因为逻辑简单。

## 性能考量

- `PostfixExpression` 节点非常轻量（一个指针 + 一个字节的运算符）
- `Convert` 的类型检查为 O(1) 操作
- `clone` 递归克隆操作数但不涉及深度复制（只有智能指针）
- `description` 的字符串拼接在调试/错误报告时才调用

## 相关文件

- `src/sksl/ir/SkSLPrefixExpression.h` / `.cpp` —— 前缀一元表达式（`++i`、`--i`、`!`、`~` 等）
- `src/sksl/ir/SkSLBinaryExpression.h` —— 二元表达式
- `src/sksl/ir/SkSLExpression.h` —— 表达式基类
- `src/sksl/SkSLOperator.h` —— 运算符定义
- `src/sksl/SkSLAnalysis.h` —— 可赋值性分析
