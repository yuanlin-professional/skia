# GrVkResourceProvider

> 源文件
> - `src/gpu/ganesh/vk/GrVkResourceProvider.h`
> - `src/gpu/ganesh/vk/GrVkResourceProvider.cpp`

## 概述

`GrVkResourceProvider` 是 Skia Ganesh Vulkan 后端的核心资源管理类，负责创建、缓存和复用各类 Vulkan 对象，包括渲染通道、管道、采样器、描述符集、命令池等。该类通过多级缓存策略显著减少 Vulkan 对象的创建开销，是 Vulkan 后端性能优化的关键组件。它还管理管道缓存的持久化，支持跨会话的着色器编译加速。

## 架构位置

`GrVkResourceProvider` 在 Ganesh Vulkan 架构中处于中心位置，作为资源工厂和缓存管理器：

```
GrVkGpu
    └── GrVkResourceProvider (资源提供器)
        ├── PipelineStateCache (管道状态缓存)
        ├── CompatibleRenderPassSet (渲染通道集合)
        ├── GrVkDescriptorSetManager (描述符集管理器)
        ├── GrVkCommandPool (命令池)
        └── 各类 Vulkan 对象缓存
```

该类与 `GrVkGpu` 紧密协作，为上层渲染操作提供各类资源，同时通过缓存机制优化资源分配性能。

## 主要类与结构体

### GrVkResourceProvider 类

**核心成员变量**：
```cpp
GrVkGpu* fGpu;                                  // GPU 接口
VkPipelineCache fPipelineCache;                 // Vulkan 管道缓存
sk_sp<PipelineStateCache> fPipelineStateCache;  // 管道状态缓存
skia_private::STArray<4, CompatibleRenderPassSet> fRenderPassArray;  // 渲染通道集合
skia_private::TArray<const GrVkRenderPass*> fExternalRenderPasses;  // 外部渲染通道
skia_private::TArray<MSAALoadPipeline> fMSAALoadPipelines;          // MSAA 加载管道
skia_private::STArray<4, GrVkCommandPool*> fActiveCommandPools;     // 活动命令池
skia_private::STArray<4, GrVkCommandPool*> fAvailableCommandPools;  // 可用命令池
SkTDynamicHash<GrVkSampler, Key> fSamplers;                         // 采样器缓存
SkTDynamicHash<GrVkSamplerYcbcrConversion, Key> fYcbcrConversions;  // YCbCr 转换缓存
skia_private::STArray<4, std::unique_ptr<GrVkDescriptorSetManager>> fDescriptorSetManagers;  // 描述符集管理器
GrVkDescriptorSetManager::Handle fUniformDSHandle;  // Uniform 描述符集句柄
GrVkDescriptorSetManager::Handle fInputDSHandle;    // Input 描述符集句柄
```

**资源句柄定义**：
```cpp
GR_DEFINE_RESOURCE_HANDLE_CLASS(CompatibleRPHandle)  // 兼容渲染通道句柄
```

**类型别名**：
```cpp
using SelfDependencyFlags = GrVkRenderPass::SelfDependencyFlags;
using LoadFromResolve = GrVkRenderPass::LoadFromResolve;
```

### PipelineStateCache 内部类

```cpp
class PipelineStateCache : public GrThreadSafePipelineBuilder {
    SkLRUCache<const GrProgramDesc, std::unique_ptr<Entry>, DescHash> fMap;
    GrVkGpu* fGpu;
};
```

LRU 缓存管道状态，支持线程安全的管道创建和查找。

### CompatibleRenderPassSet 内部类

```cpp
class CompatibleRenderPassSet {
    skia_private::STArray<4, GrVkRenderPass*> fRenderPasses;  // 兼容的渲染通道
    int fLastReturnedIndex;                                   // 最后返回的索引（优化查找）
};
```

管理一组兼容的渲染通道（相同附件配置，不同 load/store 操作）。

### MSAALoadPipeline 结构体

```cpp
struct MSAALoadPipeline {
    sk_sp<const GrVkPipeline> fPipeline;  // 管道对象
    const GrVkRenderPass* fRenderPass;    // 关联的渲染通道
};
```

缓存 MSAA 加载管道，用于 DMSAA 特性。

## 公共 API 函数

### 初始化与生命周期

**init**
```cpp
void init();
```
初始化资源提供器，创建 uniform 和 input attachment 描述符集管理器。

**destroyResources**
```cpp
void destroyResources();
```
销毁所有缓存资源，在销毁 VkDevice 前调用。假设所有队列空闲，命令缓冲区完成。

**releaseUnlockedBackendObjects**
```cpp
void releaseUnlockedBackendObjects();
```
释放未锁定的后端对象（主要是可用命令池），用于内存压力下释放资源。

### 管道管理

**makePipeline**
```cpp
sk_sp<const GrVkPipeline> makePipeline(
    const GrProgramInfo& programInfo,
    VkPipelineShaderStageCreateInfo* shaderStageInfo,
    int shaderStageCount,
    VkRenderPass compatibleRenderPass,
    VkPipelineLayout layout,
    uint32_t subpass);
```
创建 Vulkan 图形管道，使用管道缓存加速创建。

**findOrCreateCompatiblePipelineState** (两个重载)
```cpp
GrVkPipelineState* findOrCreateCompatiblePipelineState(
    GrRenderTarget* renderTarget,
    const GrProgramInfo& programInfo,
    VkRenderPass compatibleRenderPass,
    bool overrideSubpassForResolveLoad);

GrVkPipelineState* findOrCreateCompatiblePipelineState(
    const GrProgramDesc& desc,
    const GrProgramInfo& programInfo,
    VkRenderPass compatibleRenderPass,
    Stats::ProgramCacheResult* stat);
```
查找或创建兼容的管道状态。第一个重载用于运行时，第二个用于预编译（支持统计）。

**findOrCreateMSAALoadPipeline**
```cpp
sk_sp<const GrVkPipeline> findOrCreateMSAALoadPipeline(
    const GrVkRenderPass& renderPass,
    int numSamples,
    VkPipelineShaderStageCreateInfo* shaderStageInfo,
    VkPipelineLayout pipelineLayout);
```
查找或创建 MSAA 加载管道，用于将解析附件内容加载回 MSAA 附件（DMSAA）。

### 渲染通道管理

**findCompatibleRenderPass** (多个重载)
```cpp
const GrVkRenderPass* findCompatibleRenderPass(
    GrVkRenderTarget* target,
    CompatibleRPHandle* compatibleHandle,
    bool withResolve,
    bool withStencil,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve);

const GrVkRenderPass* findCompatibleRenderPass(
    GrVkRenderPass::AttachmentsDescriptor* desc,
    GrVkRenderPass::AttachmentFlags flags,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve,
    CompatibleRPHandle* compatibleHandle = nullptr);
```
查找或创建兼容的渲染通道（基本 load/store 渲染通道）。返回句柄用于后续快速查找。

**findRenderPass** (两个重载)
```cpp
const GrVkRenderPass* findRenderPass(
    GrVkRenderTarget* target,
    const LoadStoreOps& colorOps,
    const LoadStoreOps& resolveOps,
    const LoadStoreOps& stencilOps,
    CompatibleRPHandle* compatibleHandle,
    bool withResolve,
    bool withStencil,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve);

const GrVkRenderPass* findRenderPass(
    const CompatibleRPHandle& compatibleHandle,
    const LoadStoreOps& colorOps,
    const LoadStoreOps& resolveOps,
    const LoadStoreOps& stencilOps);
```
查找或创建具有特定 load/store 操作的渲染通道。第二个重载通过句柄快速查找。

**findCompatibleExternalRenderPass**
```cpp
const GrVkRenderPass* findCompatibleExternalRenderPass(
    VkRenderPass renderPass,
    uint32_t colorAttachmentIndex);
```
查找或创建兼容的外部渲染通道（用于次级命令缓冲区）。

### 采样器管理

**findOrCreateCompatibleSampler**
```cpp
GrVkSampler* findOrCreateCompatibleSampler(
    GrSamplerState params,
    const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo);
```
查找或创建兼容的采样器，支持 YCbCr 转换。

**findOrCreateCompatibleSamplerYcbcrConversion**
```cpp
GrVkSamplerYcbcrConversion* findOrCreateCompatibleSamplerYcbcrConversion(
    const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo);
```
查找或创建 YCbCr 转换对象。

### 描述符集管理

**getUniformDescriptorSet / getSamplerDescriptorSet / getInputDescriptorSet**
```cpp
const GrVkDescriptorSet* getUniformDescriptorSet();
const GrVkDescriptorSet* getSamplerDescriptorSet(const Handle& handle);
const GrVkDescriptorSet* getInputDescriptorSet();
```
获取描述符集，已增加引用计数。

**recycleDescriptorSet**
```cpp
void recycleDescriptorSet(
    const GrVkDescriptorSet* descSet,
    const GrVkDescriptorSetManager::Handle& handle);
```
回收描述符集供下次分配使用。

**getUniformDSLayout / getSamplerDSLayout / getInputDSLayout**
```cpp
VkDescriptorSetLayout getUniformDSLayout() const;
VkDescriptorSetLayout getSamplerDSLayout(const Handle& handle) const;
VkDescriptorSetLayout getInputDSLayout() const;
```
获取描述符集布局，用于创建管道布局。

**getSamplerDescriptorSetHandle / getZeroSamplerDescriptorSetHandle**
```cpp
void getSamplerDescriptorSetHandle(
    VkDescriptorType type,
    const GrVkUniformHandler& uniformHandler,
    GrVkDescriptorSetManager::Handle* handle);

void getZeroSamplerDescriptorSetHandle(Handle* handle);
```
获取采样器描述符集管理器句柄。零采样器句柄用于无采样器的管道布局。

### 命令池管理

**findOrCreateCommandPool**
```cpp
GrVkCommandPool* findOrCreateCommandPool();
```
查找或创建命令池，优先复用可用命令池。

**checkCommandBuffers**
```cpp
void checkCommandBuffers();
```
检查活动命令缓冲区是否完成，将完成的命令池回收到可用池。

**forceSyncAllCommandBuffers**
```cpp
void forceSyncAllCommandBuffers();
```
强制同步所有命令缓冲区，等待 GPU 完成。

**addFinishedProcToActiveCommandBuffers**
```cpp
void addFinishedProcToActiveCommandBuffers(
    sk_sp<skgpu::RefCntedCallback> finishedCallback);
```
向所有活动命令缓冲区添加完成回调。

### 管道缓存持久化

**storePipelineCacheData**
```cpp
void storePipelineCacheData(size_t maxSize);
```
将管道缓存数据存储到持久缓存，支持跨会话着色器编译加速。

### 描述符池管理

**findOrCreateCompatibleDescriptorPool**
```cpp
GrVkDescriptorPool* findOrCreateCompatibleDescriptorPool(
    VkDescriptorType type,
    uint32_t count);
```
查找或创建兼容的描述符池（当前实现总是创建新池）。

## 内部实现细节

### 管道缓存创建与加载

**pipelineCache** 方法延迟创建管道缓存：
```cpp
VkPipelineCache GrVkResourceProvider::pipelineCache() {
    if (fPipelineCache == VK_NULL_HANDLE) {
        // 1. 从持久缓存加载
        auto persistentCache = fGpu->getContext()->priv().getPersistentCache();
        sk_sp<SkData> cached = persistentCache->load(*keyData);

        // 2. 验证缓存头（vendorID、deviceID、UUID）
        if (cacheHeader[2] == devProps.vendorID &&
            cacheHeader[3] == devProps.deviceID &&
            !memcmp(&cacheHeader[4], supportedPipelineCacheUUID, VK_UUID_SIZE)) {
            createInfo.initialDataSize = cached->size();
            createInfo.pInitialData = cached->data();
        }

        // 3. 创建 Vulkan 管道缓存
        GR_VK_CALL_RESULT(fGpu, result, CreatePipelineCache(..., &fPipelineCache));
    }
    return fPipelineCache;
}
```

### 渲染通道查找与创建

**findCompatibleRenderPass** 实现两级查找：
```cpp
const GrVkRenderPass* GrVkResourceProvider::findCompatibleRenderPass(...) {
    // 1. 遍历已缓存的兼容渲染通道集
    for (int i = 0; i < fRenderPassArray.size(); ++i) {
        if (fRenderPassArray[i].isCompatible(*desc, attachmentFlags, ...)) {
            const GrVkRenderPass* renderPass =
                fRenderPassArray[i].getCompatibleRenderPass();
            renderPass->ref();
            *compatibleHandle = CompatibleRPHandle(i);
            return renderPass;
        }
    }

    // 2. 未找到，创建新的兼容渲染通道
    GrVkRenderPass* renderPass =
        GrVkRenderPass::CreateSimple(fGpu, desc, attachmentFlags, ...);
    fRenderPassArray.emplace_back(renderPass);
    *compatibleHandle = CompatibleRPHandle(fRenderPassArray.size() - 1);
    return renderPass;
}
```

### CompatibleRenderPassSet 实现

**getRenderPass** 方法查找特定 load/store 操作的渲染通道：
```cpp
GrVkRenderPass* CompatibleRenderPassSet::getRenderPass(
    GrVkGpu* gpu,
    const LoadStoreOps& colorOps,
    const LoadStoreOps& resolveOps,
    const LoadStoreOps& stencilOps) {

    // 优化：从上次返回的索引开始查找
    for (int i = 0; i < fRenderPasses.size(); ++i) {
        int idx = (i + fLastReturnedIndex) % fRenderPasses.size();
        if (fRenderPasses[idx]->equalLoadStoreOps(colorOps, resolveOps, stencilOps)) {
            fLastReturnedIndex = idx;
            return fRenderPasses[idx];
        }
    }

    // 未找到，创建新渲染通道
    GrVkRenderPass* renderPass =
        GrVkRenderPass::Create(gpu, *this->getCompatibleRenderPass(),
                              colorOps, resolveOps, stencilOps);
    fRenderPasses.push_back(renderPass);
    fLastReturnedIndex = fRenderPasses.size() - 1;
    return renderPass;
}
```

### 命令池回收机制

**checkCommandBuffers** 实现：
```cpp
void GrVkResourceProvider::checkCommandBuffers() {
    for (int i = fActiveCommandPools.size() - 1;
         !fActiveCommandPools.empty() && i >= 0; --i) {

        GrVkCommandPool* pool = fActiveCommandPools[i];
        if (!pool->isOpen()) {
            GrVkPrimaryCommandBuffer* buffer = pool->getPrimaryCommandBuffer();
            if (buffer->finished(fGpu)) {
                // 1. 从活动池移除
                fActiveCommandPools.removeShuffle(i);
                SkASSERT(pool->unique());

                // 2. 重置命令池
                pool->reset(fGpu);

                // 3. 检查 GPU 是否断开连接
                if (fGpu->disconnected()) {
                    pool->unref();
                    return;
                }

                // 4. 添加到可用池
                fAvailableCommandPools.push_back(pool);
            }
        }
    }
}
```

重要：客户端回调可能在 `pool->reset()` 期间触发上下文放弃，需谨慎处理。

### 采样器缓存

使用 `SkTDynamicHash` 实现采样器缓存：
```cpp
GrVkSampler* GrVkResourceProvider::findOrCreateCompatibleSampler(
    GrSamplerState params,
    const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo) {

    GrVkSampler* sampler = fSamplers.find(GrVkSampler::GenerateKey(params, ycbcrInfo));
    if (!sampler) {
        sampler = GrVkSampler::Create(fGpu, params, ycbcrInfo);
        fSamplers.add(sampler);
    }
    sampler->ref();
    return sampler;
}
```

### 管道缓存持久化

**storePipelineCacheData** 实现：
```cpp
void GrVkResourceProvider::storePipelineCacheData(size_t maxSize) {
    // 1. 获取缓存数据大小
    size_t dataSize = 0;
    GR_VK_CALL_RESULT(fGpu, result, GetPipelineCacheData(..., &dataSize, nullptr));

    // 2. 限制最大大小
    dataSize = std::min(dataSize, maxSize);

    // 3. 读取缓存数据
    std::unique_ptr<uint8_t[]> data(new uint8_t[dataSize]);
    GR_VK_CALL_RESULT(fGpu, result,
        GetPipelineCacheData(..., &dataSize, (void*)data.get()));

    // 4. 存储到持久缓存
    fGpu->getContext()->priv().getPersistentCache()->store(
        *keyData, *SkData::MakeWithoutCopy(data.get(), dataSize),
        SkString("VkPipelineCache"));
}
```

### 资源销毁顺序

**destroyResources** 严格按顺序销毁资源：
```cpp
void GrVkResourceProvider::destroyResources() {
    taskGroup->wait();  // 等待后台任务完成

    // 1. 释放 MSAA 加载管道
    fMSAALoadPipelines.clear();

    // 2. 释放渲染通道
    for (auto& rpSet : fRenderPassArray) rpSet.releaseResources();
    fRenderPassArray.clear();
    fExternalRenderPasses.clear();

    // 3. 释放采样器和 YCbCr 转换
    fSamplers.foreach([&](auto* elt) { elt->unref(); });
    fYcbcrConversions.foreach([&](auto* elt) { elt->unref(); });

    // 4. 释放管道状态缓存
    fPipelineStateCache->release();

    // 5. 销毁管道缓存
    GR_VK_CALL(..., DestroyPipelineCache(..., fPipelineCache, nullptr));

    // 6. 释放命令池
    for (GrVkCommandPool* pool : fActiveCommandPools) pool->unref();
    for (GrVkCommandPool* pool : fAvailableCommandPools) pool->unref();

    // 7. 最后释放描述符集管理器
    for (auto& dsm : fDescriptorSetManagers) dsm->release(fGpu);
}
```

顺序很重要：必须先释放引用描述符集的对象（管道、命令缓冲区），再释放描述符集管理器。

## 依赖关系

### 内部依赖
- `GrVkGpu`: GPU 接口
- `GrVkRenderPass`: 渲染通道
- `GrVkPipeline`: 图形管道
- `GrVkPipelineState`: 管道状态
- `GrVkSampler`: 采样器
- `GrVkSamplerYcbcrConversion`: YCbCr 转换
- `GrVkCommandPool`: 命令池
- `GrVkDescriptorPool`: 描述符池
- `GrVkDescriptorSet`: 描述符集
- `GrVkDescriptorSetManager`: 描述符集管理器

### 基类依赖
- `GrThreadSafePipelineBuilder`: 线程安全管道构建器基类

### 外部依赖
- `GrProgramInfo`: 程序信息
- `GrProgramDesc`: 程序描述符
- `GrRenderTarget`: 渲染目标
- `GrDirectContext`: 上下文（用于持久缓存和任务组）
- `skgpu::RefCntedCallback`: 引用计数回调

## 设计模式与设计决策

### 工厂模式

`GrVkResourceProvider` 作为资源工厂，集中管理所有 Vulkan 对象的创建：
- 统一的创建接口（`findOrCreate*` 模式）
- 透明的缓存机制
- 自动引用计数管理

### 缓存策略

**多级缓存**：
1. **渲染通道**：两级缓存（兼容集 + 具体 load/store ops）
2. **管道状态**：LRU 缓存
3. **采样器**：哈希表缓存
4. **命令池**：双列表缓存（活动/可用）

**延迟创建**：
- 管道缓存延迟到首次使用时创建
- MSAA 加载管道延迟创建
- 描述符集管理器按需创建

### 句柄抽象

使用 `CompatibleRPHandle` 和 `GrVkDescriptorSetManager::Handle` 抽象内部索引，避免暴露实现细节。

### 命令池双列表管理

- **fActiveCommandPools**: 正在使用或等待完成的命令池
- **fAvailableCommandPools**: 已完成可复用的命令池

减少命令池创建和销毁开销。

### 兼容性优先

渲染通道和管道查找优先考虑兼容性，而非完全匹配：
- 减少对象数量
- 提高缓存命中率
- 符合 Vulkan 兼容性规则

## 性能考量

### 管道缓存加速

持久化管道缓存显著减少着色器编译时间：
- 首次启动：加载缓存数据，避免重新编译
- 运行时：命中管道缓存，跳过编译
- 退出时：保存缓存数据供下次使用

### 渲染通道缓存优化

两级缓存策略：
- 第一级：兼容渲染通道集（附件配置）
- 第二级：具体渲染通道（load/store ops）

大多数渲染操作使用相同的附件配置，兼容集缓存命中率高。

### 命令池复用

维护可用命令池列表，避免频繁创建和销毁：
- 创建命令池开销较大（分配 VkDeviceMemory）
- 重置命令池成本低（重置内存池）
- 复用减少内存碎片

### 采样器哈希缓存

采样器状态有限（过滤、寻址模式、各向异性等），哈希表缓存效果好：
- O(1) 查找时间
- 高命中率（相同纹理采样参数重复使用）

### LRU 管道状态缓存

使用 LRU 策略淘汰不常用的管道状态：
- 保留热点管道状态
- 限制内存使用
- 平衡创建开销和内存占用

### CompatibleRenderPassSet 查找优化

从上次返回的索引开始查找：
```cpp
int idx = (i + fLastReturnedIndex) % fRenderPasses.size();
```

利用时间局部性，同一帧内倾向于使用相同的 load/store ops。

## 相关文件

### 核心实现文件
- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: Vulkan GPU 接口
- `src/gpu/ganesh/vk/GrVkRenderPass.h/cpp`: 渲染通道
- `src/gpu/ganesh/vk/GrVkPipeline.h/cpp`: 图形管道
- `src/gpu/ganesh/vk/GrVkPipelineState.h/cpp`: 管道状态
- `src/gpu/ganesh/vk/GrVkCommandPool.h/cpp`: 命令池
- `src/gpu/ganesh/vk/GrVkDescriptorSetManager.h/cpp`: 描述符集管理器
- `src/gpu/ganesh/vk/GrVkSampler.h/cpp`: 采样器
- `src/gpu/ganesh/vk/GrVkSamplerYcbcrConversion.h/cpp`: YCbCr 转换

### 基类文件
- `src/gpu/ganesh/GrThreadSafePipelineBuilder.h`: 线程安全管道构建器

### 工具类文件
- `src/core/SkLRUCache.h`: LRU 缓存
- `src/core/SkTDynamicHash.h`: 动态哈希表
- `src/core/SkChecksum.h`: 校验和计算
- `src/gpu/ganesh/GrProgramDesc.h`: 程序描述符
- `src/gpu/ganesh/GrResourceHandle.h`: 资源句柄

### 接口文件
- `include/gpu/ganesh/GrDirectContext.h`: Direct Context
- `include/private/gpu/vk/SkiaVulkan.h`: Vulkan 头文件
