# GlobalCache

> 源文件
> - src/gpu/graphite/GlobalCache.h
> - src/gpu/graphite/GlobalCache.cpp

## 概述

`GlobalCache` 是 Graphite 中的共享资源缓存，允许多个 `Context` 实例之间共享昂贵的GPU资源（如编译的着色器和图形管线）。这显著减少了多窗口或多设备应用中的资源重复和编译时间。

`GlobalCache` 是线程安全的，支持并发访问，并使用引用计数和最近最少使用（LRU）策略管理资源生命周期。

## 主要类与结构体

### GlobalCache 类

```cpp
class GlobalCache : public SkRefCnt {
public:
    static sk_sp<GlobalCache> Make();
    ~GlobalCache() override;

    // 添加或查找图形管线
    sk_sp<GraphicsPipeline> findOrCreateGraphicsPipeline(
            ResourceProvider*,
            const GraphicsPipelineDesc&);

    // 添加或查找编译的着色器
    sk_sp<ComputePipeline> findOrCreateComputePipeline(
            ResourceProvider*,
            const ComputePipelineDesc&);

    // 资源管理
    void deleteResources();
    void freeGpuResources();

    // 统计和调试
    size_t getResourceCount() const;
    size_t getResourceBytes() const;

private:
    GlobalCache();

    class ResourceCache;
    std::unique_ptr<ResourceCache> fResourceCache;

    // 线程安全
    mutable SkMutex fMutex;
};
```

## 公共 API 函数

### findOrCreateGraphicsPipeline

```cpp
sk_sp<GraphicsPipeline> findOrCreateGraphicsPipeline(
        ResourceProvider* resourceProvider,
        const GraphicsPipelineDesc& desc);
```

查找或创建图形管线：
1. 使用描述符作为键查找缓存
2. 如果找到，返回现有管线
3. 如果未找到，通过 `ResourceProvider` 创建新管线并缓存

**线程安全**：多个线程可以并发调用。

### deleteResources

```cpp
void deleteResources();
```

删除所有缓存的资源。通常在应用关闭时调用。

### freeGpuResources

```cpp
void freeGpuResources();
```

释放 GPU 资源但保留 CPU 端数据结构。用于低内存情况。

## 内部实现细节

### 缓存策略

- **查找优先**：首先检查缓存
- **创建后缓存**：新资源立即缓存
- **LRU 驱逐**：达到预算时驱逐最少使用的资源

### 线程安全

使用 `SkMutex` 保护所有缓存操作：
- `findOrCreate` 操作原子化
- 避免竞争条件
- 允许多个 `Context` 并发访问

### 资源生命周期

- **引用计数**：`sk_sp<>` 管理所有权
- **缓存持有弱引用**：资源可以超出缓存范围
- **定期清理**：删除零引用的资源

### 预算管理

缓存有最大预算（字节数和/或资源数）：
- 超出预算时驱逐 LRU 资源
- 可配置的预算策略
- 监控和报告使用情况

## 使用场景

### 多窗口应用

```cpp
sk_sp<GlobalCache> globalCache = GlobalCache::Make();

// 窗口 1
auto context1 = Context::MakeMetal(..., globalCache);

// 窗口 2（共享缓存）
auto context2 = Context::MakeMetal(..., globalCache);
```

两个上下文共享编译的管线，节省编译时间和内存。

### 设备切换

在多GPU系统中，`GlobalCache` 可以在不同设备间共享兼容的资源。

## 性能考量

### 编译时间

- **首次创建**：昂贵（着色器编译）
- **缓存命中**：几乎零开销
- **多Context**：显著减少总编译时间

### 内存开销

- **共享资源**：减少重复
- **缓存开销**：哈希表和LRU链表
- **预算控制**：限制总内存使用

### 并发性能

- **锁争用**：`fMutex` 可能成为瓶颈
- **细粒度锁**：未来优化方向
- **读优化**：查找比插入更频繁

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/GraphicsPipeline.h` | 缓存的管线类型 |
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 管线描述符（键） |
| `src/gpu/graphite/ResourceProvider.h` | 创建资源 |
| `src/gpu/graphite/Context.h` | 使用 GlobalCache |
| `src/gpu/graphite/GraphiteResourceKey.h` | 资源键 |
| `include/gpu/graphite/ContextOptions.h` | 缓存配置选项 |
