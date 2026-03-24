# src/lazy - 延迟加载与可丢弃内存管理模块

## 概述

`src/lazy` 目录是 Skia 图形库中专门处理延迟加载（Lazy Loading）和可丢弃内存（Discardable Memory）管理的模块。尽管该目录仅包含两个源文件，但它实现了一个在内存受限环境中至关重要的子系统 -- 可丢弃内存池（Discardable Memory Pool），该机制广泛应用于 Chromium 浏览器和 Android 系统中的图像缓存管理。

可丢弃内存的核心思想是：在内存充裕时保留已解码的图像数据以加速后续访问，而当内存压力增大时，系统可以自动丢弃这些未锁定的内存块，从而为更紧急的内存需求腾出空间。这种机制实现了"尽力缓存"（best-effort caching）的语义 -- 数据在需要时可以重新生成（例如从编码数据重新解码），因此丢弃不会导致数据丢失，只会导致需要重新计算的性能开销。

`SkDiscardableMemoryPool` 类是 `SkDiscardableMemory::Factory` 接口的具体实现，它管理一个固定预算的内存池。每个分配的内存块都有锁定（locked）和解锁（unlocked）两种状态。锁定的内存块不会被回收，而解锁的内存块在总使用量超过预算时会按 LRU（最近最少使用）策略被清除。这种设计使得 Skia 的图像解码缓存能够自适应地调整大小，在性能和内存占用之间取得平衡。

该模块提供了全局和局部两种内存池。全局池通过 `SkGetGlobalDiscardableMemoryPool()` 获取，是一个故意泄漏的单例对象（避免静态析构顺序问题），默认预算为 128MB。局部池通过 `SkDiscardableMemoryPool::Make()` 创建，主要用于单元测试和需要隔离内存管理的场景。整个模块通过互斥锁（`SkMutex`）实现线程安全，确保在多线程环境下正确运作。

值得注意的是，该模块的调试构建中还包含了缓存统计功能（通过 `SK_LAZY_CACHE_STATS` 宏控制），可以追踪缓存命中和未命中的次数，为性能调优提供数据支持。

## 架构图

```
+--------------------------------------------------+
|            SkDiscardableMemory::Factory           |
|         (include/private/chromium/)               |
|  纯虚接口: create(size_t) -> SkDiscardableMemory* |
+---------------------------+----------------------+
                            |
                            | 实现
                            v
+--------------------------------------------------+
|          SkDiscardableMemoryPool (公共接口)         |
|         (src/lazy/SkDiscardableMemoryPool.h)       |
|                                                    |
|  +getRAMUsed() : size_t                           |
|  +setRAMBudget(budget) : void                     |
|  +getRAMBudget() : size_t                         |
|  +dumpPool() : void (清除所有未锁定内存)            |
|  +Make(size) : sk_sp<Pool> (工厂方法)              |
|  [调试] getCacheHits/Misses()                      |
+---------------------------+-----------------------+
                            |
                            | 内部实现
                            v
+--------------------------------------------------+
|         DiscardableMemoryPool (私有实现)            |
|        (src/lazy/SkDiscardableMemoryPool.cpp)      |
|                                                    |
|  fMutex  : SkMutex          (线程安全互斥锁)       |
|  fBudget : size_t            (内存预算上限)         |
|  fUsed   : size_t            (当前已使用量)         |
|  fList   : SkTInternalLList  (LRU 双向链表)        |
|                                                    |
|  -dumpDownTo(budget) : void  (清除至预算以下)       |
|  -removeFromPool(dm) : void  (移除内存块)           |
|  -lock(dm) : bool            (锁定内存块)           |
|  -unlock(dm) : void          (解锁内存块)           |
+---------------------------+-----------------------+
                            |
                            | 管理
                            v
+--------------------------------------------------+
|        PoolDiscardableMemory (内存块)               |
|        (src/lazy/SkDiscardableMemoryPool.cpp)      |
|                                                    |
|  fPool    : sk_sp<Pool>      (所属池的引用)         |
|  fLocked  : bool             (锁定状态)             |
|  fPointer : UniqueVoidPtr    (实际内存指针)          |
|  fBytes   : size_t           (内存块大小)            |
|                                                    |
|  +lock() : bool    (锁定，失败表示已被清除)          |
|  +data() : void*   (获取数据指针，必须已锁定)        |
|  +unlock() : void  (解锁，允许被清除)               |
+--------------------------------------------------+

全局访问:
+--------------------------------------------------+
| SkGetGlobalDiscardableMemoryPool()                |
| --> 返回默认 128MB 预算的全局单例池                  |
| --> 故意泄漏，避免静态析构顺序问题                    |
+--------------------------------------------------+

典型用户（Skia 内部）:
+--------------------+  +---------------------+
| SkBitmapCache      |  | SkResourceCache     |
| (位图缓存)          |  | (通用资源缓存)       |
+--------------------+  +---------------------+
| SkImage_Lazy       |  | Chromium/Android    |
| (延迟图像解码缓存)  |  | (系统级缓存管理)     |
+--------------------+  +---------------------+
```

## 目录结构

```
src/lazy/
├── BUILD.bazel                       # Bazel 构建规则
├── SkDiscardableMemoryPool.h         # 可丢弃内存池公共接口头文件
└── SkDiscardableMemoryPool.cpp       # 可丢弃内存池完整实现
```

### 文件详解

#### SkDiscardableMemoryPool.h

该头文件定义了 `SkDiscardableMemoryPool` 的公共接口，继承自 `SkDiscardableMemory::Factory`。主要包含：

- 内存使用量查询和预算控制接口
- 全局池获取函数声明
- 缓存统计接口（调试模式）
- 默认全局预算常量定义

#### SkDiscardableMemoryPool.cpp

该文件包含两个关键的私有类实现以及全局池的创建逻辑。所有的内存管理、LRU 淘汰、线程同步逻辑均封装在此文件中。

## 关键类与函数

### SkDiscardableMemoryPool（公共接口类）

```cpp
class SkDiscardableMemoryPool : public SkDiscardableMemory::Factory {
public:
    // 查询当前已使用的 RAM 总量
    virtual size_t getRAMUsed() = 0;

    // 设置内存预算上限（会立即触发超预算内存的清除）
    virtual void setRAMBudget(size_t budget) = 0;

    // 获取当前内存预算
    virtual size_t getRAMBudget() = 0;

    // 清除所有未锁定的内存块
    virtual void dumpPool() = 0;

    // 创建指定预算的局部内存池（主要用于测试）
    static sk_sp<SkDiscardableMemoryPool> Make(size_t size);

#if SK_LAZY_CACHE_STATS
    virtual int getCacheHits() = 0;       // 缓存命中次数
    virtual int getCacheMisses() = 0;     // 缓存未命中次数
    virtual void resetCacheHitsAndMisses() = 0;
#endif
};
```

### DiscardableMemoryPool（内部实现类）

```cpp
class DiscardableMemoryPool : public SkDiscardableMemoryPool {
public:
    DiscardableMemoryPool(size_t budget);
    ~DiscardableMemoryPool() override;

    // 创建一个新的可丢弃内存块
    std::unique_ptr<SkDiscardableMemory> make(size_t bytes);

    // SkDiscardableMemory::Factory 接口实现
    SkDiscardableMemory* create(size_t bytes) override;

private:
    SkMutex fMutex;    // 线程安全互斥锁
    size_t fBudget;     // 内存预算上限
    size_t fUsed;       // 当前已使用量
    SkTInternalLList<PoolDiscardableMemory> fList;  // LRU 双向链表

    void dumpDownTo(size_t budget);               // 清除至目标预算
    void removeFromPool(PoolDiscardableMemory* dm); // 从池中移除
    bool lock(PoolDiscardableMemory* dm);          // 锁定内存块
    void unlock(PoolDiscardableMemory* dm);        // 解锁内存块
};
```

### PoolDiscardableMemory（内存块实现类）

```cpp
class PoolDiscardableMemory : public SkDiscardableMemory {
public:
    PoolDiscardableMemory(sk_sp<DiscardableMemoryPool> pool,
                          UniqueVoidPtr pointer,
                          size_t bytes);
    ~PoolDiscardableMemory() override;

    // 尝试锁定内存块。若内存已被清除，返回 false
    bool lock() override;

    // 获取内存数据指针（必须在锁定状态下调用）
    void* data() override;

    // 解锁内存块，允许在内存紧张时被清除
    void unlock() override;

private:
    sk_sp<DiscardableMemoryPool> fPool;   // 所属池（引用计数）
    bool fLocked;                          // 当前锁定状态
    UniqueVoidPtr fPointer;                // 实际内存指针（nullptr 表示已被清除）
    const size_t fBytes;                   // 内存块大小
};
```

### 全局池访问函数

```cpp
// 获取全局可丢弃内存池（线程安全的单例）
SkDiscardableMemoryPool* SkGetGlobalDiscardableMemoryPool();

// 默认全局池预算：128 MB
#define SK_DEFAULT_GLOBAL_DISCARDABLE_MEMORY_POOL_SIZE (128 * 1024 * 1024)
```

## 依赖关系

### 上游依赖（本模块依赖的组件）

| 依赖模块 | 文件/类 | 用途 |
|---------|---------|------|
| `include/private/chromium/` | `SkDiscardableMemory` | 可丢弃内存的纯虚接口和工厂接口 |
| `include/private/base/` | `SkMutex` | 互斥锁，用于线程安全 |
| `include/private/base/` | `SkMalloc.h` | 内存分配（`sk_malloc_canfail`） |
| `include/private/base/` | `SkTemplates.h` | `UniqueVoidPtr` 智能指针 |
| `src/base/` | `SkTInternalLList` | 侵入式双向链表（LRU 淘汰使用） |

### 下游被依赖（使用本模块的组件）

| 依赖方 | 文件/类 | 用途 |
|--------|---------|------|
| `src/core/` | `SkResourceCache` | 通用资源缓存，使用可丢弃内存作为后端 |
| `src/core/` | `SkBitmapCache` | 位图缓存，为 `SkImage_Lazy` 提供缓存存储 |
| `src/image/` | `SkImage_Lazy` | 延迟图像通过位图缓存间接使用可丢弃内存 |
| Chromium | `SkDiscardableMemory_chrome.cc` | Chrome 可提供自定义的可丢弃内存实现 |
| Android | 系统内存管理 | Android 可能使用 ashmem 等机制提供可丢弃内存 |

## 设计模式分析

### 1. 工厂模式（Factory）

`SkDiscardableMemoryPool` 本身继承自 `SkDiscardableMemory::Factory`，实现了工厂方法 `create()`。同时，`SkDiscardableMemoryPool::Make()` 是一个静态工厂方法，用于创建池的实例。全局池的获取也遵循工厂单例的模式。

### 2. 单例模式（Singleton）

全局可丢弃内存池通过 `SkGetGlobalDiscardableMemoryPool()` 以 Meyer's Singleton 的变体实现。它使用静态局部变量，但故意不释放（`new` 而非 `static` 局部对象），以避免程序退出时的静态对象析构顺序问题。

```cpp
SkDiscardableMemoryPool* SkGetGlobalDiscardableMemoryPool() {
    // 故意泄漏，避免静态析构顺序问题
    static SkDiscardableMemoryPool* global =
            new DiscardableMemoryPool(SK_DEFAULT_GLOBAL_DISCARDABLE_MEMORY_POOL_SIZE);
    return global;
}
```

### 3. LRU 缓存淘汰策略

内存池使用 `SkTInternalLList`（侵入式双向链表）维护所有活跃内存块的 LRU 顺序。当一个内存块被锁定（`lock`）时，它被移到链表头部；当需要释放内存时（`dumpDownTo`），从链表尾部开始遍历，逐个清除未锁定的内存块，直到使用量降至预算以下。

```
链表头部 (最近使用)                            链表尾部 (最久未用)
    +----+     +----+     +----+     +----+
    | DM | <-> | DM | <-> | DM | <-> | DM |
    | L  |     | U  |     | U  |     | U  |
    +----+     +----+     +----+     +----+
                                        ^
                                        |
                              dumpDownTo 从这里开始清除
L = Locked (锁定), U = Unlocked (解锁)
```

### 4. RAII 与引用计数

每个 `PoolDiscardableMemory` 持有对所属 `DiscardableMemoryPool` 的 `sk_sp` 引用。这保证了只要还有任何活跃的内存块，池对象就不会被销毁。当内存块的析构函数执行时，它会自动将自己从池中移除，并更新池的已用内存计数。

### 5. 监视器模式（Monitor）

`DiscardableMemoryPool` 内部使用 `SkMutex` 保护所有可变状态（`fUsed`、`fBudget`、`fList`），确保 `make()`、`lock()`、`unlock()`、`removeFromPool()` 等操作在多线程环境下是原子的。所有公共方法入口处都通过 `SkAutoMutexExclusive` RAII 对象获取锁。

## 数据流

### 内存块分配与使用流程

```
调用方（如 SkBitmapCache）请求分配可丢弃内存
    |
    v
DiscardableMemoryPool::make(bytes)
    |
    +--> sk_malloc_canfail(bytes)      // 分配原始内存
    |     若失败 --> 返回 nullptr
    |
    +--> 创建 PoolDiscardableMemory(pool, pointer, bytes)
    |     fLocked = true              // 新分配的内存默认锁定
    |
    +--> [获取互斥锁]
    |    +--> fList.addToHead(dm)     // 添加到 LRU 链表头部
    |    +--> fUsed += bytes          // 更新已用量
    |    +--> dumpDownTo(fBudget)     // 若超预算，清除旧内存块
    |         |
    |         +--> 从链表尾部遍历
    |         +--> 对每个未锁定的 dm:
    |              +--> dm->fPointer = nullptr  // 释放内存
    |              +--> fUsed -= dm->fBytes     // 减少使用量
    |              +--> fList.remove(dm)        // 从链表移除
    |         +--> 直到 fUsed <= fBudget
    |    [释放互斥锁]
    |
    v
返回 unique_ptr<PoolDiscardableMemory>

调用方使用 dm->data() 写入数据
    |
    v
调用方调用 dm->unlock()  // 表示数据已写入完毕
    |
    v
DiscardableMemoryPool::unlock(dm)
    +--> [获取互斥锁]
    +--> dm->fLocked = false
    +--> dumpDownTo(fBudget)  // 可能触发本块或其他块的清除
    +--> [释放互斥锁]
```

### 内存块重新访问流程

```
调用方尝试重新访问之前解锁的内存
    |
    v
dm->lock()
    |
    v
DiscardableMemoryPool::lock(dm)
    +--> [获取互斥锁]
    |
    +--> 检查 dm->fPointer
    |    |
    |    +--> fPointer == nullptr (已被清除)
    |    |    +--> fCacheMisses++
    |    |    +--> return false  --> 调用方需重新生成数据
    |    |
    |    +--> fPointer != nullptr (仍在内存中)
    |         +--> fCacheHits++
    |         +--> dm->fLocked = true
    |         +--> fList.remove(dm)
    |         +--> fList.addToHead(dm)  // 移到链表头部（最近使用）
    |         +--> return true
    |
    +--> [释放互斥锁]
    |
    v
[lock 成功] --> dm->data() 获取指针，读取缓存数据
[lock 失败] --> 重新解码/生成数据，分配新的可丢弃内存
```

### 内存块销毁流程

```
PoolDiscardableMemory 析构
    |
    +--> 断言: !fLocked (合约要求销毁前必须解锁)
    |
    v
DiscardableMemoryPool::removeFromPool(dm)
    +--> [获取互斥锁]
    |
    +--> 检查 dm->fPointer
    |    |
    |    +--> fPointer != nullptr (未被清除)
    |    |    +--> fUsed -= dm->fBytes   // 减少使用量
    |    |    +--> fList.remove(dm)      // 从链表移除
    |    |
    |    +--> fPointer == nullptr (已被清除)
    |         +--> 断言 dm 不在链表中（之前清除时已移除）
    |
    +--> [释放互斥锁]
    |
    v
PoolDiscardableMemory 的 fPool sk_sp 引用减少
    --> 若池引用计数归零，池也被销毁
```

### 与 SkImage_Lazy 的集成流程

```
SkImage_Lazy::getROPixels() 被调用
    |
    +--> SkBitmapCache::Find(desc, bitmap)    // 查找缓存
    |    内部使用 SkResourceCache，可能使用 SkDiscardableMemory
    |
    |    命中 --> 返回缓存位图（不涉及可丢弃内存的新分配）
    |
    |    未命中:
    v
    +--> SkBitmapCache::Alloc(desc, info, &pmap)
    |    |
    |    +--> 通过 SkResourceCache 分配缓存空间
    |    |    可能使用 SkDiscardableMemoryPool::make()
    |    |    分配可丢弃内存来存储解码后的像素
    |    |
    |    v
    +--> ScopedGenerator(fSharedGenerator)->getPixels(pmap)
    |    // 从生成器解码像素到可丢弃内存中
    |
    +--> SkBitmapCache::Add(cacheRec, bitmap)
    |    // 将解码结果存入缓存（可丢弃内存被解锁）
    |
    v
后续访问同一图像:
    +--> SkBitmapCache::Find() 命中
    |    内部 lock() 可丢弃内存
    |    若 lock 成功 --> 使用缓存数据
    |    若 lock 失败 --> 缓存未命中，重新解码
```

## 相关文档与参考

| 资源 | 说明 |
|------|------|
| `include/private/chromium/SkDiscardableMemory.h` | 可丢弃内存的基础接口定义 |
| `src/core/SkResourceCache.h` | 通用资源缓存，可丢弃内存池的主要消费者 |
| `src/core/SkBitmapCache.h` | 位图缓存，延迟图像的缓存基础设施 |
| `src/image/SkImage_Lazy.h` | 延迟图像，最终用户层面的可丢弃内存使用者 |
| `src/base/SkTInternalLList.h` | 侵入式双向链表实现（LRU 数据结构） |
| `include/private/base/SkMutex.h` | 互斥锁接口 |
| Chromium 源码 | `skia/ext/SkDiscardableMemory_chrome.cc` - Chrome 的自定义实现 |
| Android Skia 集成 | Android 可能通过 ashmem 提供可丢弃内存后端 |
| Skia 缓存架构设计 | Skia 的资源缓存系统整体设计文档 |
| LRU 缓存算法 | 经典的最近最少使用淘汰策略 |
