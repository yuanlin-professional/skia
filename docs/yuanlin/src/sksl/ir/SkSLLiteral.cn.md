# SkSLLiteral

> 源文件: src/sksl/ir/SkSLLiteral.h, src/sksl/ir/SkSLLiteral.cpp

## 概述

`Literal` 类是 SkSL（Skia Shading Language）中间表示(IR)中的基础表达式类型，用于表示字面量常量值。它继承自 `Expression` 类，能够存储整数、浮点数和布尔值三种基本类型的常量。该类采用统一的 `double` 类型内部存储所有值，通过类型信息区分具体的数据类型，并提供了一套完整的类型安全工厂方法用于创建不同类型的字面量。作为常量表达式，`Literal` 支持编译时常量折叠和比较操作，是 SkSL 常量传播优化的基础。

## 架构位置

`Literal` 位于 Skia 的 SkSL 编译器的 IR 表达式层中：

```
skia/
  src/
    sksl/
      ir/
        SkSLIRNode.h              # IR 节点基类
        SkSLExpression.h          # 表达式基类（Literal 的父类）
        SkSLLiteral.h/cpp         # 本文件，字面量表达式
        SkSLType.h                # 类型系统
      SkSLContext.h               # 编译上下文（包含内置类型）
      SkSLBuiltinTypes.h          # 内置类型定义
      SkSLDefines.h               # 类型别名（SKSL_INT, SKSL_FLOAT）
      SkSLString.h                # 字符串工具（to_string）
```

在编译流程中的位置：
```
词法分析 → 字面量识别 → Literal 创建 → 常量折叠 → IR 优化 → 代码生成
                                           ↓
                                    常量传播优化
```

## 主要类与结构体

### Literal 类

```cpp
class Literal : public Expression {
public:
    inline static constexpr Kind kIRNodeKind = Kind::kLiteral;

    // 构造函数（内部使用）
    Literal(Position pos, double value, const Type* type);

    // 浮点字面量工厂方法
    static std::unique_ptr<Literal> MakeFloat(const Context& context, Position pos, float value);
    static std::unique_ptr<Literal> MakeFloat(Position pos, float value, const Type* type);

    // 整数字面量工厂方法
    static std::unique_ptr<Literal> MakeInt(const Context& context, Position pos, SKSL_INT value);
    static std::unique_ptr<Literal> MakeInt(Position pos, SKSL_INT value, const Type* type);

    // 布尔字面量工厂方法
    static std::unique_ptr<Literal> MakeBool(const Context& context, Position pos, bool value);
    static std::unique_ptr<Literal> MakeBool(Position pos, bool value, const Type* type);

    // 通用工厂方法（自动推断类型）
    static std::unique_ptr<Literal> Make(Position pos, double value, const Type* type);

    // 值访问器
    float floatValue() const;
    SKSL_INT intValue() const;
    SKSL_INT boolValue() const;
    double value() const;

    // Expression 接口实现
    std::string description(OperatorPrecedence) const override;
    ComparisonResult compareConstant(const Expression& other) const override;
    std::unique_ptr<Expression> clone(Position pos) const override;
    bool supportsConstantValues() const override;
    std::optional<double> getConstantValue(int n) const override;

private:
    double fValue;  // 统一存储所有类型的值
};
```

### 类型别名

- `SKSL_INT`: 通常是 `int64_t`，表示 SkSL 整数类型
- `SKSL_FLOAT`: 通常是 `float`，表示 SkSL 浮点类型

## 公共 API 函数

### 浮点字面量工厂方法

```cpp
static std::unique_ptr<Literal> MakeFloat(const Context& context, Position pos, float value)
```

**功能**: 创建 `$floatLiteral` 类型的浮点字面量（泛型浮点类型）。

**参数**:
- `context`: 编译上下文，提供内置类型访问
- `pos`: 字面量的源代码位置
- `value`: 浮点值

**返回**: 浮点字面量对象的智能指针。

```cpp
static std::unique_ptr<Literal> MakeFloat(Position pos, float value, const Type* type)
```

**功能**: 创建指定类型的浮点字面量（如 `float`, `half` 等）。

**断言**: 类型必须是浮点类型（`type->isFloat()`）。

### 整数字面量工厂方法

```cpp
static std::unique_ptr<Literal> MakeInt(const Context& context, Position pos, SKSL_INT value)
```

**功能**: 创建 `$intLiteral` 类型的整数字面量（泛型整数类型）。

**参数**:
- `context`: 编译上下文
- `pos`: 源代码位置
- `value`: 整数值（`int64_t`）

```cpp
static std::unique_ptr<Literal> MakeInt(Position pos, SKSL_INT value, const Type* type)
```

**功能**: 创建指定类型的整数字面量（如 `int`, `short`, `uint` 等）。

**断言**:
- 类型必须是整数类型（`type->isInteger()`）
- 值必须在类型的范围内（`minimumValue()` 到 `maximumValue()`）

**边界检查**: 使用 `SkASSERTF` 验证值是否溢出，防止类型转换错误。

### 布尔字面量工厂方法

```cpp
static std::unique_ptr<Literal> MakeBool(const Context& context, Position pos, bool value)
static std::unique_ptr<Literal> MakeBool(Position pos, bool value, const Type* type)
```

**功能**: 创建布尔类型字面量（`true` 或 `false`）。

**两个重载的区别**: 第一个从 `Context` 获取 `bool` 类型，第二个直接接受类型指针（无需 `Context`）。

**断言**: 类型必须是布尔类型（`type->isBoolean()`）。

### 通用工厂方法

```cpp
static std::unique_ptr<Literal> Make(Position pos, double value, const Type* type)
```

**功能**: 根据目标类型自动创建相应的字面量，支持类型转换和舍入。

**逻辑**:
1. 如果是浮点类型 → 调用 `MakeFloat`
2. 如果是整数类型 → 调用 `MakeInt`（自动截断小数部分）
3. 否则假定为布尔类型 → 调用 `MakeBool`

**用途**: 常量折叠时需要改变字面量类型（如 `1.5 + 2` 中整数提升为浮点）。

### 值访问器

```cpp
float floatValue() const
```
返回浮点值，带断言确保类型为浮点类型。

```cpp
SKSL_INT intValue() const
```
返回整数值，带断言确保类型为整数类型。

```cpp
SKSL_INT boolValue() const
```
返回布尔值（实际类型是 `SKSL_INT`，但语义上是布尔），带断言。

```cpp
double value() const
```
返回原始 `double` 值，无类型检查（内部使用）。

### Expression 接口实现

```cpp
std::string description(OperatorPrecedence) const override
```

**功能**: 生成字面量的字符串表示。

**逻辑**:
- 布尔类型 → `"true"` 或 `"false"`
- 整数类型 → `std::to_string(intValue())`
- 浮点类型 → `skstd::to_string(floatValue())` （保留浮点格式）

```cpp
ComparisonResult compareConstant(const Expression& other) const override
```

**功能**: 编译时比较两个常量表达式。

**逻辑**:
1. 如果 `other` 不是 `Literal` → 返回 `kUnknown`
2. 如果类型的数字类别不同（如整数 vs 浮点）→ 返回 `kUnknown`
3. 比较值是否相等 → 返回 `kEqual` 或 `kNotEqual`

**用途**: 常量条件表达式优化（如 `if (true)` 的消除）。

```cpp
std::unique_ptr<Expression> clone(Position pos) const override
```
克隆字面量到新位置，复制值和类型。

```cpp
bool supportsConstantValues() const override
```
返回 `true`，表示支持常量值查询。

```cpp
std::optional<double> getConstantValue(int n) const override
```
返回常量值（标量只有一个分量，`n` 必须为 0）。

## 内部实现细节

### 统一值存储

使用 `double fValue` 统一存储所有类型的值：
- **布尔值**: 存储为 `0.0` (false) 或 `1.0` (true)
- **整数值**: 存储为 `double` 表示的整数（精确表示 53 位整数）
- **浮点值**: 直接存储浮点数

**优势**:
- 简化内存布局（无需联合体或变体类型）
- 减少内存占用（单一成员变量）
- 简化克隆和比较逻辑

**限制**:
- `double` 的 53 位尾数精度限制，超过 2^53 的整数可能损失精度
- SkSL 的 `SKSL_INT` (int64_t) 可能超出精确表示范围
- 实际上 SkSL 整数范围通常限制在 32 位，不会遇到此问题

### 类型安全机制

每个访问器都有类型断言：
```cpp
float floatValue() const {
    SkASSERT(this->type().isFloat());  // 确保类型匹配
    return (SKSL_FLOAT)fValue;
}
```

这在调试构建中捕获类型错误，发布构建中移除断言开销。

### 边界检查

`MakeInt` 进行完整的边界检查：
```cpp
SkASSERTF(value >= type->minimumValue(), "Value %" PRId64 " does not fit in type %s",
                                         value, type->description().c_str());
SkASSERTF(value <= type->maximumValue(), "Value %" PRId64 " does not fit in type %s",
                                         value, type->description().c_str());
```

防止类型转换溢出（如将 300 赋给 `byte` 类型）。

### 字符串转换优化

`description` 方法根据类型选择最佳字符串转换：
- 布尔值直接返回 `"true"`/`"false"` 字符串字面量（无分配）
- 整数使用 `std::to_string`
- 浮点使用自定义 `skstd::to_string`（可能保留 `.0` 后缀以区分整数）

## 依赖关系

### 直接依赖

**头文件**:
- `SkSLExpression.h`: 表达式基类
- `SkSLType.h`: 类型系统
- `SkSLContext.h`: 编译上下文
- `SkSLBuiltinTypes.h`: 内置类型（`fIntLiteral`, `fFloatLiteral`, `fBool`）
- `SkSLDefines.h`: 类型别名定义

**实现文件**:
- `SkSLString.h`: 浮点数字符串转换工具

### 被依赖关系

几乎所有涉及常量表达式的组件都依赖 `Literal`：
- 常量折叠优化器
- 表达式求值器
- 各种代码生成器（生成常量值）

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式**: 提供类型安全的静态工厂方法，而非直接暴露构造函数
2. **类型对象模式**: 通过 `Type` 指针表示字面量的具体类型
3. **不可变对象模式**: 字面量创建后值不可修改（仅通过克隆创建新对象）

### 设计决策

**为什么使用 `double` 统一存储？**
- 简化实现，避免复杂的联合体或变体类型
- `double` 的 53 位精度足以表示 SkSL 的整数范围（通常 32 位）
- 减少内存占用和对齐需求

**为什么提供两组工厂方法（带/不带 Context）？**
- 带 `Context` 版本：用于解析阶段，使用泛型字面量类型（`$intLiteral`, `$floatLiteral`）
- 不带 `Context` 版本：用于优化阶段，类型已确定，无需访问 `Context`
- 泛型字面量类型支持类型推断（如 `1 + 2.0` 中 `1` 提升为浮点）

**为什么 `MakeInt` 需要边界检查？**
- SkSL 支持多种整数类型（`byte`, `short`, `int`, `uint` 等）
- 用户代码可能写出越界字面量（如 `byte x = 300;`）
- 早期捕获错误，避免生成无效代码

**为什么 `compareConstant` 检查数字类别？**
- 整数和浮点的比较语义不同（如 `1 == 1.0` 在 SkSL 中可能不合法）
- 避免跨类型比较的歧义
- 编译器需要明确的类型匹配规则

**为什么 `getConstantValue` 要求 `n == 0`？**
- 字面量是标量（单个值），只有一个分量
- 向量字面量使用 `Constructor` 类，而非 `Literal`
- 统一的常量值接口支持标量和向量

## 性能考量

### 内存效率

单个 `Literal` 对象的内存占用：
- `Expression` 基类: ~16-24 字节（虚表、位置、类型指针）
- `fValue`: 8 字节（`double`）
- **总计**: ~24-32 字节/字面量

与使用联合体的替代方案相比：
- 联合体版本: `union { int64_t i; double f; bool b; }` = 8 字节 + 类型标记 = 9-16 字节（对齐）
- 差异不大，且 `double` 版本更简单

### 操作效率

- **创建**: 工厂方法内联后接近直接构造的开销（单次堆分配）
- **值访问**: 类型转换开销极小（编译器优化后可能消除）
- **比较**: 直接浮点比较，O(1) 操作
- **克隆**: 简单的值拷贝，无深拷贝需求

### 常量折叠优化

`Literal` 是编译时求值的基础：
```cpp
// 编译前: 1 + 2 * 3
// 编译后: 7

// 优化器将表达式树简化为单个 Literal
BinaryExpression(+, Literal(1), BinaryExpression(*, Literal(2), Literal(3)))
  → BinaryExpression(+, Literal(1), Literal(6))
  → Literal(7)
```

### 潜在瓶颈

- **大量字面量**: 大型着色器可能包含数百个字面量，每个都需要堆分配
- **字符串生成**: `description()` 方法在调试输出时频繁调用，字符串分配可能成为瓶颈
- **类型断言**: 调试构建中的大量断言检查可能影响性能（发布构建消除）

## 相关文件

### 核心相关文件

- **src/sksl/ir/SkSLExpression.h**: 表达式基类
- **src/sksl/ir/SkSLType.h**: 类型系统
- **src/sksl/SkSLContext.h**: 编译上下文
- **src/sksl/SkSLBuiltinTypes.h**: 内置类型定义

### 使用 Literal 的组件

- **src/sksl/SkSLConstantFolder.cpp**: 常量折叠优化器
- **src/sksl/analysis/SkSLProgramVisitor.h**: IR 遍历器
- **src/sksl/codegen/SkSLGLSLCodeGenerator.cpp**: GLSL 代码生成

### 相关表达式类型

- **src/sksl/ir/SkSLConstructor.h**: 构造函数表达式（向量/矩阵字面量）
- **src/sksl/ir/SkSLBinaryExpression.h**: 二元表达式（常量折叠目标）

### 使用示例

```cpp
// 创建整数字面量
auto intLit = Literal::MakeInt(context, pos, 42);

// 创建浮点字面量
auto floatLit = Literal::MakeFloat(pos, 3.14f, context.fTypes.fFloat.get());

// 创建布尔字面量
auto boolLit = Literal::MakeBool(context, pos, true);

// 通用创建（带类型转换）
auto roundedInt = Literal::Make(pos, 3.7, context.fTypes.fInt.get());  // 值为 3
```
