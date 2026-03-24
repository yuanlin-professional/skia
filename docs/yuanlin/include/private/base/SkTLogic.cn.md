# SkTLogic - 类型特征工具

> 源文件: `include/private/base/SkTLogic.h`

## 概述

SkTLogic 提供了一组类型特征工具和元编程辅助功能，主要用于在编译期操作类型的 const 和 volatile 修饰符。该模块扩展了 C++ 标准库的类型特征功能，为 Skia 提供了更便捷的模板元编程支持。

## 架构位置

- **所属子系统**: 基础工具库 (Base Utilities)
- **层级**: 私有头文件，位于 `include/private/base/` 目录
- **依赖层次**: 底层元编程支持模块，被模板代码广泛依赖

## 主要命名空间

### sknonstd 命名空间

该命名空间包含 Skia 提出的"标准风格"扩展功能：
- 这些功能希望未来能被 C++ 标准采纳
- 设计风格类似 std::，但不在 std:: 命名空间中
- 避免与未来标准冲突，同时保持一致的编程风格

## 核心类型特征

### copy_const / copy_const_t

```cpp
template <typename D, typename S> struct copy_const;
template <typename D, typename S> using copy_const_t = typename copy_const<D, S>::type;
```

- **功能**: 将源类型 S 的 const 修饰符"追加"到目标类型 D
- **语义**: 如果 S 是 const，则为 D 添加 const；否则保持 D 不变
- **模板参数**:
  - `D`: 目标类型（Destination）
  - `S`: 源类型（Source）
- **使用场景**: 在模板代码中传播 const 属性

**示例**:
```cpp
copy_const_t<int, const float>      // 结果: const int
copy_const_t<int, float>            // 结果: int
copy_const_t<const int, float>      // 结果: const int (保留原有const)
```

### copy_volatile / copy_volatile_t

```cpp
template <typename D, typename S> struct copy_volatile;
template <typename D, typename S> using copy_volatile_t = typename copy_volatile<D, S>::type;
```

- **功能**: 将源类型 S 的 volatile 修饰符"追加"到目标类型 D
- **语义**: 如果 S 是 volatile，则为 D 添加 volatile；否则保持 D 不变
- **使用场景**: 在需要保持 volatile 语义的模板转换中

**示例**:
```cpp
copy_volatile_t<int, volatile float>  // 结果: volatile int
copy_volatile_t<int, float>           // 结果: int
```

### copy_cv / copy_cv_t

```cpp
template <typename D, typename S> struct copy_cv;
template <typename D, typename S> using copy_cv_t = typename copy_cv<D, S>::type;
```

- **功能**: 同时复制 const 和 volatile 修饰符
- **实现**: `copy_volatile_t<copy_const_t<D, S>, S>`
- **使用场景**: 完整传播 CV 限定符

**示例**:
```cpp
copy_cv_t<int, const volatile float>  // 结果: const volatile int
copy_cv_t<int, const float>           // 结果: const int
copy_cv_t<int, float>                 // 结果: int
```

### same_const / same_const_t

```cpp
template <typename D, typename S> using same_const = copy_const<std::remove_const_t<D>, S>;
template <typename D, typename S> using same_const_t = typename same_const<D, S>::type;
```

- **功能**: 使目标类型 D 的 const 属性与源类型 S"相同"（覆盖而非追加）
- **语义**: 先移除 D 的 const，再根据 S 是否 const 决定是否添加
- **与 copy_const 的区别**:
  - `copy_const` 是追加操作
  - `same_const` 是替换操作

**示例**:
```cpp
same_const_t<const int, float>      // 结果: int (移除const)
same_const_t<int, const float>      // 结果: const int (添加const)
same_const_t<const int, const float> // 结果: const int
```

### same_volatile / same_volatile_t

```cpp
template <typename D, typename S> using same_volatile = copy_volatile<std::remove_volatile_t<D>, S>;
template <typename D, typename S> using same_volatile_t = typename same_volatile<D, S>::type;
```

- **功能**: 使目标类型 D 的 volatile 属性与源类型 S"相同"
- **语义**: 替换而非追加 volatile 修饰符

### same_cv / same_cv_t

```cpp
template <typename D, typename S> using same_cv = copy_cv<std::remove_cv_t<D>, S>;
template <typename D, typename S> using same_cv_t = typename same_cv<D, S>::type;
```

- **功能**: 使目标类型 D 的 CV 限定符与源类型 S 完全相同
- **实现**: 先完全移除 D 的 CV，再根据 S 的 CV 添加

## 辅助函数

### SkCount

```cpp
template <typename Container>
constexpr int SkCount(const Container& c)
```

- **功能**: 获取容器元素个数，返回类型为 int
- **参数**: 任何支持 `std::size()` 的容器
- **返回值**: 容器的元素数量，类型为 int（而非 size_t）
- **安全性**: 使用 `SkTo<int>` 进行类型转换，带范围检查
- **使用原因**: Skia 内部约定使用 int 而非 size_t 作为索引类型

**示例**:
```cpp
std::vector<int> vec = {1, 2, 3, 4, 5};
int count = SkCount(vec);  // 返回 5
```

## 内部实现细节

### copy 系列的实现原理

以 `copy_const` 为例：
```cpp
template <typename D, typename S> struct copy_const {
    using type = std::conditional_t<std::is_const<S>::value, std::add_const_t<D>, D>;
};
```

实现步骤：
1. 使用 `std::is_const<S>` 检查源类型是否为 const
2. 如果是，使用 `std::add_const_t<D>` 为目标类型添加 const
3. 否则，保持目标类型 D 不变
4. 使用 `std::conditional_t` 进行条件类型选择

### same 系列的实现原理

same 系列通过组合 remove 和 copy 实现：
```cpp
same_const<D, S> = copy_const<std::remove_const_t<D>, S>
```

这确保了"替换"语义：
1. 先清除目标类型的修饰符
2. 再根据源类型添加修饰符

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `<iterator>` | 提供迭代器相关支持 |
| `<type_traits>` | 提供标准类型特征工具 |
| `include/private/base/SkTo.h` | 提供安全类型转换函数 SkTo |

### 被依赖的模块

此模块被广泛用于：
- `SkTemplates.h` 中的指针偏移计算
- 容器类的模板实现
- 类型安全的转换和转发
- 泛型算法中的类型推导

## 设计模式与设计决策

### 命名约定

模块遵循 std:: 风格的命名：
- **struct 名称**: `copy_const`, `same_cv` 等，提供 `::type` 成员
- **using 别名**: `copy_const_t`, `same_cv_t` 等，直接提供类型，无需 `::type`
- 这符合 C++14 引入的 `_t` 后缀约定

### "copy" vs "same" 语义

这是该模块的核心设计决策：

**"copy" 系列（追加语义）**:
- 只添加，不移除
- 适用于"传播"限定符的场景
- 例如：函数返回类型保持输入的 const 属性

**"same" 系列（替换语义）**:
- 先移除再添加
- 适用于"对齐"限定符的场景
- 例如：类型转换时完全匹配 CV 限定

### 为什么需要这些工具

C++ 标准库提供了：
- `std::add_const_t`: 只能添加
- `std::remove_const_t`: 只能移除

但缺少：
- 条件性添加（基于另一类型）
- 替换性修改（先移除再条件添加）

SkTLogic 填补了这些空白。

## 使用场景

### 类型转换中的 CV 传播

```cpp
template <typename T>
auto process(T* ptr) {
    using ResultType = sknonstd::same_cv_t<float, T>;
    return static_cast<ResultType*>(ptr);
}
// const int* 输入 -> const float* 输出
// int* 输入 -> float* 输出
```

### 容器元素访问

```cpp
template <typename Container>
auto get_element(Container& c, int index)
    -> sknonstd::copy_const_t<typename Container::value_type, Container>&
{
    return c[index];
}
// const Container -> const value_type&
// Container -> value_type&
```

### SkCount 的典型用法

```cpp
std::array<int, 5> arr;
for (int i = 0; i < SkCount(arr); ++i) {
    // 使用 int 索引，避免 size_t 与 int 比较的警告
}
```

## 性能考量

### 编译期计算

- 所有类型特征都在编译期完全解析
- 运行时零开销
- 不生成任何机器码，纯类型系统操作

### 编译时间影响

- 模板元编程会增加编译时间
- 但这些都是简单的类型操作，影响极小
- 现代编译器对标准类型特征有优化

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/base/SkTo.h` | 提供安全转换函数，被 SkCount 使用 |
| `include/private/base/SkTemplates.h` | 使用 same_cv_t 进行类型安全的指针操作 |
| `include/private/base/SkTypeTraits.h` | 提供其他类型特征工具 |

## 注意事项

### CV 限定符的传播顺序

在使用 `copy_cv` 时，处理顺序是：
1. 先处理 const
2. 再处理 volatile

这个顺序通常不影响结果，但在某些复杂场景中需要注意。

### 引用类型的处理

这些工具不处理引用修饰符：
```cpp
copy_const_t<int&, const float>  // 仍然是 int&，不是 const int&
```

如果需要处理引用，应先使用 `std::remove_reference_t`。

### 指针类型的 CV 位置

```cpp
copy_const_t<int*, const float>  // 结果是 int* const，不是 const int*
```

这修饰的是指针本身，不是指向的对象。要修饰指向的对象，需要先取 pointee 类型。

## 未来发展方向

文件注释提到这些功能"希望被提案并感觉很 std 风格"，暗示：
- 可能会提交给 C++ 标准委员会
- 如果被采纳，将来可能迁移到 std:: 命名空间
- 当前在 sknonstd:: 中避免未来命名冲突
