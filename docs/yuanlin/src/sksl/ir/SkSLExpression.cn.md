# SkSL Expression (表达式基类)

> 源文件:
> - `src/sksl/ir/SkSLExpression.h`
> - `src/sksl/ir/SkSLExpression.cpp`

## 概述

`Expression` 是 SkSL 编译器中间表示（IR）中所有表达式的抽象基类。它定义了表达式节点的通用接口，包括类型查询、常量值获取、比较、克隆和描述等功能。所有具体的表达式类型（如 `Literal`、`BinaryExpression`、`FunctionCall` 等）都继承自该类。`Expression` 是 SkSL IR 中最核心的抽象之一，贯穿编译器的所有阶段。

## 架构位置

`Expression` 继承自 `IRNode`，位于 SkSL IR 层的核心位置。它与 `Statement` 和 `ProgramElement` 共同构成 IR 的三大基础节点类型。

```
IRNode (基类)
  |-- Expression (表达式 -- 本文件)
  |     |-- Literal
  |     |-- BinaryExpression
  |     |-- FunctionCall
  |     |-- ConstructorArray, ConstructorCompound, ...
  |     |-- VariableReference
  |     |-- Swizzle
  |     |-- IndexExpression
  |     |-- ...
  |-- Statement (语句)
  |-- ProgramElement (程序元素)
```

## 主要类与结构体

### `Expression`

抽象基类，继承自 `IRNode`。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fType` | `const Type*` | 表达式的类型（私有） |

**内嵌枚举：**

```cpp
enum class ComparisonResult {
    kUnknown = -1,  // 无法确定比较结果
    kNotEqual,      // 不相等
    kEqual          // 相等
};
```

### `ExpressionArray`

在 cpp 文件中还实现了 `ExpressionArray::clone()` 方法，用于克隆整个表达式数组。

## 公共 API 函数

### 类型与种类查询

- **`kind()`** -- 返回表达式的具体类型（`ExpressionKind` 枚举）。
- **`type()`** -- 返回表达式的 SkSL 类型引用。

### 字面量类型检查

- **`isIntLiteral()`** -- 检查是否为整数字面量（Kind 为 kLiteral 且类型为整数）。
- **`isFloatLiteral()`** -- 检查是否为浮点字面量。
- **`isBoolLiteral()`** -- 检查是否为布尔字面量。

### 构造器相关

- **`isAnyConstructor()`** -- 检查是否为任何类型的构造器表达式（从 `kConstructorArray` 到 `kConstructorStruct`）。通过范围检查实现，依赖于枚举值的连续性（有 `static_assert` 保证）。
- **`asAnyConstructor()` / `asAnyConstructor() const`** -- 将表达式转换为 `AnyConstructor` 引用。调用前需先确认 `isAnyConstructor()` 为真。

### 完整性检查

- **`isIncomplete(context)`** -- 检查表达式是否不完整。以下情况视为不完整：
  - `FunctionReference` -- 函数引用未被调用
  - `MethodReference` -- 方法引用未被调用
  - `TypeReference` -- 类型引用未被构造
  - `VariableReference` 且类型为 `SkCaps` -- 无效表达式

### 常量值操作

- **`compareConstant(other)`** -- 比较两个常量表达式是否相等。默认返回 `kUnknown`，子类可覆盖。
- **`supportsConstantValues()`** -- 返回此表达式类型是否支持 `getConstantValue` 查询。默认返回 `false`。
- **`getConstantValue(n)`** -- 获取表达式第 n 个槽位的编译时常量值。返回 `optional<double>`，非常量时返回 `nullopt`。

### 类型转换

- **`coercionCost(target)`** -- 计算将此表达式强制转换到目标类型的代价。

### 克隆与描述

- **`clone(pos)` (纯虚函数)** -- 在指定位置创建表达式的深拷贝。
- **`clone()`** -- 在原始位置创建表达式的深拷贝。
- **`description()` (final)** -- 返回表达式的文本描述，以最低优先级调用虚方法。
- **`description(parentPrecedence)` (纯虚函数)** -- 返回考虑父表达式优先级的文本描述，子类必须实现。

## 内部实现细节

### 不完整表达式检测

`isIncomplete()` 方法处理编译器前端常见的错误模式。例如，当用户写 `myFunc` 而不是 `myFunc()` 时，会生成一个 `FunctionReference` 节点，该方法检测到这种情况后报告错误 "expected '(' to begin function call"。

### ExpressionArray 克隆

`ExpressionArray::clone()` 实现了深度克隆：预分配精确大小的数组，逐个克隆非空表达式，空表达式保持为 `nullptr`。

### 常量值槽位模型

SkSL 使用"槽位"（slot）模型处理复合类型的常量值。例如 `vec4(1, vec2(2), 3)` 有 4 个槽位，值分别为 `(1, 2, 2, 3)`。`getConstantValue(n)` 允许按槽位索引获取值，`Type::slotCount()` 返回总槽位数。

### 优先级系统

`description()` 方法使用 `OperatorPrecedence` 枚举来决定是否需要在输出中添加括号。顶层调用使用 `kExpression`（最低优先级），子表达式的描述方法会根据父级优先级决定是否添加括号。

## 依赖关系

**内部依赖：**
- `SkSLIRNode` -- IR 节点基类
- `SkSLType` -- 类型系统（用于类型查询和强制转换代价计算）
- `SkSLPosition` -- 源码位置
- `SkSLContext` -- 编译器上下文
- `SkSLBuiltinTypes` -- 内建类型（用于 SkCaps 检查）
- `SkSLErrorReporter` -- 错误报告
- `SkSLOperator` -- 运算符优先级

**外部依赖：**
- `<memory>`, `<optional>`, `<string>`, `<cstdint>` -- 标准库

## 设计模式与设计决策

1. **抽象基类模式**：`Expression` 定义纯虚接口（`clone`、`description`），具体表达式类型必须实现这些方法，确保所有表达式都支持克隆和文本化。

2. **常量值的可选查询**：使用 `optional<double>` 作为 `getConstantValue` 的返回类型，优雅地处理了"不是常量"的情况。`supportsConstantValues()` 提供了快速的预判能力，避免对不支持常量值的表达式进行无意义的逐槽位查询。

3. **优先级感知的描述**：`description(OperatorPrecedence)` 模式允许正确生成带有括号的表达式文本，同时避免不必要的括号，使输出更可读。

4. **Kind 枚举分发**：通过 `kind()` 方法配合 `is<T>()` / `as<T>()` 模板（继承自 IRNode），实现类型安全的向下转换，替代了传统的 `dynamic_cast`。

5. **三态比较结果**：`ComparisonResult` 使用三态（Equal/NotEqual/Unknown），处理了编译时无法确定的比较情况。

## 性能考量

- **类型指针而非引用**：`fType` 存储为 `const Type*` 而非引用，减少了对象大小并允许运行时设置。
- **`isAnyConstructor()` 范围检查**：使用枚举值的连续性进行范围检查，只需两次比较即可判断，优于逐个枚举值的 switch-case。
- **`supportsConstantValues()` 早期退出**：允许在遍历大型表达式树时快速跳过不可能包含常量的节点，避免逐槽位调用 `getConstantValue`。
- **`ExpressionArray::clone()` 预分配**：使用 `reserve_exact` 精确预分配内存，避免动态增长。

## 相关文件

- `src/sksl/ir/SkSLIRNode.h` -- IRNode 基类
- `src/sksl/ir/SkSLType.h` -- 类型系统
- `src/sksl/ir/SkSLLiteral.h` -- 字面量表达式
- `src/sksl/ir/SkSLBinaryExpression.h` -- 二元表达式
- `src/sksl/ir/SkSLFunctionCall.h` -- 函数调用表达式
- `src/sksl/ir/SkSLConstructor.h` -- 构造器表达式基类
- `src/sksl/ir/SkSLVariableReference.h` -- 变量引用表达式
- `src/sksl/ir/SkSLStatement.h` -- 语句基类（IR 层同级）
- `src/sksl/SkSLOperator.h` -- 运算符和优先级定义
