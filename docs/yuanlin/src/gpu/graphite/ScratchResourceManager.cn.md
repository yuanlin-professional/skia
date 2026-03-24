# ScratchResourceManager (临时资源管理器)

> 源文件：[src/gpu/graphite/ScratchResourceManager.h](../../../../src/gpu/graphite/ScratchResourceManager.h)、[src/gpu/graphite/ScratchResourceManager.cpp](../../../../src/gpu/graphite/ScratchResourceManager.cpp)

## 概述

`ScratchResourceManager` 协调 Recording 内部的资源复用。在一次 Recording 中，Recorder 持有资源的使用引用，这些资源通常不是可共享的，因此不会通过 `ResourceProvider/Cache` 被复用。`ScratchResourceManager` 维护一个已分配但已被原始持有者归还的资源池，允许后续兼容的请求重新使用这些资源。

该管理器还维护一个与任务图深度优先遍历对应的栈结构，通过"待使用监听器"（PendingUseListener）机制帮助任务确定何时可以安全归还资源。

## 架构位置

`ScratchResourceManager` 在 `Recorder::snap()` 的 `prepareResources()` 阶段活跃：

- **上游**：`TextureProxy` 和其他任务通过管理器获取和归还 scratch 资源。
- **下游**：通过 `ResourceProvider` 从缓存中获取或创建资源。
- **协作**：`ProxyReadCountMap` 跟踪代理的待处理读取计数。

## 主要类与结构体

### `ProxyReadCountMap`
跟踪 `TextureProxy` 的待处理读取计数。提供 `increment`、`decrement`、`get` 方法。当计数降为零时 `decrement` 返回 true。

### `ScratchResourceManager`
**核心成员：**
- `fResourceProvider`：资源提供者。
- `fUnavailable`：当前已分发但未归还的 scratch 资源集合（`THashSet<const Resource*>`）。
- `fListenerStack`：以 null 指针分隔的监听器栈，支持嵌套作用域。
- `fProxyReadCounts`：代理读取计数映射。

### `PendingUseListener` (内部接口)
```cpp
virtual void onUseCompleted(ScratchResourceManager*) = 0;
```
当消费任务通知资源已被使用时调用，通常用于递减读取计数和归还资源。

## 公共 API 函数

- `getScratchTexture(SkISize, TextureInfo, label) -> sk_sp<Texture>`：获取 scratch 纹理。
- `returnTexture(sk_sp<Texture>)`：将纹理标记为可复用。
- `pushScope() / popScope()`：推入/弹出作用域栈。
- `notifyResourcesConsumed()`：通知当前作用域中的所有监听器，资源已被消费。
- `markResourceInUse(PendingUseListener*)`：注册待使用监听器。
- `pendingReadCount / removePendingRead`：代理读取计数操作。

## 内部实现细节

### 作用域栈机制
监听器栈使用 null 指针作为作用域分隔符：
- `pushScope()`：向栈中追加 null。
- `notifyResourcesConsumed()`：从栈顶向下遍历到最近的 null（或栈底），调用所有监听器的 `onUseCompleted`。
- `popScope()`：弹出到最近的 null，但不调用未消费的监听器（允许跨 Recording 保留资源）。

### Scratch 纹理获取流程
1. 尝试从 `fResourceProvider` 获取 scratch 纹理，传入 `fUnavailable` 排除已分发的资源。
2. 获取成功后将资源添加到 `fUnavailable`。
3. 当 `returnTexture` 被调用时，从 `fUnavailable` 中移除，使其可被后续请求复用。

## 依赖关系

- `ResourceProvider`：实际的资源获取。
- `ResourceCache::ScratchResourceSet`：不可用资源集合类型。
- `TextureProxy`：代理读取计数跟踪。

## 设计模式与设计决策

1. **作用域栈模式**：通过推入/弹出作用域，将资源的写入任务和消费任务关联起来，确保资源在正确的时机被归还。
2. **监听器回调**：解耦资源生产者和消费者，生产者注册监听器，消费者通过 `notifyResourcesConsumed` 触发。
3. **生命周期限定**：管理器仅在 `prepareResources()` 阶段存在，之后资源复用已固定。

## 性能考量

- Scratch 资源复用避免了 Recording 内重复创建相同规格的纹理。
- `fUnavailable` 哈希集合确保 O(1) 的不可用检查。
- 作用域栈的操作复杂度与监听器数量线性相关，通常很少。

## 相关文件

- `src/gpu/graphite/ResourceProvider.h/.cpp`：资源提供者。
- `src/gpu/graphite/TextureProxy.h/.cpp`：纹理代理。
- `src/gpu/graphite/ResourceCache.h/.cpp`：资源缓存。
