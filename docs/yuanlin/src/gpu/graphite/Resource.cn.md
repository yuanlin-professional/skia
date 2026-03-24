# Resource (GPU 资源基类)

> 源文件：[src/gpu/graphite/Resource.h](../../../../src/gpu/graphite/Resource.h)、[src/gpu/graphite/Resource.cpp](../../../../src/gpu/graphite/Resource.cpp)

## 概述

`Resource` 是 Skia Graphite 中所有 GPU 资源（纹理、缓冲区、采样器、管线等）的抽象基类。它定义了一套精密的多类型引用计数系统，支持资源在多线程环境下安全地创建、使用、回收和销毁。`Resource` 的引用计数被紧凑地打包在一个 64 位原子变量中，包含使用引用（usage）、命令缓冲区引用（command buffer）、缓存引用（cache）和返回队列引用（return queue）四种类型。

资源的生命周期由 `ResourceProvider`（创建）和 `ResourceCache`（缓存管理）协同控制。资源可以是预算内的或非预算的，可以是共享的、临时（scratch）的或独占的。

## 架构位置

`Resource` 位于 Graphite 资源管理系统的最底层：

- **子类**：`Texture`、`Buffer`、`Sampler`、`GraphicsPipeline`、`ComputePipeline` 等。
- **管理者**：`ResourceCache` 持有缓存引用，管理资源的清除和复用。
- **使用者**：Graphite 的各种高级组件通过 `sk_sp<Resource>` 持有使用引用。

## 主要类与结构体

### `Resource` (抽象基类)

**引用计数系统（64 位原子打包）：**
- 位 [63:33]（31 位）：命令缓冲区引用计数。
- 位 [32:2]（31 位）：使用引用计数。
- 位 1：缓存引用（0 或 1）。
- 位 0：返回队列引用（0 或 1）。

**关键成员变量：**
- `fRefs`：64 位原子引用计数。
- `fReusableRefMask`：决定资源何时可复用的掩码（可能包含或排除命令缓冲区引用）。
- `fSharedContext`：指向共享上下文（销毁时设为 nullptr）。
- `fKey` (GraphiteResourceKey)：资源的缓存键。
- `fReturnCache`：指向所属 ResourceCache 的智能指针。
- `fNextInReturnQueue`：返回队列的链表指针。
- `fGpuMemorySize`：GPU 内存大小（字节）。
- `fBudgeted` / `fShareable`：预算和共享状态。
- `fLastUseToken` / `fLastAccess`：LRU 排序信息。
- `fLabel`：资源标签。

### `Resource::UniqueID`
唯一标识符，每个资源在创建时分配，不随内容变化。

## 公共 API 函数

### 引用管理
- `ref() / unref()`：使用引用的增减。`unref()` 可能触发资源返回缓存或销毁。
- `refCommandBuffer() / unrefCommandBuffer()`：命令缓冲区引用的增减。

### 状态查询
- `ownership() -> Ownership`：资源所有权（kOwned / kWrapped）。
- `budgeted() -> Budgeted`：是否计入预算。
- `shareable() -> Shareable`：共享模式（kNo / kYes / kScratch）。
- `key() -> GraphiteResourceKey`：缓存键。
- `gpuMemorySize() -> size_t`：GPU 内存大小。
- `uniqueID() -> UniqueID`：唯一标识符。
- `wasDestroyed() -> bool`：是否已销毁。
- `getResourceType() -> const char*`（纯虚）：资源类型名称。

## 内部实现细节

### 四类引用计数的原子打包
将四种引用计数打包到一个 `std::atomic<uint64_t>` 中，关键优势：
1. **原子状态转换**：通过 CAS 操作同时修改引用计数和返回队列标志，避免竞态条件。
2. **内存效率**：仅一个缓存行即可存储所有引用状态。

### removeRef 的 CAS 逻辑
当移除使用引用或命令缓冲区引用时：
1. 加载当前引用状态。
2. 判断是否需要返回（可复用或可清除状态转换 + 返回队列引用为 0）。
3. 计算新的引用状态（减去引用，可能添加返回队列引用）。
4. 通过 `compare_exchange_weak` 原子提交。
5. 如果需要返回但缓存拒绝，则移除返回队列引用（可能导致销毁）。

### 可复用性判断
资源的可复用掩码（`fReusableRefMask`）决定何时资源可以被缓存重新分配：
- 默认：使用引用归零即可复用（命令缓冲区引用不影响）。
- 映射缓冲区等：使用引用和命令缓冲区引用都归零才可复用。

### 线程安全标签模型
- 可共享资源：标签在创建后不再改变。
- 不可共享资源：标签在缓存返回时可以更改。
- Scratch 资源：标签使用位掩码表示多种用途的并集。
- 后端标签更新延迟到 Recording 插入时，确保 GPU 帧捕获期间标签稳定。

### 生命周期状态机
```
创建 -> [已注册缓存?] -> 使用中(不可清除) -> 可复用 -> 可清除 -> 销毁
                                    ^                      |
                                    |______缓存复用________|
```

## 依赖关系

### 上游依赖
- `SharedContext`：共享上下文（访问后端 API）。
- `ResourceCache`：缓存管理。
- `GraphiteResourceKey`：缓存键。

### 下游使用者（子类）
- `Texture`、`Buffer`、`Sampler`、`GraphicsPipeline`、`ComputePipeline` 等。

## 设计模式与设计决策

1. **打包原子引用计数**：将四种引用计数打包到单个原子变量中，使状态转换可以通过单次 CAS 操作完成，消除多个原子变量之间的竞态条件。

2. **可复用与可清除分离**：资源可以在仍有命令缓冲区引用时变为可复用（但不可清除），允许缓存更早地重新分配资源。

3. **异步准备返回**：通过 `prepareForReturnToCache` 回调，资源可以在返回缓存前执行异步操作（如缓冲区重新映射），而不会阻塞返回流程。

4. **延迟销毁**：资源销毁通过 `internalDispose()` 统一处理，确保 GPU 资源和 C++ 对象被正确清理。

## 性能考量

- 引用计数操作使用 `memory_order_relaxed`（增加）和 `memory_order_acq_rel`（移除），最小化内存屏障开销。
- CAS 循环在低竞争环境下通常一次成功。
- 打包引用计数减少了缓存行争用，与四个独立原子变量相比性能更好。
- 零大小资源（管线等）不受预算清除影响，避免不必要的重编译。

## 相关文件

- `src/gpu/graphite/ResourceCache.h/.cpp`：资源缓存。
- `src/gpu/graphite/ResourceProvider.h/.cpp`：资源提供者。
- `src/gpu/graphite/GraphiteResourceKey.h`：资源缓存键。
- `src/gpu/graphite/Texture.h/.cpp`：纹理资源子类。
- `src/gpu/graphite/Buffer.h/.cpp`：缓冲区资源子类。
