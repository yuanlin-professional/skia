# SkSL PrefixExpression - 前缀一元表达式

> 源文件:
> - `src/sksl/ir/SkSLPrefixExpression.h`
> - `src/sksl/ir/SkSLPrefixExpression.cpp`

## 概述

`PrefixExpression` 表示 SkSL IR 中的前缀一元运算表达式,即运算符出现在操作数之前的表达式,如 `!flag`、`-value`、`++counter`、`~mask`。

该类在创建时执行类型检查,并包含丰富的编译期常量折叠和化简优化,包括取反消除、逻辑非反转、按位取反常量折叠以及比较运算符取反等。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── PrefixExpression  <-- 本文件
```

与 `PostfixExpression`(后缀一元)和 `BinaryExpression`(二元)共同构成运算符表达式体系。

## 主要类与结构体

### `PrefixExpression`

继承自 `Expression`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fOperator` | `Operator` | 运算符(+, -, ++, --, !, ~) |
| `fOperand` | `unique_ptr<Expression>` | 操作数 |

## 公共 API 函数

### `PrefixExpression::Convert`

```cpp
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           Operator op,
                                           std::unique_ptr<Expression> base);
```

完整类型检查的创建方法,按运算符验证:

| 运算符 | 要求 |
|--------|------|
| `+` / `-` | 操作数非数组,分量为数值类型 |
| `++` / `--` | 操作数非数组,分量为数值类型,且可赋值(更新为 ReadWrite) |
| `!` | 操作数为布尔类型 |
| `~` | 非严格 ES2 模式,操作数非数组,分量为整数类型 |

### `PrefixExpression::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        Operator op,
                                        std::unique_ptr<Expression> base);
```

带优化的工厂方法,不同运算符有不同处理:

| 运算符 | 行为 |
|--------|------|
| `+` | 空操作,直接返回操作数 |
| `-` | 调用 `negate_operand()` 进行取反优化 |
| `!` | 调用 `logical_not_operand()` 进行逻辑非优化 |
| `~` | 调用 `bitwise_not_operand()` 进行按位取反优化 |
| `++`/`--` | 不做优化,直接创建节点 |

## 内部实现细节

### 取反优化 (`simplify_negation`)

递归尝试简化取反操作:

1. **字面量/展开/复合构造器**: 对每个分量执行取反,`-vecN(literal, ...)` → `vecN(-literal, ...)`
2. **双重取反消除**: `-(-expression)` → `expression`
3. **数组取反**: `-array[N](literal, ...)` → `array[N](-literal, ...)`(仅限编译期常量)
4. **对角矩阵取反**: `-matrix(literal)` → `matrix(-literal)`(仅限编译期常量)

### 逻辑非优化 (`logical_not_operand`)

1. **布尔字面量反转**: `!true` → `false`
2. **双重逻辑非消除**: `!(!expression)` → `expression`
3. **比较运算符反转**: `!(a == b)` → `a != b`,`!(a < b)` → `a >= b` 等

### 按位取反优化 (`bitwise_not_operand`)

1. **常量折叠**: `~vecN(1, 2, ...)` → `vecN(~1, ~2, ...)`
2. **双重取反消除**: `~(~expression)` → `expression`

### 辅助函数 (`apply_to_elements`)

通用的逐元素常量运算函数:
- 提取表达式所有槽的常量值
- 对每个值应用函数(如 `negate_value` 或 `bitwise_not_value`)
- 检查结果是否在类型范围内
- 用 `ConstructorCompound::MakeFromConstants` 构造结果

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLExpression.h` | 基类 |
| `SkSLOperator.h` | 运算符类型 |
| `SkSLConstantFolder.h` | 常量变量值获取 |
| `SkSLAnalysis.h` | 赋值分析(++/--)、编译期常量检测 |
| `SkSLBinaryExpression.h` | 逻辑非优化中的比较运算符反转 |
| `SkSLConstructorArray.h` | 数组取反 |
| `SkSLConstructorCompound.h` | 复合类型常量构造 |
| `SkSLConstructorDiagonalMatrix.h` | 对角矩阵取反 |
| `SkSLLiteral.h` | 字面量创建 |
| `SkSLType.h` | 类型检查、值域检查 |
| `SkSLVariableReference.h` | 变量引用类型更新(++/--) |

## 设计模式与设计决策

1. **积极的编译期优化**: 每种运算符都有专门的优化路径,尽可能在编译期消除冗余运算
2. **递归优化**: `simplify_negation` 可以递归处理嵌套的构造器结构
3. **比较运算反转**: 逻辑非优化能够穿透到二元比较表达式,直接反转比较运算符
4. **正号消除**: 一元正号(`+`) 被视为空操作并立即消除
5. **值域安全**: 常量折叠时检查结果是否在类型范围内,越界时中止优化

## 性能考量

- 一元正号在 IR 构建时即被消除,不产生任何节点
- 取反和逻辑非的编译期折叠避免了运行时运算
- 双重取反/非消除减少了 IR 树的深度
- `apply_to_elements` 使用栈上的固定大小数组(16 元素),避免堆分配
- 按位取反中的字面量类型处理:当对字面量类型执行 `~` 时,先将其强制转换为实际类型(如 `$intLiteral` -> `int`),因为 `~123` 不再是字面量
- `negate_operands` 函数对整个表达式数组执行批量取反,用于数组和构造器的取反优化

### 比较运算符反转对照表

逻辑非优化中的比较运算符反转遵循数学对偶关系:

| 原运算符 | 反转后 |
|----------|--------|
| `==` | `!=` |
| `!=` | `==` |
| `<` | `>=` |
| `<=` | `>` |
| `>` | `<=` |
| `>=` | `<` |

## 相关文件

- `src/sksl/ir/SkSLPostfixExpression.h` -- 后缀一元表达式(i++, i--)
- `src/sksl/ir/SkSLBinaryExpression.h` -- 二元表达式
- `src/sksl/SkSLOperator.h` -- 运算符定义
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具
- `src/sksl/ir/SkSLConstructorCompound.h` -- 常量结果构造
