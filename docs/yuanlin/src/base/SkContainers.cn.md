# SkContainers - 容器内存分配工具
> 源文件: `src/base/SkContainers.cpp`

## 概述
SkContainers 模块提供了 Skia 容器类使用的底层内存分配工具。它包含 SkContainerAllocator 类用于管理容器的增长策略和容量计算，以及两个全局内存分配函数用于容器的初始分配。该模块还实现了容器溢出时的错误报告机制。这些工具确保 Skia 的容器类（如 TArray）能够安全、高效地管理动态内存。

## 架构位置
SkContainers 位于 Skia 基础容器支持模块（src/base）中，是容器内存管理的核心层。它为 TArray、THashMap、STArray 等动态容器提供统一的内存分配和增长策略，确保内存使用的安全性和高效性。

## 主要类与函数

### SkContainerAllocator
容器内存分配器类，负责计算容量和分配内存。

**关键成员变量** (在头文件中定义):
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fSizeOfT | size_t | 元素大小（字节） |
| fMaxCapacity | int | 最大容量（元素数量） |

**常量**:
```cpp
static constexpr size_t kCapacityMultiple = 8;  // 容量对齐倍数
```

## 公共 API 函数

### SkContainerAllocator 方法

#### `SkSpan<std::byte> allocate(int capacity, double growthFactor)`
- **功能**: 分配指定容量的内存，可选应用增长因子
- **参数**:
  - capacity: 请求的容量（元素数量）
  - growthFactor: 增长因子（≥ 1.0）
- **返回值**: 分配的内存块（以字节 span 表示）
- **断言**:
  - capacity >= 0
  - growthFactor >= 1.0
  - capacity <= fMaxCapacity
- **行为**: 如果 growthFactor > 1.0 且 capacity > 0，先应用增长因子

#### `size_t roundUpCapacity(int64_t capacity) const`
- **功能**: 将容量向上对齐到 kCapacityMultiple 的倍数
- **参数**: capacity - 原始容量
- **返回值**: 对齐后的容量
- **边界处理**: 如果对齐后超过 fMaxCapacity，返回 fMaxCapacity

#### `size_t growthFactorCapacity(int capacity, double growthFactor) const`
- **功能**: 应用增长因子并对齐容量
- **参数**:
  - capacity: 当前容量
  - growthFactor: 增长因子
- **返回值**: 增长并对齐后的容量
- **实现**: `roundUpCapacity(capacity * growthFactor)`

### 全局内存分配函数

#### `SkSpan<std::byte> sk_allocate_canfail(size_t size)`
- **功能**: 分配内存，失败返回空 span（不抛异常）
- **参数**: size - 请求的字节数
- **返回值**: 成功返回内存 span，失败返回空 span
- **最小大小**: 至少分配 kMinBytes (alignof(max_align_t)) 字节
- **实际大小**: 返回的 span 可能大于请求（基于 malloc 实际分配）

#### `SkSpan<std::byte> sk_allocate_throw(size_t size)`
- **功能**: 分配内存，失败抛出异常
- **参数**: size - 请求的字节数
- **返回值**: 内存 span（非空）
- **异常**: 分配失败时抛出 std::bad_alloc
- **特殊处理**: size == 0 时返回空 span（不分配）

#### `void sk_report_container_overflow_and_die()`
- **功能**: 报告容器溢出错误并终止程序
- **行为**: 调用 SK_ABORT("Requested capacity is too large.")
- **用途**: 当请求的容量超过容器限制时调用

## 内部实现细节

### 最小分配大小
```cpp
constexpr size_t kMinBytes = alignof(max_align_t);
```

**目的**: 确保 malloc 返回的内存正确对齐
- x86-64: max_align_t 通常是 16 字节
- 确保任何类型都能安全地放置在分配的内存中
- 避免未对齐访问导致的性能下降或崩溃

### complete_size 辅助函数
```cpp
SkSpan<std::byte> complete_size(void* ptr, size_t size) {
    if (ptr == nullptr) {
        return {};
    }
    return {static_cast<std::byte*>(ptr), sk_malloc_size(ptr, size)};
}
```

**功能**: 获取实际分配的内存大小
- **sk_malloc_size**: 平台特定函数，返回 malloc 实际分配的大小
- 大多数分配器会过度分配（round up）
- 容器可以利用额外空间，减少重新分配

**示例**:
```cpp
void* ptr = malloc(10);  // 请求 10 字节
sk_malloc_size(ptr, 10); // 可能返回 16 字节（实际分配）
```

### 容量对齐策略
```cpp
size_t SkContainerAllocator::roundUpCapacity(int64_t capacity) const {
    if (capacity < fMaxCapacity - kCapacityMultiple) {
        return SkAlignTo(capacity, kCapacityMultiple);
    }
    return SkToSizeT(fMaxCapacity);
}
```

**为何对齐到 8**:
- 减少重新分配次数
- 与缓存行大小相关（64 字节 / 8 元素）
- 简化容量计算

**边界处理**:
- 避免对齐后溢出 fMaxCapacity
- 如果 capacity + kCapacityMultiple > fMaxCapacity，直接返回 fMaxCapacity

### 增长因子应用
```cpp
size_t SkContainerAllocator::growthFactorCapacity(int capacity, double growthFactor) const {
    const int64_t capacityGrowth = static_cast<int64_t>(capacity * growthFactor);
    return this->roundUpCapacity(capacityGrowth);
}
```

**为何使用 int64_t**:
- 防止乘法溢出（32 位 int × double 可能溢出）
- size_t 在不同平台大小不同（32/64 位）
- 统一使用 64 位整数进行中间计算

**典型增长因子**:
- 1.5: 保守增长，内存友好
- 2.0: 标准增长（std::vector 常用）

### allocate 实现
```cpp
SkSpan<std::byte> SkContainerAllocator::allocate(int capacity, double growthFactor) {
    SkASSERT(capacity >= 0);
    SkASSERT(growthFactor >= 1.0);
    SkASSERT_RELEASE(capacity <= fMaxCapacity);

    if (growthFactor > 1.0 && capacity > 0) {
        capacity = this->growthFactorCapacity(capacity, growthFactor);
    }

    return sk_allocate_throw(capacity * fSizeOfT);
}
```

**流程**:
1. 验证参数
2. 如果需要增长，应用增长因子
3. 计算字节数（capacity × fSizeOfT）
4. 调用 sk_allocate_throw 分配内存

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkContainers.h | SkContainerAllocator 声明 |
| include/private/base/SkAlign.h | SkAlignTo 对齐工具 |
| include/private/base/SkAssert.h | 断言宏 |
| include/private/base/SkMalloc.h | sk_malloc_canfail, sk_malloc_throw, sk_malloc_size |
| include/private/base/SkTo.h | SkToSizeT 类型转换 |
| <algorithm> | std::max |
| <cstddef> | std::byte, size_t |

### 被依赖的模块
- include/private/base/SkTArray.h (TArray 容器)
- include/private/base/SkTHashMap.h (哈希表)
- src/core/SkTMultiMap.h (多重映射)
- 所有使用动态数组的 Skia 代码

## 设计模式与设计决策

### 分离策略与分配
SkContainerAllocator 分离了两个关注点：
- **策略**: 容量计算、增长因子
- **分配**: 实际内存分配

这种分离使得容器可以自定义增长策略，而不需要改变分配机制。

### 使用 SkSpan<std::byte>
返回 SkSpan 而非原始指针：
- **类型安全**: 包含大小信息
- **现代 C++**: 避免指针+大小对
- **边界检查**: 调试构建可以验证访问

### 增长因子的灵活性
允许自定义增长因子：
- TArray 默认使用 2.0（快速增长）
- 某些场景可能使用 1.5（内存节约）
- 可以禁用增长（growthFactor = 1.0）

### 容量对齐的权衡
对齐到 8 的倍数：
- **优点**: 减少重新分配，利用过度分配
- **缺点**: 可能浪费少量内存（最多 7 个元素）

### throw vs canfail 两种策略
提供两种分配方式：
- **sk_allocate_throw**: 用于构造函数、必需分配
- **sk_allocate_canfail**: 用于可选分配、预留空间

## 性能考量

### 过度分配的利用
```cpp
void* ptr = sk_malloc_canfail(100);
size_t actual = sk_malloc_size(ptr, 100);  // 可能是 112
```
容器可以使用额外的 12 字节，减少下次增长时的重新分配。

### 对齐的缓存效益
对齐到 8：
- 8 个 int (32 字节) 正好是半个缓存行
- 8 个 int64_t (64 字节) 正好是一个缓存行
- 减少缓存行分裂

### 增长因子的影响
**增长因子 2.0**:
- 增长序列: 1, 2, 4, 8, 16, 32, ...
- 快速达到目标容量（少量重新分配）
- 可能浪费 50% 的内存

**增长因子 1.5**:
- 增长序列: 1, 2, 3, 5, 8, 12, 18, 27, ...
- 更多重新分配
- 更好的内存利用率

### 64 位中间计算
使用 int64_t 避免溢出：
```cpp
int capacity = 100000000;
double growthFactor = 2.0;
// 直接乘可能溢出 int
int64_t safe = static_cast<int64_t>(capacity * growthFactor);
```

## 使用示例

### 基本分配
```cpp
SkContainerAllocator allocator(sizeof(int), INT_MAX / sizeof(int));

// 分配 10 个 int，应用 2.0 增长因子
auto span = allocator.allocate(10, 2.0);
// 实际分配可能是 20+ 个 int 的空间
```

### 容量计算
```cpp
SkContainerAllocator allocator(sizeof(float), 1000000);

// 对齐容量
size_t aligned = allocator.roundUpCapacity(15);  // 返回 16

// 增长容量
size_t grown = allocator.growthFactorCapacity(10, 1.5);  // 15 -> 16
```

### 容器使用
```cpp
class MyContainer {
    SkContainerAllocator fAllocator{sizeof(T), maxCapacity};
    T* fData = nullptr;
    int fSize = 0;
    int fCapacity = 0;

    void reserve(int newCapacity) {
        if (newCapacity > fCapacity) {
            auto span = fAllocator.allocate(newCapacity, 1.5);
            T* newData = reinterpret_cast<T*>(span.data());
            // 拷贝旧数据
            memcpy(newData, fData, fSize * sizeof(T));
            free(fData);
            fData = newData;
            fCapacity = span.size() / sizeof(T);
        }
    }
};
```

## 错误处理

### 容量溢出
```cpp
SkContainerAllocator allocator(sizeof(int), 100);
// 请求超过 maxCapacity
allocator.allocate(200, 1.0);  // SkASSERT_RELEASE 失败
```

### 分配失败
```cpp
// canfail 版本
auto span = sk_allocate_canfail(HUGE_SIZE);
if (span.empty()) {
    // 处理失败
}

// throw 版本
try {
    auto span = sk_allocate_throw(HUGE_SIZE);
} catch (std::bad_alloc&) {
    // 处理失败
}
```

### 容器溢出报告
```cpp
if (requestedCapacity > maxCapacity) {
    sk_report_container_overflow_and_die();
    // 不会返回
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkContainers.h | SkContainerAllocator 声明 |
| include/private/base/SkTArray.h | 主要使用者 |
| include/private/base/SkMalloc.h | 底层内存分配 |
| include/private/base/SkAlign.h | 对齐工具 |
| src/base/SkSafeMath.h | 安全算术运算 |
| tests/ContainersTest.cpp | 单元测试（如果存在） |

## 最佳实践

### 选择合适的 maxCapacity
```cpp
// 对于已知上限的容器
SkContainerAllocator allocator(sizeof(T), 1000);

// 对于无限制容器
SkContainerAllocator allocator(sizeof(T), INT_MAX / sizeof(T));
```

### 选择合适的增长因子
```cpp
// 频繁增长的容器（性能优先）
allocator.allocate(capacity, 2.0);

// 内存受限场景（内存优先）
allocator.allocate(capacity, 1.5);

// 精确分配（不增长）
allocator.allocate(capacity, 1.0);
```

### 利用过度分配
```cpp
auto span = sk_allocate_throw(100);
// span.size() 可能大于 100
// 容器应该使用 span.size() 作为实际容量
```

### 避免频繁小分配
```cpp
// 不好：每次增长 1 个元素
for (int i = 0; i < 1000; ++i) {
    allocator.allocate(i + 1, 1.0);
}

// 好：使用增长因子
allocator.allocate(capacity, 2.0);
```
