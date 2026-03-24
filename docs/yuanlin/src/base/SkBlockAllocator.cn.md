# SkBlockAllocator

> 源文件: `src/base/SkBlockAllocator.h`, `src/base/SkBlockAllocator.cpp`

## 概述

SkBlockAllocator 是 Skia 中的低级块分配器,提供动态尾部追踪的内存块管理功能。它自动创建和销毁内存块,支持空间预留、调整大小和释放操作,并假设分配对象的析构函数由外部调用。该分配器设计用于作为高级分配器的基础组件。

## 架构位置

- **所属子系统**: 基础设施层 (Base Infrastructure)
- **层级**: 核心内存管理组件
- **作用域**: 为 Skia 的高级分配器(如 SkArenaAlloc)提供底层内存块管理

## 主要类与结构体

### SkBlockAllocator

内存块分配器的主容器类,管理内存块的链表和增长策略。

**继承关系**: SkNoncopyable → SkBlockAllocator

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fTail | Block* | 指向当前活动块(尾部) |
| fHead | Block | 内联的头部块,避免初始堆分配 |
| fBlockIncrement | uint64_t:16 | 块大小增长单元 |
| fGrowthPolicy | uint64_t:2 | 增长策略(固定/线性/斐波那契/指数) |
| fN0, fN1 | uint64_t:23 | 增长序列的状态参数 |

### Block

单个内存块的表示,跟踪可用空间和已分配区域。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fNext/fPrev | Block* | 双向链表指针 |
| fSize | int | 块的总大小(包括头部) |
| fCursor | int | 下一次分配的偏移量 |
| fMetadata | int | 用户级元数据槽 |

### ByteRange

描述分配结果的元组结构。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fBlock | Block* | 拥有此分配的块 |
| fStart | int | 字节范围的起始偏移(含) |
| fAlignedOffset | int | 对齐后的实际数据偏移 |
| fEnd | int | 字节范围的结束偏移(不含) |

### GrowthPolicy 枚举

定义块大小增长策略:
- **kFixed**: 固定大小 (N)
- **kLinear**: 线性增长 (#blocks * N)
- **kFibonacci**: 斐波那契增长 (fibonacci(#blocks) * N)
- **kExponential**: 指数增长 (2^#blocks * N)

## 公共 API 函数

### `SkBlockAllocator(GrowthPolicy, size_t, size_t)`
- **功能**: 构造分配器,设置增长策略和初始块大小
- **参数**:
  - `policy`: 增长策略
  - `blockIncrementBytes`: 堆块大小增量
  - `additionalPreallocBytes`: 头部块的额外预分配空间
- **返回值**: 无

### `template <size_t Align, size_t Padding> ByteRange allocate(size_t size)`
- **功能**: 分配指定大小的内存,自动处理对齐和内存块扩展
- **参数**:
  - `Align`: 对齐要求(编译时常量)
  - `Padding`: 额外的填充字节,可用于存储元数据
  - `size`: 请求的字节数
- **返回值**: ByteRange 结构,包含分配的块、起始偏移、对齐偏移和结束偏移
- **约束**: size 不得超过 kMaxAllocationSize (512MB)

### `template <size_t Align, size_t Padding> void reserve(size_t size, ReserveFlags)`
- **功能**: 预留连续的可用空间,可能创建暂存块(scratch block)
- **参数**:
  - `size`: 需要预留的字节数
  - `flags`: 控制标志(是否忽略增长策略、是否忽略现有字节)
- **返回值**: 无

### `Block* currentBlock() / const Block* currentBlock() const`
- **功能**: 获取当前活动的尾部块
- **返回值**: 指向当前块的指针(永不为空)

### `void releaseBlock(Block* block)`
- **功能**: 释放指定块,可能将其转为暂存块以供重用
- **参数**: `block` - 要释放的块指针
- **返回值**: 无
- **特殊行为**: 如果是头部块,仅重置游标;否则可能保留为暂存块

### `void reset()`
- **功能**: 释放所有堆块并重置头部块到初始状态
- **返回值**: 无

### `void stealHeapBlocks(SkBlockAllocator* other)`
- **功能**: 将另一个分配器的所有堆块移交给当前分配器
- **参数**: `other` - 被窃取块的源分配器
- **返回值**: 无

### `Block* owningBlock<Align, Padding>(const void* ptr, int start)`
- **功能**: 根据分配指针和起始偏移,快速查找拥有块(常量时间)
- **参数**:
  - `ptr`: 之前返回的对齐指针
  - `start`: 原始 ByteRange 的 fStart 值
- **返回值**: 拥有此指针的 Block

### `Block* findOwningBlock(const void* ptr)`
- **功能**: 线性搜索找到包含指针的块(O(N) 复杂度)
- **参数**: `ptr` - 任意分配的指针
- **返回值**: 拥有此指针的 Block 或 nullptr

### `size_t totalSize() / totalUsableSpace() / totalSpaceInUse()`
- **功能**: 查询分配器的内存统计信息
- **返回值**:
  - `totalSize()`: 包括开销的总字节数
  - `totalUsableSpace()`: 可用于分配的总字节数
  - `totalSpaceInUse()`: 已预留的字节数

### `template<size_t Align, size_t Padding> static constexpr size_t BlockOverhead()`
- **功能**: 计算堆块的最小开销(编译时)
- **返回值**: 给定对齐和填充的块开销字节数

### `template<size_t Align, size_t Padding> static constexpr size_t Overhead()`
- **功能**: 计算预分配所需的最小字节数(编译时)
- **返回值**: 包括 SkBlockAllocator 实例本身的开销

## 内部实现细节

### 块增长算法

分配器使用状态机 (fN0, fN1) 跟踪序列:
- **固定策略**: fN0=0, fN1=1, 始终分配相同大小
- **线性策略**: fN0=1, fN1 递增, 分配 1N, 2N, 3N, ...
- **斐波那契策略**: fN0=0, fN1=1, 分配 F(0)N, F(1)N, F(2)N, ...
- **指数策略**: fN0=1, fN1=1, 分配 1N, 2N, 4N, 8N, ...

每次调用 `addBlock()` 时:
1. 计算 nextN1 = fN0 + fN1
2. 根据策略更新 fN0
3. 分配大小 = nextN1 * fBlockIncrement * kAddressAlign
4. 对大块(>32K)按 4K 对齐,小块按 max_align_t 对齐

### 暂存块机制

当 `releaseBlock()` 释放非头部块时:
- 如果该块比当前暂存块大,替换暂存块
- 暂存块标记为 `fCursor < 0`
- 存储在 `fHead.fPrev` 中(不在常规链表中)
- 后续 `addBlock()` 可激活暂存块,避免新的堆分配

### 对齐处理

```cpp
template <size_t Align, size_t Padding>
int Block::alignedOffset(int offset) const {
    if (Align <= kAddressAlign) {
        // 快速路径:位掩码对齐
        return (offset + Padding + Align - 1) & ~(Align - 1);
    } else {
        // 过对齐:考虑块指针的实际地址
        uintptr_t blockPtr = reinterpret_cast<uintptr_t>(this);
        uintptr_t alignedPtr = (blockPtr + offset + Padding + Align - 1) & ~(Align - 1);
        return (int)(alignedPtr - blockPtr);
    }
}
```

### ASAN 支持

所有未使用的内存使用 `sk_asan_poison_memory_region()` 标记为不可访问,分配时使用 `sk_asan_unpoison_memory_region()` 解毒,帮助检测越界访问。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkASAN.h | 内存安全检测(poison/unpoison) |
| SkAlign.h | 对齐计算工具 |
| SkAssert.h | 断言和调试检查 |
| SkMath.h | 数学工具函数 |
| SkNoncopyable | 禁止拷贝的基类 |

### 被依赖的模块
- **SkArenaAlloc**: 使用 SkBlockAllocator 的增长策略逻辑作为参考
- **高级分配器**: 作为构建更复杂内存管理系统的基础

## 设计模式与设计决策

### 设计模式
1. **内存池模式**: 管理多个块以减少堆分配次数
2. **对象池模式**: 暂存块的重用机制
3. **策略模式**: 可插拔的增长策略(固定/线性/斐波那契/指数)

### 设计决策

**为什么限制最大分配为 512MB?**
- 允许所有内部操作使用 32 位有符号整数
- 避免溢出检查,简化算法
- 足够 Skia 的实际用例

**为什么使用双向链表?**
- 支持前向和后向遍历(blocks() / rblocks())
- 高效的块插入和删除操作
- 允许在迭代时安全地释放块

**为什么内联头部块?**
- 避免小分配场景的堆分配
- 减少冷启动延迟
- 对象和数据局部性更好

**为什么支持 Padding 参数?**
- 允许在用户数据前嵌入元数据
- 中间分配器可存储管理信息
- 不浪费额外对齐空间

## 性能考量

### 时间复杂度
- `allocate()`: O(1) 均摊,偶尔 O(1) 分配新块
- `release()` / `resize()`: O(1)
- `owningBlock<Align, Padding>()`: O(1) 当 Align ≤ kAddressAlign
- `findOwningBlock()`: O(N) 块数量
- `blocks()` 迭代: O(N) 块数量

### 空间效率
- **每块开销**: sizeof(Block) = 40 字节(64 位系统,debug 模式更多)
- **对齐浪费**: 每次分配最多 (Align - 1) 字节
- **暂存块开销**: 最多保留一个未使用块

### 优化策略
1. **块大小对齐**: >32K 按 4K 对齐,兼容 jemalloc 分配器
2. **位域压缩**: fBlockIncrement(16位) + fGrowthPolicy(2位) + fN0(23位) + fN1(23位) = 64 位
3. **内联头部块**: 避免初始堆分配
4. **暂存块重用**: 避免块分配的抖动(thrashing)

## 相关文件
| 文件 | 关系 |
|------|------|
| src/base/SkArenaAlloc.h | 使用相似的斐波那契增长策略 |
| include/private/base/SkAlign.h | 提供对齐工具函数 |
| include/private/base/SkMalloc.h | 底层内存分配 |

## 使用示例场景

### 场景 1: 栈分配的小型分配器
```cpp
SkBlockAllocator allocator(GrowthPolicy::kFixed, 512);
auto br = allocator.allocate<8>(100);  // 分配 100 字节,8 字节对齐
void* ptr = br.fBlock->ptr(br.fAlignedOffset);
```

### 场景 2: 带预分配的分配器
```cpp
SkSBlockAllocator<4096> allocator(GrowthPolicy::kFibonacci);
// 前 4096 字节不需要堆分配
```

### 场景 3: 嵌入元数据的分配
```cpp
struct Meta { int id; };
constexpr size_t align = std::max(alignof(MyData), alignof(Meta));
auto br = allocator.allocate<align, sizeof(Meta)>(dataSize);
Meta* meta = reinterpret_cast<Meta*>(
    br.fBlock->ptr(br.fAlignedOffset - sizeof(Meta)));
meta->id = 42;
```

## 注意事项

1. **线程安全**: SkBlockAllocator 不是线程安全的,需要外部同步
2. **析构函数**: 分配器不调用对象析构函数,调用者负责
3. **指针稳定性**: 块指针稳定,但块内偏移可能在某些操作后失效
4. **内存泄漏**: 必须确保所有对象在分配器销毁前适当清理
