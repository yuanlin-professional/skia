# SkBitSet

> 源文件: src/utils/SkBitSet.h

## 概述

`SkBitSet` 是 Skia 图形库中实现的高效位集合(bit set)数据结构,用于在紧凑的内存空间中存储和操作布尔值集合。该类通过位运算提供了快速的集合操作,广泛应用于标记、状态管理和集合运算等场景。

作为一个完整的位集合实现,`SkBitSet` 提供了设置、清除、测试、遍历等核心操作,并通过位级别的紧凑存储实现了极高的内存效率。

## 架构位置

```
src/
  └── utils/
      ├── SkBitSet.h        # 位集合实现(本文件)
      ├── SkBitArray.h      # 其他位操作工具
      └── ...
```

`SkBitSet` 位于 Skia 的实用工具层,为上层算法提供高效的位集合数据结构支持。

## 主要类与结构体

### `SkBitSet`

核心位集合类,提供完整的位操作接口。

#### 构造与析构

```cpp
explicit SkBitSet(size_t size);  // 创建指定大小的位集合
SkBitSet(const SkBitSet&) = delete;  // 禁止拷贝构造
SkBitSet(SkBitSet&& that);  // 支持移动构造
~SkBitSet() = default;  // 默认析构
```

#### 成员变量

```cpp
private:
    size_t fSize;  // 位集合的大小(位数)
    using Chunk = uint32_t;  // 存储单元类型(32位)
    std::unique_ptr<Chunk, SkOverloadedFunctionObject<void(void*), sk_free>> fChunks;
```

**设计要点**:
- 使用 `uint32_t` 作为存储块(Chunk),每块存储 32 位
- 使用 `std::unique_ptr` 管理内存,自动释放
- 自定义删除器使用 `sk_free`,配合 `sk_calloc_throw` 分配

## 公共 API 函数

### 位操作

#### `set(size_t index)`
设置指定位为 true:
```cpp
void set(size_t index);  // 设置单个位
void set();              // 设置所有位
```

#### `reset(size_t index)`
清除指定位为 false:
```cpp
void reset(size_t index);  // 清除单个位
void reset();              // 清除所有位
```

#### `test(size_t index)`
测试指定位的值:
```cpp
bool test(size_t index) const;
```

### 查询操作

#### `size()`
返回位集合的大小:
```cpp
size_t size() const { return fSize; }
```

#### `findFirst()`
查找第一个被设置的位:
```cpp
OptionalIndex findFirst();  // 返回 std::optional<size_t>
```

#### `findFirstUnset()`
查找第一个未设置的位:
```cpp
OptionalIndex findFirstUnset();
```

### 遍历操作

#### `forEachSetIndex(FN f)`
遍历所有被设置的位:
```cpp
template<typename FN>
void forEachSetIndex(FN f) const;
```

**使用示例**:
```cpp
SkBitSet bits(100);
bits.set(5);
bits.set(10);
bits.set(42);

bits.forEachSetIndex([](size_t index) {
    printf("Bit %zu is set\n", index);
});
// 输出: Bit 5 is set, Bit 10 is set, Bit 42 is set
```

### 比较操作

```cpp
bool operator==(const SkBitSet& that) const;
bool operator!=(const SkBitSet& that) const;
```

## 内部实现细节

### 存储结构

位集合使用**分块存储**(chunked storage)策略:

```
位索引:  0  1  2  ... 31 | 32 33 34 ... 63 | 64 65 ...
         [--- Chunk 0 ---] [--- Chunk 1 ---] [--- Chunk 2 ---]
```

每个 `Chunk`(uint32_t)存储 32 位,位集合根据大小分配对应数量的 Chunk。

### 位索引计算

```cpp
// 计算位所在的 Chunk
Chunk* chunkFor(size_t index) const {
    return fChunks.get() + (index / kChunkBits);  // kChunkBits = 32
}

// 计算位在 Chunk 中的掩码
static constexpr Chunk ChunkMaskFor(size_t index) {
    return (Chunk)1 << (index & (kChunkBits-1));
}
```

**示例**:
- 位索引 5: Chunk 0, 掩码 `1 << 5 = 0x20`
- 位索引 35: Chunk 1, 掩码 `1 << 3 = 0x08`

### set() 实现

```cpp
void set(size_t index) {
    SkASSERT(index < fSize);
    *this->chunkFor(index) |= ChunkMaskFor(index);  // 位或运算
}
```

使用**位或**(`|=`)操作设置特定位,不影响其他位。

### reset() 实现

```cpp
void reset(size_t index) {
    SkASSERT(index < fSize);
    *this->chunkFor(index) &= ~ChunkMaskFor(index);  // 位与非运算
}
```

使用**位与非**(`&= ~`)操作清除特定位。

### test() 实现

```cpp
bool test(size_t index) const {
    SkASSERT(index < fSize);
    return SkToBool(*this->chunkFor(index) & ChunkMaskFor(index));
}
```

使用**位与**(`&`)操作检测位是否被设置。

### findFirst() 实现

```cpp
OptionalIndex findFirst() {
    const Chunk* chunks = fChunks.get();
    const size_t numChunks = NumChunksFor(fSize);
    for (size_t i = 0; i < numChunks; ++i) {
        if (Chunk chunk = chunks[i]) {  // 找到非零块
            const size_t bitIndex = i * kChunkBits + SkCTZ(chunk);
            return OptionalIndex(bitIndex);
        }
    }
    return OptionalIndex();  // 未找到
}
```

**关键技术**:
- `SkCTZ(chunk)`: Count Trailing Zeros,计算最低位 1 的位置
- 利用硬件指令(如 x86 的 `bsf`)实现高效查找

### forEachSetIndex() 实现

```cpp
template<typename FN>
void forEachSetIndex(FN f) const {
    const Chunk* chunks = fChunks.get();
    const size_t numChunks = NumChunksFor(fSize);
    for (size_t i = 0; i < numChunks; ++i) {
        if (Chunk chunk = chunks[i]) {
            const size_t index = i * kChunkBits;
            for (size_t j = 0; j < kChunkBits; ++j) {
                if (0x1 & (chunk >> j)) {
                    f(index + j);
                }
            }
        }
    }
}
```

**优化**:
- 先检查整个 Chunk 是否为零,跳过空块
- 逐位检查非零块中的每一位

## 依赖关系

### Skia 内部依赖

```cpp
#include "include/private/base/SkMalloc.h"    // sk_calloc_throw, sk_free
#include "include/private/base/SkTemplates.h" // SkOverloadedFunctionObject
#include "src/base/SkMathPriv.h"              // SkCTZ
```

### 标准库依赖

```cpp
#include <climits>    // CHAR_BIT
#include <cstring>    // memset, memcmp
#include <limits>     // std::numeric_limits
#include <memory>     // std::unique_ptr
#include <optional>   // std::optional (C++17)
```

## 设计模式与设计决策

### 1. RAII 内存管理

使用 `std::unique_ptr` 自动管理内存:
```cpp
std::unique_ptr<Chunk, SkOverloadedFunctionObject<void(void*), sk_free>> fChunks;
```

**优点**:
- 自动释放内存,避免泄漏
- 异常安全
- 移动语义支持

### 2. 移动语义优化

```cpp
SkBitSet(SkBitSet&& that) { *this = std::move(that); }
SkBitSet& operator=(SkBitSet&& that) {
    if (this != &that) {
        this->fSize = that.fSize;
        this->fChunks = std::move(that.fChunks);
        that.fSize = 0;
    }
    return *this;
}
```

支持高效的移动操作,避免不必要的内存拷贝。

### 3. 禁止拷贝

```cpp
SkBitSet(const SkBitSet&) = delete;
SkBitSet& operator=(const SkBitSet&) = delete;
```

**理由**:
- 避免意外的深拷贝开销
- 强制使用移动语义或引用传递
- 提高代码性能意识

### 4. 模板回调模式

```cpp
template<typename FN>
void forEachSetIndex(FN f) const;
```

使用模板接受任意可调用对象,支持 lambda、函数指针、仿函数等。

## 性能考量

### 内存效率

**存储密度**: 每个位占用 1 bit,是 `bool` 数组的 1/8:
```
SkBitSet(1000)     -> 1000 bits  = 125 bytes
std::vector<bool>  -> 1000 bits  = 125 bytes (类似实现)
bool[1000]         -> 1000 bytes = 1000 bytes (8倍开销)
```

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| `set(index)` | O(1) | 常数时间位操作 |
| `reset(index)` | O(1) | 常数时间位操作 |
| `test(index)` | O(1) | 常数时间位操作 |
| `set()` / `reset()` | O(n/32) | 按 Chunk 批量操作 |
| `findFirst()` | O(n/32) | 最坏情况遍历所有 Chunk |
| `forEachSetIndex()` | O(n/32 + m) | m 为设置的位数 |

### 缓存友好性

- **紧凑存储**: 连续的内存布局,缓存命中率高
- **块级操作**: 以 32 位为单位操作,减少内存访问次数
- **跳过空块**: 在遍历时跳过为 0 的 Chunk,提高效率

### 硬件加速

- **SkCTZ**: 使用硬件 CTZ 指令(x86 的 `bsf`, ARM 的 `clz`)
- **位操作**: 编译器优化为高效的位指令

## 相关文件

### Skia 内部使用场景

1. **图形裁剪**: 标记哪些区域需要绘制
2. **字形缓存**: 标记字形是否已加载
3. **资源管理**: 跟踪资源使用状态
4. **优化算法**: 集合运算和快速查找

### 替代方案

- `std::vector<bool>`: C++ 标准库的位集合特化,但接口不同
- `std::bitset<N>`: 编译时固定大小的位集合
- `boost::dynamic_bitset`: 动态大小的位集合(外部库)

`SkBitSet` 的优势在于与 Skia 内存分配器集成,并提供特定于 Skia 需求的 API。

### 典型使用模式

```cpp
// 标记活跃的字形
SkBitSet activeGlyphs(65536);  // Unicode BMP
for (uint16_t glyph : textGlyphs) {
    activeGlyphs.set(glyph);
}

// 批量处理
activeGlyphs.forEachSetIndex([&](size_t glyphIndex) {
    loadGlyph(glyphIndex);
});

// 查找第一个未加载的字形
auto firstUnloaded = activeGlyphs.findFirstUnset();
if (firstUnloaded.has_value()) {
    loadGlyph(*firstUnloaded);
}
```

`SkBitSet` 是 Skia 中高效的位集合实现,通过紧凑的存储和位级别的操作,为各种标记和集合运算场景提供了出色的性能和内存效率。
