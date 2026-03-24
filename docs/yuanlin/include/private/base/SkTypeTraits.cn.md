# SkTypeTraits

> 源文件: `include/private/base/SkTypeTraits.h`

## 概述

SkTypeTraits 提供了类型特征检测工具，特别是定义了"可平凡重定位"（trivially relocatable）的类型特征。该特征用于容器优化，允许通过 memcpy 移动对象而无需调用移动构造函数和析构函数，从而显著提升容器操作（如 resize、realloc）的性能。

## 架构位置

本模块位于 Skia 的私有基础设施层，属于 C++ 元编程工具集。它为 Skia 的容器类（如 SkTArray、SkTDArray）提供类型特征信息，使容器能够针对不同类型选择最优的实现策略。

## 主要类型特征

### sk_has_trivially_relocatable_member

```cpp
template<typename, typename = void>
struct sk_has_trivially_relocatable_member : std::false_type {};

template<typename T>
struct sk_has_trivially_relocatable_member<T, std::void_t<typename T::sk_is_trivially_relocatable>>
        : T::sk_is_trivially_relocatable {};
```

- **功能**: 检测类型 T 是否声明了 `sk_is_trivially_relocatable` 成员类型
- **默认情况**: 继承自 `std::false_type`（值为 false）
- **特化情况**: 如果 T 有 `sk_is_trivially_relocatable` 成员，继承自该成员的值
- **用途**: 允许类型通过成员类型声明自己是可平凡重定位的

**使用方式**：
```cpp
class MyType {
public:
    using sk_is_trivially_relocatable = std::true_type;
    // ...
};
```

### sk_is_trivially_relocatable

```cpp
template <typename T>
struct sk_is_trivially_relocatable
        : std::disjunction<std::is_trivially_copyable<T>, sk_has_trivially_relocatable_member<T>>{};
```

- **功能**: 判断类型 T 是否可平凡重定位
- **条件**: 满足以下任一条件即为 true
  1. `std::is_trivially_copyable<T>` 为 true（C++ 标准定义的可平凡拷贝类型）
  2. `sk_has_trivially_relocatable_member<T>` 为 true（显式声明）
- **用途**: 容器类使用此特征决定是否可以用 memcpy 移动对象

### sk_is_trivially_relocatable (unique_ptr 特化)

```cpp
template <typename T>
struct sk_is_trivially_relocatable<std::unique_ptr<T>> : std::true_type {};
```

- **功能**: 将所有 `std::unique_ptr<T>` 标记为可平凡重定位
- **原理**: unique_ptr 通常只包含一个指针，移动它等价于拷贝指针值
- **警告**: 这依赖于所有合理的 unique_ptr 实现的假设，技术上不受 C++ 标准保证
- **注释**: "Here be some dragons"（这里有龙）暗示了一定的风险

### sk_is_trivially_relocatable_v

```cpp
template <typename T>
inline constexpr bool sk_is_trivially_relocatable_v = sk_is_trivially_relocatable<T>::value;
```

- **功能**: 提供便捷的变量模板访问
- **用途**: 简化语法，使用 `sk_is_trivially_relocatable_v<T>` 代替 `sk_is_trivially_relocatable<T>::value`
- **C++17 风格**: 遵循标准库的命名约定（如 `std::is_same_v`）

## 可平凡重定位概念

### 定义

类型 T 是可平凡重定位的，当且仅当可以通过以下步骤移动对象：

1. 将源对象的字节内容 memcpy 到目标位置
2. 不调用源对象的析构函数
3. 不调用目标对象的构造函数

### 等价于

```cpp
// 传统移动
T* dest = new (memory) T(std::move(*source));
source->~T();

// 平凡重定位
memcpy(memory, source, sizeof(T));
```

### 合法条件

类型可平凡重定位需要满足：
- 不包含自引用指针（指向对象自身成员的指针）
- 不依赖对象的地址（如不在全局表中注册地址）
- 移动构造和析构的组合效果等价于 memcpy

### 常见可平凡重定位类型

- 所有平凡类型（POD）
- 标准库智能指针（std::unique_ptr、std::shared_ptr）
- 简单的 RAII 包装器（只包含指针或句柄）
- Skia 的大部分值类型（如 SkString、SkPath）

### 常见不可平凡重定位类型

- 包含自引用的类（如侵入式链表节点）
- 在构造时注册地址的类
- 使用 placement new 的复杂类

## 内部实现细节

### SFINAE 技巧

使用 `std::void_t` 实现 SFINAE（Substitution Failure Is Not An Error）：

```cpp
template<typename T>
struct sk_has_trivially_relocatable_member<T, std::void_t<typename T::sk_is_trivially_relocatable>>
```

- 如果 `T::sk_is_trivially_relocatable` 不存在，SFINAE 导致此特化被丢弃
- 回退到主模板（返回 false）
- 如果存在，使用此特化（返回成员的值）

### std::disjunction

使用 C++17 的 `std::disjunction` 实现逻辑或：

```cpp
std::disjunction<std::is_trivially_copyable<T>, sk_has_trivially_relocatable_member<T>>
```

- 短路求值：如果第一个条件为 true，不评估第二个
- 继承自第一个为 true 的类型，或最后一个类型

### 特化优先级

模板特化优先于主模板，因此 unique_ptr 的特化会优先匹配。

## 容器优化应用

### resize 操作

```cpp
template <typename T>
void resize(size_t newSize) {
    if constexpr (sk_is_trivially_relocatable_v<T>) {
        // 快速路径：使用 realloc 或 memcpy
        T* newData = realloc(fData, newSize * sizeof(T));
    } else {
        // 慢速路径：逐个移动对象
        T* newData = allocate(newSize);
        for (size_t i = 0; i < oldSize; ++i) {
            new (&newData[i]) T(std::move(fData[i]));
            fData[i].~T();
        }
    }
}
```

### insert 操作

可平凡重定位类型可以使用 memmove 移动元素，而无需调用移动构造函数。

### 性能提升

对于可平凡重定位类型，容器操作可以提速数倍甚至数十倍。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| &lt;memory&gt; | std::unique_ptr |
| &lt;type_traits&gt; | 标准类型特征 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkTArray.h | 使用可平凡重定位优化 |
| SkTDArray.h | 使用可平凡重定位优化 |
| SkArenaAlloc.h | 内存池分配优化 |
| 所有 Skia 容器 | 受益于类型特征 |

## 设计模式与设计决策

### 渐进式特性采用

通过 `sk_has_trivially_relocatable_member` 检测，允许类型逐步添加优化标记，而不破坏现有代码。

### 安全默认值

默认情况下，类型被视为不可平凡重定位，只有在确认安全后才显式标记。

### 实用主义

unique_ptr 的特化虽然技术上不受标准保证，但基于所有合理实现的共识，体现了实用主义精神。

### 编译期决策

所有检测在编译期完成，使用 `if constexpr` 在编译期选择代码路径，零运行时开销。

## 性能考量

### 编译期零开销

类型特征检测完全在编译期完成，不产生运行时代码。

### 容器性能提升

对于可平凡重定位类型：
- resize: 提速 10-100 倍（取决于对象复杂度）
- insert/erase: 提速 2-10 倍
- swap: 提速 2-5 倍

### 内存优化

某些容器可以使用 realloc，避免分配新内存和拷贝。

## 使用示例

### 标记自定义类型

```cpp
class MyHandle {
    int fd;
public:
    using sk_is_trivially_relocatable = std::true_type;

    MyHandle(int f) : fd(f) {}
    ~MyHandle() { close(fd); }
    MyHandle(MyHandle&& o) : fd(o.fd) { o.fd = -1; }
};
```

### 检测类型特征

```cpp
static_assert(sk_is_trivially_relocatable_v<int>);
static_assert(sk_is_trivially_relocatable_v<std::unique_ptr<int>>);
static_assert(sk_is_trivially_relocatable_v<MyHandle>);
```

### 容器使用

```cpp
SkTArray<MyHandle> handles;
handles.reserve(100);  // 如果 MyHandle 可平凡重定位，使用 realloc
```

## 注意事项

### unique_ptr 的假设

虽然 unique_ptr 被标记为可平凡重定位，但这依赖于实现细节。如果使用自定义删除器且删除器不可平凡重定位，此假设可能失效。

### 验证重要性

在标记类型为可平凡重定位前，必须仔细验证：
- 移动构造 + 源对象析构 == memcpy
- 无自引用指针
- 无地址依赖

### 调试困难

如果错误地标记类型为可平凡重定位，可能导致难以追踪的内存损坏或崩溃。

## 未来方向

### C++ 标准提案

有提案将 `[[trivially_relocatable]]` 加入 C++ 标准，届时可以替换此自定义实现。

### 编译器支持

Clang 已有实验性支持 `[[clang::trivially_relocatable]]` 属性。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/base/SkTArray.h` | 动态数组容器 |
| `include/private/base/SkTDArray.h` | 模板数组容器 |
| `include/private/base/SkContainers.h` | 容器工具 |
| `src/core/SkArenaAlloc.h` | 内存池分配器 |
