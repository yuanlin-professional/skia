# SkSpan - 轻量级数组视图

> 源文件: `include/private/base/SkSpan_impl.h`

## 概述

SkSpan 是一个轻量级的数组视图类，提供对连续内存区域的非拥有引用。它类似于 C++20 的 std::span，但为了保持兼容性提供了自己的实现。SkSpan 可以方便地统一处理各种数组形式（C数组、std::vector、std::array 等），无需拷贝数据。

## 架构位置

- **所属子系统**: 基础容器工具 (Base Container Utilities)
- **层级**: 私有头文件，位于 `include/private/base/` 目录
- **依赖层次**: 底层数组视图抽象，被容器和算法广泛依赖

## 编译选项

### SK_USE_LEGACY_SKSPAN

该宏控制使用哪种实现：
- **已定义**: 使用 Skia 自定义的 SkSpan 实现（当前默认）
- **未定义**: SkSpan 变为 std::span 的别名

**过渡策略**:
- 当前保持自定义实现，直到客户端准备好迁移
- 未来将完全切换到 std::span

### SKSPAN_INIT_ONE 宏

```cpp
#ifdef SK_USE_LEGACY_SKSPAN
    #define SKSPAN_INIT_ONE(elem)   {elem}
#else
    #define SKSPAN_INIT_ONE(elem)   {{elem}}
#endif
```

- **用途**: 跨实现兼容的单元素初始化
- **原因**: SkSpan 和 std::span 对单个 POD 初始化语法不同
- **使用**: `SkSpan<int> span = SKSPAN_INIT_ONE(42);`

## 主要类

### SkSpan<T>

非拥有的连续数组引用类。

**模板参数**:
- `T`: 元素类型，可以是 const 限定的

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fPtr | T* | 指向数组第一个元素的指针 |
| fSize | size_t | 数组中的元素数量 |

## 公共 API 函数

### 构造函数

#### 默认构造

```cpp
constexpr SkSpan()
```

- **功能**: 创建空 span，指针为 nullptr，大小为0

#### 指针和大小构造

```cpp
template <typename Integer>
constexpr SkSpan(T* ptr, Integer size)
```

- **功能**: 从指针和大小创建 span
- **参数**:
  - `ptr`: 数组指针，可以为 nullptr（当 size 为0时）
  - `size`: 元素数量，整数类型
- **断言检查**:
  - `ptr || fSize == 0`: 禁止 nullptr + 非零大小
  - 总字节数不超过 size_t 最大值

#### 拷贝构造（const 转换）

```cpp
template <typename U>
constexpr SkSpan(const SkSpan<U>& that)
```

- **功能**: 从 SkSpan<U> 构造 SkSpan<const U>
- **约束**: 只能从非 const 到 const，不能反向

#### C 数组构造

```cpp
template<size_t N>
constexpr SkSpan(T(&a)[N])
```

- **功能**: 从 C 风格数组自动推导大小
- **示例**: `int arr[5]; SkSpan<int> span(arr);`

#### 容器构造

```cpp
template<typename Container>
constexpr SkSpan(Container&& c)
```

- **功能**: 从支持 `std::data()` 和 `std::size()` 的容器构造
- **支持的容器**:
  - std::vector
  - std::array
  - std::string
  - 自定义容器（只要提供 data() 和 size()）

#### initializer_list 构造

```cpp
SkSpan(std::initializer_list<T> il SK_CHECK_IL_LIFETIME)
```

- **功能**: 从初始化列表创建 span
- **警告**: initializer_list 生命周期极短，仅限当前语句
- **正确用法**: `function(SkSpan<int>({1, 2, 3}));`
- **错误用法**: `auto il = {1, 2, 3}; function(SkSpan<int>(il));`  // UB！

### 元素访问

#### operator[]

```cpp
constexpr T& operator[](size_t i) const
```

- **功能**: 访问第 i 个元素
- **边界检查**: 使用 `sk_collection_check_bounds` 进行调试检查
- **返回值**: 元素的引用

#### front / back

```cpp
constexpr T& front() const
constexpr T& back() const
```

- **功能**: 访问首元素和尾元素
- **前置条件**: span 非空（调试模式检查）

### 迭代器

```cpp
constexpr T* begin() const
constexpr T* end() const
constexpr auto rbegin() const
constexpr auto rend() const
```

- **功能**: 提供正向和反向迭代器
- **范围 for 支持**: 支持 `for (auto& elem : span) { ... }`

### 属性查询

```cpp
constexpr T* data() const
constexpr size_t size() const
constexpr bool empty() const
constexpr size_t size_bytes() const
```

- **data()**: 获取底层指针
- **size()**: 获取元素数量
- **empty()**: 判断是否为空
- **size_bytes()**: 获取总字节数（`size() * sizeof(T)`）

### 子视图操作

#### first

```cpp
constexpr SkSpan<T> first(size_t prefixLen) const
```

- **功能**: 获取前 prefixLen 个元素的子 span
- **边界检查**: prefixLen 不能超过 size()

#### last

```cpp
constexpr SkSpan<T> last(size_t postfixLen) const
```

- **功能**: 获取后 postfixLen 个元素的子 span
- **边界检查**: postfixLen 不能超过 size()

#### subspan

```cpp
constexpr SkSpan<T> subspan(size_t offset) const
constexpr SkSpan<T> subspan(size_t offset, size_t count) const
```

- **功能**: 获取从 offset 开始的子 span
- **第一个重载**: 从 offset 到末尾
- **第二个重载**: 从 offset 开始的 count 个元素
- **边界检查**: 确保 offset + count 不超过 size()

## 内部实现细节

### 类推导指引

```cpp
template <typename Container>
SkSpan(Container&&) ->
    SkSpan<std::remove_pointer_t<decltype(std::data(std::declval<Container>()))>>;
```

- **C++17 特性**: 类模板参数推导 (CTAD)
- **作用**: 从容器自动推导元素类型
- **示例**: `SkSpan span(vec);  // 自动推导为 SkSpan<int>`

### 边界检查宏

#### sk_collection_check_bounds

在索引访问时检查边界：
```cpp
fPtr[sk_collection_check_bounds(i, this->size())]
```

- 调试构建中抛出异常或中止
- 发布构建中可能优化掉

#### sk_collection_not_empty

在 front()/back() 中检查非空：
```cpp
sk_collection_not_empty(this->empty());
```

### 生命周期注解

#### SK_CHECK_IL_LIFETIME

```cpp
#if defined(__clang__) && defined(__has_cpp_attribute) && __has_cpp_attribute(clang::lifetimebound)
#define SK_CHECK_IL_LIFETIME [[clang::lifetimebound]]
```

- **Clang 扩展**: 生命周期绑定属性
- **作用**: 编译器警告 initializer_list 悬空引用
- **重要性**: 防止常见的生命周期错误

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/private/base/SkAssert.h` | 提供断言宏 |
| `include/private/base/SkDebug.h` | 提供调试工具 |
| `include/private/base/SkTo.h` | 提供安全类型转换 |
| `<type_traits>` | 类型特征检查 |
| `<initializer_list>` | 初始化列表支持 |
| `<iterator>` | 迭代器支持 |

### 被依赖的模块

SkSpan 被广泛用于：
- 函数参数传递（避免模板重载爆炸）
- 容器适配器
- 算法接口
- 数据传输层

## 设计模式与设计决策

### 视图模式（View Pattern）

SkSpan 遵循视图模式：
- **非拥有**: 不管理内存，不负责析构
- **轻量级**: 只包含指针和大小（16字节，64位系统）
- **浅拷贝**: 拷贝 span 只拷贝引用，不拷贝数据

### 统一接口模式

SkSpan 统一了多种数组表示：
```cpp
void process(SkSpan<const int> data) {
    // 可以接受各种形式的数据
}

int arr[5] = {1, 2, 3, 4, 5};
std::vector<int> vec = {1, 2, 3, 4, 5};
std::array<int, 5> stdarr = {1, 2, 3, 4, 5};

process(arr);
process(vec);
process(stdarr);
process({1, 2, 3, 4, 5});  // initializer_list
```

### const 正确性

SkSpan 支持 const 传播：
```cpp
SkSpan<int> span1;           // 可修改元素
SkSpan<const int> span2;     // 只读元素
SkSpan<int> span3 = span1;   // OK
SkSpan<const int> span4 = span1;  // OK：非const到const
// SkSpan<int> span5 = span2;  // 错误：const到非const
```

## 性能考量

### 零开销抽象

- **内联**: 所有函数都是 constexpr 和内联的
- **无虚函数**: 没有虚表开销
- **值语义**: 通常通过寄存器传递（两个机器字）

### 与原始指针的比较

```cpp
// 传统方式
void func(const int* data, size_t size);

// SkSpan 方式
void func(SkSpan<const int> data);
```

优势：
- 类型更安全（绑定指针和大小）
- 提供丰富的 API（subspan, first, last 等）
- 性能相同（编译器优化后）

### 与 std::vector 的比较

传递 std::vector 有三种方式：
1. **按值**: 拷贝整个容器（昂贵）
2. **按引用**: 绑定到 std::vector 类型（不够通用）
3. **SkSpan**: 视图，既高效又通用

## 使用场景

### 函数参数

```cpp
// 避免函数重载爆炸
void draw(SkSpan<const SkPoint> points);

// 可接受各种来源
std::vector<SkPoint> vec;
SkPoint arr[100];
draw(vec);
draw(arr);
draw(SkSpan<SkPoint>(ptr, count));
```

### 数组切片

```cpp
std::vector<int> data = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
SkSpan<int> span(data);

SkSpan<int> first_half = span.first(5);  // {1,2,3,4,5}
SkSpan<int> last_half = span.last(5);    // {6,7,8,9,10}
SkSpan<int> middle = span.subspan(3, 4); // {4,5,6,7}
```

### 范围迭代

```cpp
void processPixels(SkSpan<const uint32_t> pixels) {
    for (uint32_t pixel : pixels) {
        // 处理每个像素
    }
}
```

### 与 C API 交互

```cpp
// 包装 C 风格 API
extern "C" void c_function(const float* data, int size);

void cpp_wrapper(SkSpan<const float> data) {
    c_function(data.data(), static_cast<int>(data.size()));
}
```

## 常见陷阱

### 陷阱1：悬空引用

```cpp
SkSpan<int> getSpan() {
    std::vector<int> vec = {1, 2, 3};
    return SkSpan<int>(vec);  // 错误！vec 在函数结束时销毁
}
```

**解决方案**: 确保被引用的数据生命周期足够长。

### 陷阱2：initializer_list 生命周期

```cpp
// 错误示例
auto il = {1, 2, 3};
SkSpan<const int> span(il);  // UB：il 已失效
use(span);

// 正确示例
use(SkSpan<const int>({1, 2, 3}));  // OK：在同一语句中
```

### 陷阱3：修改 const span

```cpp
SkSpan<const int> span = ...;
// span[0] = 42;  // 编译错误：const int 不可修改
```

### 陷阱4：空指针陷阱

```cpp
int* ptr = nullptr;
SkSpan<int> span(ptr, 5);  // 断言失败！nullptr + 非零大小
```

## 最佳实践

1. **优先使用 SkSpan 作为参数**: 而非 const T* + size
2. **明确 const**: 不修改时使用 `SkSpan<const T>`
3. **避免存储 span**: span 是临时视图，不要长期保存
4. **检查生命周期**: 确保底层数据在 span 使用期间有效
5. **使用子视图**: 利用 first/last/subspan 而非手动指针运算

## 与 std::span 的差异

| 特性 | SkSpan | std::span |
|------|--------|-----------|
| C++ 版本要求 | C++11+ | C++20+ |
| 静态大小 | 不支持 | 支持 `std::span<T, N>` |
| 单 POD 初始化 | `{elem}` | `{{elem}}` |
| 动态大小常量 | 不支持 | `std::dynamic_extent` |

## 迁移到 std::span

未来当 Skia 迁移到 std::span 时：
1. 取消定义 `SK_USE_LEGACY_SKSPAN`
2. 使用 `SKSPAN_INIT_ONE` 宏的代码需要更新为 `{{elem}}`
3. 其他代码应该可以无缝切换

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/base/SkTo.h` | 提供类型转换，被 SkSpan 使用 |
| `include/private/base/SkTArray.h` | 容器类，可转换为 SkSpan |
| `include/core/SkData.h` | 数据封装类，提供 span 视图 |

## 参考资料

- **C++20 std::span**: cppreference.com/w/cpp/container/span
- **CppCon 2018**: "std::span: The Best Thing Since Sliced Arrays" by Neil MacIntosh
