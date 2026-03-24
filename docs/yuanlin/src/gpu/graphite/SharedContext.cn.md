# SharedContext

> 源文件: src/gpu/graphite/SharedContext.h, src/gpu/graphite/SharedContext.cpp

## 概述

`SharedContext` 是 Skia Graphite 渲染架构中的核心上下文对象，负责管理在多个 `Recorder` 之间共享的资源和配置。该类继承自 `SkRefCnt`，提供线程安全的资源管理、图形管线缓存、着色器代码字典以及后端能力查询接口。

`SharedContext` 是 Graphite 多 `Recorder` 设计的关键组成部分，允许多个录制器并发创建命令缓冲区，同时共享管线、着色器和全局资源。每个 `Context` 持有一个 `SharedContext` 实例，并为每个 `Recorder` 提供引用。

## 架构位置

`SharedContext` 在 Graphite 架构中的位置：

```
Graphite 上下文架构：
  ├── Context（客户端上下文）
  │   ├── SharedContext（共享上下文）★
  │   │   ├── Caps（后端能力）
  │   │   ├── GlobalCache（全局管线缓存）
  │   │   ├── PipelineManager（管线管理器）
  │   │   ├── ShaderCodeDictionary（着色器字典）
  │   │   ├── RendererProvider（渲染器提供者）
  │   │   └── ThreadSafeResourceProvider（线程安全资源提供者）
  │   └── Recorder（命令录制器，多个）
  │       └── ResourceProvider（每个 Recorder 独立）
  └── 后端特定实现：
      ├── MtlSharedContext（Metal）
      ├── VulkanSharedContext（Vulkan）
      └── DawnSharedContext（Dawn）
```

协作关系：
- **Context**: 拥有 `SharedContext` 并为 `Recorder` 提供访问
- **Recorder**: 通过 `SharedContext` 访问共享资源和能力
- **ResourceProvider**: 每个 `Recorder` 独立的资源提供者，通过 `makeResourceProvider()` 创建

## 主要类与结构体

### SharedContext 类

```cpp
class SharedContext : public SkRefCnt {
public:
    ~SharedContext() override;

    // 能力和配置查询
    const Caps* caps() const;
    BackendApi backend() const;
    Protected isProtected() const;

    // 共享资源访问
    GlobalCache* globalCache();
    PipelineManager* pipelineManager();
    const RendererProvider* rendererProvider() const;
    ShaderCodeDictionary* shaderCodeDictionary();

    // 资源提供者工厂（由后端实现）
    virtual std::unique_ptr<ResourceProvider> makeResourceProvider(
        SingleOwner* owner,
        uint32_t recorderID,
        size_t resourceBudget) = 0;

    // 图形管线查找/创建
    sk_sp<GraphicsPipeline> findOrCreateGraphicsPipeline(
        const RuntimeEffectDictionary* rtDict,
        const UniqueKey& pipelineKey,
        const GraphicsPipelineDesc& desc,
        const RenderPassDesc& rpDesc,
        SkEnumBitMask<PipelineCreationFlags> flags);

    // 后端特定接口（由子类实现）
    virtual bool isDeviceLost() const;
    virtual void deviceTick(Context* context);
    virtual void syncPipelineData(PersistentPipelineStorage*, size_t maxSize);

    // 捕获管理器（用于调试和录制）
    SkCaptureManager* captureManager();

    // 资源管理
    void dumpMemoryStatistics(SkTraceMemoryDump*) const;
    void freeGpuResources();
    void purgeResourcesNotUsedSince(StdSteadyClock::time_point purgeTime);
    void forceProcessReturnedResources();

protected:
    SharedContext(std::unique_ptr<const Caps> caps,
                  BackendApi backend,
                  SkExecutor* executor,
                  SkSpan<sk_sp<SkRuntimeEffect>> userDefinedKnownRuntimeEffects);

    // 线程安全资源提供者的预算（所有资源应为 0 大小）
    static constexpr size_t kThreadedSafeResourceBudget = 256;

    // 成员变量
    mutable SingleOwner fSingleOwner;
    std::unique_ptr<ThreadSafeResourceProvider> fThreadSafeResourceProvider;

private:
    // 由子类实现的管线创建
    virtual sk_sp<GraphicsPipeline> createGraphicsPipeline(
        const RuntimeEffectDictionary*,
        const UniqueKey&,
        const GraphicsPipelineDesc&,
        const RenderPassDesc&,
        SkEnumBitMask<PipelineCreationFlags>,
        uint32_t compilationID) = 0;

    // 由 Context 调用的设置方法
    void setRendererProvider(std::unique_ptr<RendererProvider>);
    void setCaptureManager(sk_sp<SkCaptureManager>);

    // 成员变量
    std::unique_ptr<const Caps> fCaps;
    BackendApi fBackend;
    GlobalCache fGlobalCache;
    PipelineManager fPipelineManager;
    std::unique_ptr<RendererProvider> fRendererProvider;
    ShaderCodeDictionary fShaderDictionary;
    sk_sp<SkCaptureManager> fCaptureManager;
};
```

### 关键成员变量

| 成员变量 | 类型 | 用途 |
|---------|------|------|
| `fCaps` | `std::unique_ptr<const Caps>` | 后端能力查询接口 |
| `fBackend` | `BackendApi` | 后端类型（Metal/Vulkan/Dawn） |
| `fGlobalCache` | `GlobalCache` | 全局图形管线缓存 |
| `fPipelineManager` | `PipelineManager` | 管线编译和管理 |
| `fRendererProvider` | `std::unique_ptr<RendererProvider>` | 渲染步骤提供者 |
| `fShaderDictionary` | `ShaderCodeDictionary` | 着色器代码片段字典 |
| `fThreadSafeResourceProvider` | `std::unique_ptr<ThreadSafeResourceProvider>` | 线程安全资源提供者 |
| `fCaptureManager` | `sk_sp<SkCaptureManager>` | 命令捕获管理器 |

## 公共 API 函数

### 构造函数

```cpp
protected:
SharedContext(std::unique_ptr<const Caps> caps,
              BackendApi backend,
              SkExecutor* executor,
              SkSpan<sk_sp<SkRuntimeEffect>> userDefinedKnownRuntimeEffects);
```

**参数说明**:
- `caps`: 后端能力对象（由后端子类创建）
- `backend`: 后端 API 类型枚举
- `executor`: 任务执行器（用于异步编译，当前未使用）
- `userDefinedKnownRuntimeEffects`: 用户定义的已知运行时效果数组

**初始化流程**:
1. 移动 `caps` 到 `fCaps` 成员
2. 设置 `fBackend` 标识
3. 初始化 `fShaderDictionary`，传入 uniform/storage buffer 布局
4. 初始化空的 `fGlobalCache` 和 `fPipelineManager`

### 能力查询

```cpp
const Caps* caps() const;
BackendApi backend() const;
Protected isProtected() const;
```

**功能**:
- **caps()**: 返回后端能力对象，用于查询特性支持情况
- **backend()**: 返回后端类型（`kMetal`、`kVulkan`、`kDawn`）
- **isProtected()**: 返回是否支持受保护内存（用于 DRM 内容）

### 共享资源访问

```cpp
GlobalCache* globalCache();
PipelineManager* pipelineManager();
const RendererProvider* rendererProvider() const;
ShaderCodeDictionary* shaderCodeDictionary();
```

**功能**:
- **globalCache()**: 访问全局图形管线缓存
- **pipelineManager()**: 访问管线编译管理器
- **rendererProvider()**: 访问渲染步骤注册表
- **shaderCodeDictionary()**: 访问着色器代码片段字典

### 图形管线查找/创建

```cpp
sk_sp<GraphicsPipeline> findOrCreateGraphicsPipeline(
    const RuntimeEffectDictionary* runtimeDict,
    const UniqueKey& pipelineKey,
    const GraphicsPipelineDesc& pipelineDesc,
    const RenderPassDesc& renderPassDesc,
    SkEnumBitMask<PipelineCreationFlags> pipelineCreationFlags);
```

**功能**: 从全局缓存中查找图形管线，如果不存在则创建新管线。

**工作流程**:
1. 调用 `globalCache->findGraphicsPipeline()` 尝试查找
2. 如果未找到，调用虚函数 `createGraphicsPipeline()` 创建新管线
3. 将新管线添加到全局缓存（处理竞态条件）
4. 如果设置了管线回调，序列化管线描述并触发回调

**线程安全性**: 无锁管线创建，通过 `GlobalCache::addGraphicsPipeline()` 处理竞态。

**关键决策**:
- 允许多个线程同时创建相同的管线，第一个完成的被缓存
- 冗余的管线创建工作在罕见的竞态中被丢弃
- 避免在管线创建时锁定全局缓存，提高并发性能

### 资源提供者工厂

```cpp
virtual std::unique_ptr<ResourceProvider> makeResourceProvider(
    SingleOwner* owner,
    uint32_t recorderID,
    size_t resourceBudget) = 0;
```

**功能**: 为每个 `Recorder` 创建独立的资源提供者（纯虚函数）。

**后端实现示例**:
```cpp
// Metal 后端
std::unique_ptr<ResourceProvider> MtlSharedContext::makeResourceProvider(...) {
    return std::make_unique<MtlResourceProvider>(this, owner, recorderID, budget);
}
```

### 资源管理

```cpp
void dumpMemoryStatistics(SkTraceMemoryDump* traceMemoryDump) const;
void freeGpuResources();
void purgeResourcesNotUsedSince(StdSteadyClock::time_point purgeTime);
void forceProcessReturnedResources();
```

**功能**:
- **dumpMemoryStatistics()**: 导出内存统计信息到追踪工具
- **freeGpuResources()**: 释放所有可释放的 GPU 资源
- **purgeResourcesNotUsedSince()**: 清除指定时间后未使用的资源
- **forceProcessReturnedResources()**: 强制处理已返回的资源

这些方法委托给 `fThreadSafeResourceProvider` 处理。

### 后端特定接口

```cpp
virtual bool isDeviceLost() const;
virtual void deviceTick(Context* context);
virtual void syncPipelineData(PersistentPipelineStorage*, size_t maxSize);
```

**功能**:
- **isDeviceLost()**: 检查设备是否进入不可恢复的丢失状态（默认返回 `false`）
- **deviceTick()**: 后端特定的每帧维护操作（如 Metal 的自动释放池）
- **syncPipelineData()**: 将管线数据同步到持久化存储（用于管线缓存）

## 内部实现细节

### 构造函数实现

```cpp
SharedContext::SharedContext(
    std::unique_ptr<const Caps> caps,
    BackendApi backend,
    SkExecutor* executor,
    SkSpan<sk_sp<SkRuntimeEffect>> userDefinedKnownRuntimeEffects)
    : fCaps(std::move(caps))
    , fBackend(backend)
    , fGlobalCache()
    , fPipelineManager()
    , fShaderDictionary(get_binding_layout(fCaps.get()), userDefinedKnownRuntimeEffects) {}
```

**绑定布局选择**:
```cpp
static Layout get_binding_layout(const Caps* caps) {
    ResourceBindingRequirements reqs = caps->resourceBindingRequirements();
    return caps->storageBufferSupport()
        ? reqs.fStorageBufferLayout
        : reqs.fUniformBufferLayout;
}
```

根据后端是否支持 storage buffer 选择 uniform 布局。

### 渲染器提供者设置

```cpp
void SharedContext::setRendererProvider(std::unique_ptr<RendererProvider> rendererProvider) {
    SkASSERT(rendererProvider && !fRendererProvider);  // 只能设置一次
    fRendererProvider = std::move(rendererProvider);
}
```

**调用时机**: 由 `Context` 在初始化时调用，必须在创建任何 `Recorder` 之前完成。

**延迟设置原因**: `RendererProvider` 需要访问 `QueueManager`，而队列管理器在 `Context` 层创建。

### 管线查找/创建流程

```cpp
sk_sp<GraphicsPipeline> SharedContext::findOrCreateGraphicsPipeline(...) {
    uint32_t compilationID = 0;
    sk_sp<GraphicsPipeline> pipeline =
        fGlobalCache.findGraphicsPipeline(pipelineKey, flags, &compilationID);

    if (!pipeline) {
        // 追踪管线创建事件
        TRACE_EVENT1_ALWAYS("skia.shaders", "createGraphicsPipeline", "desc", ...);

        // 调用后端特定的创建函数
        pipeline = this->createGraphicsPipeline(
            runtimeDict, pipelineKey, pipelineDesc, renderPassDesc, flags, compilationID);

        if (pipeline) {
            // 添加到缓存（处理竞态）
            bool addedToCache;
            std::tie(pipeline, addedToCache) = fGlobalCache.addGraphicsPipeline(pipelineKey, pipeline);

            // 触发管线缓存回调
            if (addedToCache && fGlobalCache.hasPipelineCallback()) {
                sk_sp<SkData> data = PipelineDescToData(...);
                fGlobalCache.invokePipelineCallback(
                    ContextOptions::PipelineCacheOp::kAddingPipeline,
                    pipeline.get(),
                    std::move(data));
            }
        }
    }
    return pipeline;
}
```

**关键点**:
1. **无锁查找**: `findGraphicsPipeline()` 是线程安全的读操作
2. **并发创建**: 多个线程可能同时创建相同的管线
3. **竞态处理**: `addGraphicsPipeline()` 返回第一个添加的管线
4. **管线回调**: 支持将管线数据序列化到磁盘缓存

### 受保护内存支持

```cpp
Protected SharedContext::isProtected() const {
    return Protected(fCaps->protectedSupport());
}
```

**用途**: 查询是否支持受保护内存（用于 DRM 内容，防止屏幕截图）。

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `Caps` | 查询后端能力和资源绑定需求 |
| `GlobalCache` | 缓存图形管线和其他共享资源 |
| `PipelineManager` | 管理管线编译任务 |
| `ShaderCodeDictionary` | 存储着色器代码片段和节点定义 |
| `RendererProvider` | 提供渲染步骤的注册表 |
| `ThreadSafeResourceProvider` | 线程安全的资源提供者 |
| `ResourceBindingRequirements` | 后端资源绑定需求 |
| `RuntimeEffectDictionary` | 运行时效果字典 |
| `GraphicsPipelineDesc` | 图形管线描述符 |
| `RenderPassDesc` | 渲染通道描述符 |

### 外部依赖

| 依赖 | 用途 |
|------|------|
| `SkRefCnt` | 引用计数基类 |
| `SkExecutor` | 异步任务执行器 |
| `SkCaptureManager` | 命令捕获和录制 |
| `SkTraceMemoryDump` | 内存统计导出 |
| `SkRuntimeEffect` | 用户自定义的着色器效果 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `Context` | 拥有并管理 `SharedContext` |
| `Recorder` | 通过 `SharedContext` 访问共享资源 |
| `ResourceProvider` | 查询能力和使用共享字典 |
| `GraphicsPipeline` | 通过 `SharedContext` 创建 |

## 设计模式与设计决策

### 抽象工厂模式

`SharedContext` 是后端特定上下文的抽象基类：
```cpp
class SharedContext {
    virtual std::unique_ptr<ResourceProvider> makeResourceProvider(...) = 0;
    virtual sk_sp<GraphicsPipeline> createGraphicsPipeline(...) = 0;
};

class MtlSharedContext : public SharedContext {
    std::unique_ptr<ResourceProvider> makeResourceProvider(...) override;
    sk_sp<GraphicsPipeline> createGraphicsPipeline(...) override;
};
```

### 单例模式（变体）

每个 `Context` 持有一个 `SharedContext` 实例，所有 `Recorder` 共享：
- 全局缓存避免重复的管线编译
- 着色器字典在所有录制器间共享
- 能力查询结果一致

### 策略模式

后端特定行为通过虚函数实现：
```cpp
virtual bool isDeviceLost() const { return false; }  // 默认策略
virtual void deviceTick(Context*) {}                 // 可选策略
```

Metal、Vulkan、Dawn 各自提供不同的策略实现。

### 延迟初始化

`fRendererProvider` 和 `fCaptureManager` 延迟设置：
- 允许在创建 `SharedContext` 后进行额外配置
- 避免构造函数参数过多
- 确保依赖项按正确顺序初始化

### 关键设计决策

1. **共享资源集中化**: 所有跨 `Recorder` 共享的资源集中在 `SharedContext`
2. **无锁管线查找**: 通过无锁缓存实现高并发管线访问
3. **竞态容忍**: 允许冗余的管线创建，避免创建时的锁竞争
4. **线程安全资源提供者**: `ThreadSafeResourceProvider` 独立于 `Recorder` 的资源提供者
5. **后端抽象**: 通过虚函数隔离后端特定逻辑

## 性能考量

### 管线缓存

1. **全局缓存**: 避免跨 `Recorder` 的重复编译
2. **无锁查找**: 读操作无锁，最大化并发
3. **编译 ID 追踪**: 允许追踪管线编译性能

### 内存管理

1. **资源预算**: `ThreadSafeResourceProvider` 使用固定预算（256 字节）
2. **0 大小资源**: 线程安全提供者中的资源不占用预算
3. **内存统计**: 通过 `dumpMemoryStatistics()` 追踪内存使用

### 并发性能

1. **多 Recorder 并发**: 多个录制器可并发创建命令缓冲区
2. **管线创建并行化**: 多个线程可同时创建不同的管线
3. **竞态窗口最小化**: 管线创建是无锁操作，只有添加到缓存时需要同步

### 追踪和调试

1. **TRACE_EVENT**: 管线创建事件追踪
2. **管线生命周期日志**: 通过 `SK_PIPELINE_LIFETIME_LOGGING` 追踪管线生命周期
3. **内存转储**: 支持将内存统计导出到追踪工具

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/Context.h` | 拥有并管理 `SharedContext` |
| `src/gpu/graphite/Recorder.h` | 使用 `SharedContext` 访问共享资源 |
| `src/gpu/graphite/Caps.h` | 后端能力查询接口 |
| `src/gpu/graphite/GlobalCache.h` | 全局图形管线缓存 |
| `src/gpu/graphite/PipelineManager.h` | 管线编译管理 |
| `src/gpu/graphite/ShaderCodeDictionary.h` | 着色器代码片段字典 |
| `src/gpu/graphite/RendererProvider.h` | 渲染步骤提供者 |
| `src/gpu/graphite/ThreadSafeResourceProvider.h` | 线程安全资源提供者 |
| `src/gpu/graphite/ResourceProvider.h` | 每个 Recorder 的资源提供者 |
| `src/gpu/graphite/GraphicsPipeline.h` | 图形管线对象 |
| `src/gpu/graphite/mtl/MtlSharedContext.h` | Metal 后端实现 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | Vulkan 后端实现 |
| `src/gpu/graphite/dawn/DawnSharedContext.h` | Dawn 后端实现 |
