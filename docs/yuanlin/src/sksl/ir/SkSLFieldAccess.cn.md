# SkSLFieldAccess

> 源文件: src/sksl/ir/SkSLFieldAccess.h, src/sksl/ir/SkSLFieldAccess.cpp

## 概述

`FieldAccess` 是 SkSL IR 中表示字段访问表达式的节点类，用于从结构体或对象中提取特定字段，例如 `foo.bar` 这样的表达式。该类继承自 `Expression`，提供了对结构体成员访问的完整语义支持，包括普通结构体字段访问、匿名接口块字段访问以及效果子对象的方法引用。

作为 SkSL 编译器 IR 层的核心组件，`FieldAccess` 负责将源代码中的字段访问操作转换为可优化的中间表示形式，支持常量折叠、表达式简化等编译器优化。它还处理特殊情况，如 `sk_Caps` 访问会转换为 `Setting` 节点，效果子对象的字段访问会转换为 `MethodReference` 节点。

## 架构位置

`FieldAccess` 位于 Skia 图形库的 SkSL 着色器语言编译器的中间表示（IR）层：

- **模块位置**: `src/sksl/ir/` - SkSL 中间表示节点定义目录
- **继承关系**: `FieldAccess` → `Expression` → `IRNode`
- **编译流程**: Parser → AST → IR（FieldAccess） → 优化 → 代码生成
- **依赖层次**:
  - 向上依赖: `Context`、`Type`、`SymbolTable`
  - 向下被用于: 代码生成器、优化器、分析工具
  - 平级关系: 与 `IndexExpression`、`ConstructorStruct` 等表达式节点并列

## 主要类与结构体

### FieldAccessOwnerKind 枚举
```cpp
enum class FieldAccessOwnerKind : int8_t {
    kDefault,
    kAnonymousInterfaceBlock
};
```
定义字段访问的所有者类型：
- `kDefault`: 普通结构体字段访问
- `kAnonymousInterfaceBlock`: 匿名接口块字段访问（GLSL 中仅需输出字段名）

### FieldAccess 类
```cpp
class FieldAccess final : public Expression {
public:
    using OwnerKind = FieldAccessOwnerKind;
    inline static constexpr Kind kIRNodeKind = Kind::kFieldAccess;

private:
    int fFieldIndex;                           // 字段在结构体中的索引
    FieldAccessOwnerKind fOwnerKind;           // 所有者类型
    std::unique_ptr<Expression> fBase;         // 基础表达式（被访问的对象）
};
```

核心职责：
- 存储字段访问的基础表达式和字段索引
- 区分不同类型的字段访问（普通/匿名接口块）
- 支持表达式克隆和描述生成

## 公共 API 函数

### 静态构造函数

#### Convert
```cpp
static std::unique_ptr<Expression> Convert(
    const Context& context,
    Position pos,
    std::unique_ptr<Expression> base,
    std::string_view field);
```
将字段名转换为 `FieldAccess` 表达式：
- 处理效果子对象，将字段转换为方法引用（`$` 前缀）
- 在结构体字段中查找匹配的字段名
- 处理 `sk_Caps` 特殊情况，转换为 `Setting` 节点
- 错误处理：通过 `ErrorReporter` 报告字段不存在错误

#### Make
```cpp
static std::unique_ptr<Expression> Make(
    const Context& context,
    Position pos,
    std::unique_ptr<Expression> base,
    int fieldIndex,
    OwnerKind ownerKind = OwnerKind::kDefault);
```
直接创建 `FieldAccess` 表达式（使用 ASSERT 进行错误检查）：
- 验证字段索引有效性
- 尝试常量折叠优化：如果基础表达式是 `ConstructorStruct`，直接提取字段值
- 仅在优化失败或有副作用时创建 `FieldAccess` 节点

### 访问器函数

```cpp
std::unique_ptr<Expression>& base();              // 获取基础表达式（可修改）
const std::unique_ptr<Expression>& base() const;  // 获取基础表达式（只读）
int fieldIndex() const;                           // 获取字段索引
OwnerKind ownerKind() const;                      // 获取所有者类型
```

### 工具函数

#### initialSlot
```cpp
size_t initialSlot() const;
```
计算字段在统一存储布局中的起始槽位，遍历前序字段累加槽位数量。

#### description
```cpp
std::string description(OperatorPrecedence) const override;
```
生成字段访问的字符串描述，格式为 `base.fieldName`。

#### clone
```cpp
std::unique_ptr<Expression> clone(Position pos) const override;
```
深度克隆字段访问表达式，包括基础表达式和所有属性。

## 内部实现细节

### 字段查找机制

在 `Convert` 函数中实现三种不同的字段解析策略：

1. **效果子对象处理**：
   - 检测 `baseType.isEffectChild()`
   - 将字段名转换为方法名（添加 `$` 前缀）
   - 在符号表中查找对应的函数声明
   - 创建 `MethodReference` 而非 `FieldAccess`

2. **结构体字段查找**：
   - 遍历 `baseType.fields()` 中的所有字段
   - 按名称匹配字段
   - 找到后调用 `Make` 创建访问节点

3. **特殊类型处理**：
   - 检测 `sk_Caps` 类型
   - 转换为 `Setting::Convert` 调用

### 常量折叠优化

`extract_field` 静态函数实现编译时优化：
```cpp
static std::unique_ptr<Expression> extract_field(
    Position pos,
    const ConstructorStruct& ctor,
    int fieldIndex)
```
- 检查结构体构造器中所有字段是否无副作用
- 如果安全，直接返回目标字段的克隆
- 避免运行时字段访问开销

应用场景：
```glsl
struct S { float a; float b; };
const S s = S(1.0, 2.0);
float x = s.a;  // 直接优化为 1.0
```

### 槽位计算

`initialSlot` 函数计算字段在展平的存储布局中的位置：
- 遍历字段索引之前的所有字段
- 累加每个字段的 `slotCount()`
- 支持嵌套结构体和数组的槽位计算

示例：
```glsl
struct S {
    float a;      // 槽位 0
    vec3 b;       // 槽位 1-3
    float c;      // 槽位 4
}
S s;
s.c;  // initialSlot() 返回 4
```

### 描述生成

`description` 函数生成人类可读的表达式字符串：
- 递归调用基础表达式的 `description`，传递 `kPostfix` 优先级
- 添加 `.` 分隔符
- 附加字段名（从类型信息中获取）
- 处理空基础表达式的边界情况

## 依赖关系

### 头文件依赖

**核心依赖**：
- `SkSLExpression.h` - 表达式基类
- `SkSLType.h` - 类型系统，提供字段信息
- `SkSLIRNode.h` - IR 节点基类

**功能依赖**：
- `SkSLContext.h` - 编译上下文
- `SkSLSymbolTable.h` - 符号查找
- `SkSLConstantFolder.h` - 常量折叠
- `SkSLAnalysis.h` - 副作用分析

**关联节点**：
- `SkSLConstructorStruct.h` - 结构体构造器
- `SkSLMethodReference.h` - 方法引用
- `SkSLSetting.h` - 编译器设置访问

### 运行时依赖

- **类型系统**: 依赖 `Type::fields()` 获取字段信息
- **符号表**: 查找效果子对象的方法声明
- **常量折叠器**: 获取基础表达式的常量值
- **分析工具**: 检测副作用以决定是否可以优化

## 设计模式与设计决策

### 工厂模式

提供两个静态工厂方法：
- `Convert`: 面向用户输入，执行完整验证和错误报告
- `Make`: 面向编译器内部，使用断言检查，性能更高

设计原因：
- 分离用户错误和编译器错误的处理路径
- `Convert` 可以返回不同类型的节点（`MethodReference`、`Setting`）
- `Make` 保证创建纯粹的 `FieldAccess` 节点

### 优化优先设计

在 `Make` 函数中首先尝试常量折叠：
```cpp
const Expression* expr = ConstantFolder::GetConstantValueForVariable(*base);
if (expr->is<ConstructorStruct>()) {
    if (std::unique_ptr<Expression> field = extract_field(...)) {
        return field;  // 直接返回字段值
    }
}
```
设计决策：
- 在创建节点时就进行优化，避免后续优化遍历
- 仅在无副作用时优化，保证语义正确性
- 简化后续编译阶段的工作负担

### 类型安全

使用强类型枚举 `FieldAccessOwnerKind`：
- 避免 `int` 或 `bool` 的语义不明确
- `int8_t` 节省内存（每个节点仅占 1 字节）
- 为未来扩展留出空间（如添加新的所有者类型）

### 不可变设计

字段索引和所有者类型在构造后不可修改：
- 简化并发访问（只读数据）
- 避免节点状态不一致
- 符合函数式编程范式

## 性能考量

### 内存布局优化

```cpp
int fFieldIndex;                    // 4 字节
FieldAccessOwnerKind fOwnerKind;    // 1 字节
// 3 字节填充
std::unique_ptr<Expression> fBase;  // 8 字节
```
总大小：约 16 字节（加上 `Expression` 基类）

优化策略：
- 使用 `int8_t` 枚举减少内存占用
- 字段顺序考虑对齐以减少填充

### 常量折叠

编译时优化减少运行时开销：
- 结构体字面量的字段访问完全消除
- 避免不必要的 IR 节点创建
- 副作用检查确保优化安全性

### 槽位计算缓存

`initialSlot` 不缓存结果，因为：
- 计算成本低（小规模循环）
- 缓存会增加内存占用
- 调用频率不高（仅在代码生成阶段）

### 字符串生成延迟

`description` 按需生成字符串：
- 避免在正常编译流程中的开销
- 仅在错误报告和调试时调用
- 使用递归生成，支持复杂嵌套表达式

## 相关文件

### 同级 IR 节点
- `src/sksl/ir/SkSLIndexExpression.h/cpp` - 数组索引表达式
- `src/sksl/ir/SkSLSwizzle.h/cpp` - 向量分量访问
- `src/sksl/ir/SkSLConstructorStruct.h/cpp` - 结构体构造器

### 依赖的核心组件
- `src/sksl/SkSLContext.h` - 编译上下文
- `src/sksl/ir/SkSLType.h/cpp` - 类型系统
- `src/sksl/ir/SkSLSymbolTable.h/cpp` - 符号表
- `src/sksl/SkSLConstantFolder.h` - 常量折叠
- `src/sksl/SkSLAnalysis.h` - 程序分析

### 特殊节点转换
- `src/sksl/ir/SkSLMethodReference.h` - 效果子对象方法引用
- `src/sksl/ir/SkSLSetting.h/cpp` - 编译器设置访问

### 使用场景
- `src/sksl/SkSLCompiler.cpp` - 编译器主流程
- `src/sksl/codegen/` - 各种后端代码生成器
- `src/sksl/transform/` - IR 变换和优化器
