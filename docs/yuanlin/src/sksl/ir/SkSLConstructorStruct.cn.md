# SkSLConstructorStruct

> 源文件: src/sksl/ir/SkSLConstructorStruct.h, src/sksl/ir/SkSLConstructorStruct.cpp

## 概述

`ConstructorStruct` 类是 SkSL（Skia Shading Language）中间表示(IR)中的表达式类型，专门用于表示结构体对象的构造。它继承自 `MultiArgumentConstructor` 类，能够接受多个参数并将它们组装成一个结构体实例，例如 `Color(red, green, blue, 1)`。该类提供了严格的类型检查机制，确保构造参数的数量和类型与结构体定义完全匹配，并支持自动类型强制转换。作为终结类（`final`），它不允许进一步派生，确保构造语义的一致性。

## 架构位置

`ConstructorStruct` 位于 Skia 的 SkSL 编译器的 IR 表达式层中：

```
skia/
  src/
    sksl/
      ir/
        SkSLIRNode.h                  # IR 节点基类
        SkSLExpression.h              # 表达式基类
        SkSLConstructor.h             # 构造函数基类
          ├─ SingleArgumentConstructor
          └─ MultiArgumentConstructor  # ConstructorStruct 的父类
        SkSLConstructorStruct.h/cpp   # 本文件，结构体构造表达式
        SkSLType.h                    # 类型系统（包含 Field 定义）
      SkSLContext.h                   # 编译上下文
      SkSLErrorReporter.h             # 错误报告
```

在编译流程中的位置：
```
语法分析 → 构造表达式识别 → Convert (类型检查) → Make → IR 节点 → 代码生成
                                    ↓
                            类型强制转换（coerceExpression）
```

## 主要类与结构体

### ConstructorStruct 类

```cpp
class ConstructorStruct final : public MultiArgumentConstructor {
public:
    inline static constexpr Kind kIRNodeKind = Kind::kConstructorStruct;

    // 直接构造函数（内部使用）
    ConstructorStruct(Position pos, const Type& type, ExpressionArray arguments);

    // 类型检查 + 创建（可能失败，返回 nullptr）
    static std::unique_ptr<Expression> Convert(const Context& context,
                                               Position pos,
                                               const Type& type,
                                               ExpressionArray args);

    // 直接创建（假设已通过类型检查，使用断言）
    static std::unique_ptr<Expression> Make(const Context& context,
                                            Position pos,
                                            const Type& type,
                                            ExpressionArray args);

    // 克隆表达式
    std::unique_ptr<Expression> clone(Position pos) const override;

private:
    using INHERITED = MultiArgumentConstructor;
};
```

### 继承层次

```
Expression (基类)
  └─ MultiArgumentConstructor (多参数构造函数基类)
      └─ ConstructorStruct (结构体构造，终结类)
```

`MultiArgumentConstructor` 提供：
- 参数数组管理（`ExpressionArray arguments()`）
- 基本的构造函数接口

## 公共 API 函数

### 构造函数

```cpp
ConstructorStruct(Position pos, const Type& type, ExpressionArray arguments)
```

**功能**: 创建结构体构造表达式对象。

**参数**:
- `pos`: 构造表达式在源代码中的位置
- `type`: 结构体类型（必须是 `isStruct()` 返回 `true` 的类型）
- `arguments`: 构造参数表达式数组

**注意**: 通常不直接调用，而是通过 `Convert` 或 `Make` 工厂方法创建。

### Convert (类型检查工厂)

```cpp
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           const Type& type,
                                           ExpressionArray args)
```

**功能**: 对构造表达式进行完整的类型检查和转换，是创建结构体构造表达式的标准方法。

**参数**:
- `context`: 编译上下文，提供类型系统和错误报告器
- `pos`: 源代码位置
- `type`: 目标结构体类型
- `args`: 构造参数表达式数组（会被修改以进行类型强制）

**类型检查流程**:

1. **结构体验证**: 断言类型是非空结构体（`type.isStruct() && type.fields().size() > 0`）

2. **参数数量检查**:
   - 验证参数数量是否匹配结构体字段数量
   - 不匹配时报错：`"invalid arguments to 'TypeName' constructor (expected N elements, but found M)"`

3. **原子成员检查**:
   - 如果结构体包含原子类型成员，禁止构造
   - 报错：`"construction of struct type 'TypeName' with atomic member is not allowed"`

4. **类型强制转换**:
   - 遍历每个参数，调用 `field.fType->coerceExpression(argument, context)`
   - 尝试将参数转换为对应字段的类型
   - 如果任何转换失败，返回 `nullptr`

5. **创建表达式**: 所有检查通过后，调用 `Make` 创建最终对象

**返回**: 成功返回 `ConstructorStruct` 对象，失败返回 `nullptr` 并报告错误。

### Make (直接创建工厂)

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        ExpressionArray args)
```

**功能**: 直接创建结构体构造表达式，假设所有类型检查已完成。

**断言**:
- `type.isAllowedInES2(context)`: 类型在 ES2 中合法
- `arguments_match_field_types(args, type)`: 参数类型与字段类型完全匹配
- `!type.isOrContainsAtomic()`: 不包含原子类型

**用途**:
- IR 优化传递中创建已知合法的构造表达式
- 跳过重复的类型检查，提高性能

**与 Convert 的区别**:
- `Convert`: 用户代码解析阶段，需要完整错误报告
- `Make`: 编译器内部使用，错误是编译器 bug（使用断言）

### clone

```cpp
std::unique_ptr<Expression> clone(Position pos) const override
```

**功能**: 克隆结构体构造表达式到新位置。

**实现**: 递归克隆参数数组（`arguments().clone()`），保留类型信息。

## 内部实现细节

### 类型强制转换机制

`Convert` 中的核心循环：
```cpp
for (int index = 0; index < args.size(); ++index) {
    std::unique_ptr<Expression>& argument = args[index];
    const Field& field = type.fields()[index];

    // 尝试将参数转换为字段类型
    argument = field.fType->coerceExpression(std::move(argument), context);
    if (!argument) {
        return nullptr;  // 转换失败
    }
}
```

**`coerceExpression` 的作用**:
- 自动类型提升（如 `int` → `float`）
- 隐式类型转换（如 `vec2` → `vec3` 通过补零）
- 报告不兼容类型的错误

### 参数类型匹配验证

辅助函数 `arguments_match_field_types` 在 `Make` 中用于断言：
```cpp
static bool arguments_match_field_types(const ExpressionArray& args, const Type& type) {
    SkASSERT(type.fields().size() == SkToSizeT(args.size()));

    for (int index = 0; index < args.size(); ++index) {
        const std::unique_ptr<Expression>& argument = args[index];
        const Field& field = type.fields()[index];
        if (!argument->type().matches(*field.fType)) {
            return false;
        }
    }
    return true;
}
```

**标记为 `maybe_unused`**: 在发布构建中，断言被移除，函数未使用。

### 原子类型限制

原子类型（如 `atomic_uint`）不能作为结构体成员参与构造：
```cpp
if (type.isOrContainsAtomic()) {
    context.fErrors->error(pos, "construction of struct type '...' with atomic member is not allowed");
    return nullptr;
}
```

**原因**:
- 原子类型需要特殊的初始化语义
- GLSL/SPIR-V 标准不支持原子类型的值构造
- 避免运行时未定义行为

### ES2 兼容性检查

`Make` 中断言 `type.isAllowedInES2(context)`：
- 确保生成的代码可以在 OpenGL ES 2.0 环境中运行
- 某些高级结构体特性可能不被旧版本支持

## 依赖关系

### 直接依赖

**头文件**:
- `SkSLConstructor.h`: 提供 `MultiArgumentConstructor` 基类
- `SkSLExpression.h`: 表达式接口
- `SkSLType.h`: 类型系统和 `Field` 定义
- `SkSLDefines.h`: `ExpressionArray` 类型定义

**实现文件额外依赖**:
- `SkSLContext.h`: 编译上下文
- `SkSLErrorReporter.h`: 错误报告
- `SkSLString.h`: 字符串格式化工具
- `SkSpan.h`: 数组视图
- `SkTArray.h`: 动态数组

### 被依赖关系

- **语法分析器**: 解析结构体字面量时创建 `ConstructorStruct`
- **类型推断系统**: 根据上下文确定结构体构造的目标类型
- **代码生成器**: 将结构体构造转换为目标语言语法（GLSL, Metal, SPIR-V）

### 相关构造函数类型

- `ConstructorArray`: 数组构造
- `ConstructorCompound`: 复合向量/矩阵构造
- `ConstructorDiagonalMatrix`: 对角矩阵构造

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式**: 提供 `Convert` 和 `Make` 两种创建策略
2. **模板方法模式**: 继承 `MultiArgumentConstructor` 的通用构造逻辑
3. **策略模式**: 通过 `Type` 对象决定字段类型和验证规则

### 设计决策

**为什么区分 `Convert` 和 `Make`？**
- `Convert`: 面向用户代码，需要友好的错误消息
- `Make`: 编译器内部使用，性能优先，使用断言捕获 bug
- 清晰分离职责，避免重复检查

**为什么禁止原子类型成员的构造？**
- 原子类型的初始值必须在运行时通过特殊操作设置
- 着色器语言标准不支持原子类型的值初始化
- 避免生成不可移植的代码

**为什么使用类型强制而非严格匹配？**
- 提升用户体验（如允许 `MyStruct(1, 2.0)` 而非强制 `MyStruct(1.0, 2.0)`）
- 符合着色器语言的隐式转换规则
- 减少手动类型转换的冗余代码

**为什么是终结类（`final`）？**
- 结构体构造语义明确，不需要进一步特化
- 防止意外继承导致的语义混淆
- 编译器优化机会（虚函数调用可能去虚化）

**为什么克隆需要递归克隆参数？**
- 参数表达式可能被多处引用，克隆确保独立性
- IR 优化可能修改表达式，需要隔离副作用

## 性能考量

### 类型检查开销

`Convert` 方法的主要开销：
1. **参数数量比较**: O(1)
2. **原子类型检查**: O(字段数) - 可能遍历嵌套结构体
3. **类型强制转换**: O(参数数) × O(转换成本)
   - 简单转换（如 `int` → `float`）: 创建 `Constructor` 节点
   - 复杂转换（如向量扩展）: 可能创建多个中间节点

**优化**: 大多数结构体字段数很少（<10），开销可接受。

### 内存占用

单个 `ConstructorStruct` 对象：
- `MultiArgumentConstructor` 基类: ~24 字节（虚表 + 位置 + 类型 + 参数数组指针）
- 参数数组: 24 字节（vector 开销） + N × 8 字节（指针）
- **总计**: ~48 + 8N 字节（N 为字段数）

### 克隆成本

`clone` 递归克隆所有参数表达式：
- 浅层参数（字面量）: O(N) 时间和空间
- 深层参数（嵌套表达式）: O(N × M) （M 为表达式树深度）

### 潜在瓶颈

- **深层嵌套结构体**: 原子类型检查需要递归遍历
- **大量字段**: 类型强制转换的累积开销
- **频繁克隆**: 大型结构体构造的克隆成本高

## 相关文件

### 核心相关文件

- **src/sksl/ir/SkSLConstructor.h**: 构造函数基类
- **src/sksl/ir/SkSLExpression.h**: 表达式基类
- **src/sksl/ir/SkSLType.h**: 类型系统和字段定义
- **src/sksl/SkSLContext.h**: 编译上下文

### 其他构造函数类型

- **src/sksl/ir/SkSLConstructorArray.h**: 数组构造
- **src/sksl/ir/SkSLConstructorCompound.h**: 向量/矩阵构造
- **src/sksl/ir/SkSLConstructorDiagonalMatrix.h**: 对角矩阵构造

### 代码生成相关

- **src/sksl/codegen/SkSLGLSLCodeGenerator.cpp**: GLSL 代码生成
- **src/sksl/codegen/SkSLMetalCodeGenerator.cpp**: Metal 代码生成
- **src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp**: SPIR-V 代码生成

### 使用示例

```cpp
// 用户代码: struct Color { float r, g, b, a; };
// 构造表达式: Color(1.0, 0.5, 0.0, 1.0)

// 解析阶段
auto args = parseArguments();  // [Literal(1.0), Literal(0.5), Literal(0.0), Literal(1.0)]
auto ctor = ConstructorStruct::Convert(context, pos, colorType, std::move(args));

// IR 优化阶段（已知类型正确）
auto optimizedCtor = ConstructorStruct::Make(context, pos, colorType, std::move(validArgs));
```
