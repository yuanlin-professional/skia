# SkSL BinaryExpression - 二元表达式

> 源文件:
> - `src/sksl/ir/SkSLBinaryExpression.h`
> - `src/sksl/ir/SkSLBinaryExpression.cpp`

## 概述

`BinaryExpression` 表示 SkSL IR 中的二元运算操作,包括算术运算(`+`, `-`, `*`, `/`)、比较运算(`==`, `!=`, `<`, `>`)、逻辑运算(`&&`, `||`)、赋值运算(`=`, `+=`, `-=`)等。它是 SkSL 表达式系统中最通用的运算节点之一。

该类在创建时进行类型检查、类型强制转换、赋值合法性验证以及常量折叠优化。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── BinaryExpression  <-- 本文件
```

`BinaryExpression` 直接继承自 `Expression`,与 `PrefixExpression`(前缀一元)和 `PostfixExpression`(后缀一元)一起构成 SkSL 的运算符表达式体系。

## 主要类与结构体

### `BinaryExpression`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fLeft` | `unique_ptr<Expression>` | 左操作数 |
| `fOperator` | `Operator` | 运算符 |
| `fRight` | `unique_ptr<Expression>` | 右操作数 |

## 公共 API 函数

### `BinaryExpression::Convert`

```cpp
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           std::unique_ptr<Expression> left,
                                           Operator op,
                                           std::unique_ptr<Expression> right);
```

完整的类型检查和二元表达式创建:

1. **整数字面量类型推导**: 整数字面量的类型由另一侧操作数决定
2. **赋值验证**: 赋值操作更新左操作数的变量引用类型(Write/ReadWrite)
3. **类型确定**: 通过 `op.determineBinaryType()` 确定左右操作数和结果的类型
4. **不透明类型保护**: 禁止对不透明类型和原子类型赋值
5. **ES2 合规检查**: 在严格 ES2 模式下检查运算符合法性
6. **数组限制**: ES2 模式和逗号运算符禁止操作数组类型
7. **类型强制转换**: 将左右操作数强制转换为确定的类型

### `BinaryExpression::Make` (两个重载)

```cpp
// 自动确定结果类型
static std::unique_ptr<Expression> Make(const Context& context, Position pos,
                                        std::unique_ptr<Expression> left, Operator op,
                                        std::unique_ptr<Expression> right);

// 指定结果类型
static std::unique_ptr<Expression> Make(const Context& context, Position pos,
                                        std::unique_ptr<Expression> left, Operator op,
                                        std::unique_ptr<Expression> right,
                                        const Type* resultType);
```

带指定结果类型的版本执行:
1. ES2 合规性断言
2. 赋值合法性断言
3. 值域检查(对简单赋值检测越界字面量)
4. **常量折叠**: 调用 `ConstantFolder::Simplify()` 尝试编译期化简

### `isAssignmentIntoVariable`

```cpp
VariableReference* isAssignmentIntoVariable();
```

如果表达式是对变量的赋值(如 `a = 1` 或 `a += sin(b)`),返回被赋值的 `VariableReference`。用于优化和分析。

## 内部实现细节

### `CheckRef` (私有静态方法)

验证赋值操作的左操作数是否已正确标记为 Write 或 ReadWrite 引用。支持嵌套检查:
- **FieldAccess**: 递归检查基表达式
- **IndexExpression**: 递归检查基表达式
- **Swizzle**: 递归检查基表达式
- **TernaryExpression**: 两个分支都必须通过检查
- **VariableReference**: 直接检查 `refKind`

### 描述生成

```cpp
std::string description(OperatorPrecedence parentPrecedence) const override;
```

根据父级优先级决定是否添加括号,递归生成表达式文本。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLExpression.h` | 基类 |
| `SkSLOperator.h` | 运算符类型和优先级 |
| `SkSLConstantFolder.h` | 常量折叠优化 |
| `SkSLAnalysis.h` | 赋值分析、变量引用更新 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLType.h` | 类型系统 |
| `SkSLVariableReference.h` | 变量引用(赋值检测) |
| `SkSLFieldAccess.h` | 字段访问(CheckRef) |
| `SkSLIndexExpression.h` | 索引表达式(CheckRef) |
| `SkSLSwizzle.h` | 混洗(CheckRef) |
| `SkSLTernaryExpression.h` | 三元表达式(CheckRef) |

## 设计模式与设计决策

1. **Convert/Make 分层**: `Convert()` 处理类型推导和验证,`Make()` 假定类型已知并执行优化
2. **常量折叠集成**: `Make()` 方法中自动调用 `ConstantFolder::Simplify()`,在 IR 构建阶段就进行化简
3. **赋值安全检查**: 在构造时即验证左操作数的引用类型,通过断言确保一致性
4. **优先级感知描述**: `description()` 方法接受父级优先级参数,智能添加括号
5. **整数字面量类型推导**: 当一侧是整数字面量时,其类型由另一侧决定(如 `myUint + 1` 中 `1` 的类型为 uint)

## 性能考量

- 常量折叠在构建 IR 时即执行,避免了冗余的常量运算节点
- `isAssignmentIntoVariable()` 通过 `Analysis::IsAssignable` 实现,仅在需要时调用
- `CheckRef` 的递归深度取决于表达式嵌套深度,通常较浅
- `Convert()` 中的类型确定通过 `Operator::determineBinaryType()` 一次性完成,避免多次类型计算
- 类型强制转换仅在类型不匹配时执行,大多数情况下直接返回原表达式

### 整数字面量的类型推导细节

`Convert()` 中对整数字面量的处理值得特别关注:

```cpp
const Type* rawLeftType = (left->isIntLiteral() && right->type().isInteger())
        ? &right->type()
        : &left->type();
```

当一侧是整数字面量(`$intLiteral`)而另一侧是具体整数类型时,字面量的类型由另一侧决定。这使得 `myUint + 1` 中的 `1` 被视为 `uint` 类型,避免了不必要的类型转换。

### 赋值运算的特殊处理

对于赋值运算(如 `=`, `+=`, `-=`):
1. 左操作数的变量引用类型被更新为 `kWrite`(简单赋值)或 `kReadWrite`(复合赋值)
2. 不允许对不透明类型赋值(如 sampler2D)
3. 不允许对原子类型赋值
4. 简单赋值(`=`)会触发右操作数的越界字面量检查

## 相关文件

- `src/sksl/ir/SkSLPrefixExpression.h` -- 前缀一元表达式
- `src/sksl/ir/SkSLPostfixExpression.h` -- 后缀一元表达式
- `src/sksl/ir/SkSLTernaryExpression.h` -- 三元表达式
- `src/sksl/SkSLOperator.h` -- 运算符类型定义和优先级
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠引擎
- `src/sksl/SkSLAnalysis.h` -- 表达式分析工具
