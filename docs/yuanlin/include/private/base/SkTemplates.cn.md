# SkTemplates - 模板工具集

> 源文件: `include/private/base/SkTemplates.h`

## 概述

SkTemplates 提供了一组轻量级的模板类和工具函数，用于类型安全和异常安全的资源管理。该文件包含智能指针包装器、自动释放数组、内存管理工具以及各种模板辅助函数，是 Skia 基础设施的核心组件之一。

## 架构位置

- **所属子系统**: 基础模板工具库 (Base Template Utilities)
- **层级**: 私有头文件，位于 `include/private/base/` 目录
- **依赖层次**: 底层资源管理和模板元编程支持

## 核心工具函数

### sk_ignore_unused_variable

```cpp
template<typename T> inline void sk_ignore_unused_variable(const T&) { }
```

- **功能**: 标记局部变量为已知未使用，避免编译器警告
- **注意**: 不阻止编译器优化掉该变量
- **使用场景**: 条件编译中某些变量仅在特定配置下使用

### SkTAbs

```cpp
template <typename T> static inline T SkTAbs(T value)
```

- **功能**: 通用绝对值函数
- **与 SkAbs32 的区别**: SkAbs32 专门用于 32 位整数且有断言；SkTAbs 适用于任意类型
- **实现**: `if (value < 0) value = -value; return value;`

### SkTAfter

```cpp
template <typename D, typename S> inline D* SkTAfter(S* ptr, size_t count = 1)
```

- **功能**: 返回指向 `S[count]` 之后的 `D*` 指针
- **用途**: 类型安全的指针偏移计算
- **示例**: `int* p = ...; float* f = SkTAfter<float>(p, 10);`

### SkTAddOffset

```cpp
template <typename D, typename S> inline D* SkTAddOffset(S* ptr, ptrdiff_t byteOffset)
```

- **功能**: 在字节级别偏移指针，返回不同类型
- **CV 限定符处理**: 中间 char* 保持与 D 相同的 const/volatile 属性
- **实现**: 通过 `sknonstd::same_cv_t<char, D>*` 保持类型安全

## 智能指针类

### SkAutoTCallVProc

```cpp
template <typename T, void (*P)(T*)> class SkAutoTCallVProc
    : public std::unique_ptr<T, SkFunctionObject<P>>
```

- **功能**: RAII 封装，析构时自动调用指定函数
- **模板参数**:
  - `T`: 对象类型
  - `P`: 析构时调用的函数指针
- **基类**: std::unique_ptr 的特化，使用函数对象作为删除器
- **使用场景**: 包装 C 风格资源管理 API

**示例**:
```cpp
void cleanup_resource(Resource* r) { /* ... */ }
SkAutoTCallVProc<Resource, cleanup_resource> resource(new Resource);
// 自动调用 cleanup_resource
```

## skia_private 命名空间容器

### AutoTArray<T>

动态分配的自动释放数组。

**关键成员**:
- `std::unique_ptr<T[]> fData`: 底层存储
- `size_t fSize`: 元素数量

**主要方法**:

```cpp
explicit AutoTArray(size_t size)  // 分配 size 个 T
T& operator[](size_t index)       // 访问元素
T* data() / const T* data()       // 获取指针
size_t size() / bool empty()      // 查询大小
void reset(size_t count = 0)      // 重新分配
T* begin() / T* end()             // 迭代器
```

**特点**:
- 自动内存管理，RAII 语义
- 移动语义支持
- 边界检查（调试模式）
- 不调用构造/析构函数（与 std::unique_ptr<T[]> 不同）

### AutoSTArray<kCountRequested, T>

带有栈存储优化的自动数组。

**模板参数**:
- `kCountRequested`: 请求的栈存储元素数
- `kCount`: 实际栈存储元素数（可能更多，利用对齐填充）

**关键成员**:
- `T* fArray`: 指向当前数组的指针
- `alignas(T) std::byte fStorage[...]`: 栈上存储空间
- `int fCount`: 元素数量

**主要方法**:

```cpp
AutoSTArray()                     // 空数组
explicit AutoSTArray(int count)   // 分配 count 个元素
void reset(int count)             // 重新分配并默认构造
void trimTo(int count)            // 移除 >= count 的元素
int count() / T* get()            // 查询和访问
```

**存储策略**:
- `count <= kCount`: 使用栈存储
- `count > kCount`: 堆分配
- 自动切换，对用户透明

**Google3 优化**:
```cpp
#if defined(SK_BUILD_FOR_GOOGLE3)
    static constexpr int kMaxBytes = 4 * 1024;
    static constexpr int kMinCount = ...;  // 限制栈使用
#endif
```

### AutoTMalloc<T>

POD 类型的手动内存管理容器。

**约束**: `T` 必须是 trivially copyable 和 trivially destructible

**主要方法**:

```cpp
explicit AutoTMalloc(T* ptr)      // 接管指针
explicit AutoTMalloc(size_t count) // 分配
void realloc(size_t count)        // 保留内容重新分配
T* reset(size_t count = 0)        // 不保留内容重新分配
T* release()                      // 释放所有权
```

**特点**:
- 使用 sk_malloc_throw / sk_realloc_throw
- 不调用构造/析构
- 适合原始数据缓冲区

### AutoSTMalloc<kCountRequested, T>

带栈存储的 POD 数组。

**模板参数**:
- `kCountRequested`: 请求的栈元素数
- `kCount`: 实际栈元素数（考虑对齐）

**关键成员**:
- `T* fPtr`: 当前数组指针
- `union { uint32_t fStorage32[...]; T fTStorage[1]; }`: 栈存储

**主要方法**:

```cpp
AutoSTMalloc(size_t count)        // 构造
T* reset(size_t count)            // 重新分配
void realloc(size_t count)        // 调整大小
```

**存储策略**:
- 小数组在栈上（fTStorage）
- 大数组在堆上（sk_malloc）
- 自动管理切换

**对齐技巧**:
```cpp
union {
    uint32_t fStorage32[...];  // 确保对齐
    T fTStorage[1];            // 不调用构造函数
};
```

## 辅助模板

### SkOverloadedFunctionObject

```cpp
template <typename T, T* P> struct SkOverloadedFunctionObject
```

- **功能**: 将函数指针包装为函数对象
- **用途**: 作为 std::unique_ptr 的删除器
- **实现**: 完美转发到函数指针 P

### SkFunctionObject

```cpp
template <auto F> using SkFunctionObject =
    SkOverloadedFunctionObject<std::remove_pointer_t<decltype(F)>, F>;
```

- **C++17 特性**: 使用 `auto` 模板参数
- **简化语法**: 从函数指针自动推导类型

## 数组生成工具

### SkMakeArray

```cpp
template<size_t N, typename C> constexpr auto SkMakeArray(C c)
```

- **功能**: 从可调用对象生成 std::array
- **参数**: `c` 是一个函数对象，接受索引返回元素
- **返回**: `std::array<decltype(c(0)), N>`

**示例**:
```cpp
auto squares = SkMakeArray<5>([](int i) { return i * i; });
// squares = {0, 1, 4, 9, 16}
```

### SkMakeArrayFromIndexSequence

```cpp
template<typename C, std::size_t... Is>
constexpr auto SkMakeArrayFromIndexSequence(C c, std::index_sequence<Is...> is)
```

- **功能**: SkMakeArray 的底层实现
- **技术**: 利用参数包展开和索引序列

## 内部实现细节

### 内存分配策略

所有容器使用 Skia 自定义分配器：
- `sk_malloc_throw`: 失败时抛异常而非返回 nullptr
- `sk_realloc_throw`: 重新分配，失败抛异常
- `sk_free`: 对应的释放函数

### 边界检查

```cpp
T& operator[](size_t index) const {
    return fData[sk_collection_check_bounds(index, fSize)];
}
```

- 调试构建中验证 `index < fSize`
- 发布构建中可能优化掉

### 移动语义

大多数容器支持移动：
```cpp
AutoTArray(AutoTArray&& other)
    : fData(std::move(other.fData))
    , fSize(std::exchange(other.fSize, 0)) {}
```

- 转移所有权，不拷贝数据
- 源对象变为空状态

### Google3 栈限制

```cpp
#if defined(SK_BUILD_FOR_GOOGLE3)
    static constexpr int kMaxBytes = 4 * 1024;
```

- Google3 环境中栈帧大小有限制
- 自动限制栈分配大小
- 超出部分使用堆

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/private/base/SkAlign.h` | 对齐计算 |
| `include/private/base/SkAssert.h` | 断言 |
| `include/private/base/SkMalloc.h` | 内存分配 |
| `include/private/base/SkTLogic.h` | 类型特征工具 |
| `<memory>` | std::unique_ptr |
| `<utility>` | std::move, std::exchange |

### 被依赖的模块

该文件被 Skia 全局广泛使用：
- 资源管理
- 临时缓冲区
- RAII 封装
- 容器实现

## 设计模式与设计决策

### RAII（Resource Acquisition Is Initialization）

所有容器都遵循 RAII：
- 构造时获取资源
- 析构时自动释放
- 异常安全

### SBO（Small Buffer Optimization）

AutoSTArray 和 AutoSTMalloc 实现 SBO：
- 小对象在栈上
- 大对象在堆上
- 避免小分配的堆开销

### 类型安全

通过模板和类型特征确保：
- POD 容器只接受 POD 类型
- 类型转换保持 CV 限定符
- 编译期类型检查

## 性能考量

### 内联和 constexpr

```cpp
template<typename T> inline void sk_ignore_unused_variable(const T&) { }
static inline T SkTAbs(T value) { ... }
```

- 短函数标记为 inline
- 可能的标记为 constexpr
- 鼓励编译器优化

### 栈分配优化

AutoSTArray 和 AutoSTMalloc：
- 避免小对象的堆分配
- 更好的缓存局部性
- 减少内存碎片

### 移动语义

所有容器支持移动：
- 避免不必要的拷贝
- O(1) 所有权转移
- 现代 C++ 最佳实践

## 使用场景

### 临时缓冲区

```cpp
skia_private::AutoSTArray<256, uint8_t> buffer;
buffer.reset(neededSize);
// 自动决定栈或堆
```

### C API 封装

```cpp
void closeFd(int* fd) { close(*fd); }
SkAutoTCallVProc<int, closeFd> autoFd(new int(open(...)));
```

### 数组生成

```cpp
auto lookupTable = SkMakeArray<256>([](int i) {
    return computeLookup(i);
});
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/base/SkTArray.h` | 功能更强的动态数组 |
| `include/private/base/SkTDArray.h` | POD 类型专用数组 |
| `include/private/base/SkMalloc.h` | 底层内存分配 |

## 注意事项

1. **AutoTMalloc/AutoSTMalloc**: 仅用于 POD 类型
2. **栈大小**: AutoST* 容器可能消耗大量栈空间
3. **异常安全**: 大多数操作是强异常安全的
4. **线程安全**: 非线程安全，需要外部同步
5. **迭代器失效**: 重新分配会使指针失效

## 最佳实践

1. **优先使用栈优化版本**: AutoSTArray 而非 AutoTArray（对小数组）
2. **POD 类型用 AutoTMalloc**: 避免不必要的构造/析构
3. **合理预估栈大小**: 避免栈溢出
4. **利用移动语义**: 返回值使用 std::move（虽然通常自动）
5. **constexpr 数组**: 编译期常量用 SkMakeArray
