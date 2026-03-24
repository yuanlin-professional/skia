# SkTDArray - POD 类型动态数组

> 源文件: `include/private/base/SkTDArray.h`

## 概述

SkTDArray 是一个专为 POD（Plain Old Data）类型设计的动态数组容器，类似于 std::vector 但不调用元素的构造和析构函数。所有对象通过原始 memcpy 进行移动，新创建的对象包含未初始化的内存。该容器通过 SkTDStorage 实现底层存储管理。

## 架构位置

- **所属子系统**: 基础容器工具 (Base Container Utilities)
- **层级**: 私有头文件，位于 `include/private/base/` 目录
- **依赖层次**: 底层数组容器，被需要高性能 POD 存储的模块使用

## 主要类与结构体

### SkTDStorage

底层类型无关的存储管理类。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fSizeOfT | const int | 元素大小（字节），不可变 |
| fStorage | std::byte* | 指向分配内存的指针 |
| fCapacity | int | 已分配容量（元素数量） |
| fSize | int | 当前元素数量 |

**设计要点**:
- 类型擦除设计，不使用模板
- 存储原始字节，不关心元素类型
- 提供类型安全的 SkTDArray 封装

### SkTDArray<T>

类型安全的 POD 数组模板类。

**模板参数**:
- `T`: 元素类型，必须是可通过 memcpy 移动的类型

**继承关系**: 无继承，包含一个 SkTDStorage 成员

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fStorage | SkTDStorage | 底层存储对象 |

## SkTDStorage 公共 API

### 构造与赋值

```cpp
explicit SkTDStorage(int sizeOfT)
SkTDStorage(const void* src, int size, int sizeOfT)
```

- **第一个**: 创建指定元素大小的空存储
- **第二个**: 从原始内存拷贝创建

支持拷贝和移动语义。

### 容量管理

```cpp
void reserve(int newCapacity)
void shrink_to_fit()
void resize(int newSize)
```

- **reserve**: 预留至少 newCapacity 的容量
- **shrink_to_fit**: 释放多余容量，使 capacity == size
- **resize**: 改变元素数量，可能重新分配

### 插入操作

```cpp
void* prepend()
void append()
void append(int count)
void* append(const void* src, int count)
void* insert(int index)
void* insert(int index, int count, const void* src)
```

- **prepend**: 在开头插入一个未初始化元素
- **append**: 在末尾添加元素
- **insert**: 在指定位置插入元素
- 返回指向新元素的 void* 指针

### 删除操作

```cpp
void erase(int index, int count)
void removeShuffle(int index)
void pop_back()
```

- **erase**: 删除 [index, index+count) 范围的元素
- **removeShuffle**: 删除 index 处元素，用最后一个元素替换（O(1)）
- **pop_back**: 删除最后一个元素

## SkTDArray<T> 公共 API

### 构造函数

```cpp
SkTDArray()
SkTDArray(const T src[], int count)
SkTDArray(const std::initializer_list<T>& list)
```

- **默认构造**: 创建空数组
- **数组构造**: 从 C 数组拷贝
- **初始化列表**: 从 `{...}` 语法构造

### 元素访问

```cpp
T& operator[](int index)
const T& operator[](int index) const
T& back()
const T& back() const
```

- **operator[]**: 随机访问，调试模式有边界检查
- **back**: 访问最后一个元素，要求非空

### 迭代器

```cpp
T* begin() / const T* begin() const
T* end() / const T* end() const
T* data() / const T* data() const
```

- 提供标准迭代器接口
- 支持范围 for 循环

### 容量与大小

```cpp
bool empty() const
int size() const
int capacity() const
size_t size_bytes() const
void clear()
void reset()
void resize(int count)
void reserve(int n)
void shrink_to_fit()
```

- **clear**: 清空元素但保留容量
- **reset**: 清空元素并释放内存
- **resize**: 改变大小，新元素未初始化
- **reserve**: 预留容量

### 添加元素

```cpp
T* append()
T* append(int count)
T* append(int count, const T* src)
void push_back(const T& v)
```

- **append()**: 添加一个未初始化元素，返回指针
- **append(count)**: 添加 count 个未初始化元素
- **append(count, src)**: 从 src 拷贝 count 个元素
- **push_back**: 添加元素并赋值

### 插入与删除

```cpp
T* insert(int index)
T* insert(int index, int count, const T* src)
void remove(int index, int count = 1)
void removeShuffle(int index)
void pop_back()
```

### 栈操作

```cpp
void push_back(const T& v)
void pop_back()
```

SkTDArray 可以用作栈。

## 内部实现细节

### 类型擦除模式

SkTDStorage 使用类型擦除：
```cpp
class SkTDStorage {
    const int fSizeOfT;  // 编译期传入
    std::byte* fStorage;  // 原始字节存储
};
```

优点：
- 减少模板代码膨胀
- 所有类型共享相同的核心逻辑
- 易于调试和维护

### 内存管理策略

#### 增长策略

虽然代码中未明确指定，但通常采用几何增长：
- 每次重新分配时容量翻倍
- 减少频繁分配的开销
- 与 std::vector 行为类似

#### 移动语义

```cpp
void moveTail(int dstIndex, int tailStart, int tailEnd)
```

使用 `memmove` 进行元素移动：
- 处理重叠内存区域
- 高效的批量移动
- 不调用移动构造函数

#### 拷贝操作

```cpp
void copySrc(int dstIndex, const void* src, int count)
```

使用 `memcpy` 进行元素拷贝：
- 假设 T 可按位拷贝
- 不调用拷贝构造函数
- 对 POD 类型最高效

### 边界检查

使用 `sk_collection_check_bounds` 宏：
```cpp
T& operator[](int index) {
    return this->data()[sk_collection_check_bounds(index, this->size())];
}
```

- 调试构建中检查
- 发布构建中可能优化掉

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/private/base/SkAPI.h` | 提供 SK_SPI 宏 |
| `include/private/base/SkAssert.h` | 提供断言 |
| `include/private/base/SkDebug.h` | 提供调试工具 |
| `include/private/base/SkTo.h` | 类型安全转换 |
| `<initializer_list>` | 初始化列表支持 |

### 被依赖的模块

SkTDArray 适用于：
- 存储基本类型（int, float, 指针等）
- 存储简单结构体（无析构函数）
- 需要最大性能的场景
- 与 C API 交互

## 设计模式与设计决策

### 为什么需要 SkTDArray

与 std::vector 的区别：

| 特性 | SkTDArray | std::vector |
|------|-----------|-------------|
| 构造函数调用 | 不调用 | 调用 |
| 析构函数调用 | 不调用 | 调用 |
| 移动方式 | memcpy | 移动构造 |
| 新元素状态 | 未初始化 | 默认构造 |
| 适用类型 | POD/Trivial | 任意类型 |

**使用场景**:
- 已知元素是 POD 类型
- 不需要构造/析构开销
- 需要最大性能
- 处理原始数据块

### removeShuffle 的设计

```cpp
void removeShuffle(int index) {
    fStorage.removeShuffle(index);
}
```

实现：用最后一个元素覆盖要删除的元素。

**优点**:
- O(1) 时间复杂度
- 无需移动其他元素

**缺点**:
- 不保持元素顺序

**适用场景**: 元素顺序不重要的集合。

### 友元函数 swap

```cpp
template <typename T>
static inline void swap(SkTDArray<T>& a, SkTDArray<T>& b) {
    a.swap(b);
}
```

提供 ADL（Argument-Dependent Lookup）查找的 swap。

## 性能考量

### 内存布局

```cpp
sizeof(SkTDArray<int>) == sizeof(SkTDStorage)
                        == sizeof(int) + sizeof(std::byte*) + 2*sizeof(int)
                        ≈ 20 字节（32位）或 24 字节（64位）
```

紧凑的内存布局，适合值语义传递。

### 操作复杂度

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| push_back | 摊销 O(1) | 可能触发重新分配 |
| pop_back | O(1) | 不释放内存 |
| insert | O(n) | 需要移动后续元素 |
| remove | O(n) | 需要移动后续元素 |
| removeShuffle | O(1) | 不保持顺序 |
| operator[] | O(1) | 直接索引 |

### 与 std::vector 的性能比较

对于 POD 类型：
- **SkTDArray 更快**: 无构造/析构开销
- **内存使用相同**: 两者都是动态数组
- **代码生成更简洁**: 无复杂的构造逻辑

对于非 POD 类型：
- **不应使用 SkTDArray**: 会导致未定义行为
- **std::vector 是唯一选择**

## 使用场景

### 存储原始数据

```cpp
SkTDArray<uint8_t> pixels;
pixels.resize(width * height * 4);
// 直接写入像素数据
```

### 索引数组

```cpp
SkTDArray<int> indices;
indices.push_back(0);
indices.push_back(1);
indices.push_back(2);
```

### 临时缓冲区

```cpp
SkTDArray<float> tempBuffer;
tempBuffer.reserve(1024);
// 使用 tempBuffer 进行计算
```

### 指针集合

```cpp
SkTDArray<SkPath*> paths;
paths.append(pathCount);
for (int i = 0; i < pathCount; ++i) {
    paths[i] = new SkPath;
}
// 注意：需要手动 delete
```

## 常见陷阱

### 陷阱1：未初始化的元素

```cpp
SkTDArray<int> arr;
arr.append();  // 添加未初始化的 int
int value = arr[0];  // 读取垃圾值！
```

**解决方案**: 添加后立即初始化，或使用 push_back。

### 陷阱2：使用非 POD 类型

```cpp
SkTDArray<std::string> strings;  // 错误！std::string 不是 POD
strings.append();  // 未定义行为：析构函数未调用
```

**解决方案**: 对非 POD 类型使用 SkTArray。

### 陷阱3：悬空指针

```cpp
SkTDArray<int*> ptrs;
{
    int x = 42;
    ptrs.push_back(&x);
}  // x 销毁
int value = *ptrs[0];  // 悬空指针！
```

### 陷阱4：removeShuffle 改变顺序

```cpp
SkTDArray<int> arr = {1, 2, 3, 4, 5};
arr.removeShuffle(1);  // 删除 2
// arr 现在可能是 {1, 5, 3, 4}，不是 {1, 3, 4, 5}
```

## 最佳实践

1. **仅用于 POD 类型**: 确认类型是 trivially copyable
2. **初始化元素**: append() 后立即赋值
3. **预留容量**: 已知大小时使用 reserve()
4. **考虑 removeShuffle**: 顺序不重要时用于高效删除
5. **避免频繁插入**: insert 操作代价高

## 类型要求

T 必须满足：
- **Trivially copyable**: 可按位拷贝
- **Trivially destructible**: 无需析构
- **无构造副作用**: 未初始化状态下也安全

典型合法类型：
- 基本类型：int, float, double, pointer, enum
- POD 结构体：只包含 POD 成员，无虚函数，无自定义构造/析构

## 调试支持

### 边界检查

在调试模式下：
```cpp
arr[10];  // 如果 size() < 11，触发断言或异常
```

### 空数组检查

```cpp
arr.back();  // 如果 empty()，调试模式下报错
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/base/SkTArray.h` | 用于非 POD 类型的动态数组 |
| `src/core/SkTDArray.cpp` | SkTDStorage 的实现 |
| `include/private/base/SkTemplates.h` | 提供其他模板容器 |

## 迁移指南

### 从 std::vector 迁移

如果你的 std::vector 满足：
- 元素是 POD 类型
- 不依赖默认构造
- 性能关键

可以考虑迁移到 SkTDArray：

```cpp
// 之前
std::vector<int> vec;
vec.push_back(42);

// 之后
SkTDArray<int> arr;
arr.push_back(42);  // API 基本兼容
```

### 到 SkTArray 的升级

如果需要非 POD 类型支持：
```cpp
// SkTDArray<std::string> strings;  // 错误
SkTArray<std::string> strings;  // 正确
```

## 注意事项

1. **不适合复杂类型**: 有虚函数、自定义构造/析构的类型禁用
2. **内存未初始化**: append() 返回的内存内容不确定
3. **异常安全**: 不提供强异常保证（但 POD 通常不抛异常）
4. **线程安全**: 非线程安全，需要外部同步
5. **迭代器失效**: 重新分配后所有指针/迭代器失效
