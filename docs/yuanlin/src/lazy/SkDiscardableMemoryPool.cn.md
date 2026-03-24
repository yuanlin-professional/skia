# SkDiscardableMemoryPool

> 源文件: `src/lazy/SkDiscardableMemoryPool.h`, `src/lazy/SkDiscardableMemoryPool.cpp`

## 概述

`SkDiscardableMemoryPool` 是 Skia 中用于管理可丢弃内存（Discardable Memory）的内存池实现。它维护一个固定大小的内存预算（budget），当已分配的内存超过预算时，会自动清除（purge）处于未锁定状态的内存块。如果所有内存块都处于锁定状态，实际内存使用量可以超过预算限制。

该模块的核心设计理念是为图像解码缓存等场景提供一种智能内存管理机制：当系统内存紧张时，可以安全地丢弃那些不再被活跃使用的数据，需要时再重新生成。

默认的全局内存池大小为 128 MB（`SK_DEFAULT_GLOBAL_DISCARDABLE_MEMORY_POOL_SIZE`）。

## 架构位置

`SkDiscardableMemoryPool` 位于 Skia 的 `src/lazy/` 目录下，属于惰性加载（lazy loading）子系统的一部分。在 Skia 架构中，它的位置如下：

```
Chromium / 上层应用
    |
SkImageGenerator / SkCachingPixelRef (图像缓存层)
    |
SkDiscardableMemoryPool (内存池管理)  <-- 本模块
    |
    +-- PoolDiscardableMemory (可丢弃内存块)
    |
SkDiscardableMemory::Factory (工厂接口)
    |
sk_malloc_canfail (底层内存分配)
```

- **上层接口**: 继承自 `SkDiscardableMemory::Factory`（定义在 `include/private/chromium/SkDiscardableMemory.h`），该工厂接口提供了创建 `SkDiscardableMemory` 实例的标准方法。
- **使用场景**: 主要被 Skia 的图像缓存系统使用，特别是在 Chromium 集成中用于管理图像解码后的像素数据缓存。
- **层级关系**: 作为基础设施层组件，被上层的图像解码器和缓存管理器调用。

## 主要类与结构体

### SkDiscardableMemoryPool（公共抽象基类）

```cpp
class SkDiscardableMemoryPool : public SkDiscardableMemory::Factory {
public:
    virtual size_t getRAMUsed() = 0;
    virtual void setRAMBudget(size_t budget) = 0;
    virtual size_t getRAMBudget() = 0;
    virtual void dumpPool() = 0;
    static sk_sp<SkDiscardableMemoryPool> Make(size_t size);
};
```

这是对外暴露的抽象接口类，定义了内存池的核心操作：查询已用内存、设置/获取预算、以及清空池。在调试模式（`SK_DEBUG`）下，还提供缓存命中/未命中统计功能（通过 `SK_LAZY_CACHE_STATS` 宏控制）。

### DiscardableMemoryPool（内部实现类）

```cpp
class DiscardableMemoryPool : public SkDiscardableMemoryPool {
    SkMutex      fMutex;
    size_t       fBudget;
    size_t       fUsed;
    SkTInternalLList<PoolDiscardableMemory> fList;
};
```

实际的内存池实现，定义在匿名命名空间中。使用互斥锁 `fMutex` 保证线程安全，用 `fBudget` 和 `fUsed` 跟踪内存预算与使用量，用 `SkTInternalLList` 双向链表管理所有活跃的内存块。

### PoolDiscardableMemory（内部内存块类）

```cpp
class PoolDiscardableMemory : public SkDiscardableMemory {
    sk_sp<DiscardableMemoryPool> fPool;
    bool                         fLocked;
    UniqueVoidPtr                fPointer;
    const size_t                 fBytes;
};
```

单个可丢弃内存块的实现。每个实例持有对所属内存池的智能指针引用，记录自身的锁定状态、底层内存指针和大小。通过 `SK_DECLARE_INTERNAL_LLIST_INTERFACE` 宏实现双向链表节点接口。

## 公共 API 函数

### `SkDiscardableMemoryPool::Make(size_t size)`
- **功能**: 创建一个具有指定内存预算的非全局内存池实例。
- **参数**: `size` - 内存预算的字节数。
- **返回值**: `sk_sp<SkDiscardableMemoryPool>` 智能指针，管理新创建的池。
- **用途**: 主要用于单元测试，也可在需要独立内存管理的场景中使用。

### `SkGetGlobalDiscardableMemoryPool()`
- **功能**: 获取全局唯一的线程安全可丢弃内存池。
- **返回值**: `SkDiscardableMemoryPool*` 裸指针（该全局对象有意泄露，不会被释放）。
- **预算**: 默认为 128 MB，可通过 `SK_DEFAULT_GLOBAL_DISCARDABLE_MEMORY_POOL_SIZE` 编译宏自定义。

### `getRAMUsed()`
- **功能**: 查询当前池中已分配的内存总量（字节）。

### `setRAMBudget(size_t budget)`
- **功能**: 动态调整内存预算。调用后会立即触发清除操作，将内存使用量降至新预算以下。

### `getRAMBudget()`
- **功能**: 查询当前的内存预算。

### `dumpPool()`
- **功能**: 清除所有未锁定的内存块，将预算设为 0 进行清除（内部调用 `dumpDownTo(0)`）。

### 缓存统计 API（仅在 `SK_LAZY_CACHE_STATS` 启用时可用）
- `getCacheHits()`: 返回 `lock()` 成功次数。
- `getCacheMisses()`: 返回 `lock()` 失败次数（内存已被清除）。
- `resetCacheHitsAndMisses()`: 重置两个计数器。

## 内部实现细节

### 内存分配流程 (`make`)
1. 调用 `sk_malloc_canfail` 分配指定大小的内存（允许失败返回 `nullptr`）。
2. 创建 `PoolDiscardableMemory` 实例，初始状态为已锁定（`fLocked = true`）。
3. 获取互斥锁后，将新内存块插入链表头部，更新已用内存计数。
4. 调用 `dumpDownTo(fBudget)` 检查是否超预算，如超出则清除尾部的未锁定块。

### 内存清除策略 (`dumpDownTo`)

`dumpDownTo` 是内存池的核心清除方法，其详细流程如下：

```cpp
void DiscardableMemoryPool::dumpDownTo(size_t budget) {
    fMutex.assertHeld();               // 必须在持有锁的状态下调用
    if (fUsed <= budget) { return; }   // 未超预算，直接返回
    // 从尾部（最旧）开始遍历
    PoolDiscardableMemory* cur = iter.init(fList, Iter::kTail_IterStart);
    while ((fUsed > budget) && (cur)) {
        if (!cur->fLocked) {
            dm->fPointer = nullptr;    // 释放底层内存
            fUsed -= dm->fBytes;       // 更新计数
            fList.remove(dm);          // 从链表移除
        }
        cur = iter.prev();             // 继续向前遍历
    }
}
```

关键特性：
- 从链表尾部（最久未使用）开始遍历。
- 跳过已锁定的内存块，继续遍历更早的块。
- 对未锁定的块：释放其底层内存指针（设为 `nullptr`），从链表中移除，更新已用内存计数。
- 当已用内存降至预算以下时立即停止，不会过度清除。
- 注意：被清除的 `PoolDiscardableMemory` 对象本身不会被删除，只是其数据被释放。

### LRU 策略
- 每次 `lock()` 成功时，被锁定的内存块会被移动到链表头部。
- 清除时从尾部开始，因此实现了 LRU（最近最少使用）淘汰策略。
- 新分配的内存块也会被添加到链表头部。

### 锁定与解锁

**lock() 流程**:
```cpp
bool DiscardableMemoryPool::lock(PoolDiscardableMemory* dm) {
    SkAutoMutexExclusive autoMutexAcquire(fMutex);
    if (nullptr == dm->fPointer) {
        // 内存已被清除，锁定失败
        ++fCacheMisses;  // 仅在 SK_LAZY_CACHE_STATS 启用时
        return false;
    }
    dm->fLocked = true;
    fList.remove(dm);      // 从当前位置移除
    fList.addToHead(dm);   // 移到链表头部（最近使用）
    ++fCacheHits;          // 仅在 SK_LAZY_CACHE_STATS 启用时
    return true;
}
```

**unlock() 流程**:
- 将锁定标志设为 `false`，然后触发 `dumpDownTo` 检查是否需要清除。
- 解锁操作之所以触发清除检查，是因为解锁后可能有新的内存块变为可清除状态，而此时总使用量可能已超预算。

### removeFromPool 流程

当 `PoolDiscardableMemory` 对象被析构时，调用 `removeFromPool` 将自身从池中移除：
- 如果 `fPointer != nullptr`（尚未被清除），则从链表中移除并减少已用内存计数。
- 如果 `fPointer == nullptr`（已被清除），则断言确认该块不在链表中，无需额外操作。

### 生命周期管理
- `PoolDiscardableMemory` 持有对 `DiscardableMemoryPool` 的 `sk_sp` 引用，保证池在所有内存块销毁之前不会被释放。
- 全局池使用 `new` 创建且有意泄露，避免静态析构顺序问题。
- `PoolDiscardableMemory` 析构时调用 `removeFromPool` 将自身从池中移除。

## 依赖关系

### 内部依赖
- `include/private/base/SkMutex.h` - 互斥锁，提供线程安全保护
- `include/private/base/SkMalloc.h` - 内存分配函数（`sk_malloc_canfail`）
- `include/private/base/SkTemplates.h` - 模板工具（`UniqueVoidPtr` 等）
- `include/private/chromium/SkDiscardableMemory.h` - 可丢弃内存基类和工厂接口
- `src/base/SkTInternalLList.h` - 侵入式双向链表实现

### 被依赖方
- Skia 的图像缓存系统
- Chromium 浏览器的图像解码缓存

## 设计模式与设计决策

### 工厂模式
`SkDiscardableMemoryPool` 同时是一个工厂（继承自 `SkDiscardableMemory::Factory`），负责创建和管理 `SkDiscardableMemory` 实例。

### 侵入式链表
使用 `SkTInternalLList` 侵入式链表而非 `std::list`，避免额外的堆分配开销。链表节点接口直接嵌入到 `PoolDiscardableMemory` 中。

### 单例模式（全局池）
`SkGetGlobalDiscardableMemoryPool()` 使用函数内部静态变量实现线程安全的惰性初始化。全局池有意泄露以避免析构顺序问题。

### 引用计数所有权
`PoolDiscardableMemory` 通过 `sk_sp` 持有对池的引用，形成了一种"子对象延长父对象生命周期"的所有权模型，确保池不会在仍有活跃内存块时被销毁。

### 清除与删除的分离
被清除（purged）的内存块只是释放了底层数据（`fPointer = nullptr`）并从链表中移除，但 `PoolDiscardableMemory` 对象本身仍然存在。这使得调用方仍然可以持有该对象的引用，并在 `lock()` 返回 `false` 时知道数据需要重新生成。

## 性能考量

- **锁粒度**: 使用单一互斥锁 `fMutex` 保护所有操作。在高并发场景下可能成为瓶颈，但简化了实现并保证了正确性。
- **LRU 淘汰**: O(1) 的链表头/尾操作实现了高效的 LRU 策略。
- **内存分配**: 使用 `sk_malloc_canfail` 允许分配失败优雅降级，而非直接终止程序。
- **清除时机**: 在 `make`（新分配）和 `unlock`（解锁）时触发清除检查，确保及时回收内存。
- **缓存统计开销**: 缓存命中/未命中统计仅在调试模式下启用（`SK_LAZY_CACHE_STATS`），不影响发行版性能。
- **预算超限容忍**: 当所有内存块都被锁定时，允许超预算分配，保证了功能正确性。

## 相关文件

- `include/private/chromium/SkDiscardableMemory.h` - `SkDiscardableMemory` 基类与 `Factory` 接口定义
- `src/base/SkTInternalLList.h` - 侵入式双向链表的实现
- `include/private/base/SkMutex.h` - Skia 互斥锁封装
- `include/private/base/SkMalloc.h` - 内存分配接口
- `include/private/base/SkTemplates.h` - 模板工具（包含 `UniqueVoidPtr`）
