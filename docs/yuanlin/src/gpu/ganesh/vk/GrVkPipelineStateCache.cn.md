# GrVkPipelineStateCache

> 源文件
> - src/gpu/ganesh/vk/GrVkPipelineStateCache.cpp

## 概述

`GrVkPipelineStateCache` 是 Skia Ganesh Vulkan 后端中管线状态缓存的实现类。它是 `GrVkResourceProvider` 的内部类（`PipelineStateCache`），负责缓存和管理 `GrVkPipelineState` 对象。该类使用 LRU（最近最少使用）缓存策略，根据程序描述符（`GrProgramDesc`）查找或创建管线状态，避免重复编译着色器和创建管线对象。

主要职责包括：
- 基于程序描述符缓存管线状态
- 实现 LRU 缓存策略，自动淘汰旧对象
- 追踪缓存命中率和编译失败统计
- 在缓存未命中时调用构建器创建新状态
- 管理缓存条目的生命周期和 GPU 资源释放

该类是 Vulkan 后端性能优化的关键组件，着色器编译和管线创建是昂贵的操作，缓存可以显著提升渲染性能。

## 架构位置

`GrVkPipelineStateCache` 在 Vulkan 资源管理系统中的位置：

```
Skia Ganesh Vulkan 后端
  └─ GrVkResourceProvider (资源提供者)
      └─ PipelineStateCache (管线状态缓存) ← 当前类
          ├─ SkLRUCache<GrProgramDesc, Entry> (LRU 缓存)
          └─ Stats (统计信息)
```

该类作为 `GrVkResourceProvider` 的嵌套类，专门负责管线状态的缓存管理。

## 主要类与结构体

### 核心类

| 类名 | 说明 |
|------|------|
| `GrVkResourceProvider::PipelineStateCache` | 管线状态缓存管理器 |

### 内部结构体

**Entry**
```cpp
struct Entry {
    GrVkGpu* fGpu;                              // GPU 设备指针
    std::unique_ptr<GrVkPipelineState> fPipelineState;  // 管线状态对象

    Entry(GrVkGpu* gpu, GrVkPipelineState* pipelineState);
    ~Entry();  // 析构时释放管线状态的 GPU 资源
};
```

缓存条目封装了管线状态对象和必要的清理逻辑。

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fMap` | `SkLRUCache<GrProgramDesc, unique_ptr<Entry>>` | LRU 缓存映射 |
| `fGpu` | `GrVkGpu*` | 关联的 GPU 设备 |
| `fStats` | `Stats` | 缓存统计信息（继承或关联） |

## 公共 API 函数

### 构造与析构

```cpp
PipelineStateCache(GrVkGpu* gpu);
```
构造函数，初始化 LRU 缓存，缓存大小由 `GrContextOptions::fRuntimeProgramCacheSize` 配置。

```cpp
~PipelineStateCache();
```
析构函数，断言所有缓存已清空，在调试模式下输出缓存统计信息。

### 缓存管理

```cpp
void release();
```
清空缓存，释放所有管线状态对象。

### 查找或创建

```cpp
GrVkPipelineState* findOrCreatePipelineState(
    GrRenderTarget* renderTarget,
    const GrProgramInfo& programInfo,
    VkRenderPass compatibleRenderPass,
    bool overrideSubpassForResolveLoad);
```
主要的公共接口，根据渲染目标和程序信息查找或创建管线状态。返回管线状态指针（缓存拥有所有权）。

## 内部实现细节

### 缓存查找流程

`findOrCreatePipelineState` 实现了完整的查找和创建流程：

1. **验证模板附件**（调试模式）：
```cpp
if (programInfo.isStencilEnabled()) {
    SkASSERT(renderTarget->getStencilAttachment(programInfo.numSamples() > 1));
    SkASSERT(renderTarget->numStencilBits(programInfo.numSamples() > 1) == 8);
    SkASSERT(renderTarget->getStencilAttachment(...)->numSamples() ==
             programInfo.numSamples());
}
```

2. **生成程序描述符**：
```cpp
auto flags = overrideSubpassForResolveLoad
    ? GrCaps::ProgramDescOverrideFlags::kVulkanHasResolveLoadSubpass
    : GrCaps::ProgramDescOverrideFlags::kNone;

GrProgramDesc desc = fGpu->caps()->makeDesc(renderTarget, programInfo, flags);
```
描述符包含所有影响管线状态的信息，用作缓存键。

3. **调用实现方法**：
```cpp
auto tmp = this->findOrCreatePipelineStateImpl(desc, programInfo,
                                               compatibleRenderPass,
                                               overrideSubpassForResolveLoad, &stat);
```

4. **更新统计信息**：
```cpp
if (!tmp) {
    fStats.incNumInlineCompilationFailures();
} else {
    fStats.incNumInlineProgramCacheResult(stat);
}
```

### 实现方法

`findOrCreatePipelineStateImpl` 是实际执行查找和创建的方法：

```cpp
GrVkPipelineState* findOrCreatePipelineStateImpl(
    const GrProgramDesc& desc,
    const GrProgramInfo& programInfo,
    VkRenderPass compatibleRenderPass,
    bool overrideSubpassForResolveLoad,
    Stats::ProgramCacheResult* stat) {

    *stat = Stats::ProgramCacheResult::kHit;

    // 尝试从缓存查找
    std::unique_ptr<Entry>* entry = fMap.find(desc);
    if (!entry) {
        // 缓存未命中，创建新的管线状态
        *stat = Stats::ProgramCacheResult::kMiss;

        GrVkPipelineState* pipelineState =
            GrVkPipelineStateBuilder::CreatePipelineState(
                fGpu, desc, programInfo, compatibleRenderPass,
                overrideSubpassForResolveLoad);

        if (!pipelineState) {
            return nullptr;  // 创建失败
        }

        // 插入缓存
        entry = fMap.insert(desc, std::make_unique<Entry>(fGpu, pipelineState));
        return (*entry)->fPipelineState.get();
    }

    // 缓存命中
    return (*entry)->fPipelineState.get();
}
```

### Entry 生命周期管理

`Entry` 的析构函数负责清理 GPU 资源：
```cpp
~Entry() {
    if (fPipelineState) {
        fPipelineState->freeGPUResources(fGpu);
    }
}
```

当 LRU 缓存淘汰条目或缓存被清空时，`Entry` 的析构函数自动调用，确保 GPU 资源正确释放。

### 缓存大小配置

缓存大小由 `GrContextOptions` 配置：
```cpp
PipelineStateCache::PipelineStateCache(GrVkGpu* gpu)
    : fMap(gpu->getContext()->priv().options().fRuntimeProgramCacheSize)
    , fGpu(gpu) {
}
```

默认大小通常为 256，但可以根据应用需求调整。较大的缓存可以提高命中率，但会占用更多内存。

### 调试统计

在调试模式下，析构时输出缓存统计：
```cpp
#ifdef SK_DEBUG
if (c_DisplayVkPipelineCache) {
    int misses = fStats.numInlineProgramCacheResult(CacheResult::kMiss) +
                 fStats.numPreProgramCacheResult(CacheResult::kMiss);
    int total = misses + fStats.numInlineProgramCacheResult(CacheResult::kHit) +
                         fStats.numPreProgramCacheResult(CacheResult::kHit);

    SkDebugf("--- Pipeline State Cache ---\n");
    SkDebugf("Total requests: %d\n", total);
    SkDebugf("Cache misses: %d\n", misses);
    SkDebugf("Cache miss %%: %f\n", (total > 0) ? 100.f * misses / total : 0.0f);
}
#endif
```

通过设置 `c_DisplayVkPipelineCache` 为 `true` 可以启用统计输出。

### 程序描述符作为键

`GrProgramDesc` 包含所有影响编译和管线状态的信息：
- 着色器代码哈希
- 顶点属性配置
- 混合模式
- 渲染目标格式
- 模板设置
- MSAA 配置
- Vulkan 特定标志（如 resolve load subpass）

描述符实现了高效的哈希和比较，确保缓存查找快速且准确。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkLRUCache` | LRU 缓存实现 |
| `GrVkGpu` | GPU 设备访问 |
| `GrVkPipelineState` | 缓存的对象类型 |
| `GrVkPipelineStateBuilder` | 创建新的管线状态 |
| `GrProgramDesc` | 缓存键 |
| `GrProgramInfo` | 程序信息 |
| `GrCaps` | 生成程序描述符 |
| `GrContextOptions` | 缓存大小配置 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `GrVkResourceProvider` | 通过缓存管理管线状态 |
| `GrVkOpsRenderPass` | 通过资源提供者获取管线状态 |

## 设计模式与设计决策

### 缓存代理模式
该类作为 `GrVkPipelineState` 的缓存代理，拦截创建请求，返回缓存对象或创建新对象。

### LRU 淘汰策略
使用 `SkLRUCache` 实现自动淘汰最近最少使用的对象，在有限内存下保持较高的命中率。

### 嵌套类设计
作为 `GrVkResourceProvider` 的嵌套类，封装实现细节，外部只需通过资源提供者接口访问。

### 统计追踪
集成统计功能，帮助开发者和性能分析工具了解缓存效率，识别性能瓶颈。

### RAII 资源管理
通过 `Entry` 的析构函数自动管理 GPU 资源，确保在缓存淘汰或清空时正确清理。

### 可配置缓存大小
通过 `GrContextOptions` 配置缓存大小，允许应用根据内存预算和性能需求调整。

## 性能考量

### 缓存命中率
高的缓存命中率直接转化为性能提升。着色器编译和管线创建可能需要几十到几百毫秒，缓存可以将这些操作减少到几乎为零。

### 缓存大小权衡
- **较小缓存**：内存占用少，但命中率低，可能频繁编译
- **较大缓存**：命中率高，但占用更多内存
- **默认 256**：在大多数场景下提供良好的平衡

### LRU 策略优势
LRU 策略确保频繁使用的管线状态保留在缓存中，而长时间未使用的对象被淘汰，适合大多数渲染场景的访问模式。

### 程序描述符效率
`GrProgramDesc` 的高效哈希和比较对缓存性能至关重要。描述符应该足够紧凑以快速比较，同时包含所有必要信息以避免误命中。

### 统计开销
统计信息收集在发布版本中通过条件编译禁用，确保零开销。

### 延迟创建
仅在实际需要时创建管线状态，避免预先创建大量不会使用的对象。

### 资源释放时机
通过 LRU 缓存的自动淘汰机制，确保在内存压力下及时释放不常用的对象，而不是等到程序结束。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/vk/GrVkResourceProvider.h` | 宿主类 | 包含缓存作为成员 |
| `src/gpu/ganesh/vk/GrVkPipelineState.h` | 缓存对象 | 被缓存的管线状态 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.h` | 依赖 | 创建新的管线状态 |
| `src/gpu/ganesh/GrProgramDesc.h` | 依赖 | 缓存键 |
| `src/gpu/ganesh/GrProgramInfo.h` | 依赖 | 程序信息 |
| `src/core/SkLRUCache.h` | 依赖 | LRU 缓存实现 |
| `include/gpu/ganesh/GrContextOptions.h` | 依赖 | 缓存配置 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | 依赖 | GPU 设备 |
