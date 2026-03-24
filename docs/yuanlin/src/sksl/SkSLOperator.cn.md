# SkSL Operator（运算符系统）

> 源文件：[src/sksl/SkSLOperator.h](../../src/sksl/SkSLOperator.h)、[src/sksl/SkSLOperator.cpp](../../src/sksl/SkSLOperator.cpp)

## 概述

`SkSLOperator` 模块定义了 SkSL 着色语言中所有运算符的表示、分类和类型推导逻辑。它包含运算符种类枚举（`OperatorKind`）、优先级枚举（`OperatorPrecedence`）以及核心的 `Operator` 类。`Operator` 类封装了运算符的各种属性查询（如是否为赋值运算符、是否适用于整型等），并实现了二元表达式的类型推导规则，这是 SkSL 类型系统中最复杂的部分之一。

## 架构位置

`Operator` 位于 SkSL 编译器的 IR 层和类型系统之间：

```
解析器（创建带 Operator 的 BinaryExpression）
    |
    v
Operator::determineBinaryType()（类型推导）
    |
    v
IR 树（BinaryExpression、PrefixExpression、PostfixExpression 持有 Operator）
    |
    v
代码生成器（通过 operatorName() 输出运算符文本）
```

## 主要类与结构体

### `enum class OperatorKind : uint8_t`

所有运算符种类（33 种），包括：

| 类别 | 运算符 |
|------|--------|
| 算术 | `PLUS`, `MINUS`, `STAR`, `SLASH`, `PERCENT` |
| 移位 | `SHL`, `SHR` |
| 逻辑 | `LOGICALNOT`, `LOGICALAND`, `LOGICALOR`, `LOGICALXOR` |
| 位运算 | `BITWISENOT`, `BITWISEAND`, `BITWISEOR`, `BITWISEXOR` |
| 比较 | `EQEQ`, `NEQ`, `LT`, `GT`, `LTEQ`, `GTEQ` |
| 赋值 | `EQ`, `PLUSEQ`, `MINUSEQ`, `STAREQ`, `SLASHEQ`, `PERCENTEQ`, `SHLEQ`, `SHREQ`, `BITWISEANDEQ`, `BITWISEOREQ`, `BITWISEXOREQ` |
| 自增减 | `PLUSPLUS`, `MINUSMINUS` |
| 逗号 | `COMMA` |

### `enum class OperatorPrecedence : uint8_t`

运算符优先级，从高到低：

| 值 | 级别 | 说明 |
|----|------|------|
| 1 | `kParentheses` | 括号 |
| 2 | `kPostfix` | 后缀（`++`、`--`） |
| 3 | `kPrefix` | 前缀（`!`、`~`、`-`） |
| 4 | `kMultiplicative` | 乘法类（`*`、`/`、`%`） |
| 5-6 | `kAdditive`, `kShift` | 加法、移位 |
| 7-8 | `kRelational`, `kEquality` | 关系、等价比较 |
| 9-11 | `kBitwiseAnd/Xor/Or` | 位运算 |
| 12-14 | `kLogicalAnd/Xor/Or` | 逻辑运算 |
| 15-16 | `kTernary`, `kAssignment` | 三元、赋值 |
| 17-18 | `kSequence`, `kStatement` | 逗号序列、语句 |

### `class Operator`

运算符类，包装单个 `OperatorKind` 值：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fKind` | `Kind` | 运算符种类 |

## 公共 API 函数

### 属性查询

- **`kind()`** —— 返回运算符种类
- **`isEquality()`** —— 是否为等价比较（`==` 或 `!=`）
- **`isAssignment()`** —— 是否为赋值运算符（包括 `=` 和复合赋值）
- **`isCompoundAssignment()`** —— 是否为复合赋值（不含 `=`）
- **`isRelational()`** —— 是否为关系比较（`<`、`<=`、`>`、`>=`）
- **`isOnlyValidForIntegralTypes()`** —— 是否仅对整型有效（移位、位运算、取模）
- **`isValidForMatrixOrVector()`** —— 是否适用于矩阵或向量运算
- **`isAllowedInStrictES2Mode()`** —— 是否在严格 ES2 模式下允许

### 转换

- **`removeAssignment()`** —— 将复合赋值运算符转换为其基础运算符（如 `+=` -> `+`）
- **`getBinaryPrecedence()`** —— 获取二元运算符的优先级

### 文本表示

- **`operatorName()`** —— 返回带空格的运算符名称（如 `" + "`），用于代码生成
- **`tightOperatorName()`** —— 返回不带空格的运算符名称（如 `"+"`）

### 类型推导

- **`determineBinaryType(context, left, right, outLeftType, outRightType, outResultType)`** —— 确定二元表达式中操作数和结果的类型。返回 `true` 表示表达式合法，`false` 表示非法。

## 内部实现细节

### determineBinaryType 的复杂类型推导

这是运算符系统中最复杂的函数，处理多种情况：

1. **赋值（`=`）**：结果类型为左侧类型，右侧必须能强制转换为左侧类型
2. **等价比较（`==`、`!=`）**：寻找最低成本的双向强制转换，结果为 `bool`
3. **逻辑运算**：两侧都强制为 `bool`
4. **矩阵乘法**：特殊处理，考虑矩阵维度兼容性（左侧列数 = 右侧行数）
5. **标量-向量/矩阵运算**：标量提升为与另一侧匹配的复合类型
6. **同类型运算**：选择成本最低的强制转换方向

### 矩阵乘法的特殊处理

`isMatrixMultiply` 检查是否为矩阵与矩阵/向量的乘法运算。矩阵乘法结果的维度计算遵循标准线性代数规则：

```
matrix(M x K) * matrix(K x N) -> matrix(M x N)
matrix(M x K) * vector(K)     -> vector(M)
vector(K) * matrix(K x N)     -> vector(N)
```

### 强制转换成本

类型推导使用 `CoercionCost` 比较不同转换方向的成本，选择成本更低的方向。赋值运算符只允许右到左的转换（`leftToRightCost` 设为不可能）。

### ES2 兼容性

在严格 ES2 模式下，整型运算符被禁止。这是因为 ES2 不要求 `int` 有独立的硬件支持，它实际上是浮点运算加截断的语法糖。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLBuiltinTypes.h` | 内置类型（`bool`、`float` 等） |
| `SkSLContext.h` | 编译上下文和程序设置 |
| `SkSLType.h` | 类型系统（强制转换成本、组件类型等） |
| `SkSLProgramSettings.h` | 窄化转换设置 |

## 设计模式与设计决策

1. **值类型设计**：`Operator` 仅包含一个 `uint8_t` 枚举值，可以高效地按值传递和存储。
2. **枚举分离**：`OperatorKind` 和 `OperatorPrecedence` 是独立枚举，避免在优先级不相关的上下文中暴露优先级信息。
3. **完备的 switch-case**：所有方法都使用完整的 switch-case 覆盖所有运算符种类，确保新增运算符时编译器会发出警告。
4. **集中式类型推导**：所有二元表达式的类型规则集中在 `determineBinaryType` 中，避免逻辑分散。
5. **窄化转换控制**：通过 `fAllowNarrowingConversions` 设置控制是否允许窄化转换，Runtime Effect 默认允许。

## 性能考量

- `Operator` 仅占用 1 字节内存（`uint8_t` 底层类型）
- 所有属性查询都是简单的 switch-case，编译器可优化为跳转表
- `operatorName` 返回静态字符串指针，无内存分配
- `determineBinaryType` 使用早期返回避免不必要的类型检查

## 相关文件

- `src/sksl/ir/SkSLBinaryExpression.h` —— 二元表达式，持有 `Operator`
- `src/sksl/ir/SkSLPrefixExpression.h` —— 前缀表达式
- `src/sksl/ir/SkSLPostfixExpression.h` —— 后缀表达式
- `src/sksl/ir/SkSLType.h` —— 类型系统，`coercionCost` 等
- `src/sksl/SkSLConstantFolder.h` —— 常量折叠，使用运算符执行编译时运算
