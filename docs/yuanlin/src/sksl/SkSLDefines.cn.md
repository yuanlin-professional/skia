# SkSLDefines — SkSL 编译器基础类型和常量定义

> 源文件：[`src/sksl/SkSLDefines.h`](../../src/sksl/SkSLDefines.h)

## 概述

SkSLDefines.h 定义了 SkSL 编译器使用的基础类型别名、容器类型和编译器常量。它为 SkSL 编译器建立了 IR（中间表示）节点的基本类型系统基础设施，包括表达式数组、语句数组、内联阈值和变量槽位限制。

该文件 47 行，是一个简洁的基础定义文件。

## 架构位置

```
SkSL 编译器基础设施
  └── SkSLDefines.h（基础类型和常量）
        ├── SKSL_INT / SKSL_FLOAT — 数值类型别名
        ├── ExpressionArray — 表达式容器
        ├── StatementArray — 语句容器
        └── kDefaultInlineThreshold / kVariableSlotLimit — 编译器常量
```

此文件被 SkSL 编译器的几乎所有模块间接引用，是最基础的定义文件之一。

## 主要类与结构体

### 类型别名

```cpp
using SKSL_INT = int64_t;    // SkSL 整数字面量的 C++ 表示类型
using SKSL_FLOAT = float;    // SkSL 浮点字面量的 C++ 表示类型
```

- `SKSL_INT` 使用 `int64_t` 以容纳 SkSL 整数字面量的完整范围
- `SKSL_FLOAT` 使用 `float`（32 位）

### `ExpressionArray`

```cpp
class ExpressionArray : public skia_private::STArray<2, std::unique_ptr<Expression>> {
public:
    using STArray::STArray;
    ExpressionArray clone() const;
};
```

- 继承自 `skia_private::STArray<2, ...>`，内联存储 2 个元素
- 存储 `std::unique_ptr<Expression>`，拥有表达式节点的所有权
- 提供 `clone()` 方法用于深拷贝整个数组

### `StatementArray`

```cpp
using StatementArray = skia_private::STArray<2, std::unique_ptr<Statement>>;
```

- 类型别名，与 `ExpressionArray` 类似但不提供 `clone()` 方法

### 常量

```cpp
static constexpr int kDefaultInlineThreshold = 50;
static constexpr int kVariableSlotLimit = 100000;
```

- `kDefaultInlineThreshold`：内联阈值，IR 节点数超过此值的函数不会被内联。该值乘以调用次数来计算总代码膨胀量。
- `kVariableSlotLimit`：函数/全局作用域中允许的最大变量槽位数。防止代码生成占用无限时间或空间。

## 公共 API 函数

```cpp
ExpressionArray clone() const;
```
- 返回包含每个表达式深拷贝的新数组
- 声明在此，实现在其他编译单元中

## 内部实现细节

### STArray 的内联存储

`ExpressionArray` 和 `StatementArray` 使用 `STArray<2, ...>`，这意味着前 2 个元素存储在对象自身的内存中（栈上），避免堆分配。大多数 SkSL IR 节点的子表达式/子语句数量很少（例如二元运算只有 2 个操作数），因此内联存储可以覆盖大部分情况。

### 前向声明

文件对 `Expression` 和 `Statement` 类进行了前向声明，避免包含完整的 IR 节点头文件，减少编译依赖。

## 依赖关系

- `<cstdint>` — `int64_t` 类型
- `include/core/SkTypes.h` — Skia 基础类型
- `include/private/base/SkTArray.h` — `skia_private::STArray` 模板

## 设计模式与设计决策

- **类型别名集中管理**：将 SkSL 的数值类型映射集中在一处定义，便于全局修改。
- **内联小数组**：使用 `STArray<2, ...>` 的小缓冲区优化，适配 IR 节点典型的低子节点数量。
- **安全限制常量**：`kVariableSlotLimit` 防止恶意或错误的着色器代码导致编译器资源耗尽。
- **前向声明**：最小化头文件依赖，加速编译。

## 性能考量

1. **内联存储**：`STArray<2, ...>` 避免了大量小数组的堆分配开销。
2. **内联阈值**：`kDefaultInlineThreshold = 50` 是经验值，在内联带来的性能提升和代码膨胀之间取得平衡。
3. **变量槽位限制**：`kVariableSlotLimit = 100000` 防止极端着色器导致的编译时间爆炸。

## 相关文件

- `src/sksl/ir/SkSLExpression.h` — Expression 基类
- `src/sksl/ir/SkSLStatement.h` — Statement 基类
- `src/sksl/SkSLProgramSettings.h` — 引用 `kDefaultInlineThreshold`
- `include/private/base/SkTArray.h` — STArray 模板实现
