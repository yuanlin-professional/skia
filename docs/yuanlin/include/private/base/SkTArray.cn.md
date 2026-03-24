# SkTArray - 智能动态数组

> 源文件: `include/private/base/SkTArray.h`

## 概述

TArray 是 Skia 的主力动态数组容器，类似于 std::vector，支持任意类型的元素。它提供了完整的构造/析构语义、移动优化、栈存储优化（STArray）以及灵活的内存管理策略。TArray 根据类型是否可平凡重定位（trivially relocatable）自动选择最优的移动策略。

## 架构位置

- **所属子系统**: 核心容器库 (Core Container Library)
- **层级**: 私有头文件，位于 `include/private/base/` 目录，命名空间 `skia_private`
- **依赖层次**: 高级动态数组实现，被 Skia 全局广泛使用

## 主要类与结构体

### TArray<T, MEM_MOVE>

功能完整的动态数组模板类。

**模板参数**:
- `T`: 元素类型，可以是任意类型
- `MEM_MOVE`: 布尔值，控制移动方式
  - `true`: 使用 memcpy 按位拷贝（默认：`sk_is_trivially_relocatable_v<T>`）
  - `false`: 使用移动构造函数

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fData | T* | 指向元素数组的指针 |
| fSize | int | 当前元素数量 |
| fOwnMemory | uint32_t : 1 | 是否拥有内存（位域） |
| fCapacity | uint32_t : 31 | 已分配容量（位域） |
| fPoisoned | bool | ASAN 毒化状态（仅在 ASAN 构建中） |

### STArray<N, T, MEM_MOVE>

带栈存储优化的 TArray 子类。

**模板参数**:
- `N`: 请求的栈存储元素数
- `T`: 元素类型
- `MEM_MOVE`: 移动策略（同 TArray）

**继承关系**:
```cpp
STArray<N, T, MEM_MOVE>
  ├─ SkAlignedSTStorage<RoundUp<T>(N), T>  // 栈存储基类
  └─ TArray<T, MEM_MOVE>                    // 功能基类
```

**存储策略**:
- 元素数 <= N: 使用栈存储
- 元素数 > N: 自动切换到堆存储
- 缩小后可能切回栈存储

## 公共 API 函数

### 构造函数

```cpp
TArray()                                    // 空数组
explicit TArray(int reserveCount)          // 预留容量
TArray(const TArray& that)                 // 拷贝构造
TArray(TArray&& that)                      // 移动构造
TArray(const T* array, int count)          // 从 C 数组
TArray(SkSpan<const T> data)               // 从 span
TArray(std::initializer_list<T> data)      // 初始化列表
```

### 赋值运算符

```cpp
TArray& operator=(const TArray& that)      // 拷贝赋值
TArray& operator=(TArray&& that)           // 移动赋值
```

### 容量管理

```cpp
void reserve(int n)                        // 预留容量（可能增长）
void reserve_exact(int n)                  // 精确预留
void resize_back(int newCount)             // 调整大小
void clear()                               // 清空元素
void shrink_to_fit()                       // 释放多余容量
bool empty() const                         // 是否为空
int size() const                           // 元素数量
int capacity() const                       // 已分配容量
```

### 元素访问

```cpp
T& operator[](int i)                       // 索引访问
const T& operator[](int i) const
T& at(int i)                               // 带异常的访问
T& front()                                 // 首元素
const T& front() const
T& back()                                  // 尾元素
const T& back() const
T& fromBack(int i)                         // 倒数第 i 个
```

### 添加元素

```cpp
T& push_back()                             // 添加默认构造元素
T& push_back(const T& t)                   // 拷贝添加
T& push_back(T&& t)                        // 移动添加
template<typename... Args>
T& emplace_back(Args&&... args)            // 原位构造
T* push_back_n(int n)                      // 添加 n 个默认元素
T* push_back_n(int n, const T& t)          // 添加 n 个相同元素
T* push_back_n(int n, const T t[])         // 添加 n 个元素
T* move_back_n(int n, T* t)                // 移动添加 n 个
```

### 删除元素

```cpp
void pop_back()                            // 删除最后一个
void pop_back_n(int n)                     // 删除最后 n 个
void removeShuffle(int n)                  // 无序删除（O(1)）
```

### 批量操作

```cpp
void swap(TArray& that)                    // 交换
void move_back(TArray& that)               // 移动追加
void reset(int n)                          // 重置为 n 个默认元素
void reset(SkSpan<const T> src)            // 重置为副本
```

### 迭代器

```cpp
T* begin() / const T* begin() const
T* end() / const T* end() const
T* data() / const T* data() const
```

## 内部实现细节

### 内存管理策略

#### 增长因子

```cpp
static constexpr double kExactFit = 1.0;   // 精确适配
static constexpr double kGrowing = 1.5;    // 增长模式（1.5倍）
```

#### 容量计算

```cpp
static constexpr int kMinHeapAllocCount = 8;  // 最小堆分配
static constexpr int kMaxCapacity = ...;       // 最大容量
```

- 初次分配至少 8 个元素
- 几何增长避免频繁重新分配
- 最大容量受 INT_MAX 和 SIZE_MAX 限制

### 移动策略

#### MEM_MOVE = true（按位移动）

```cpp
void move(void* dst) {
    sk_careful_memcpy(dst, fData, Bytes(fSize));
}
```

- 使用 memcpy 批量移动
- 不调用移动构造/析构
- 适用于 trivially relocatable 类型

#### MEM_MOVE = false（构造移动）

```cpp
void move(void* dst) {
    for (int i = 0; i < this->size(); ++i) {
        new (static_cast<char*>(dst) + Bytes(i)) T(std::move(fData[i]));
        fData[i].~T();
    }
}
```

- 逐个调用移动构造
- 销毁源对象
- 适用于需要移动语义的复杂类型

### ASAN 支持

#### 内存毒化

```cpp
void poison() {
#ifdef SK_SANITIZE_ADDRESS
    if (fData && fCapacity > fSize) {
        sk_asan_poison_memory_region(this->end(), Bytes(fCapacity - fSize));
        fPoisoned = true;
    }
#endif
}
```

- 未使用的容量被"毒化"
- ASAN 检测越界访问
- 性能分析时的宝贵工具

#### 去毒化

操作前需要 `unpoison()`，操作后重新 `poison()`。

### 快速路径优化

#### push_back 的优化

```cpp
T& push_back(const T& t) {
    this->unpoison();
    T* newT;
    if (this->capacity() > fSize) SK_LIKELY {  // 快速路径
        newT = new (fData + fSize) T(t);
    } else {
        newT = this->growAndConstructAtEnd(t);  // 慢速路径
    }
    this->changeSize(fSize + 1);
    return *newT;
}
```

- **SK_LIKELY**: 提示编译器优化分支预测
- 有容量时避免重新分配逻辑

### CFI（Control Flow Integrity）禁用

```cpp
SK_NO_SANITIZE_CFI
static T* TCast(void* buffer) {
    return (T*)buffer;
}
```

- 未初始化内存转为 T* 会触发 CFI 警告
- 但在 TArray 中是安全的（构造前不访问虚函数）
- 显式禁用以避免误报

## 高级特性

### 受保护构造函数（STArray 使用）

```cpp
template <int InitialCapacity>
TArray(SkAlignedSTStorage<InitialCapacity, T>* storage, int size = 0)
```

- STArray 通过此接口使用栈存储
- fOwnMemory 设为 false
- 析构时不释放栈内存

### 两阶段构造

某些操作分为两步：
1. **preallocateNewData**: 分配新内存
2. **installDataAndUpdateCapacity**: 移动元素并切换指针

这允许在构造新元素后再提交更改。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `SkASAN.h` | 地址消毒器支持 |
| `SkAlignedStorage.h` | 栈存储对齐 |
| `SkAssert.h` | 断言 |
| `SkContainers.h` | 容器分配器 |
| `SkMalloc.h` | 内存分配 |
| `SkSpan_impl.h` | Span 支持 |
| `SkTypeTraits.h` | 类型特征检查 |

### 被依赖的模块

TArray 是 Skia 中最常用的容器：
- 图形对象集合
- 顶点和索引数组
- 临时计算缓冲区
- 几乎所有需要动态数组的场景

## 设计模式与设计决策

### 值语义 vs 引用语义

TArray 使用值语义：
- 拷贝构造深拷贝
- 赋值运算符深拷贝
- 移动操作转移所有权

### 零初始化 vs 默认构造

```cpp
void reset(int n) {
    // ...
    for (int i = 0; i < this->size(); ++i) {
        new (fData + i) T;  // 默认构造
    }
}
```

- 新元素总是默认构造的
- 不同于 SkTDArray（未初始化）

### SBO（Small Buffer Optimization）

STArray 实现 SBO：
```cpp
STArray<16, int> arr;  // 前 16 个元素在栈上
```

- 减少小对象的堆分配
- 更好的缓存局部性
- 透明的存储管理

### 容量舍入

```cpp
static constexpr int N = SkContainerAllocator::RoundUp<T>(Nreq);
```

- 容量向上舍入到分配器边界
- 利用对齐填充空间
- 减少内存浪费

## 性能考量

### 时间复杂度

| 操作 | 摊销复杂度 | 最坏情况 |
|------|-----------|---------|
| push_back | O(1) | O(n) |
| pop_back | O(1) | O(1) |
| operator[] | O(1) | O(1) |
| insert | O(n) | O(n) |
| removeShuffle | O(1) | O(1) |
| reserve | O(1) | O(n) |

### 内存开销

```cpp
sizeof(TArray<int>)
= sizeof(int*) + sizeof(int) + sizeof(uint32_t)
≈ 16 字节（64位系统）
```

### 与 std::vector 的比较

| 特性 | TArray | std::vector |
|------|--------|-------------|
| SBO 支持 | 是（STArray） | 否（标准） |
| 索引类型 | int | size_t |
| 增长因子 | 1.5 | 实现定义 |
| ASAN 集成 | 是 | 部分 |
| 可定制性 | 高 | 中 |

## 使用场景

### 通用容器

```cpp
skia_private::TArray<SkPoint> points;
points.push_back({10, 20});
points.emplace_back(30, 40);
```

### 小对象优化

```cpp
skia_private::STArray<4, SkRect> rects;  // 4个以内无堆分配
rects.push_back(rect1);
rects.push_back(rect2);
```

### 批量操作

```cpp
TArray<int> source, dest;
// 填充 source...
dest.move_back(source);  // 高效移动，source 变空
```

### 预留容量

```cpp
TArray<SkPath> paths;
paths.reserve(1000);  // 预先分配
for (int i = 0; i < 1000; ++i) {
    paths.emplace_back();  // 无重新分配
}
```

## 常见陷阱

### 陷阱1：迭代器失效

```cpp
TArray<int> arr = {1, 2, 3};
int* ptr = &arr[0];
arr.push_back(4);  // 可能重新分配
// ptr 可能已失效！
```

### 陷阱2：引用失效

```cpp
TArray<std::string> arr;
arr.push_back("hello");
const std::string& ref = arr.back();
arr.push_back("world");  // 重新分配
// ref 失效！
```

### 陷阱3：栈溢出

```cpp
STArray<1000000, int> huge;  // 栈上分配 4MB！
// 可能导致栈溢出
```

### 陷阱4：非 const 到 const

```cpp
void func(TArray<const int>& arr);

TArray<int> myArr;
func(myArr);  // 编译错误！TArray<int> != TArray<const int>
```

## 最佳实践

1. **小集合用 STArray**: 减少堆分配
2. **预留容量**: 已知大小时使用 reserve()
3. **使用 emplace_back**: 避免临时对象
4. **批量操作**: 利用 push_back_n 和 move_back
5. **注意引用生命周期**: 避免悬空引用
6. **选择正确的 MEM_MOVE**: 默认值通常正确

## 类型要求

### MEM_MOVE = true 的要求

T 必须是 trivially relocatable：
- 可按位拷贝
- 析构后原对象不再访问
- 大多数基本类型和 POD

### MEM_MOVE = false 的要求

T 必须：
- 可移动构造
- 可移动赋值
- 可析构

## 调试支持

### 边界检查

```cpp
T& operator[](int i) {
    return fData[sk_collection_check_bounds(i, this->size())];
}
```

### ASAN 集成

- 自动检测越界访问
- 使用后释放检测
- 双重释放检测

## 相关文件

| 文件 | 关系 |
|------|------|
| `SkTDArray.h` | POD 类型专用数组 |
| `SkTemplates.h` | 其他模板容器 |
| `SkContainers.h` | 容器分配策略 |
| `SkAlignedStorage.h` | STArray 的栈存储 |

## 平台相关说明

### Google3 栈限制

```cpp
#if defined(SK_BUILD_FOR_GOOGLE3)
    static constexpr int kMaxBytes = 4 * 1024;
```

- 限制栈分配到 4KB
- 超出部分自动使用堆
- 避免栈溢出

### 对齐要求

```cpp
static_assert(alignof(int) <= alignof(T*) || alignof(int) <= alignof(T));
```

- 确保 fSize 和 fStorage 的对齐兼容
- 利用填充字节增加栈容量

## 性能调优

### 减少重新分配

```cpp
arr.reserve(expectedSize);  // 预先分配
```

### 批量添加

```cpp
arr.push_back_n(1000);  // 一次分配 1000 个
```

### 使用移动语义

```cpp
arr.push_back(std::move(largeObject));  // 避免拷贝
```

### 选择合适的 STArray 大小

```cpp
// 分析实际使用情况
STArray<8, T> arr;  // 大多数情况 <= 8 个元素
```

## 注意事项

1. **线程安全**: 非线程安全，需要外部同步
2. **异常安全**: 提供强异常保证（在支持异常的构建中）
3. **内存对齐**: 元素按 T 的对齐要求对齐
4. **最大容量**: 受 INT_MAX 限制
5. **STArray 析构**: 必须确保栈上的 STArray 正确析构
