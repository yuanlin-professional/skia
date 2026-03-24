# SkSLTernaryExpression

> 源文件: src/sksl/ir/SkSLTernaryExpression.h, src/sksl/ir/SkSLTernaryExpression.cpp

## 概述

`TernaryExpression` 类是 SkSL（Skia Shading Language）中间表示(IR)中的表达式类型，用于表示三元条件运算符 `test ? ifTrue : ifFalse`。它继承自 `Expression` 类，包含三个子表达式：测试条件、真值分支和假值分支。该类实现了多种编译时优化，包括常量条件折叠、冗余分支消除、布尔表达式简化等，是 SkSL 优化器的重要组成部分。作为终结类（`final`），它确保三元表达式语义的一致性和优化的完整性。

## 架构位置

`TernaryExpression` 位于 Skia 的 SkSL 编译器的 IR 表达式层中：

```
skia/
  src/
    sksl/
      ir/
        SkSLIRNode.h                 # IR 节点基类
        SkSLExpression.h             # 表达式基类（TernaryExpression 的父类）
        SkSLTernaryExpression.h/cpp  # 本文件，三元表达式
        SkSLBinaryExpression.h       # 二元表达式（优化目标）
        SkSLPrefixExpression.h       # 前缀表达式（优化目标）
        SkSLLiteral.h                # 字面量
        SkSLConstructorScalarCast.h  # 标量类型转换（优化目标）
      SkSLConstantFolder.h           # 常量折叠工具
      SkSLAnalysis.h                 # IR 分析工具
      SkSLOperator.h                 # 运算符定义
```

在优化流程中的位置：
```
解析阶段 → 三元表达式识别 → Convert (类型检查) → Make (优化) → IR 节点或简化表达式
                                                        ↓
                                              常量折叠、模式匹配简化
```

## 主要类与结构体

### TernaryExpression 类

```cpp
class TernaryExpression final : public Expression {
public:
    inline static constexpr Kind kIRNodeKind = Kind::kTernary;

    // 构造函数
    TernaryExpression(Position pos, std::unique_ptr<Expression> test,
                     std::unique_ptr<Expression> ifTrue, std::unique_ptr<Expression> ifFalse);

    // 类型检查 + 创建（可能失败）
    static std::unique_ptr<Expression> Convert(const Context& context,
                                               Position pos,
                                               std::unique_ptr<Expression> test,
                                               std::unique_ptr<Expression> ifTrue,
                                               std::unique_ptr<Expression> ifFalse);

    // 直接创建 + 优化（假设已通过类型检查）
    static std::unique_ptr<Expression> Make(const Context& context,
                                            Position pos,
                                            std::unique_ptr<Expression> test,
                                            std::unique_ptr<Expression> ifTrue,
                                            std::unique_ptr<Expression> ifFalse);

    // 访问器
    std::unique_ptr<Expression>& test();
    const std::unique_ptr<Expression>& test() const;
    std::unique_ptr<Expression>& ifTrue();
    const std::unique_ptr<Expression>& ifTrue() const;
    std::unique_ptr<Expression>& ifFalse();
    const std::unique_ptr<Expression>& ifFalse() const;

    // 克隆表达式
    std::unique_ptr<Expression> clone(Position pos) const override;

    // 字符串表示
    std::string description(OperatorPrecedence parentPrecedence) const override;

private:
    std::unique_ptr<Expression> fTest;    // 测试条件
    std::unique_ptr<Expression> fIfTrue;  // 真值分支
    std::unique_ptr<Expression> fIfFalse; // 假值分支
};
```

### 三元表达式的语义

```glsl
test ? ifTrue : ifFalse
```

**执行逻辑**:
1. 计算 `test` 表达式（必须是布尔类型）
2. 如果 `test` 为 `true`，返回 `ifTrue` 的值
3. 如果 `test` 为 `false`，返回 `ifFalse` 的值

**类型要求**:
- `test` 必须是 `bool` 类型
- `ifTrue` 和 `ifFalse` 的类型必须兼容（可强制转换为同一类型）
- 结果类型与 `ifTrue`/`ifFalse` 的共同类型相同

## 公共 API 函数

### 构造函数

```cpp
TernaryExpression(Position pos, std::unique_ptr<Expression> test,
                 std::unique_ptr<Expression> ifTrue, std::unique_ptr<Expression> ifFalse)
```

**功能**: 创建三元表达式对象。

**参数**:
- `pos`: 表达式在源代码中的位置
- `test`: 测试条件表达式
- `ifTrue`: 真值分支表达式
- `ifFalse`: 假值分支表达式

**断言**: `ifTrue` 和 `ifFalse` 的类型必须匹配。

**类型推导**: 表达式的类型取自 `ifTrue->type()`（两个分支类型相同）。

### Convert (类型检查工厂)

```cpp
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           std::unique_ptr<Expression> test,
                                           std::unique_ptr<Expression> ifTrue,
                                           std::unique_ptr<Expression> ifFalse)
```

**功能**: 对三元表达式进行完整的类型检查和转换，是创建三元表达式的标准方法。

**类型检查流程**:

1. **测试条件类型强制**:
   ```cpp
   test = context.fTypes.fBool->coerceExpression(std::move(test), context);
   ```
   将 `test` 强制转换为 `bool` 类型（如 `int` → `bool`）。

2. **不透明类型检查**:
   ```cpp
   if (ifTrue->type().componentType().isOpaque()) {
       context.fErrors->error(pos, "ternary expression of opaque type '...' is not allowed");
       return nullptr;
   }
   ```
   禁止不透明类型（如 `sampler2D`、`atomic_uint`）作为三元表达式的结果。

3. **分支类型兼容性检查**:
   ```cpp
   Operator equalityOp(Operator::Kind::EQEQ);
   if (!equalityOp.determineBinaryType(context, ifTrue->type(), ifFalse->type(),
                                       &trueType, &falseType, &resultType) ||
       !trueType->matches(*falseType)) {
       context.fErrors->error(pos, "ternary operator result mismatch: '...'");
       return nullptr;
   }
   ```
   使用相等运算符的类型推导逻辑判断两个分支是否兼容。

4. **void 类型检查**:
   ```cpp
   if (ifTrue->type().isVoid()) {
       context.fErrors->error(pos, "ternary expression of type 'void' is not allowed");
       return nullptr;
   }
   ```
   禁止 `void` 类型的三元表达式。

5. **数组类型检查**:
   ```cpp
   if (trueType->isOrContainsArray()) {
       context.fErrors->error(pos, "ternary operator result may not be an array (or struct containing an array)");
       return nullptr;
   }
   ```
   禁止数组类型（包括包含数组的结构体）作为三元表达式的结果。

6. **类型强制转换**:
   ```cpp
   ifTrue = trueType->coerceExpression(std::move(ifTrue), context);
   ifFalse = falseType->coerceExpression(std::move(ifFalse), context);
   ```
   将两个分支转换为共同类型。

7. **创建表达式**: 调用 `Make` 完成最终创建和优化。

**返回**: 成功返回优化后的表达式，失败返回 `nullptr` 并报告错误。

### Make (直接创建工厂)

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        std::unique_ptr<Expression> test,
                                        std::unique_ptr<Expression> ifTrue,
                                        std::unique_ptr<Expression> ifFalse)
```

**功能**: 创建三元表达式，并应用编译时优化。

**断言验证**:
- `ifTrue` 和 `ifFalse` 类型匹配
- 不包含不透明类型
- 严格 ES2 模式下不包含数组

**优化策略**（按优先级排序）:

1. **常量条件折叠**:
   ```cpp
   const Expression* testExpr = ConstantFolder::GetConstantValueForVariable(*test);
   if (testExpr->isBoolLiteral()) {
       if (testExpr->as<Literal>().boolValue()) {
           return ifTrue;  // test 为 true，直接返回 ifTrue
       } else {
           return ifFalse;  // test 为 false，直接返回 ifFalse
       }
   }
   ```
   **示例**: `true ? a : b` → `a`

2. **相同分支消除**:
   ```cpp
   if (Analysis::IsSameExpressionTree(*ifTrueExpr, *ifFalseExpr)) {
       if (!Analysis::HasSideEffects(*test)) {
           return ifTrue;  // test 无副作用，直接返回 ifTrue
       }
       return BinaryExpression::Make(context, pos, std::move(test),
                                     Operator::Kind::COMMA, std::move(ifTrue));  // (test, ifTrue)
   }
   ```
   **示例**:
   - `test ? x : x` → `x` （test 无副作用）
   - `test ? x : x` → `(test, x)` （test 有副作用，如函数调用）

3. **布尔表达式优化 - false 假值分支**:
   ```cpp
   if (ifFalseExpr->isBoolLiteral() && !ifFalseExpr->as<Literal>().boolValue()) {
       return BinaryExpression::Make(context, pos, std::move(test),
                                     Operator::Kind::LOGICALAND, std::move(ifTrue));
   }
   ```
   **示例**: `test ? expr : false` → `test && expr`

4. **布尔表达式优化 - true 真值分支**:
   ```cpp
   if (ifTrueExpr->isBoolLiteral() && ifTrueExpr->as<Literal>().boolValue()) {
       return BinaryExpression::Make(context, pos, std::move(test),
                                     Operator::Kind::LOGICALOR, std::move(ifFalse));
   }
   ```
   **示例**: `test ? true : expr` → `test || expr`

5. **布尔取反优化**:
   ```cpp
   if (ifTrueExpr->isBoolLiteral() && !ifTrueExpr->as<Literal>().boolValue() &&
       ifFalseExpr->isBoolLiteral() && ifFalseExpr->as<Literal>().boolValue()) {
       return PrefixExpression::Make(context, pos, Operator::Kind::LOGICALNOT, std::move(test));
   }
   ```
   **示例**: `test ? false : true` → `!test`

6. **布尔到数值转换**:
   ```cpp
   if (ifTrueExpr->is<Literal>() && ifTrueExpr->as<Literal>().value() == 1.0 &&
       ifFalseExpr->is<Literal>() && ifFalseExpr->as<Literal>().value() == 0.0) {
       return ConstructorScalarCast::Make(context, pos, ifTrue->type(), std::move(test));
   }
   ```
   **示例**: `test ? 1 : 0` → `int(test)` 或 `float(test)`

**返回**: 优化后的表达式（可能是三元表达式、二元表达式、前缀表达式、类型转换或单个分支）。

### 访问器方法

```cpp
std::unique_ptr<Expression>& test() / const std::unique_ptr<Expression>& test() const
```
获取测试条件表达式（可变和常量版本）。

```cpp
std::unique_ptr<Expression>& ifTrue() / const std::unique_ptr<Expression>& ifTrue() const
```
获取真值分支表达式。

```cpp
std::unique_ptr<Expression>& ifFalse() / const std::unique_ptr<Expression>& ifFalse() const
```
获取假值分支表达式。

### clone

```cpp
std::unique_ptr<Expression> clone(Position pos) const override
```

**功能**: 递归克隆三元表达式到新位置。

**实现**: 克隆三个子表达式并创建新的三元表达式对象。

### description

```cpp
std::string description(OperatorPrecedence parentPrecedence) const override
```

**功能**: 生成三元表达式的字符串表示。

**格式**: `test ? ifTrue : ifFalse` 或 `(test ? ifTrue : ifFalse)`（需要括号时）

**括号规则**:
```cpp
bool needsParens = (OperatorPrecedence::kTernary >= parentPrecedence);
```
当父表达式的优先级高于或等于三元运算符时添加括号。

## 内部实现细节

### 常量变量展开

在优化前展开常量变量：
```cpp
const Expression* testExpr = ConstantFolder::GetConstantValueForVariable(*test);
const Expression* ifTrueExpr = ConstantFolder::GetConstantValueForVariable(*ifTrue);
const Expression* ifFalseExpr = ConstantFolder::GetConstantValueForVariable(*ifFalse);
```

**示例**:
```glsl
const bool flag = true;
int result = flag ? 1 : 2;
// testExpr 指向 Literal(true)，而非 VariableReference(flag)
```

### 表达式树相等性检查

`Analysis::IsSameExpressionTree` 递归比较两个表达式树：
```cpp
// 相同: x, x
// 相同: a + b, a + b
// 不同: x, y
// 不同: a + b, b + a （顺序不同）
```

**注意**: 这是结构相等，不是语义相等（不考虑交换律等）。

### 副作用检测

`Analysis::HasSideEffects` 检测表达式是否有副作用：
```cpp
// 有副作用: func(), i++, array[i++]
// 无副作用: x, a + b, sin(x)
```

**重要性**: 决定是否可以安全消除表达式。

### 优化权衡

**为什么 `test ? x : x` 不总是简化为 `x`？**
- 如果 `test` 有副作用（如 `func() ? x : x`），必须保留 `func()` 的调用
- 使用逗号运算符 `(func(), x)` 保留副作用

**为什么布尔优化优先于数值转换？**
- 布尔逻辑运算（`&&`, `||`）支持短路求值
- 类型转换无法短路
- 性能和语义优势

### 类型强制的微妙之处

```cpp
int3 a = ...;
float3 b = ...;
bool test = ...;
auto result = test ? a : b;  // 结果类型是 float3

// 类型强制过程
trueType = float3   // int3 提升为 float3
falseType = float3  // 已经是 float3
// a 被强制转换: ConstructorCompoundCast::Make(..., float3, a)
```

## 依赖关系

### 直接依赖

**头文件**:
- `SkSLExpression.h`: 表达式基类
- `SkSLType.h`: 类型系统
- `SkSLPosition.h`: 位置信息

**实现文件额外依赖**:
- `SkSLConstantFolder.h`: 常量折叠工具
- `SkSLAnalysis.h`: IR 分析工具
- `SkSLOperator.h`: 运算符定义
- `SkSLBinaryExpression.h`: 二元表达式（优化目标）
- `SkSLPrefixExpression.h`: 前缀表达式（优化目标）
- `SkSLConstructorScalarCast.h`: 标量类型转换
- `SkSLLiteral.h`: 字面量

### 被依赖关系

- **表达式解析**: 解析 `?:` 运算符时创建 `TernaryExpression`
- **优化传递**: 常量传播、死代码消除等优化
- **代码生成器**: 将三元表达式转换为目标语言（GLSL, SPIR-V, Metal）

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式**: `Convert` 和 `Make` 提供不同的创建策略
2. **策略模式**: 根据表达式模式选择不同的优化策略
3. **访问者模式**: `ConstantFolder` 和 `Analysis` 对表达式树进行遍历分析

### 设计决策

**为什么禁止不透明类型？**
- 采样器、原子变量等不能存储或复制
- GLSL/SPIR-V 标准不支持不透明类型的三元表达式
- 防止生成无效代码

**为什么禁止数组类型？**
- OpenGL ES 2.0 不支持数组作为一等值
- 简化实现和类型系统
- 可通过索引访问元素规避限制

**为什么使用相等运算符判断类型兼容性？**
- 相等运算符的类型规则是 SkSL 类型兼容性的权威定义
- 复用已有的类型推导逻辑
- 确保三元表达式和相等比较的类型规则一致

**为什么优化 `test ? 1 : 0` 为类型转换？**
- 布尔到数值的常见模式（如 `int(condition)`）
- 目标代码更简洁高效
- GPU 上类型转换通常是无开销的

**为什么保留副作用的测试条件？**
- 用户可能依赖副作用（如计数器、日志）
- 语义正确性优先于优化激进性
- 使用逗号运算符保留执行顺序

**为什么 `test ? true : expr` 优化为 `test || expr`？**
- 逻辑或支持短路求值：`test` 为 `true` 时不计算 `expr`
- 三元表达式总是计算两个分支（某些平台）
- 性能提升 + 副作用控制

## 性能考量

### 编译时优化收益

**常量条件折叠**:
- 消除运行时分支
- 减少寄存器压力
- 启用进一步优化（如常量传播）

**短路求值优化**:
- `test ? true : expr` → `test || expr`
- 如果 `test` 为 `true`，`expr` 不被计算
- GPU 分支预测友好

### 代码生成优化

**简化前**:
```glsl
float result = condition ? 1.0 : 0.0;
// GPU 可能生成条件分支或 select 指令
```

**简化后**:
```glsl
float result = float(condition);
// GPU 生成简单的类型转换（通常无开销）
```

### 内存占用

单个 `TernaryExpression` 对象：
- `Expression` 基类: ~24 字节（虚表 + 位置 + 类型）
- `fTest`, `fIfTrue`, `fIfFalse`: 24 字节（3 个智能指针）
- **总计**: ~48 字节

优化后消除：
- 常量折叠成功时，节点被简化为单个分支或运算符
- 内存节省 + 遍历加速

### 潜在瓶颈

- **深层嵌套三元表达式**: 递归分析开销大
- **复杂分支表达式**: 表达式树相等性检查耗时
- **频繁的常量变量查找**: 符号表查询开销

## 相关文件

### 核心相关文件

- **src/sksl/ir/SkSLExpression.h**: 表达式基类
- **src/sksl/ir/SkSLBinaryExpression.h**: 二元表达式
- **src/sksl/ir/SkSLPrefixExpression.h**: 前缀表达式
- **src/sksl/SkSLConstantFolder.h**: 常量折叠工具
- **src/sksl/SkSLAnalysis.h**: IR 分析工具

### 优化相关

- **src/sksl/transform/**: IR 优化传递

### 代码生成相关

- **src/sksl/codegen/SkSLGLSLCodeGenerator.cpp**: GLSL 代码生成
- **src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp**: SPIR-V 代码生成
- **src/sksl/codegen/SkSLMetalCodeGenerator.cpp**: Metal 代码生成

### 使用示例

```cpp
// 用户代码
int result = condition ? 10 : 20;

// IR 构建
auto ternary = TernaryExpression::Convert(
    context,
    pos,
    conditionExpr,
    Literal::MakeInt(context, pos, 10),
    Literal::MakeInt(context, pos, 20)
);

// 优化示例 1: 常量条件
true ? 10 : 20 → 10

// 优化示例 2: 布尔表达式
test ? true : false → test

// 优化示例 3: 逻辑简化
test ? true : expr → test || expr
```
