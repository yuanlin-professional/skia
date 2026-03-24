# ResourceCache (资源缓存)

> 源文件：[src/gpu/graphite/ResourceCache.h](../../../../src/gpu/graphite/ResourceCache.h)、[src/gpu/graphite/ResourceCache.cpp](../../../../src/gpu/graphite/ResourceCache.cpp)

## 概述

`ResourceCache` 是 Graphite 中管理 GPU 资源生命周期和预算的核心组件。它负责缓存、查找、复用和清除 GPU 资源（纹理、缓冲区、管线等），在内存预算范围内最大化资源复用以减少 GPU 内存分配和创建开销。

`ResourceCache` 使用 LRU（最近最少使用）策略管理可清除资源，通过无锁的返回队列支持多线程安全的资源回收，并与 `ProxyCache` 协作管理纹理代理级别的缓存。

## 架构位置

`ResourceCache` 位于资源管理系统的核心：

- **上游**：`ResourceProvider` 创建资源时通过 `insertResource` 注册到缓存，通过 `findAndRefResource` 查找可复用资源。
- **下游**：`Resource` 对象在引用计数归零时通过 `returnResource` 返回到缓存的返回队列。
- **协作者**：`ProxyCache` 管理纹理代理到资源的映射，在预算超支时辅助释放资源。

## 主要类与结构体

### `ResourceCache` (继承自 SkRefCnt)

**核心数据结构：**
- `fPurgeableQueue` (PurgeableQueue)：优先队列，按使用令牌排序的可清除资源。
- `fNonpurgeableResources` (ResourceArray)：当前正在使用的不可清除资源数组。
- `fResourceMap` (ResourceMap)：`SkTMultiMap`，支持按键查找可复用资源，同一键可关联多个资源。
- `fProxyCache`：纹理代理缓存。

**预算管理：**
- `fMaxBytes`：预算上限。
- `fBudgetedBytes`：当前预算内资源的总字节数。
- `fPurgeableBytes`：当前可清除资源的总字节数。

**使用令牌：**
- `fUseToken`：单调递增的令牌，用于维护 LRU 排序。零大小资源使用 `kMaxUseToken` 避免被清除。

**返回队列：**
- `fReturnQueue`：原子指针，指向返回队列的头节点。使用哨兵（Sentinel）标记缓存已关闭。

### `Sentinel` (内部类)
单例 `Resource` 子类，提供固定地址作为返回队列的关闭标记和尾标记。使用 `SkNoDestructor` 确保全局唯一且不销毁。

## 公共 API 函数

### 资源查找与插入
- `findAndRefResource(key, Budgeted, Shareable, label, unavailable) -> Resource*`：按键查找可复用资源。对于 Scratch 资源，使用 `unavailable` 集合过滤已被占用的资源。找到后增加引用并从可清除队列移至不可清除数组。
- `insertResource(Resource*, key, Budgeted, Shareable)`：将新创建的资源注册到缓存。

### 清除与预算管理
- `purgeResourcesNotUsedSince(time_point)`：清除指定时间点之前未使用的资源。
- `purgeResources()`：清除所有可清除资源。
- `setMaxBudget(bytes)`：动态调整预算上限。

### 生命周期
- `shutdown()`：关闭缓存，处理返回队列，释放所有资源的缓存引用。
- `returnResource(Resource*) -> bool`：线程安全地将资源添加到返回队列。

### 查询
- `getResourceCount() / currentBudgetedBytes() / currentPurgeableBytes()`：资源统计。
- `dumpMemoryStatistics(SkTraceMemoryDump*)`：内存统计导出。

## 内部实现细节

### 无锁返回队列
资源回收使用 lock-free 的单链表：
1. 需要返回的资源通过 `compare_exchange_weak` 原子操作插入队列头部。
2. 缓存线程通过 `exchange` 原子操作获取整个队列进行批量处理。
3. 使用 Sentinel 地址标记缓存已关闭，拒绝后续的返回操作。

### 资源返回处理 (processReturnedResource)
处理返回的资源时：
- 可共享资源：保留在资源映射中，重置共享模式为 `kNo`。
- 不可共享但可复用的资源：重新添加到资源映射，可能从非预算变为预算资源。
- 可清除的资源：从不可清除数组移到可清除队列，或立即清除（如果标记为 DeleteASAP）。

### 异步准备返回缓存
Dawn/WebGPU 后端的缓冲区需要在返回缓存前异步重新映射。`prepareForReturnToCache` 机制允许资源在准备完成前保持使用引用，准备完成后再次进入返回队列。

### LRU 排序与使用令牌
- 每次资源被访问时分配递增的使用令牌。
- 令牌溢出时（达到 `kMaxUseToken`），对所有资源重新排序和分配令牌（O(n log n)，但极少发生）。
- 零大小资源（如管线对象）使用 `kMaxUseToken`，永远不会因预算超支被清除。

### 预算清除策略 (purgeAsNeeded)
1. 首先尝试让 `ProxyCache` 释放唯一持有的纹理代理。
2. 然后从可清除队列中按 LRU 顺序清除资源，直到预算内或队列为空。
3. 跳过 `kMaxUseToken` 的零大小资源。

## 依赖关系

### 上游依赖
- `Resource`：被缓存管理的资源基类。
- `GraphiteResourceKey`：资源缓存键。
- `ProxyCache`：纹理代理缓存。

### 下游使用者
- `ResourceProvider`：创建和查找资源。
- `Context` / `Recorder`：持有 ResourceCache 实例。

## 设计模式与设计决策

1. **无锁返回队列**：使用原子操作的单链表避免资源回收时的锁竞争，支持多线程同时返回资源。

2. **可清除/不可清除分离**：使用优先队列和数组分别管理两种状态的资源，避免状态混淆。

3. **延迟处理**：返回队列的处理延迟到缓存线程的查找或插入操作时，减少不必要的同步。

4. **哨兵模式**：使用全局单例 Sentinel 作为队列关闭标记，简化关闭逻辑。

## 性能考量

- 资源查找基于哈希表，O(1) 平均时间。
- 返回队列使用无锁原子操作，无锁竞争开销。
- LRU 清除在正常情况下 O(1)（从队列头部取出），令牌溢出的重排是 O(n log n) 但极罕见。
- `purgeAsNeeded` 仅在预算超支时执行实质工作。

## 相关文件

- `src/gpu/graphite/Resource.h/.cpp`：GPU 资源基类。
- `src/gpu/graphite/ResourceProvider.h/.cpp`：资源提供者。
- `src/gpu/graphite/GraphiteResourceKey.h`：资源缓存键。
- `src/gpu/graphite/ProxyCache.h/.cpp`：纹理代理缓存。
