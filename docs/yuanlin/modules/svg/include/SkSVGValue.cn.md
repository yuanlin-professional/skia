# SkSVGValue

> 源文件: modules/svg/include/SkSVGValue.h

## 概述

`SkSVGValue` 是 Skia SVG 模块中的核心类型系统基类，用于表示 SVG 属性值的多态类型体系。该类提供了一个类型安全的包装器框架，允许不同类型的 SVG 属性值（如颜色、长度、变换、数字等）使用统一的接口进行处理和访问。通过模板类 `SkSVGWrapperValue`，该系统实现了对各种 SVG 基础类型的封装，同时保持了类型安全性和运行时类型识别能力。

## 架构位置

`SkSVGValue` 位于 Skia 的 SVG 模块中，作为属性值类型系统的基础抽象层：

- **模块路径**: `modules/svg/include/`
- **类层次**: 作为所有 SVG 值类型的基类，通过 `SkNoncopyable` 禁止拷贝
- **依赖关系**: 被 SVG 节点属性系统广泛使用，为属性解析和渲染提供类型支持
- **角色定位**: 类型系统基础设施，提供运行时类型识别（RTTI）和类型安全访问

在 SVG 架构中，`SkSVGValue` 处于类型层，为上层的节点属性管理和下层的具体类型实现提供桥接。

## 主要类与结构体

### SkSVGValue 基类

不可拷贝的抽象基类，定义了 SVG 值类型系统的基本接口：

```cpp
class SK_API SkSVGValue : public SkNoncopyable {
public:
    enum class Type {
        kColor,                      // 颜色类型
        kFilter,                     // 滤镜引用
        kLength,                     // 长度值
        kNumber,                     // 数字类型
        kObjectBoundingBoxUnits,     // 对象边界框单位
        kPreserveAspectRatio,        // 宽高比保持策略
        kStopColor,                  // 渐变停止颜色
        kString,                     // 字符串类型
        kTransform,                  // 变换矩阵
        kViewBox,                    // 视图框
    };

    Type type() const;               // 获取运行时类型
    template <typename T> const T* as() const;  // 类型安全转换
};
```

**类型枚举**: `Type` 枚举定义了所有支持的 SVG 值类型，涵盖了 SVG 规范中常用的属性值类别。

### SkSVGWrapperValue 模板类

栈上分配的包装器模板，用于封装具体的 SVG 类型：

```cpp
template <typename T, SkSVGValue::Type ValueType>
class SK_API SkSVGWrapperValue final : public SkSVGValue {
public:
    static constexpr Type TYPE = ValueType;

    explicit SkSVGWrapperValue(const T& v);
    operator const T&() const;       // 自动转换为被包装类型
    const T* operator->() const;     // 指针访问操作符

private:
    void* operator new(size_t) = delete;  // 禁止堆分配
    const T& fWrappedValue;          // 引用语义，轻量级包装
};
```

**设计特点**:
- **栈上分配**: 通过删除 `new` 操作符强制栈分配，避免堆内存开销
- **引用语义**: 内部存储引用而非拷贝，减少数据复制
- **类型安全**: 编译期绑定类型标识，支持高效的运行时类型检查

### 类型别名定义

为常用 SVG 类型提供了便捷的别名：

```cpp
using SkSVGColorValue        = SkSVGWrapperValue<SkSVGColorType, Type::kColor>;
using SkSVGLengthValue       = SkSVGWrapperValue<SkSVGLength, Type::kLength>;
using SkSVGTransformValue    = SkSVGWrapperValue<SkSVGTransformType, Type::kTransform>;
using SkSVGViewBoxValue      = SkSVGWrapperValue<SkSVGViewBoxType, Type::kViewBox>;
using SkSVGNumberValue       = SkSVGWrapperValue<SkSVGNumberType, Type::kNumber>;
using SkSVGStringValue       = SkSVGWrapperValue<SkSVGStringType, Type::kString>;
using SkSVGStopColorValue    = SkSVGWrapperValue<SkSVGStopColor, Type::kStopColor>;
using SkSVGPreserveAspectRatioValue = SkSVGWrapperValue<SkSVGPreserveAspectRatio, Type::kPreserveAspectRatio>;
using SkSVGObjectBoundingBoxUnitsValue = SkSVGWrapperValue<SkSVGObjectBoundingBoxUnits, Type::kObjectBoundingBoxUnits>;
```

这些别名简化了代码中对特定类型包装器的使用。

## 公共 API 函数

### Type type() const

获取值对象的运行时类型标识。

**返回值**: `Type` 枚举值，指示当前对象封装的数据类型。

**用途**: 用于运行时类型判断和条件分支，例如在属性设置时根据类型选择处理逻辑。

### template <typename T> const T* as() const

类型安全的向下转换方法，尝试将基类指针转换为特定派生类型。

**模板参数**: `T` 目标包装器类型，必须定义 `TYPE` 常量。

**返回值**: 如果类型匹配返回指向 `T` 的指针，否则返回 `nullptr`。

**实现机制**: 通过比较 `fType` 与 `T::TYPE` 进行编译期类型检查。

**使用示例**:
```cpp
const SkSVGValue* value = ...;
if (auto* lengthValue = value->as<SkSVGLengthValue>()) {
    float resolved = lengthValue->resolve(...);
}
```

### SkSVGWrapperValue 构造与访问

**构造函数**: `explicit SkSVGWrapperValue(const T& v)` 接受常量引用，避免不必要的拷贝。

**类型转换操作符**: `operator const T&()` 允许隐式转换回被包装类型，简化使用代码。

**指针访问**: `operator->()` 支持像指针一样访问被包装对象的成员。

## 内部实现细节

### 类型标识机制

每个 `SkSVGValue` 实例在构造时存储一个 `Type` 枚举值：

```cpp
Type fType;
```

该字段在基类构造函数中初始化，并在整个对象生命周期内保持不变。派生类通过模板参数 `ValueType` 将类型信息传递给基类。

### 栈分配约束

通过删除堆分配操作符实现强制栈分配：

```cpp
void* operator new(size_t) = delete;
void* operator new(size_t, void*) = delete;
```

这种设计确保了包装器对象的生命周期短暂且可预测，避免了内存管理的复杂性。由于包装器仅存储引用，其生命周期必须短于被引用对象，栈分配保证了这一约束。

### 引用语义实现

`fWrappedValue` 成员使用常量引用：

```cpp
const T& fWrappedValue;
```

这意味着包装器不拥有数据，只是提供了一个带类型信息的访问层。这种设计适用于临时转换场景，例如在属性设置过程中将类型化值传递给通用接口。

### 类型安全转换

`as<T>()` 方法利用编译期常量进行类型匹配：

```cpp
return fType == T::TYPE ? static_cast<const T*>(this) : nullptr;
```

由于 `T::TYPE` 是编译期常量，该检查非常高效。如果类型匹配，使用 `static_cast` 进行零开销转换。

## 依赖关系

### 核心依赖

- **SkNoncopyable**: 提供不可拷贝语义的基类
- **SkSVGTypes.h**: 定义具体的 SVG 类型（如 `SkSVGLength`、`SkSVGColorType` 等）
- **SkColor.h**: 颜色类型支持
- **SkMatrix.h**: 变换矩阵支持
- **SkPath.h**: 路径类型支持

### 被依赖模块

- **SVG 节点属性系统**: 使用 `SkSVGValue` 作为属性值的通用表示
- **属性解析器**: 解析 XML 属性后创建相应的包装器对象
- **渲染上下文**: 在渲染时提取和使用具体类型的值

### 数据流

1. **解析阶段**: 属性解析器将字符串解析为具体类型（如 `SkSVGLength`）
2. **包装阶段**: 创建栈上的 `SkSVGWrapperValue` 实例
3. **传递阶段**: 通过 `SkSVGValue*` 基类指针传递给通用设置接口
4. **提取阶段**: 接收方使用 `as<T>()` 恢复具体类型并访问数据

## 设计模式与设计决策

### 类型擦除模式（Type Erasure）

`SkSVGValue` 系统实现了一种轻量级的类型擦除模式：

- **统一接口**: 基类提供类型无关的接口
- **类型恢复**: 通过 `as<T>()` 恢复具体类型
- **运行时识别**: 使用枚举而非 RTTI，减少开销

这种模式允许在不使用虚函数的情况下实现多态，适合性能敏感的图形渲染场景。

### 值语义与引用语义混合

- **基类**: 不可拷贝，强制通过指针或引用传递
- **包装器**: 存储引用，轻量级且生命周期短暂
- **被包装类型**: 通常具有值语义，可以独立存在

这种混合策略平衡了性能和易用性。

### 栈分配约束

强制栈分配的设计决策基于以下考虑：

1. **性能**: 避免堆分配和析构开销
2. **生命周期**: 包装器仅用于临时转换，不需要长期存在
3. **安全性**: 防止误用导致的悬挂引用

### 编译期类型绑定

通过模板参数和 `static constexpr` 将类型信息绑定到编译期：

```cpp
static constexpr Type TYPE = ValueType;
```

这使得类型检查可以在编译期优化，同时保留运行时类型识别能力。

## 性能考量

### 零开销抽象

- **无虚函数**: 避免虚函数表查找开销
- **内联友好**: 简单方法易于内联优化
- **栈分配**: 消除堆分配和释放成本

### 缓存友好性

包装器对象非常小（仅包含一个 `Type` 枚举和一个引用），可以高效地存储在栈或寄存器中。

### 类型检查开销

`as<T>()` 方法的类型检查是一个简单的整数比较，通常被优化为单条 CPU 指令。在类型已知的情况下，编译器可能完全消除该检查。

### 引用语义的权衡

虽然引用语义避免了拷贝，但要求被引用对象在包装器生命周期内保持有效。这限制了包装器的使用场景，但对于属性设置等短暂操作是合理的。

## 相关文件

### 核心类型定义

- **modules/svg/include/SkSVGTypes.h**: 定义 `SkSVGLength`、`SkSVGColorType`、`SkSVGTransformType` 等被包装的具体类型
- **modules/svg/include/SkSVGNode.h**: SVG 节点基类，使用 `SkSVGValue` 系统管理属性

### 属性系统

- **modules/svg/include/SkSVGAttribute.h**: 属性容器，存储和管理 SVG 属性值
- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析器，将字符串解析为类型化的 `SkSVGValue` 对象

### 渲染上下文

- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文，在渲染时访问和使用属性值

### 实现文件

- **modules/svg/src/SkSVGValue.cpp**: 基类的实现细节（如果有运行时逻辑）

### 使用示例

- **modules/svg/src/SkSVGDOM.cpp**: SVG DOM 构建过程中使用属性值系统
- **modules/svg/src/SkSVGNode.cpp**: 节点属性设置和访问的具体实现

该文件是 SVG 模块类型系统的核心，为整个属性管理框架提供了类型安全和性能保证。
