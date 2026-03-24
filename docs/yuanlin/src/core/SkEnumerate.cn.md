# SkEnumerate

> 源文件
> - src/core/SkEnumerate.h

## 概述

`SkEnumerate.h` 提供了 Skia 中用于迭代容器并同时获取索引和元素的工具类模板。`SkEnumerate` 实现了类似 Python 的 `enumerate()` 功能,允许在 C++ range-based for 循环中同时访问元素索引和值。该模板支持任意迭代器类型,并提供了分片(first/last/subspan)功能。

这个工具大大简化了需要同时跟踪索引和元素的代码,使得循环更加简洁和直观。`SkEnumerate` 通过模板元编程和 C++17 结构化绑定特性,提供了零开销的抽象。

## 架构位置

`SkEnumerate` 是 Skia 基础工具层的一部分,为整个代码库提供迭代辅助:

```
应用层代码
    ↓
SkEnumerate (迭代器包装)
    ↓
标准容器/自定义迭代器
    ↓
底层数据存储
```

**使用场景**:
- 需要索引的容器遍历
- 批量处理时跟踪进度
- 调试输出元素位置
- 并行任务分配(根据索引)

## 主要类与结构体

### SkEnumerate 模板类

**模板参数**:
```cpp
template <typename Iter, typename C = std::monostate>
class SkEnumerate { ... };
```
- `Iter`: 底层迭代器类型
- `C`: 可选的容器类型(用于移动语义)

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCollection` | `C` | 拥有的容器对象(右值引用版本) |
| `fBeginIndex` | `const ptrdiff_t` | 起始索引(用于分片) |
| `fBegin` | `Iter` | 起始迭代器 |
| `fEnd` | `Iter` | 结束迭代器 |

### Iterator 内部类

**迭代器特性**:
```cpp
class Iterator {
public:
    using value_type = Result;
    using difference_type = ptrdiff_t;
    using pointer = value_type*;
    using reference = value_type;
    using iterator_category = std::input_iterator_tag;
    ...
};
```

**关键成员**:
- `fIndex`: 当前索引
- `fIt`: 底层迭代器

## 公共 API 函数

### 构造函数

```cpp
constexpr SkEnumerate(Iter begin, Iter end);
```
- **功能**: 从迭代器范围创建 SkEnumerate
- **参数**: `begin` 和 `end` 迭代器
- **用途**: 包装已有的迭代器

```cpp
explicit constexpr SkEnumerate(C&& c);
```
- **功能**: 从容器右值创建 SkEnumerate
- **参数**: 容器的右值引用
- **特点**: 转移容器所有权,避免拷贝

```cpp
constexpr SkEnumerate(const SkEnumerate& that) = default;
```
- **功能**: 拷贝构造函数
- **特点**: 编译器生成的默认实现

### Range-Based For 循环支持

```cpp
constexpr Iterator begin() const;
constexpr Iterator end() const;
```
- **功能**: 返回起始和结束迭代器
- **用途**: 支持 C++11 range-based for 循环

### 容器接口

```cpp
constexpr bool empty() const;
constexpr size_t size() const;
constexpr ptrdiff_t ssize() const;
```
- **empty**: 检查范围是否为空
- **size**: 返回元素数量(无符号)
- **ssize**: 返回元素数量(有符号)

### 分片操作

```cpp
constexpr SkEnumerate first(size_t n);
```
- **功能**: 返回前 n 个元素的 SkEnumerate
- **断言**: `n <= this->size()`
- **索引**: 保持原始索引

```cpp
constexpr SkEnumerate last(size_t n);
```
- **功能**: 返回后 n 个元素的 SkEnumerate
- **断言**: `n <= this->size()`
- **索引**: 调整起始索引

```cpp
constexpr SkEnumerate subspan(size_t offset, size_t count);
```
- **功能**: 返回子范围的 SkEnumerate
- **参数**:
  - `offset`: 起始偏移
  - `count`: 元素数量
- **断言**: 范围有效性检查

### 工厂函数

```cpp
template <typename C, typename Iter = decltype(std::begin(std::declval<C>()))>
inline constexpr SkEnumerate<Iter> SkMakeEnumerate(C& c);
```
- **功能**: 从左值容器创建 SkEnumerate
- **特点**: 不转移所有权,保持引用

```cpp
template <typename C, typename Iter = decltype(std::begin(std::declval<C>()))>
inline constexpr SkEnumerate<Iter, C> SkMakeEnumerate(C&& c);
```
- **功能**: 从右值容器创建 SkEnumerate
- **特点**: 转移容器所有权

```cpp
template <class T, std::size_t N, typename Iter = decltype(std::begin(std::declval<T(&)[N]>()))>
inline constexpr SkEnumerate<Iter> SkMakeEnumerate(T (&a)[N]);
```
- **功能**: 从 C 风格数组创建 SkEnumerate
- **特点**: 自动推导数组大小

## 内部实现细节

### MakeResult 静态方法

```cpp
static constexpr auto MakeResult(size_t i, Captured&& v) {
    if constexpr (is_tuple<Captured>::value) {
        return std::tuple_cat(std::tuple<size_t>{i}, v);
    } else {
        return std::tuple_cat(std::tuple<size_t>{i}, std::tie(v));
    }
}
```

**功能**: 将索引和元素值组合成元组

**两种模式**:
1. **元素本身是 tuple**: 直接拼接
   - `(index, (a, b, c))` → `(index, a, b, c)`
2. **元素不是 tuple**: 使用 `std::tie` 绑定引用
   - `(index, element)` → `(index, element&)`

**使用示例**:
```cpp
// 单个元素
for (auto [i, value] : SkMakeEnumerate(vector)) { ... }

// 元素本身是 tuple (如 SkMakeZip 的结果)
for (auto [i, a, b] : SkMakeEnumerate(zipped)) { ... }
```

### 迭代器实现

```cpp
class Iterator {
    constexpr Iterator operator++() {
        ++fIndex;
        ++fIt;
        return *this;
    }

    constexpr reference operator*() {
        return MakeResult(fIndex, *fIt);
    }

    constexpr bool operator==(const Iterator& rhs) const {
        return fIt == rhs.fIt;
    }
};
```

**关键点**:
- 同步递增索引和迭代器
- `operator*` 返回 `(index, value)` 元组
- 比较仅基于底层迭代器(索引自然同步)

### 分片实现

```cpp
constexpr SkEnumerate first(size_t n) {
    SkASSERT(n <= this->size());
    ptrdiff_t deltaEnd = this->ssize() - n;
    return SkEnumerate{fBeginIndex, fBegin, std::prev(fEnd, deltaEnd)};
}

constexpr SkEnumerate last(size_t n) {
    SkASSERT(n <= this->size());
    ptrdiff_t deltaBegin = this->ssize() - n;
    return SkEnumerate{fBeginIndex + deltaBegin, std::next(fBegin, deltaBegin), fEnd};
}
```

**first**:
- 保持起始索引不变
- 提前结束迭代器

**last**:
- 调整起始索引
- 推进起始迭代器

**subspan**:
```cpp
constexpr SkEnumerate subspan(size_t offset, size_t count) {
    SkASSERT(offset < this->size());
    SkASSERT(count <= this->size() - offset);
    auto newBegin = std::next(fBegin, offset);
    return SkEnumerate(fBeginIndex + offset, newBegin, std::next(newBegin, count));
}
```
- 同时调整索引和迭代器
- 支持任意子范围提取

### 类型推导

使用 C++17 的 `decltype` 和 `std::declval` 自动推导类型:
```cpp
template <typename C, typename Iter = decltype(std::begin(std::declval<C>()))>
inline constexpr SkEnumerate<Iter> SkMakeEnumerate(C& c) {
    return SkEnumerate<Iter>{std::begin(c), std::end(c)};
}
```

**优势**:
- 无需手动指定迭代器类型
- 支持任意具有 `begin()`/`end()` 的容器
- 编译时类型检查

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<cstddef>` | `size_t`, `ptrdiff_t` 类型 |
| `<iterator>` | 迭代器特性和辅助函数 |
| `<tuple>` | `std::tuple`, `std::tuple_cat`, `std::tie` |
| `<variant>` | `std::monostate`(空占位类型) |

### 被依赖的模块

`SkEnumerate` 是通用工具,被 Skia 各处使用:
- 字形处理循环
- 批量图像操作
- 路径点遍历
- 调试和日志输出

## 设计模式与设计决策

### Adaptor 模式

`SkEnumerate` 适配现有迭代器,添加索引功能:
```cpp
std::vector<int> vec = {10, 20, 30};

// 原始迭代
for (auto& val : vec) { ... }

// 带索引的迭代
for (auto [i, val] : SkMakeEnumerate(vec)) { ... }
```

### 零开销抽象

**编译时优化**:
- 所有函数都是 `constexpr` 和 `inline`
- 编译器完全内联,生成与手写循环相同的代码
- 无运行时开销

**示例**:
```cpp
// 使用 SkEnumerate
for (auto [i, val] : SkMakeEnumerate(vec)) {
    process(i, val);
}

// 手写等价代码(编译后相同)
for (size_t i = 0; i < vec.size(); ++i) {
    auto& val = vec[i];
    process(i, val);
}
```

### RAII 和所有权

**左值引用版本**: 不拥有容器
```cpp
std::vector<int> vec = {1, 2, 3};
auto enumerated = SkMakeEnumerate(vec);  // 仅保存迭代器
// vec 仍然有效
```

**右值引用版本**: 拥有容器
```cpp
auto enumerated = SkMakeEnumerate(std::vector<int>{1, 2, 3});
// 容器被移动到 SkEnumerate 中
```

### 设计决策

1. **constexpr 优先**: 支持编译时计算和优化
2. **元组返回**: 使用现代 C++ 结构化绑定
3. **迭代器类别**: 使用 `input_iterator_tag`(最宽松)
   - 原因: 不假设底层迭代器能力
4. **索引类型**: 使用 `ptrdiff_t`(有符号)
   - 原因: 支持反向索引和算术运算
5. **分片保留索引**: `first`/`last` 保留原始索引
   - 原因: 方便追踪元素在原容器中的位置

## 性能考量

### 零运行时开销

**编译器优化**:
```cpp
// 源代码
for (auto [i, val] : SkMakeEnumerate(vec)) {
    result += i * val;
}

// 编译后(类似)
for (size_t i = 0; i < vec.size(); ++i) {
    result += i * vec[i];
}
```
- 完全内联
- 无额外内存分配
- 无虚函数调用

### 引用语义

使用 `std::tie` 避免拷贝:
```cpp
return std::tuple_cat(std::tuple<size_t>{i}, std::tie(v));
```
- 元组存储引用,不是值
- 避免大对象拷贝
- 使用时需注意生命周期

### 迭代器分类

使用 `input_iterator_tag`:
- 不假设随机访问能力
- 兼容性最好
- 对于随机访问容器,编译器会优化

### 内存占用

```cpp
sizeof(SkEnumerate<Iter, std::monostate>) ≈
    sizeof(C)                 // 容器(如果拥有)
    + sizeof(ptrdiff_t)       // fBeginIndex
    + 2 * sizeof(Iter)        // fBegin + fEnd
```

**典型值**:
- 引用版本: ~24 字节(64位系统)
- 拥有版本: + 容器大小

## 使用示例

### 基本用法

```cpp
std::vector<std::string> names = {"Alice", "Bob", "Charlie"};

for (auto [i, name] : SkMakeEnumerate(names)) {
    SkDebugf("%zu: %s\n", i, name.c_str());
}
// 输出:
// 0: Alice
// 1: Bob
// 2: Charlie
```

### 与 SkMakeZip 结合

```cpp
std::vector<int> ids = {1, 2, 3};
std::vector<std::string> names = {"A", "B", "C"};

for (auto [i, id, name] : SkMakeEnumerate(SkMakeZip(ids, names))) {
    SkDebugf("Row %zu: id=%d, name=%s\n", i, id, name.c_str());
}
```

### 分片处理

```cpp
auto enumerated = SkMakeEnumerate(largeVector);

// 处理前半部分
for (auto [i, val] : enumerated.first(largeVector.size() / 2)) {
    processFirstHalf(i, val);
}

// 处理后半部分
for (auto [i, val] : enumerated.last(largeVector.size() / 2)) {
    processSecondHalf(i, val);  // i 仍然是全局索引
}
```

### 条件索引

```cpp
for (auto [i, item] : SkMakeEnumerate(items)) {
    if (i % 2 == 0) {
        processEvenIndex(item);
    } else {
        processOddIndex(item);
    }
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/base/SkZip.h` | 配合使用 | 多容器并行迭代 |
| `include/private/base/SkSpan.h` | 类似功能 | 轻量级容器视图 |
| `include/private/base/SkTArray.h` | 使用者 | Skia 动态数组 |
| `src/core/*` | 广泛使用 | 整个核心模块 |
