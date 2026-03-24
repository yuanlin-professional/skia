# SkTDArray (SkTDStorage)

> 源文件: `src/base/SkTDArray.cpp`

## 概述

SkTDArray.cpp 实现了 `SkTDStorage` 类，这是 Skia 的底层类型擦除动态数组存储引擎。`SkTDStorage` 为模板类 `SkTDArray<T>` 提供所有内存管理和数据操作的非模板化实现，通过将元素大小（`sizeOfT`）作为运行时参数来避免模板膨胀。

`SkTDArray<T>` 类似于 `std::vector<T>`，但专门设计用于 POD（Plain Old Data）类型——不需要调用构造函数或析构函数的原始数据对象。所有元素移动通过 `memcpy`/`memmove` 完成，新创建的元素包含未初始化的内存。

该实现文件约 238 行，头文件中的 `SkTDArray<T>` 模板类是一个薄封装层，将类型安全的 API 委托给 `SkTDStorage` 的类型擦除实现。

## 架构位置

```
SkTDArray<T> (模板头文件, 类型安全封装)
    │
    ▼
SkTDStorage (本文件, 类型擦除实现)
    │
    ├── sk_malloc_throw / sk_realloc_throw / sk_free (内存分配)
    └── memcpy / memmove (数据移动)
```

`SkTDArray` 被 Skia 内部广泛用于存储各种 POD 数据，如索引数组、坐标数组、颜色值数组等。与 `skia_private::TArray`（Skia 的通用动态数组）相比，`SkTDArray` 使用 `int` 而非 `size_t` 作为大小类型，且不调用构造/析构函数。

## 主要类与结构体

### SkTDStorage
```cpp
class SK_SPI SkTDStorage {
    const int fSizeOfT;            // 元素大小（字节数），构造时确定，不可变
    std::byte* fStorage{nullptr};  // 动态分配的存储缓冲区
    int fCapacity{0};              // 已分配的元素容量
    int fSize{0};                  // 逻辑元素数量 (fSize <= fCapacity)
};
```

### SkTDArray<T> (头文件中定义)
```cpp
template <typename T>
class SkTDArray {
    SkTDStorage fStorage;  // 底层存储
    // 所有操作委托给 fStorage，加上类型转换
};
```

## 公共 API 函数

### 构造与析构
| 方法 | 说明 |
|------|------|
| `SkTDStorage(int sizeOfT)` | 构造空存储，指定元素大小 |
| `SkTDStorage(const void* src, int size, int sizeOfT)` | 从源数据拷贝构造 |
| `SkTDStorage(const SkTDStorage&)` | 拷贝构造 |
| `SkTDStorage(SkTDStorage&&)` | 移动构造（窃取指针） |
| `operator=(const SkTDStorage&)` | 拷贝赋值 |
| `operator=(SkTDStorage&&)` | 移动赋值 |
| `~SkTDStorage()` | 析构（释放 `fStorage`） |

### 大小与容量管理
| 方法 | 说明 |
|------|------|
| `empty()` | 是否为空 |
| `size()` | 逻辑元素数量 |
| `clear()` | 将 `fSize` 置零（不释放内存） |
| `reset()` | 完全重置（释放内存并回到初始状态） |
| `resize(int newSize)` | 调整逻辑大小，必要时扩容 |
| `capacity()` | 当前已分配容量 |
| `reserve(int newCapacity)` | 预分配至少 newCapacity 的容量 |
| `shrink_to_fit()` | 收缩内存至恰好容纳当前元素 |
| `size_bytes()` | 当前数据占用的字节数 |

### 数据访问
| 方法 | 说明 |
|------|------|
| `data()` / `data() const` | 返回底层 `std::byte*` / `const std::byte*` |

### 元素插入
| 方法 | 说明 |
|------|------|
| `prepend()` | 在头部插入一个未初始化元素，返回指针 |
| `append()` | 在尾部追加一个未初始化元素 |
| `append(int count)` | 在尾部追加多个未初始化元素 |
| `append(const void* src, int count)` | 在尾部追加从 src 复制的 count 个元素 |
| `insert(int index)` | 在指定位置插入一个未初始化元素 |
| `insert(int index, int count, const void* src)` | 在指定位置插入 count 个元素 |
| `pop_back()` | 移除尾部元素（仅减小 fSize） |

### 元素删除
| 方法 | 说明 |
|------|------|
| `erase(int index, int count)` | 删除从 index 开始的 count 个元素（保持顺序） |
| `removeShuffle(int index)` | 删除指定位置的元素，用最后一个元素填补（不保持顺序） |

### 其他操作
| 方法 | 说明 |
|------|------|
| `swap(SkTDStorage& that)` | 与另一个存储交换内容 |
| `operator==(a, b)` | 按字节比较两个存储是否相等 |

## 内部实现细节

### 容量增长策略
`reserve()` 采用渐进式增长策略，避免频繁的重新分配：

```cpp
void SkTDStorage::reserve(int newCapacity) {
    if (newCapacity > fCapacity) {
        int expandedReserve = INT_MAX;  // 假设最大
        if (INT_MAX - newCapacity > 4) {
            int growth = 4 + ((newCapacity + 4) >> 2);  // 增长 25% + 4
            if (INT_MAX - newCapacity > growth) {
                expandedReserve = newCapacity + growth;
            }
        }
        // 对于单字节元素，向上对齐到 16 字节边界
        if (fSizeOfT == 1) {
            expandedReserve = (expandedReserve + 15) & ~15;
        }
        fCapacity = expandedReserve;
        fStorage = static_cast<std::byte*>(sk_realloc_throw(fStorage, bytes(fCapacity)));
    }
}
```

关键设计决策：
- 增长因子为 25%（`newCapacity / 4`）加上常数 4，兼顾小数组和大数组的效率
- 对于单字节元素（如 `SkTDArray<uint8_t>`），向上对齐到 16 字节，匹配 `max_align_t` 的常见大小，减少小数组的频繁 realloc
- 溢出保护：使用减法而非加法检查以避免有符号整数溢出

### 安全的大小计算
```cpp
int SkTDStorage::calculateSizeOrDie(int delta) {
    SkASSERT_RELEASE(-fSize <= delta);  // 确保不会变为负数
    uint32_t testCount = (uint32_t)fSize + (uint32_t)delta;
    SkASSERT_RELEASE(SkTFitsIn<int>(testCount));  // 确保结果可以放入 int
    return SkToInt(testCount);
}
```
使用 `uint32_t` 中间计算避免有符号整数溢出的未定义行为，然后检查结果是否仍在 `int` 范围内。

### 数据移动
```cpp
void SkTDStorage::moveTail(int to, int tailStart, int tailEnd) {
    if (to != tailStart && tailStart != tailEnd) {
        this->copySrc(to, this->address(tailStart), tailEnd - tailStart);
    }
}
void SkTDStorage::copySrc(int dstIndex, const void* src, int count) {
    memmove(this->address(dstIndex), src, this->bytes(count));
}
```
使用 `memmove`（而非 `memcpy`）处理所有内部数据移动，因为源和目标区域可能重叠（如插入和删除操作）。

### 拷贝赋值优化
```cpp
SkTDStorage& SkTDStorage::operator=(const SkTDStorage& that) {
    if (that.fSize <= fCapacity) {
        // 现有容量足够，直接覆盖数据
        fSize = that.fSize;
        if (fSize > 0) {
            memcpy(fStorage, that.data(), that.size_bytes());
        }
    } else {
        // 需要重新分配
        *this = SkTDStorage{that.data(), that.size(), that.fSizeOfT};
    }
    return *this;
}
```
当现有容量足够时避免重新分配，仅复制数据。

### 移动赋值
```cpp
SkTDStorage& SkTDStorage::operator=(SkTDStorage&& that) {
    if (this != &that) {
        this->~SkTDStorage();
        new (this) SkTDStorage{std::move(that)};
    }
    return *this;
}
```
使用析构+移动构造实现，确保旧内存被正确释放。

### removeShuffle 优化
```cpp
void SkTDStorage::removeShuffle(int index) {
    const int newCount = this->calculateSizeOrDie(-1);
    this->moveTail(index, fSize - 1, fSize);  // 用最后一个元素覆盖被删除的元素
    this->resize(newCount);
}
```
通过将最后一个元素移动到被删除位置来避免大量元素的移动，时间复杂度为 O(1)，但不保持元素顺序。适用于元素顺序不重要的场景。

## 依赖关系

- `include/private/base/SkTDArray.h` — 头文件，包含 `SkTDStorage` 和 `SkTDArray<T>` 声明
- `include/private/base/SkMalloc.h` — `sk_malloc_throw`、`sk_realloc_throw`、`sk_free` 内存分配函数
- `include/private/base/SkTFitsIn.h` — 整数范围检查工具
- `include/private/base/SkTo.h` — 安全的整数类型转换

## 设计模式与设计决策

### 类型擦除（Type Erasure）
`SkTDStorage` 通过运行时的 `fSizeOfT` 参数实现类型擦除，避免了每种元素类型生成独立的模板实例。所有内存操作（分配、复制、移动）都基于字节计算，与具体类型无关。这显著减少了代码膨胀（code bloat），对于一个被广泛使用的容器类尤为重要。

### POD 约束
不调用构造函数/析构函数是一个有意的设计约束。这使得所有数据移动可以使用 `memcpy`/`memmove`，比逐元素的构造/析构快得多。使用者必须确保存储的类型满足 POD 或 trivially copyable 要求。

### int 而非 size_t
使用 `int` 作为大小和索引类型是 Skia 的历史设计选择。`calculateSizeOrDie` 中的溢出检查确保了安全性，而 `int` 避免了 `size_t` 与有符号类型混用时的隐式转换问题。

### 就地析构+重建
`reset()` 和移动赋值使用 `this->~SkTDStorage(); new (this) SkTDStorage{...};` 模式，这是一种简洁但需谨慎使用的技术，确保所有成员正确重置。

## 性能考量

1. **25% 增长策略 + 常数 4**：在小数组时提供快速增长（常数 4 避免逐个增长），大数组时控制内存浪费在 25% 以内
2. **16 字节对齐**：单字节元素数组的容量向上对齐到 16 字节，匹配常见的 `max_align_t` 大小，减少小分配场景的 realloc 次数
3. **容量复用**：拷贝赋值在现有容量足够时直接覆盖，避免 free + malloc
4. **removeShuffle**：O(1) 删除操作，适合对顺序不敏感的场景
5. **clear vs reset**：`clear()` 仅置零大小（O(1)），保留分配内存供后续使用；`reset()` 释放内存回到初始状态
6. **shrink_to_fit**：在内存敏感场景下可主动收缩，但一般建议避免频繁调用
7. **memmove 而非 memcpy**：统一使用 `memmove` 简化了重叠区域的处理逻辑，现代 CPU 上 `memmove` 对非重叠区域的性能与 `memcpy` 基本持平

## 相关文件

- `/Users/yuanlin/workspace/skia/src/base/SkTDArray.cpp` — 本文件（实现）
- `/Users/yuanlin/workspace/skia/include/private/base/SkTDArray.h` — 头文件，包含 SkTDStorage 和 SkTDArray<T> 声明
- `/Users/yuanlin/workspace/skia/include/private/base/SkMalloc.h` — Skia 内存分配接口
- `/Users/yuanlin/workspace/skia/include/private/base/SkTArray.h` — Skia 的通用动态数组（支持非 POD 类型）
- `/Users/yuanlin/workspace/skia/include/private/base/SkTFitsIn.h` — 安全整数范围检查
