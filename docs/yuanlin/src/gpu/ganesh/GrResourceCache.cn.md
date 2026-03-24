# GrResourceCache

> 源文件
> - src/gpu/ganesh/GrResourceCache.h
> - src/gpu/ganesh/GrResourceCache.cpp

## 概述

`GrResourceCache` 是 Skia Ganesh GPU 后端的核心资源管理器,负责管理所有 `GrGpuResource` 实例的生命周期。它实现了基于预算的资源缓存机制,支持两种类型的资源键(scratch key 和 unique key),并通过 LRU(最近最少使用)策略自动清理资源。该缓存系统能够在内存紧张时智能地清理可清除资源,同时支持跨线程的安全资源返回机制。

## 架构位置

`GrResourceCache` 在 Skia GPU 架构中处于资源管理的核心位置:

```
GrDirectContext
    ├── GrResourceCache (资源缓存管理器)
    │   ├── 管理所有 GrGpuResource 生命周期
    │   ├── LRU 清理策略
    │   └── 预算控制
    ├── GrResourceProvider (资源提供者,使用缓存)
    └── GrProxyProvider (代理提供者,查询缓存)
```

它作为资源的集中存储和管理中心,协调资源的创建、查找、复用和销毁。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `GrResourceCache` | 无 | 主缓存管理器类 |
| `GrResourceCache::ResourceAccess` | 无 | 提供 GrGpuResource 的特权访问接口 |
| `GrResourceCache::UnrefResourceMessage` | 无 | 跨线程资源释放的消息类型 |
| `GrResourceCache::AutoValidate` | `SkNoncopyable` | RAII 验证辅助类 |

### GrResourceCache 关键成员变量

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fPurgeableQueue` | `PurgeableQueue` | 可清除资源的优先队列(按时间戳排序) |
| `fNonpurgeableResources` | `ResourceArray` | 不可清除的资源数组 |
| `fScratchMap` | `ScratchMap` | Scratch key 到资源的多重映射 |
| `fUniqueHash` | `UniqueHash` | Unique key 到资源的哈希表 |
| `fBytes` | `size_t` | 当前资源总字节数 |
| `fBudgetedBytes` | `size_t` | 计入预算的资源字节数 |
| `fBudgetedCount` | `int` | 计入预算的资源数量 |
| `fPurgeableBytes` | `size_t` | 可清除资源的总字节数 |
| `fMaxBytes` | `size_t` | 预算上限(默认 256MB) |
| `fTimestamp` | `uint32_t` | LRU 时间戳计数器 |
| `fProxyProvider` | `GrProxyProvider*` | 代理提供者指针 |
| `fThreadSafeCache` | `GrThreadSafeCache*` | 线程安全缓存指针 |

### 统计相关成员(GR_CACHE_STATS 启用时)

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fHighWaterCount` | `int` | 历史最大资源数量 |
| `fHighWaterBytes` | `size_t` | 历史最大内存占用 |
| `fBudgetedHighWaterCount` | `int` | 历史最大预算资源数量 |
| `fBudgetedHighWaterBytes` | `size_t` | 历史最大预算内存占用 |

## 公共 API 函数

### 构造与配置

```cpp
GrResourceCache(skgpu::SingleOwner* owner,
                GrDirectContext::DirectContextID owningContextID,
                uint32_t familyID);

void setLimit(size_t bytes);  // 设置预算上限
```

### 资源查找

```cpp
// 查找并引用 scratch 资源
GrGpuResource* findAndRefScratchResource(const skgpu::ScratchKey& scratchKey);

// 查找并引用 unique 资源
GrGpuResource* findAndRefUniqueResource(const skgpu::UniqueKey& key);

// 检查 unique key 是否存在
bool hasUniqueKey(const skgpu::UniqueKey& key) const;
```

### 资源清理

```cpp
// 按需清理资源以满足预算
void purgeAsNeeded();

// 清理未锁定的资源
void purgeUnlockedResources(GrPurgeResourceOptions opts);

// 清理指定时间之前的资源
void purgeResourcesNotUsedSince(skgpu::StdSteadyClock::time_point purgeTime,
                                GrPurgeResourceOptions opts);

// 清理指定字节数的资源
void purgeUnlockedResources(size_t bytesToPurge, bool preferScratchResources);

// 尝试清理出足够的预算空间
bool purgeToMakeHeadroom(size_t desiredHeadroomBytes);
```

### 资源释放

```cpp
// 放弃所有资源(不释放 GPU 资源)
void abandonAll();

// 释放所有资源(释放 GPU 资源)
void releaseAll();
```

### 状态查询

```cpp
int getResourceCount() const;          // 总资源数量
int getBudgetedResourceCount() const;  // 预算内资源数量
size_t getResourceBytes() const;       // 总字节数
size_t getPurgeableBytes() const;      // 可清除字节数
size_t getBudgetedResourceBytes() const; // 预算内字节数
size_t getMaxResourceBytes() const;    // 预算上限
bool overBudget() const;               // 是否超预算
```

### 跨线程资源返还

```cpp
template<typename T>
static void ReturnResourceFromThread(sk_sp<T>&& resource,
                                     GrDirectContext::DirectContextID id);
```

## 内部实现细节

### 双队列资源管理

缓存维护两个资源集合:

1. **Purgeable Queue** (`fPurgeableQueue`):
   - 使用优先队列,按时间戳排序
   - 存储引用计数为 0 的资源
   - LRU 清理时从这里选择资源

2. **Non-Purgeable Array** (`fNonpurgeableResources`):
   - 存储引用计数 > 0 或有挂起 IO 的资源
   - 数组索引存储在资源对象中,支持 O(1) 删除

### 资源键系统

**Scratch Key**:
- 用于可复用但不保留内容的资源
- 多个资源可以共享同一个 scratch key
- 使用 `SkTMultiMap` 实现多重映射
- 资源创建时设置,通常不改变

**Unique Key**:
- 域特定的唯一标识符
- 每个 unique key 只对应一个资源
- 使用 `SkTDynamicHash` 实现快速查找
- 可以在创建后设置、清除或改变
- Unique key 优先级高于 scratch key

### LRU 时间戳管理

```cpp
uint32_t getNextTimestamp();
```

每个资源在以下情况下会更新时间戳:
- 首次加入缓存
- 被查找并引用(MRU - 最近使用)
- 引用计数归零(变为可清除)

**时间戳溢出处理**:
当 `fTimestamp` 溢出归零时,会对所有资源重新分配连续的时间戳:
1. 从优先队列中提取所有资源
2. 与非可清除资源一起按时间戳排序
3. 按顺序分配新的递增时间戳
4. 重建优先队列

### 资源生命周期管理

**资源插入** (`insertResource`):
```cpp
void insertResource(GrGpuResource* resource)
```
- 分配时间戳
- 加入非可清除数组
- 更新统计信息
- 立即调用 `purgeAsNeeded` 检查预算

**资源移除** (`removeResource`):
```cpp
void removeResource(GrGpuResource* resource)
```
- 从队列或数组中移除
- 从 scratch map 和 unique hash 中移除键
- 更新统计信息

**引用计数归零处理** (`notifyARefCntReachedZero`):
- 如果变为可清除,移入优先队列
- 如果是 scratch 资源,加入 scratch map
- 根据预算和键类型决定是否立即释放

### 预算控制与清理策略

**purgeAsNeeded 逻辑**:
1. 处理 unique key 失效消息
2. 处理跨线程释放消息
3. 如果超预算,从优先队列头部开始清理
4. 如果仍超预算,请求 thread-safe cache 释放引用
5. 继续清理直到满足预算

**清理选项** (`GrPurgeResourceOptions`):
- `kScratchResourcesOnly`: 只清理没有 unique key 的资源
- `kAllResources`: 清理所有可清除资源

**preferScratchResources 策略**:
优先清理 scratch 资源,保留带 unique key 的资源(通常包含重要内容)。

### 跨线程资源返还机制

使用消息总线模式 (`SkMessageBus`):
```cpp
class UnrefResourceMessage {
    sk_sp<GrGpuResource> fResource;
    GrDirectContext::DirectContextID fRecipient;
};
```

工作流程:
1. 其他线程调用 `ReturnResourceFromThread` 发送消息
2. 消息包含资源智能指针和目标 context ID
3. 主线程在 `purgeAsNeeded` 中检查收件箱
4. 消息销毁时自动调用资源的 unref

### 与 Proxy Provider 和 Thread-Safe Cache 的协作

- **GrProxyProvider**: 处理 unique key 失效,移除相关的 proxy
- **GrThreadSafeCache**: 提供线程安全的资源访问,在预算紧张时可被请求释放资源

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrGpuResource` | 被管理的资源基类 |
| `skgpu::ScratchKey` | Scratch 键类型 |
| `skgpu::UniqueKey` | Unique 键类型 |
| `SkMessageBus` | 跨线程消息传递 |
| `SkTDPQueue` | 优先队列实现 |
| `SkTDynamicHash` | 动态哈希表 |
| `SkTMultiMap` | 多重映射 |
| `skgpu::SingleOwner` | 线程安全检查 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrResourceProvider` | 查找和创建资源时访问缓存 |
| `GrResourceAllocator` | 预算检查和清理请求 |
| `GrProxyProvider` | 处理 unique key 失效 |
| `GrDirectContext` | Context 持有并管理缓存 |

## 设计模式与设计决策

### 设计模式

1. **LRU 缓存模式**:
   - 使用时间戳实现最近最少使用策略
   - 优先队列提供 O(log n) 的插入和 O(1) 的最小值访问

2. **对象池模式**:
   - 缓存本身就是 GPU 资源的对象池
   - 通过 scratch key 实现资源复用

3. **消息总线模式**:
   - 使用 `SkMessageBus` 实现跨线程通信
   - 解耦线程间的直接依赖

4. **特权访问模式** (`ResourceAccess`):
   - 通过友元内部类限制访问权限
   - 只有 `GrGpuResource` 可以修改缓存状态

5. **RAII 验证模式** (`AutoValidate`):
   - 在调试模式下自动前后验证缓存一致性

### 关键设计决策

**为何使用双队列结构**:
- 可清除和不可清除资源的访问模式不同
- 不可清除资源需要频繁的随机删除(O(1))
- 可清除资源需要按时间排序(O(log n))

**为何同时支持两种键类型**:
- Scratch key: 支持临时资源的高效复用
- Unique key: 支持持久内容的缓存(如纹理缓存)
- 两者互补,满足不同的使用场景

**时间戳溢出重建的权衡**:
- 溢出是极罕见事件(需要数十亿次操作)
- 重建保证了 LRU 语义的正确性
- O(n log n) 的重建成本可接受

**默认预算选择**:
```cpp
static const size_t kDefaultMaxSize = 256 * (1 << 20);  // 256MB
```
- 足够大以缓存常用资源
- 不会过度占用系统内存
- 可通过 `setLimit` 动态调整

## 性能考量

### 时间复杂度分析

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 插入资源 | O(1) | 追加到数组,常数时间 |
| 移除资源 | O(1) | 数组尾部填充洞 |
| 查找 unique key | O(1) | 哈希表查找 |
| 查找 scratch key | O(1) 均摊 | 多重映射查找 |
| 标记为可清除 | O(log n) | 插入优先队列 |
| 清理一个资源 | O(log n) | 从优先队列删除 |
| 时间戳溢出重建 | O(n log n) | 极罕见 |

### 空间优化

1. **数组索引存储**: 资源对象中存储数组索引,避免反向查找。
2. **稀疏哈希表**: `SkTDynamicHash` 针对稀疏数据优化。
3. **多重映射**: `SkTMultiMap` 只为实际存在的键分配空间。

### 性能优化技巧

**避免过度验证**:
```cpp
#ifdef SK_DEBUG
void validate() const {
    // 对于大型缓存,随机采样验证
    static SkRandom gRandom;
    int mask = (SkNextPow2(fCount + 1) >> 5) - 1;
    if (~mask && (gRandom.nextU() & mask)) {
        return;
    }
    // 实际验证逻辑
}
#endif
```

**批量消息处理**:
```cpp
TArray<UnrefResourceMessage> msgs;
fUnrefResourceInbox.poll(&msgs);  // 一次性获取所有消息
```

**早期返回优化**:
- 在 `purgeUnlockedResources` 中,如果队列头资源都太新,直接返回
- 避免不必要的排序和遍历

### 性能权衡

- **内存 vs 速度**: 使用优先队列增加了内存开销,但提供了高效的 LRU 清理。
- **精确性 vs 效率**: 时间戳机制比完全精确的访问时间记录更高效,但足够满足 LRU 需求。
- **线程安全 vs 性能**: 使用消息总线而非锁,避免了同步开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuResource.h` | 被管理对象 | 缓存中存储的资源基类 |
| `src/gpu/ganesh/GrResourceProvider.h` | 使用者 | 通过缓存查找和创建资源 |
| `src/gpu/ganesh/GrProxyProvider.h` | 协作者 | 处理 unique key 失效 |
| `src/gpu/ganesh/GrThreadSafeCache.h` | 协作者 | 线程安全的资源访问 |
| `src/gpu/ganesh/GrDirectContext.h` | 拥有者 | Context 持有缓存实例 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 使用者 | 预算检查和空间清理 |
| `src/gpu/ResourceKey.h` | 键类型 | Scratch 和 Unique key 定义 |
| `src/core/SkMessageBus.h` | 工具 | 跨线程消息传递 |
| `src/base/SkTDPQueue.h` | 数据结构 | 优先队列实现 |
