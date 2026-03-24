# SkSLExpressionStatement

> 源文件: src/sksl/ir/SkSLExpressionStatement.h, src/sksl/ir/SkSLExpressionStatement.cpp

## 概述

`ExpressionStatement` 是 SkSL IR 中表示表达式语句的节点类，用于将独立的表达式作为语句使用，例如函数调用、赋值操作等。该类继承自 `Statement`，负责将表达式转换为可执行的语句，并在此过程中执行优化，如消除无副作用的表达式和优化变量引用类型。

作为 SkSL 编译器中最简单但使用最频繁的语句类型之一，`ExpressionStatement` 充当了表达式和语句之间的桥梁。它在转换过程中会验证表达式的完整性，确保不会出现不完整的表达式（如单独的类型引用或函数引用），并应用编译器优化以提升性能。

## 架构位置

`ExpressionStatement` 位于 Skia 图形库的 SkSL 着色器语言编译器的中间表示（IR）层：

- **模块位置**: `src/sksl/ir/` - SkSL 中间表示节点定义目录
- **继承关系**: `ExpressionStatement` → `Statement` → `IRNode`
- **编译流程**: Parser → AST → IR（ExpressionStatement） → 优化 → 代码生成
- **依赖层次**:
  - 向上依赖: `Expression`、`Context`、`Analysis`
  - 向下被用于: 代码生成器、优化器、语句遍历器
  - 平级关系: 与 `Block`、`IfStatement`、`ForStatement` 等语句节点并列

## 主要类与结构体

### ExpressionStatement 类

```cpp
class ExpressionStatement final : public Statement {
public:
    inline static constexpr Kind kIRNodeKind = Kind::kExpression;

private:
    std::unique_ptr<Expression> fExpression;  // 被包装的表达式
};
```

核心职责：
- 将表达式包装为语句
- 存储并管理单个表达式的生命周期
- 提供表达式的访问接口

该类的设计非常简洁，仅包含一个表达式成员，所有复杂逻辑都在静态工厂方法中实现。

## 公共 API 函数

### 静态构造函数

#### Convert
```cpp
static std::unique_ptr<Statement> Convert(
    const Context& context,
    std::unique_ptr<Expression> expr);
```

将表达式转换为表达式语句：
- 验证表达式的完整性（通过 `isIncomplete` 检查）
- 拒绝不完整的表达式（如 `FunctionReference`、`TypeReference`）
- 通过 `ErrorReporter` 报告错误
- 成功后调用 `Make` 创建语句

#### Make
```cpp
static std::unique_ptr<Statement> Make(
    const Context& context,
    std::unique_ptr<Expression> expr);
```

直接创建表达式语句（假设表达式已验证）：
- 断言表达式完整性
- 在优化模式下执行优化：
  - **无副作用消除**: 如果表达式无副作用，替换为 `Nop`
  - **引用类型降级**: 将赋值表达式中的 `kReadWrite` 引用降级为 `kWrite`
- 创建并返回 `ExpressionStatement` 节点

### 访问器函数

```cpp
const std::unique_ptr<Expression>& expression() const;  // 获取表达式（只读）
std::unique_ptr<Expression>& expression();              // 获取表达式（可修改）
```

### 工具函数

#### description
```cpp
std::string description() const override;
```

生成表达式语句的字符串表示：
- 调用表达式的 `description`，传递 `kStatement` 优先级
- 添加分号后缀
- 格式: `expression;`

## 内部实现细节

### 表达式完整性验证

`Convert` 函数通过 `isIncomplete` 检查表达式的完整性：

```cpp
if (expr->isIncomplete(context)) {
    return nullptr;  // 错误已由 isIncomplete 报告
}
```

**不完整的表达式示例**：
- `int` - 类型引用（`TypeReference`）
- `foo` - 函数引用（`FunctionReference`），未调用
- `shader.sample` - 方法引用（`MethodReference`），未调用

这些表达式不能单独作为语句使用，必须在上下文中被进一步处理（如函数调用、构造器调用）。

### 无副作用优化

在 `Make` 函数中，启用优化时会检查表达式的副作用：

```cpp
if (context.fConfig->fSettings.fOptimize) {
    if (!Analysis::HasSideEffects(*expr)) {
        return Nop::Make();
    }
}
```

**被优化的表达式示例**：
```glsl
42;              // 字面量，无副作用 → Nop
x + y;           // 纯计算，无副作用 → Nop
const float k;   // 常量引用，无副作用 → Nop
```

**保留的表达式示例**：
```glsl
x = 5;           // 赋值，有副作用
foo();           // 函数调用，可能有副作用
x++;             // 自增，有副作用
```

### 变量引用类型降级

针对赋值表达式的特殊优化：

```cpp
if (expr->is<BinaryExpression>()) {
    BinaryExpression& binary = expr->as<BinaryExpression>();
    if (VariableReference* assignedVar = binary.isAssignmentIntoVariable()) {
        if (assignedVar->refKind() == VariableRefKind::kReadWrite) {
            assignedVar->setRefKind(VariableRefKind::kWrite);
        }
    }
}
```

**优化原理**：
- 在赋值表达式中，左值变量通常被标记为 `kReadWrite`
- 这是因为赋值运算符（如 `+=`）需要读取变量的当前值
- 但在表达式语句中，赋值结果被丢弃，不会被读取
- 因此可以安全地将引用类型降级为 `kWrite`

**优化示例**：
```glsl
// 原始代码
a += b;

// 内部表示（优化前）
// a: kReadWrite（读取 a 的值，加上 b，写回 a，并返回结果）

// 优化后
// a: kWrite（读取 a 的值，加上 b，写回 a，结果被丢弃）
```

**优化效果**：
- 更准确的引用类型语义
- 帮助后续优化识别未使用的变量
- 减少不必要的数据流追踪

### 描述生成

`description` 函数使用 `kStatement` 优先级：

```cpp
return this->expression()->description(OperatorPrecedence::kStatement) + ";";
```

**优先级影响**：
- `kStatement` 优先级最低
- 避免在表达式语句中添加不必要的括号
- 例如: `x = y + z;` 而非 `(x = y + z);`

## 依赖关系

### 头文件依赖

**核心依赖**：
- `SkSLExpression.h` - 表达式基类
- `SkSLStatement.h` - 语句基类
- `SkSLIRNode.h` - IR 节点基类

**功能依赖**：
- `SkSLContext.h` - 编译上下文
- `SkSLAnalysis.h` - 副作用分析
- `SkSLOperator.h` - 操作符优先级
- `SkSLProgramSettings.h` - 优化配置

**关联节点**：
- `SkSLBinaryExpression.h` - 二元表达式（赋值优化）
- `SkSLVariableReference.h` - 变量引用（引用类型修改）
- `SkSLNop.h` - 空操作（优化结果）

### 运行时依赖

- **分析工具**: `Analysis::HasSideEffects` - 检测表达式副作用
- **表达式验证**: `Expression::isIncomplete` - 验证表达式完整性
- **优化配置**: `Context::fConfig->fSettings.fOptimize` - 控制优化开关

## 设计模式与设计决策

### 工厂模式

提供两个静态工厂方法：
- `Convert`: 面向用户输入，执行完整验证
- `Make`: 面向编译器内部，假设已验证

设计原因：
- 分离验证和创建逻辑
- `Convert` 处理所有错误情况
- `Make` 专注于优化和构造

### 优化即构造

在 `Make` 中直接执行优化，而非延迟到优化阶段：
```cpp
static std::unique_ptr<Statement> Make(...) {
    if (optimize && no_side_effects) {
        return Nop::Make();  // 立即优化
    }
    return std::make_unique<ExpressionStatement>(...);
}
```

设计优势：
- 减少 IR 节点数量
- 避免创建无用节点
- 简化后续优化遍历

### 不可变表达式

表达式在构造后位置固定：
```cpp
ExpressionStatement(std::unique_ptr<Expression> expression)
    : INHERITED(expression->fPosition, kIRNodeKind)
    , fExpression(std::move(expression)) {}
```

- 语句的位置继承自表达式
- 表达式所有权转移
- 符合 RAII 原则

### 引用类型语义优化

变量引用类型降级体现了精确的语义分析：
- 区分真正的读写操作和仅写操作
- 支持死代码消除优化
- 提升数据流分析精度

## 性能考量

### 内存占用

```cpp
std::unique_ptr<Expression> fExpression;  // 8 字节
```

总大小：约 16 字节（加上 `Statement` 基类）

- 最小化内存占用
- 使用智能指针管理生命周期
- 无额外开销

### 编译时优化

**无副作用消除**：
```glsl
x + y;  →  Nop
```
- 避免生成无用代码
- 减少后端负担
- 编译时零开销

**引用类型优化**：
```glsl
a += b;  // kReadWrite → kWrite
```
- 提升后续分析精度
- 支持更激进的优化
- 编译时微小开销

### 优化触发条件

优化仅在以下条件下执行：
```cpp
if (context.fConfig->fSettings.fOptimize) { ... }
```

- 用户可控
- 调试模式下禁用（保留所有语句）
- 发布模式下启用（最大化性能）

### 描述生成延迟

`description` 方法按需生成字符串：
- 仅在错误报告和调试时调用
- 正常编译流程无开销
- 递归生成支持嵌套表达式

## 相关文件

### 同级 IR 节点
- `src/sksl/ir/SkSLBlock.h/cpp` - 块语句
- `src/sksl/ir/SkSLIfStatement.h/cpp` - 条件语句
- `src/sksl/ir/SkSLForStatement.h/cpp` - 循环语句
- `src/sksl/ir/SkSLReturnStatement.h` - 返回语句

### 依赖的核心组件
- `src/sksl/SkSLContext.h` - 编译上下文
- `src/sksl/SkSLAnalysis.h` - 程序分析工具
- `src/sksl/ir/SkSLExpression.h` - 表达式基类
- `src/sksl/SkSLOperator.h` - 操作符定义
- `src/sksl/SkSLProgramSettings.h` - 编译器设置

### 相关的表达式节点
- `src/sksl/ir/SkSLBinaryExpression.h/cpp` - 二元表达式
- `src/sksl/ir/SkSLVariableReference.h/cpp` - 变量引用
- `src/sksl/ir/SkSLFunctionCall.h/cpp` - 函数调用

### 优化相关
- `src/sksl/ir/SkSLNop.h` - 空操作节点
- `src/sksl/transform/` - IR 变换和优化器

### 使用场景
- `src/sksl/SkSLCompiler.cpp` - 编译器主流程
- `src/sksl/codegen/` - 各种后端代码生成器
- `src/sksl/analysis/SkSLProgramVisitor.cpp` - 程序遍历器
