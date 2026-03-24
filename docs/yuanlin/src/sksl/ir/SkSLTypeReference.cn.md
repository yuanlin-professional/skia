# TypeReference

> 源文件: src/sksl/ir/SkSLTypeReference.h, src/sksl/ir/SkSLTypeReference.cpp

## 概述

`TypeReference` 是 SkSL 中间表示中用于表示类型引用的 IR 节点。它是一个中间值,在编译过程中最终会被替换为构造函数调用或其他有效的表达式。TypeReference 出现在类型名称被用作表达式的场景,例如类型转换 `float(x)` 或构造函数调用 `vec3(1.0, 0.0, 0.0)`。

## 架构位置

TypeReference 位于 SkSL 编译器的中间表示层,属于表达式系统:

```
src/sksl/
  ├── ir/
  │   ├── SkSLTypeReference.h/cpp     ← 当前组件
  │   ├── SkSLExpression.h            ← 父类:表达式基类
  │   ├── SkSLType.h                  ← 引用的类型
  │   ├── SkSLConstructor.h           ← 最终替换为构造函数
  │   └── SkSLIRNode.h                ← IR 节点基类
```

在编译流程中的位置:
1. Parser 识别类型名称出现在表达式位置
2. 创建 TypeReference 作为占位符
3. 类型检查阶段将 TypeReference 替换为适当的构造函数或转换表达式
4. 有效程序中不应包含 TypeReference

## 主要类与结构体

### TypeReference 类

```cpp
class TypeReference final : public Expression {
    const Type& fValue;  // 引用的类型
};
```

**核心特征:**
- 继承自 `Expression`,可参与表达式树
- 存储对 `Type` 对象的引用
- `type()` 返回 `fInvalid` 类型(表示这不是有效表达式)
- 仅在编译中间阶段存在

## 公共 API 函数

### VerifyType

**函数签名:**
```cpp
static bool VerifyType(const Context& context,
                       const SkSL::Type* type,
                       Position pos);
```

**功能:** 验证类型是否可以在用户代码中使用

**验证规则:**
1. **泛型类型检查:** 拒绝泛型类型如 `$genType`, `$genIType`
2. **字面量类型检查:** 拒绝字面量类型如 `$floatLiteral`, `$intLiteral`
3. **ES2 兼容性检查:** 在 strict-ES2 模式下,拒绝不支持的类型

**特殊情况:**
- 内置代码(`isBuiltinCode()`)跳过所有检查
- 允许内部使用泛型和字面量类型

**返回值:** 类型有效返回 true,否则返回 false

### Convert

**函数签名:**
```cpp
static std::unique_ptr<TypeReference> Convert(
    const Context& context,
    Position pos,
    const Type* type);
```

**功能:** 创建 TypeReference 并执行类型验证

**流程:**
1. 调用 `VerifyType()` 验证类型
2. 验证通过则调用 `Make()` 创建对象
3. 验证失败返回 nullptr

**应用场景:** Parser 创建类型引用时使用

### Make

**函数签名:**
```cpp
static std::unique_ptr<TypeReference> Make(
    const Context& context,
    Position pos,
    const Type* type);
```

**功能:** 直接创建 TypeReference,不执行验证(仅 ASSERT)

**前提条件:**
- 类型必须允许在 ES2 中使用
- 内部代码可以跳过检查

**应用场景:** 内部创建已知有效的类型引用

### value

**函数签名:**
```cpp
const Type& value() const;
```

**功能:** 返回引用的类型对象

**返回值:** Type 对象的常量引用

### description

**函数签名:**
```cpp
std::string description(OperatorPrecedence) const override;
```

**功能:** 返回类型名称的字符串表示

**实现:** 直接返回 `this->value().name()`

**用途:** 调试和错误报告

### clone

**函数签名:**
```cpp
std::unique_ptr<Expression> clone(Position pos) const override;
```

**功能:** 克隆 TypeReference 对象到新位置

**返回值:** 新的 TypeReference,引用相同的类型

## 内部实现细节

### 无效类型标记

TypeReference 的 `type()` 方法返回 `fInvalid` 类型:
```cpp
TypeReference(const Context& context, Position pos, const Type* value)
    : TypeReference(pos, value, context.fTypes.fInvalid.get())
```

**设计目的:**
- 标记 TypeReference 不是有效的表达式
- 防止在类型推导中被误用
- 强制在后续阶段替换为有效表达式

### 泛型类型处理

泛型类型(如 `$genType`)仅在内置代码中使用:
```cpp
if (type->isGeneric() || type->isLiteral()) {
    context.fErrors->error(pos,
        "type '" + std::string(type->name()) + "' is generic");
    return false;
}
```

**用途:**
- SkSL 内置函数使用泛型签名
- 编译时替换为具体类型
- 用户代码不能直接使用

### ES2 兼容性

在 strict-ES2 模式下,检查类型支持:
```cpp
if (!type->isAllowedInES2(context)) {
    context.fErrors->error(pos,
        "type '" + std::string(type->name()) + "' is not supported");
    return false;
}
```

**限制类型示例:**
- `uint`: GLSL ES 3.0+
- 某些纹理类型: 需要扩展支持

## 依赖关系

### 直接依赖

- `SkSLExpression.h`: 父类,提供表达式接口
- `SkSLType.h`: 引用的类型系统
- `SkSLContext.h`: 编译上下文
- `SkSLBuiltinTypes.h`: 内置类型(如 fInvalid)

### 被依赖

- Parser: 创建 TypeReference 节点
- IRGenerator: 将 TypeReference 转换为构造函数
- 类型检查器: 验证类型引用的合法性

### 转换关系

TypeReference 最终转换为:
- `Constructor`: 类型构造函数,如 `vec3(1.0)`
- `TypeCast`: 类型转换,如 `int(x)`
- 编译错误: 如果无法转换

## 设计模式与设计决策

### 设计模式

**1. 占位符模式 (Placeholder Pattern)**
- TypeReference 作为临时占位符
- 在后续阶段替换为实际表达式
- 分离解析和语义分析

**2. 值对象模式 (Value Object Pattern)**
- 不可变引用类型
- 仅包含类型引用和位置信息
- 轻量级对象

### 设计决策

**1. 中间表示策略**
- **问题:** 类型名称和函数调用语法相同:`float(x)`
- **解决:** 先创建 TypeReference,后续判断并转换
- **优点:** 简化 Parser 逻辑,延迟语义决策

**2. 无效类型标记**
- **问题:** 如何标记 TypeReference 不是有效表达式?
- **解决:** type() 返回 fInvalid
- **优点:** 类型系统层面防止误用

**3. 分离验证和构造**
- `VerifyType()`: 类型验证逻辑
- `Convert()`: 验证 + 创建
- `Make()`: 直接创建(跳过验证)
- **优点:** 灵活性,内部代码可绕过验证

**4. 泛型类型隔离**
- 泛型类型仅在内置代码中使用
- 用户代码不能创建泛型 TypeReference
- **优点:** 保持类型系统的封闭性

## 性能考量

### 内存占用

**TypeReference 大小:**
- Expression 基类: ~24-32 字节
- `fValue` 引用: 8 字节
- **总计:** 约 32-40 字节/对象

**临时性质:** TypeReference 在 IR 最终形式中不存在,仅在编译中间阶段产生临时开销

### 验证成本

**VerifyType 复杂度:** O(1)
- 泛型检查: 位标志检查
- ES2 兼容性: 类型属性查询
- 非常轻量级

### 转换成本

TypeReference → Constructor 转换:
- 解析参数列表
- 选择合适的构造函数重载
- 创建 Constructor 节点
- 成本取决于参数数量和类型推导复杂度

## 相关文件

### 核心文件

- `src/sksl/ir/SkSLExpression.h`: 表达式基类
- `src/sksl/ir/SkSLType.h`: 类型系统
- `src/sksl/ir/SkSLConstructor.h`: 构造函数表达式

### 转换相关

- `src/sksl/SkSLIRGenerator.cpp`: 执行 TypeReference 到 Constructor 的转换
- `src/sksl/SkSLParser.cpp`: 创建 TypeReference 节点

### 类型系统

- `src/sksl/SkSLBuiltinTypes.h`: 内置类型定义
- `src/sksl/SkSLContext.h`: 编译上下文

### 使用示例

TypeReference 的典型使用场景:
```glsl
vec3(1.0, 0.0, 0.0)  // vec3 先创建为 TypeReference
float(x)              // float 先创建为 TypeReference
mat4()                // mat4 先创建为 TypeReference
```

这些都会在语义分析阶段转换为相应的 Constructor 节点。
