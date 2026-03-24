# SkZip

> 源文件
> - src/base/SkZip.h

## 概述

SkZip 是 Skia 基础库中的并行迭代器工具,提供了一种优雅的方式同时遍历多个序列。它类似于 Python 的 `zip()` 函数,可以将多个数组或容器"拉链"在一起,在迭代时同时访问对应位置的元素。SkZip 采用现代 C++ 模板元编程技术,支持任意数量和类型的序列,并通过 constexpr 实现编译时优化。

## 架构位置

SkZip 位于 Skia 基础设施层 (`src/base`),作为通用的容器工具,被广泛用于需要并行遍历多个数组的场景,如图形管线、粒子系统、顶点处理等。

## 主要类与结构体

### SkZip<Ts...>

**模板参数**: `Ts...` - 可变数量的元素类型

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fPointers` | `std::tuple<Ts*...>` | 指向各序列起始位置的指针元组 |
| `fSize` | `size_t` | 序列长度(所有序列长度必须相同) |

### SkZip::Iterator

**迭代器类型**: `std::input_iterator_tag`

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `value_type` | `std::tuple<Ts&...>` | 解引用返回引用元组 |
| `difference_type` | `ptrdiff_t` | 迭代器距离类型 |
| `fZip` | `const SkZip*` | 指向所属 SkZip 对象 |
| `fIndex` | `size_t` | 当前索引 |

### SkMakeZipDetail

辅助类,用于从不同类型的容器(数组、指针、SkSpan、容器引用)推导并构造 SkZip。

## 公共 API 函数

### 构造函数

#### 默认构造

```cpp
constexpr SkZip();
```

构造空的 SkZip。

#### 指针+大小构造

```cpp
constexpr SkZip(size_t size, Ts*... ts);
```

**示例**:
```cpp
int a[] = {1, 2, 3};
float b[] = {1.5f, 2.5f, 3.5f};
SkZip<int, float> zip(3, a, b);
```

#### 转换构造(const 转换)

```cpp
template<typename... Us>
constexpr SkZip(const SkZip<Us...>& that);
```

允许 `SkZip<T>` 转换为 `SkZip<const T>`:

```cpp
SkZip<int, float> nonConst = ...;
SkZip<const int, const float> asConst = nonConst;  // OK
```

### 访问操作

#### operator[]

```cpp
constexpr ReturnTuple operator[](size_t i) const;
```

**功能**: 访问第 i 个位置的所有元素

**返回值**: `std::tuple<Ts&...>` - 引用元组

**示例**:
```cpp
auto [x, y] = zip[0];  // 结构化绑定
```

#### front / back

```cpp
constexpr ReturnTuple front() const;
constexpr ReturnTuple back() const;
```

访问第一个/最后一个元素元组。

### 迭代器

#### begin / end

```cpp
constexpr Iterator begin() const;
constexpr Iterator end() const;
```

**用法**:
```cpp
for (auto [x, y, z] : zip) {
    // x, y, z 是对应位置的元素引用
}
```

### 尺寸查询

#### size / empty

```cpp
constexpr size_t size() const;
constexpr bool empty() const;
```

### 子范围操作

#### first

```cpp
constexpr SkZip first(size_t n) const;
```

**功能**: 返回前 n 个元素的 SkZip

#### last

```cpp
constexpr SkZip last(size_t n) const;
```

**功能**: 返回后 n 个元素的 SkZip

#### subspan

```cpp
constexpr SkZip subspan(size_t offset, size_t count) const;
```

**功能**: 返回子范围 `[offset, offset+count)`

### 投影访问

#### get<I>

```cpp
template<size_t I>
constexpr auto get() const;
```

**功能**: 获取第 I 个序列的 SkSpan

**示例**:
```cpp
SkZip<int, float, double> zip = ...;
SkSpan<int> ints = zip.get<0>();
SkSpan<float> floats = zip.get<1>();
```

#### data

```cpp
constexpr std::tuple<Ts*...> data() const;
```

**功能**: 返回指针元组

### 工厂函数: SkMakeZip

```cpp
template<typename... Ts>
inline constexpr auto SkMakeZip(Ts&& ... ts);
```

**功能**: 从多个容器/数组/指针创建 SkZip

**支持的输入类型**:
- 原始指针: `T*` (大小视为 SIZE_MAX)
- C 数组: `T (&)[N]`
- SkSpan: `SkSpan<T>`
- 容器引用: 任何有 `.data()` 和 `.size()` 的容器

**示例**:
```cpp
// 从数组
int a[] = {1, 2, 3};
float b[] = {1.5f, 2.5f, 3.5f};
auto zip1 = SkMakeZip(a, b);

// 从 std::vector
std::vector<int> vec1 = {1, 2, 3};
std::vector<float> vec2 = {1.5f, 2.5f, 3.5f};
auto zip2 = SkMakeZip(vec1, vec2);

// 从 SkSpan
SkSpan<int> span1 = ...;
SkSpan<float> span2 = ...;
auto zip3 = SkMakeZip(span1, span2);
```

## 内部实现细节

### 类型推导机制

#### DecayPointer

```cpp
template<typename T> struct DecayPointer {
    using U = typename std::remove_cv<typename std::remove_reference<T>::type>::type;
    using type = typename std::conditional<std::is_pointer<U>::value, U, T>::type;
};
```

**功能**: 保留指针类型,移除其他类型的 cv 和引用修饰符。

#### ContiguousMemory

针对不同输入类型提供统一的 `Data()` 和 `Size()` 接口:

```cpp
// 原始指针
template<typename T> struct ContiguousMemory<T*> {
    static constexpr T* Data(T* t) { return t; }
    static constexpr size_t Size(T* s) { return SIZE_MAX; }
};

// C 数组
template<typename T, size_t N> struct ContiguousMemory<T(&)[N]> {
    static constexpr T* Data(T(&t)[N]) { return t; }
    static constexpr size_t Size(T(&)[N]) { return N; }
};

// SkSpan (支持右值)
template<typename T> struct ContiguousMemory<SkSpan<T>> {
    static constexpr T* Data(SkSpan<T> s) { return s.data(); }
    static constexpr size_t Size(SkSpan<T> s) { return s.size(); }
};

// 容器引用 (仅左值)
template<typename C> struct ContiguousMemory<C&> {
    static constexpr auto* Data(C& c) { return c.data(); }
    static constexpr size_t Size(C& c) { return c.size(); }
};
```

**设计考虑**:
- 右值容器不支持(除了 SkSpan,因为它是视图)
- 避免悬空引用

### 大小选择策略: PickOneSize

从多个输入中选择第一个非 `SIZE_MAX` 的大小:

```cpp
// 指针: 跳过,继续
template <typename T, typename... Ts> struct PickOneSize<T*, Ts...> {
    static constexpr size_t Size(T* t, Ts... ts) {
        return PickOneSize<Ts...>::Size(std::forward<Ts>(ts)...);
    }
};

// C 数组: 返回大小
template <typename T, typename... Ts, size_t N> struct PickOneSize<T(&)[N], Ts...> {
    static constexpr size_t Size(T(&)[N], Ts...) { return N; }
};
```

**Debug 检查**:
```cpp
#ifdef SK_DEBUG
    size_t minSize = SIZE_MAX;
    size_t maxSize = 0;
    size_t sizes[sizeof...(Ts)] = {Span<Ts>::Size(std::forward<Ts>(ts))...};
    for (size_t s : sizes) {
        if (s != SIZE_MAX) {
            minSize = std::min(minSize, s);
            maxSize = std::max(maxSize, s);
        }
    }
    SkASSERT(minSize == maxSize);  // 所有大小必须一致
#endif
```

### 索引访问实现

```cpp
constexpr ReturnTuple index(size_t i) const {
    return indexDetail(i, std::make_index_sequence<sizeof...(Ts)>());
}

template<std::size_t... Is>
constexpr ReturnTuple indexDetail(size_t i, std::index_sequence<Is...>) const {
    return ReturnTuple((std::get<Is>(fPointers))[i]...);
}
```

**技巧**: 使用 `std::index_sequence` 展开参数包。

### 迭代器实现

```cpp
constexpr Iterator& operator++() {
    ++fIndex;
    return *this;
}

constexpr reference operator*() {
    return (*fZip)[fIndex];  // 调用 SkZip::operator[]
}
```

迭代器是轻量级的,仅包含指针和索引。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<tuple>` | 存储多类型指针 |
| `<iterator>` | 迭代器特征 |
| `<utility>` | `std::index_sequence` |
| `include/private/base/SkAssert.h` | 断言 |
| `include/private/base/SkSpan_impl.h` | SkSpan 定义 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| 图形管线 | 并行遍历顶点属性(位置、颜色、UV) |
| 粒子系统 | 更新位置、速度、生命周期 |
| 文本渲染 | 字形、位置、度量信息 |
| 批量处理 | 并行处理多个输入数组 |

## 设计模式与设计决策

### 1. 泛型编程 + 模板元编程

通过可变参数模板支持任意数量和类型的序列:

```cpp
SkZip<int, float, double, char*> quad = ...;
```

### 2. 零开销抽象

全部 constexpr + 内联,运行时零开销:
- 编译时计算大小
- 迭代器展开为直接指针访问

### 3. 类型安全

使用 `std::tuple<Ts&...>` 而非 `void*`,提供编译时类型检查。

### 4. 统一接口设计

通过 `ContiguousMemory` 特化,统一处理不同容器类型。

### 5. 安全性保障

- 拒绝右值容器(除 SkSpan)
- Debug 模式检查大小一致性
- constexpr 边界检查

### 6. 现代 C++ 特性

- 结构化绑定: `auto [x, y] = zip[i];`
- constexpr: 编译时计算
- CTAD(C++17): `SkZip zip(3, a, b);`

## 性能考量

### 1. 编译时优化

所有操作都是 constexpr,编译器能完全优化:

```cpp
for (auto [x, y] : zip) {
    // 展开为:
    // for (size_t i = 0; i < size; ++i) {
    //     auto& x = ptr1[i];
    //     auto& y = ptr2[i];
    //     ...
    // }
}
```

### 2. 缓存友好

通过索引访问,保持良好的空间局部性:

```cpp
// 等价于手写循环
for (size_t i = 0; i < n; ++i) {
    process(a[i], b[i], c[i]);
}
```

### 3. 避免临时对象

返回引用元组 `std::tuple<Ts&...>`,无复制开销。

### 4. 内联友好

轻量级迭代器(16 字节: 指针 + 索引)易于内联。

### 5. SIMD 友好

连续内存访问模式有利于编译器自动向量化:

```cpp
for (auto [x, y] : SkMakeZip(a, b)) {
    x = x * y;  // 可能被向量化
}
```

### 6. 子范围零开销

```cpp
auto sub = zip.subspan(10, 20);  // 仅调整指针和大小,无内存分配
```

## 典型用例

### 1. 顶点处理

```cpp
SkSpan<SkPoint> positions = ...;
SkSpan<SkColor> colors = ...;
SkSpan<SkPoint> uvs = ...;

for (auto [pos, color, uv] : SkMakeZip(positions, colors, uvs)) {
    // 变换顶点
    pos = transform.mapPoint(pos);
    // 调整颜色
    color = adjustColor(color);
}
```

### 2. 粒子系统

```cpp
for (auto [pos, vel, life] : SkMakeZip(fPositions, fVelocities, fLifetimes)) {
    pos += vel * dt;
    life -= dt;
}
```

### 3. 批量转换

```cpp
std::vector<float> inputs = ...;
std::vector<float> scales = ...;
std::vector<float> outputs(inputs.size());

for (auto [in, scale, out] : SkMakeZip(inputs, scales, outputs)) {
    out = in * scale;
}
```

### 4. 多数组排序

```cpp
// 根据 keys 排序,同时重排 values
auto zip = SkMakeZip(keys, values);
std::sort(zip.begin(), zip.end(), [](auto a, auto b) {
    auto [k1, v1] = a;
    auto [k2, v2] = b;
    return k1 < k2;
});
```

### 5. 投影访问

```cpp
auto zip = SkMakeZip(xs, ys, zs);
SkSpan<float> xCoords = zip.get<0>();  // 提取 x 坐标
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/private/base/SkSpan_impl.h` | 依赖 | SkSpan 定义 |
| `src/core/SkVertices.cpp` | 使用者 | 顶点数据处理 |
| `src/core/SkRasterPipeline.cpp` | 使用者 | 像素管线批处理 |
| `src/text/GlyphRun.cpp` | 使用者 | 字形运行处理 |
| `modules/particles/...` | 使用者 | 粒子系统 |
