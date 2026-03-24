# SkFixedArray - 固定大小的数组容器
> 源文件: `src/base/SkFixedArray.h`

## 概述
SkFixedArray 是一个模板类，提供固定最大容量的数组容器。与 TArray 不同，SkFixedArray 在编译期确定最大容量，不能超出此限制，从而实现更紧凑的内存布局和更优的代码生成。该容器仅支持平凡类型（trivial types），简化了实现并保证了性能。设计目标是为已知容量上限的小型数组提供零开销的抽象。

## 架构位置
SkFixedArray 位于 Skia 基础容器模块（src/base）命名空间 skia_private 中，属于编译期容器层。它为编译器优化路径、SIMD 代码、小型缓冲区等场景提供类型安全且性能最优的固定数组解决方案。

## 主要类与结构体

### skia_private::FixedArray<N, T>
固定最大容量的数组容器模板类。

**模板参数**:
- `N`: 最大容量（编译期常量，1 ≤ N < 256）
- `T`: 元素类型（必须是平凡类型 trivial type）

**继承关系**: 无

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fData | T[N] | 固定大小的数组存储 |
| fSize | uint8_t | 当前元素数量（0-255） |

**类型别名**:
```cpp
using value_type = T;
```

**静态断言**:
- `std::is_trivial_v<T>`: 确保 T 是平凡类型
- `N > 0`: 容量至少为 1
- `N < 256`: 容量限制（因为 fSize 是 uint8_t）

## 公共 API 函数

### 构造函数

#### `FixedArray()`
- **功能**: 默认构造，创建空数组
- **后置条件**: size() == 0

#### `FixedArray(std::initializer_list<T> values)`
- **功能**: 从初始化列表构造
- **参数**: values - 初始元素列表
- **断言**: values.size() <= N
- **示例**: `FixedArray<4, int> arr = {1, 2, 3};`

#### `FixedArray(int reserveCount)`
- **功能**: 预留容量构造（兼容 TArray 接口）
- **参数**: reserveCount - 预留数量（必须 <= N）
- **说明**: 实际不分配内存，仅验证参数

#### `FixedArray(SkSpan<const T> array)`
- **功能**: 从 span 构造
- **参数**: array - 源数组
- **断言**: array.size() <= N
- **实现**: 调用 reset(array)

#### `FixedArray(const FixedArray<N, T>& that)`
- **功能**: 拷贝构造
- **实现**: 调用 reset() 拷贝数据

### 赋值运算符

#### `FixedArray<N, T>& operator=(const FixedArray<N, T>& that)`
- **功能**: 拷贝赋值
- **参数**: that - 源数组
- **返回值**: *this 引用
- **自赋值检查**: 避免自我赋值

### 元素访问

#### `T& operator[](size_t index)` / `const T& operator[](size_t index) const`
- **功能**: 下标访问元素
- **参数**: index - 元素索引
- **断言**: index < fSize
- **返回值**: 元素引用

### 比较运算符

#### `bool operator==(const FixedArray<N, T>& that) const`
- **功能**: 判断两个数组是否相等
- **实现**: 先比较 size，再用 memcmp 比较数据
- **返回值**: 相等返回 true

#### `bool operator!=(const FixedArray<N, T>& that) const`
- **功能**: 判断两个数组是否不相等
- **实现**: `!(*this == that)`

### 容量与大小

#### `int size() const`
- **功能**: 返回当前元素数量
- **返回值**: fSize

#### `bool empty() const`
- **功能**: 检查数组是否为空
- **返回值**: fSize == 0

#### `constexpr int capacity() const`
- **功能**: 返回最大容量
- **返回值**: N（编译期常量）

#### `void clear()`
- **功能**: 清空数组
- **实现**: fSize = 0（不销毁元素）

### 修改操作

#### `void reset(SkSpan<const T> array)`
- **功能**: 重置数组内容
- **参数**: array - 新的元素数组
- **断言**: array.size() <= N
- **实现**: 使用 std::memcpy 拷贝数据

#### `void resize(int newSize)`
- **功能**: 调整数组大小
- **参数**: newSize - 新大小（0 ≤ newSize ≤ N）
- **行为**:
  - 缩小：减少 size，不销毁元素
  - 扩大：增加 size，新元素值初始化为 T()

#### `void reserve(int size)`
- **功能**: 预留容量（兼容 TArray 接口）
- **参数**: size - 预留大小
- **断言**: size >= 0 && size <= N
- **说明**: 实际不做任何操作（容量已固定）

### 尾部操作

#### `T& push_back()`
- **功能**: 在尾部添加默认构造的元素
- **断言**: fSize < N
- **返回值**: 新元素的引用（已初始化为 T()）

#### `void push_back(T x)`
- **功能**: 在尾部添加元素
- **参数**: x - 要添加的元素
- **断言**: fSize < N

#### `T* push_back_n(int n)`
- **功能**: 在尾部添加 n 个默认构造的元素
- **参数**: n - 元素数量
- **断言**: fSize + n <= N
- **返回值**: 指向第一个新元素的指针

#### `T* push_back_n(int n, const T& t)`
- **功能**: 在尾部添加 n 个元素（值拷贝）
- **参数**:
  - n - 元素数量
  - t - 元素值
- **断言**: fSize + n <= N
- **返回值**: 指向第一个新元素的指针

#### `void pop_back()`
- **功能**: 移除尾部元素
- **断言**: fSize >= 1
- **实现**: --fSize

#### `void pop_back_n(int n)`
- **功能**: 移除尾部 n 个元素
- **参数**: n - 要移除的数量
- **断言**: fSize >= n

#### `void removeShuffle(int n)`
- **功能**: 移除指定索引的元素（用最后一个元素替换）
- **参数**: n - 要移除的索引
- **断言**: n < fSize
- **特点**: O(1) 操作，但不保持顺序

### 迭代器与访问

#### `T* data()` / `const T* data() const`
- **功能**: 返回底层数组指针
- **返回值**: fData

#### `T* begin()` / `const T* begin() const`
- **功能**: 返回首元素迭代器
- **返回值**: fData

#### `T* end()` / `const T* end() const`
- **功能**: 返回尾后迭代器
- **返回值**: fData + fSize

#### `T& front()` / `const T& front() const`
- **功能**: 返回首元素引用
- **断言**: fSize > 0

#### `T& back()` / `const T& back() const`
- **功能**: 返回尾元素引用
- **断言**: fSize > 0

## 内部实现细节

### 为何限制为平凡类型
```cpp
static_assert(std::is_trivial_v<T>);
```

**平凡类型的特点**:
- 可以用 memcpy 拷贝
- 不需要调用构造/析构函数
- 编译器可以生成更优的代码

**限制的好处**:
- 简化实现（不需要手动管理生命周期）
- 更好的性能（编译器优化）
- 零开销抽象

**如果需要非平凡类型**: 使用 TArray 或 std::array

### 为何用 uint8_t 作为 fSize
```cpp
uint8_t fSize = 0;
```

**优点**:
- 节省内存（1 字节 vs 4/8 字节）
- 缓存友好
- 对于小数组，size 永远不会超过 255

**限制**: N < 256

**内存布局示例** (FixedArray<4, int>):
```
+----+----+----+----+---+---+---+
| i0 | i1 | i2 | i3 |sz |pad|pad| (24 bytes with padding)
+----+----+----+----+---+---+---+
```

### 比较使用 memcmp
```cpp
bool operator==(const FixedArray<N, T>& that) const {
    return fSize == that.fSize &&
           (0 == memcmp(fData, that.fData, fSize * sizeof(T)));
}
```

**为何安全**:
- T 是平凡类型，memcmp 比较位模式是有效的
- 比逐元素比较更快
- 编译器可能优化为 SIMD 指令

### resize 的实现
```cpp
void resize(int newSize) {
    SkASSERT(newSize >= 0);
    SkASSERT(newSize <= N);

    if (fSize > newSize) {
        fSize = newSize;  // 缩小
    } else {
        while (fSize < newSize) {
            fData[fSize++] = T();  // 扩大并初始化
        }
    }
}
```

**设计选择**:
- 缩小时不销毁元素（平凡类型无需销毁）
- 扩大时值初始化为 T()
- 逐个赋值而非 memset（更通用）

### removeShuffle 的优化
```cpp
void removeShuffle(int n) {
    SkASSERT(n < fSize);
    int last = fSize - 1;
    if (n != last) {
        fData[n] = fData[last];  // 用最后元素替换
    }
    fSize = last;
}
```

**O(1) 移除**: 不保持顺序，用于顺序无关的场景

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 断言检查 |
| include/private/base/SkSpan_impl.h | SkSpan 类型 |
| <cstdint> | uint8_t 类型 |
| <cstring> | memcpy, memcmp |
| <initializer_list> | 初始化列表支持 |
| <type_traits> | std::is_trivial_v |

### 被依赖的模块
- 编译器优化路径
- SIMD 向量缓冲区
- 小型临时数组
- 固定大小的缓存
- 栈分配的缓冲区

## 设计模式与设计决策

### 编译期容量限制
优势：
- 编译器可以完全展开循环
- 更好的代码内联
- 栈分配友好
- 无需动态内存

劣势：
- 不能超出容量 N
- 每个不同的 N 生成不同的类型

### TArray 接口兼容
提供 reserve()、capacity() 等方法：
- 与 TArray 接口兼容
- 可以在模板代码中替换
- 更容易从 TArray 迁移

### 平凡类型限制的权衡
**优点**:
- 简单的实现
- 更好的性能
- 零开销抽象

**缺点**:
- 不支持 std::string、std::unique_ptr 等
- 需要手动管理复杂类型

**设计哲学**: 为常见情况（POD 类型）提供最优实现

### 初始化列表支持
```cpp
FixedArray<4, int> arr = {1, 2, 3};
```
提供现代 C++ 风格的初始化，提升可用性。

## 性能考量

### 内存布局
FixedArray<4, int> 的大小：
- fData: 16 字节（4 × 4 字节）
- fSize: 1 字节
- 对齐填充: 3 字节（假设 4 字节对齐）
- 总计: 20 字节（实际可能是 24 字节，取决于编译器）

### 与 std::array 比较
**FixedArray 优势**:
- 支持动态 size（std::array 固定满）
- push_back、resize 等 STL 容器接口
- 更小的内存占用（size 使用 uint8_t）

**std::array 优势**:
- 标准库，更广泛支持
- constexpr 支持更好
- 无 size 限制（可以 > 255 元素）

### 与 TArray 比较
**FixedArray 优势**:
- 编译期容量，更好的优化
- 栈分配，无堆开销
- 更小的对象大小

**TArray 优势**:
- 动态增长
- 支持非平凡类型
- 容量无上限

### 循环展开
编译器可能完全展开固定大小的循环：
```cpp
FixedArray<4, int> arr;
for (int i = 0; i < arr.capacity(); ++i) {
    arr.push_back(i);
}
// 可能被优化为 4 个独立的赋值语句
```

## 使用场景

### 场景 1: SIMD 临时缓冲区
```cpp
FixedArray<4, float> components;
components.push_back(r);
components.push_back(g);
components.push_back(b);
components.push_back(a);
// 传递给 SIMD 函数
processSIMD(components.data());
```

### 场景 2: 小型缓存
```cpp
class ShaderCache {
    FixedArray<8, ShaderKey> recentKeys;

    void addKey(ShaderKey key) {
        if (recentKeys.size() == recentKeys.capacity()) {
            recentKeys.pop_back();
        }
        recentKeys.push_back(key);
    }
};
```

### 场景 3: 栈分配的临时数组
```cpp
void processValues() {
    FixedArray<16, int> temp;
    for (int i = 0; i < 10; ++i) {
        temp.push_back(computeValue(i));
    }
    // 使用 temp
    sortValues(temp.data(), temp.size());
}
```

### 场景 4: 编译期已知大小的数据
```cpp
enum class Corner { kTopLeft, kTopRight, kBottomRight, kBottomLeft };
FixedArray<4, SkPoint> corners;
corners.push_back(rect.topLeft());
corners.push_back(rect.topRight());
// ...
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkTArray.h | 动态数组容器 |
| include/private/base/SkSpan_impl.h | Span 类型定义 |
| src/base/SkVx.h | SIMD 向量（可能使用 FixedArray） |
| tests/FixedArrayTest.cpp | 单元测试（如果存在） |

## 最佳实践

### 选择合适的 N
- 过小：频繁触发断言
- 过大：浪费栈空间
- 建议：根据实际使用的最大值 +10% 余量

### 避免存储复杂类型
```cpp
// 不推荐
FixedArray<10, std::string> strings;  // 编译错误（非平凡类型）

// 推荐
FixedArray<10, const char*> stringPtrs;  // OK
```

### 利用编译期容量
```cpp
template<int N>
void processArray(FixedArray<N, int>& arr) {
    // 编译器知道 N，可能优化循环
    for (int i = 0; i < N; ++i) {
        // ...
    }
}
```

### 栈溢出风险
```cpp
// 危险：大数组在栈上
void function() {
    FixedArray<10000, int> bigArray;  // 40KB+ 栈空间！
}

// 更安全
void function() {
    static FixedArray<10000, int> bigArray;  // 静态存储
}
```
