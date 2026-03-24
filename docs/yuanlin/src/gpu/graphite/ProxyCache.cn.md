# ProxyCache

> 源文件
> - src/gpu/graphite/ProxyCache.h
> - src/gpu/graphite/ProxyCache.cpp

## 概述

`ProxyCache` 是 Graphite 渲染引擎中专门负责缓存 `TextureProxy` 实例的管理类，它维护了一个 Recorder 本地的内部代理缓存系统。该类主要用于缓存实用工具所需的纹理代理，避免重复创建相同的纹理资源，从而提升渲染性能。与 Ganesh 引擎不同，`ProxyCache` 不用于客户端上传的位图（不需要生成 mipmap），而是专注于内部实用数据的缓存，因此设计上不支持带 mipmap 的缓存代理。

该缓存系统基于 `UniqueKey` 进行索引，能够自动处理源数据（如 `SkBitmap`）失效的情况，并通过消息总线机制实现失效通知。缓存项包含纹理代理和可选的变更监听器，确保资源的生命周期管理和内存使用的高效性。

## 架构位置

`ProxyCache` 位于 Skia 的 Graphite GPU 后端架构中，处于以下层次：

```
skgpu::graphite 命名空间
├── Recorder (记录器 - 拥有 ProxyCache 实例)
│   └── ProxyCache (代理缓存 - 每个 Recorder 独立拥有)
│       ├── TextureProxy (纹理代理 - 缓存的资源)
│       ├── UniqueKey (唯一键 - 缓存索引)
│       └── SkIDChangeListener (变更监听器 - 源数据失效通知)
├── ResourceCache (资源缓存 - 好友类，可访问 freeUniquelyHeld)
└── TextureUtils (纹理工具 - 提供位图转代理的功能)
```

该类作为 Recorder 的组成部分，与资源管理子系统紧密协作，提供了上层渲染系统所需的纹理代理缓存服务。

## 主要类与结构体

### ProxyCache 类

主缓存管理类，负责纹理代理的查找、创建和生命周期管理。

**关键成员变量：**
- `fCache`: `THashMap<UniqueKey, CacheEntry, UniqueKeyHash>` - 缓存映射表，使用 `UniqueKey` 作为键
- `fInvalidUniqueKeyInbox`: 消息总线收件箱，接收键失效通知消息

**主要方法：**
- `findOrCreateCachedProxy()`: 三个重载版本，分别处理 `SkBitmap`、`BitmapGeneratorFn` 和 `GPUGeneratorFn`
- `purgeAll()`: 清空所有缓存项
- `processInvalidKeyMsgs()`: 处理失效键消息
- `freeUniquelyHeld()`: 释放仅被缓存持有的代理
- `purgeProxiesNotUsedSince()`: 清理特定时间之前未使用的代理

### CacheEntry 结构体

```cpp
struct CacheEntry {
    sk_sp<TextureProxy> fProxy;              // 缓存的纹理代理
    sk_sp<SkIDChangeListener> fListener;     // 变更监听器（源位图不变时为 null）
};
```

缓存条目包含纹理代理和可选的监听器，监听器用于监测源数据的变化并自动触发缓存失效。

### UniqueKeyHash 结构体

```cpp
struct UniqueKeyHash {
    uint32_t operator()(const UniqueKey& key) const;
};
```

为 `UniqueKey` 提供哈希函数，用于在哈希表中快速查找。

## 公共 API 函数

### findOrCreateCachedProxy (SkBitmap 版本)

```cpp
sk_sp<TextureProxy> findOrCreateCachedProxy(Recorder* recorder,
                                            const SkBitmap& bitmap,
                                            std::string_view label);
```

根据 `SkBitmap` 查找或创建缓存的纹理代理。内部会从位图生成 `UniqueKey`，然后委托给生成器函数版本。

### findOrCreateCachedProxy (BitmapGeneratorFn 版本)

```cpp
sk_sp<TextureProxy> findOrCreateCachedProxy(Recorder* recorder,
                                            const UniqueKey& key,
                                            GeneratorContext context,
                                            BitmapGeneratorFn fn,
                                            std::string_view label = {});
```

使用外部管理的 `UniqueKey` 查找或创建缓存代理。如果缓存未命中，会调用提供的位图生成器函数创建位图，然后上传到 GPU 并缓存。失败时返回 `nullptr`。

**关键特性：**
- 生成器函数允许延迟创建位图数据
- 自动添加 `SkIDChangeListener` 监听源数据变化
- 只在位图被多个地方引用时添加监听器（`!bitmap.pixelRef()->unique()`）
- 纹理代理标签默认使用键的标签

### findOrCreateCachedProxy (GPUGeneratorFn 版本)

```cpp
sk_sp<TextureProxy> findOrCreateCachedProxy(Recorder* recorder,
                                            const UniqueKey& key,
                                            GeneratorContext context,
                                            GPUGeneratorFn fn,
                                            std::string_view label = {});
```

与 CPU 位图版本类似，但生成器函数直接返回 GPU 图像（`sk_sp<Image>`）而非 CPU 位图。

**特殊处理：**
- 强制实例化纹理代理，避免被当作临时 scratch 纹理
- 刷新定义图像内容的待处理工作，添加到根任务列表
- GPU 创建的代理不需要 `SkIDChangeListener`

### purgeAll

```cpp
void purgeAll();
```

清空所有缓存项，并标记所有监听器应该注销，防止内存泄漏。

## 内部实现细节

### 键生成机制

```cpp
void make_bitmap_key(skgpu::UniqueKey* key, const SkBitmap& bm) {
    SkIPoint origin = bm.pixelRefOrigin();
    SkIRect subset = SkIRect::MakePtSize(origin, bm.dimensions());

    static const skgpu::UniqueKey::Domain kProxyCacheDomain =
        skgpu::UniqueKey::GenerateDomain();
    skgpu::UniqueKey::Builder builder(key, kProxyCacheDomain, 5, "ProxyCache");
    builder[0] = bm.pixelRef()->getGenerationID();
    builder[1] = subset.fLeft;
    builder[2] = subset.fTop;
    builder[3] = subset.fRight;
    builder[4] = subset.fBottom;
}
```

位图键由 5 个部分组成：
1. `PixelRef` 的生成 ID（唯一标识位图数据源）
2-5. 子集矩形的四个坐标（left, top, right, bottom）

这确保了即使两个 `SkBitmap` 共享同一个 `PixelRef`，只要它们的子集不同，就会生成不同的键。

### 失效监听机制

```cpp
sk_sp<SkIDChangeListener> make_unique_key_invalidation_listener(
    const skgpu::UniqueKey& key, uint32_t recorderID) {
    class Listener : public SkIDChangeListener {
    public:
        Listener(const skgpu::UniqueKey& key, uint32_t recorderUniqueID)
                : fMsg(key, recorderUniqueID) {}

        void changed() override {
            SkMessageBus<skgpu::UniqueKeyInvalidatedMsg_Graphite, uint32_t>::Post(fMsg);
        }
    private:
        skgpu::UniqueKeyInvalidatedMsg_Graphite fMsg;
    };
    return sk_make_sp<Listener>(key, recorderID);
}
```

监听器实现了 `SkIDChangeListener` 接口，当源位图的生成 ID 改变时（通常是位图被销毁），会通过消息总线发送失效消息到对应的 Recorder。

### 缓存查找与创建模板

```cpp
template <typename CreateEntryFn>
sk_sp<TextureProxy> ProxyCache::findOrCreateCacheEntry(
    const UniqueKey& key, std::string_view label, CreateEntryFn fn) {
    this->processInvalidKeyMsgs();  // 先处理失效消息

    if (CacheEntry* cached = fCache.find(key)) {
        if (Resource* resource = cached->fProxy->texture()) {
            resource->updateAccessTime();  // 更新访问时间用于 LRU 策略
        }
        return cached->fProxy;
    }

    CacheEntry newEntry = fn(label.empty() ? key.tag() : label);
    if (newEntry.fProxy) {
        fCache.set(key, newEntry);  // 成功则添加到缓存
    }
    return newEntry.fProxy;
}
```

这个模板函数是所有 `findOrCreateCachedProxy` 方法的核心实现：
1. 首先处理失效消息，确保缓存状态是最新的
2. 查找缓存，如果命中则更新访问时间并返回
3. 缓存未命中时调用创建函数生成新条目
4. 只有成功创建时才添加到缓存

### 缓存清理策略

**唯一持有清理：**
```cpp
void ProxyCache::freeUniquelyHeld() {
    this->processInvalidKeyMsgs();
    TArray<UniqueKey> toRemove;

    fCache.foreach([&](const UniqueKey& key, const CacheEntry* entry) {
        if (entry->fProxy->unique()) {  // 仅被缓存引用
            toRemove.push_back(key);
        }
    });

    this->removeEntriesAndListeners(toRemove);
}
```

这个方法由 `ResourceCache` 友元类调用，用于释放那些除了缓存之外没有其他引用的代理。

**基于时间的清理：**
```cpp
void ProxyCache::purgeProxiesNotUsedSince(
    const StdSteadyClock::time_point* purgeTime) {
    this->processInvalidKeyMsgs();
    TArray<UniqueKey> toRemove;

    fCache.foreach([&](const UniqueKey& key, const CacheEntry* entry) {
        if (Resource* resource = entry->fProxy->texture();
            resource && (!purgeTime || resource->lastAccessTime() < *purgeTime)) {
            toRemove.push_back(key);
        }
    });

    this->removeEntriesAndListeners(toRemove);
}
```

根据资源的最后访问时间清理长期未使用的缓存项，实现了基于时间的 LRU 策略。

### 监听器注销机制

```cpp
void ProxyCache::removeEntriesAndListeners(SkSpan<const UniqueKey> toRemove) {
    for (const UniqueKey& k : toRemove) {
        CacheEntry* e = fCache.find(k);
        if (e->fListener) {
            e->fListener->markShouldDeregister();  // 标记应注销，避免泄漏
        }
        fCache.remove(k);
    }
}
```

移除缓存项时必须标记监听器应该注销，这样当位图最终被销毁时，监听器能够正确清理，避免内存泄漏。

## 依赖关系

### 直接依赖

| 依赖项 | 类型 | 用途 |
|-------|------|------|
| `SkBitmap` | Skia 核心类 | 源位图数据 |
| `SkPixelRef` | Skia 核心类 | 位图像素数据引用，提供生成 ID |
| `SkIDChangeListener` | Skia 核心类 | 监听像素数据变化 |
| `UniqueKey` | GPU 资源键 | 缓存索引键 |
| `TextureProxy` | Graphite 类 | 缓存的纹理代理对象 |
| `Recorder` | Graphite 类 | 记录器上下文 |
| `Resource` | Graphite 类 | GPU 资源基类，提供访问时间 |
| `SkMessageBus` | 消息系统 | 失效消息传递 |
| `TextureUtils` | Graphite 工具 | 位图转纹理代理 |

### 被依赖关系

- `Recorder`: 拥有 `ProxyCache` 实例，通过 `RecorderPriv` 访问
- `ResourceCache`: 友元类，调用 `freeUniquelyHeld()` 进行缓存清理
- 各种内部工具系统：使用 `ProxyCache` 缓存常用的纹理数据

## 设计模式与设计决策

### 1. 缓存模式（Cache Pattern）

`ProxyCache` 是典型的缓存模式实现，通过键值对存储避免重复创建相同资源。

**设计决策：**
- 使用 `UniqueKey` 而非直接使用 `SkBitmap` 指针，确保语义正确性
- 缓存键包含位图的子集信息，支持对同一 `PixelRef` 的不同区域缓存
- 不支持 mipmap 缓存，简化了内部工具纹理的管理

### 2. 观察者模式（Observer Pattern）

通过 `SkIDChangeListener` 实现了观察者模式，监听源数据的变化。

**设计决策：**
- 只在位图被多处引用时添加监听器，避免不必要的开销
- 使用消息总线而非直接回调，解耦了 `PixelRef` 和 `ProxyCache`
- 监听器标记注销机制避免了竞态条件和内存泄漏

### 3. 模板方法模式（Template Method Pattern）

`findOrCreateCacheEntry` 是模板方法，定义了缓存查找与创建的算法骨架，具体创建逻辑由调用者提供。

**设计优势：**
- 三个 `findOrCreateCachedProxy` 重载共享相同的核心逻辑
- 通过函数对象（生成器函数）实现策略替换
- 代码复用度高，易于维护

### 4. 延迟初始化（Lazy Initialization）

使用生成器函数实现延迟初始化，只在缓存未命中时才创建实际资源。

**设计决策：**
- CPU 位图生成器和 GPU 图像生成器分别处理不同的数据来源
- 生成器失败时返回空代理而不抛异常，调用者需检查返回值
- 上下文参数使用 `const void*`，提供灵活性但牺牲了类型安全

### 5. 资源生命周期管理

通过引用计数和主动清理策略管理缓存资源的生命周期。

**清理策略：**
- **失效驱动**：通过消息总线响应源数据销毁
- **引用计数驱动**：`freeUniquelyHeld()` 清理无外部引用的项
- **时间驱动**：`purgeProxiesNotUsedSince()` 清理长期未用的项
- **手动驱动**：`purgeAll()` 立即清空所有缓存

## 性能考量

### 1. 缓存命中率

**优化措施：**
- 使用 `THashMap` 提供 O(1) 平均查找时间
- 键生成包含位图的完整标识（生成 ID + 子集），确保正确性
- 访问时更新 `Resource` 的访问时间，支持 LRU 策略

### 2. 内存管理

**内存优化：**
- 监听器仅在必要时创建（位图有多个引用者）
- 提供多种清理策略，适应不同的内存压力场景
- GPU 生成的图像不创建监听器，减少开销

**潜在问题：**
- 注释提到 TODO(b/409888039)：GPU 生成的图像任务需要保留，确保乱序 Recording 能正确初始化纹理
- 缓存大小没有硬限制，可能在极端情况下占用过多内存

### 3. 多线程安全

**竞态条件处理：**
- 注释说明了可能的竞态：一个线程正在移除条目，另一个线程发送失效消息
- 通过 `markShouldDeregister()` 标记监听器，确保即使收到重复的失效消息也不会崩溃
- 每个 Recorder 有独立的 `ProxyCache` 实例，减少了跨线程共享

**设计限制：**
- 消息总线使用 Recorder ID 进行路由，确保消息发送到正确的缓存
- `processInvalidKeyMsgs()` 在每次查找前调用，确保缓存状态的一致性

### 4. GPU 资源实例化

```cpp
// 强制实例化，避免被当作 scratch 纹理
textureImage->textureProxyView().proxy()->instantiate(
    recorder->priv().resourceProvider());
```

对于 GPU 生成的图像，必须立即实例化纹理代理，确保它有固定的 GPU 资源而不是可能被复用的临时资源。

### 5. 访问时间跟踪

```cpp
if (Resource* resource = cached->fProxy->texture()) {
    resource->updateAccessTime();  // LRU 跟踪
}
```

缓存命中时更新访问时间，为基于时间的清理策略提供数据，实现了简单但有效的 LRU 管理。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/TextureProxy.h` | 使用 | 缓存的对象类型 |
| `src/gpu/graphite/Recorder.h` | 被包含 | Recorder 拥有 ProxyCache |
| `src/gpu/graphite/RecorderPriv.h` | 使用 | 访问 Recorder 的内部接口 |
| `src/gpu/graphite/ResourceCache.h` | 友元 | 调用内部清理方法 |
| `src/gpu/graphite/Resource.h` | 使用 | 访问时间跟踪 |
| `src/gpu/graphite/TextureUtils.h` | 使用 | 位图转代理功能 |
| `src/gpu/graphite/Image_Graphite.h` | 使用 | GPU 图像类型 |
| `src/gpu/ResourceKey.h` | 使用 | UniqueKey 定义 |
| `src/core/SkMessageBus.h` | 使用 | 失效消息传递 |
| `include/core/SkBitmap.h` | 使用 | 位图数据源 |
| `include/core/SkPixelRef.h` | 使用 | 像素数据引用和生成 ID |
| `src/core/SkTHash.h` | 使用 | 哈希表实现 |
