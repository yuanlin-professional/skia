# GrVkDescriptorSetManager

> 源文件
> - `src/gpu/ganesh/vk/GrVkDescriptorSetManager.h`
> - `src/gpu/ganesh/vk/GrVkDescriptorSetManager.cpp`

## 概述

`GrVkDescriptorSetManager` 是 Skia Ganesh Vulkan 后端中管理描述符集分配和复用的核心类。它负责创建兼容的描述符集布局、从描述符池分配描述符集，并维护空闲描述符集列表以供复用。该类通过池化和回收机制显著减少描述符集的创建和销毁开销，是 Vulkan 资源管理的关键组件。

## 架构位置

在 Vulkan 描述符管理体系中的位置：

```
GrVkResourceProvider
    └── GrVkDescriptorSetManager (管理单类型描述符集)
        ├── DescriptorPoolManager (管理描述符池)
        │   └── GrVkDescriptorPool (封装 VkDescriptorPool)
        └── GrVkDescriptorSet (封装 VkDescriptorSet)
```

每个管理器负责一种特定配置（类型、可见性、不可变采样器）的描述符集。

## 主要类与结构体

### GrVkDescriptorSetManager 类

**核心成员**：
```cpp
DescriptorPoolManager fPoolManager;                   // 描述符池管理器
skia_private::TArray<const GrVkDescriptorSet*> fFreeSets;  // 空闲描述符集列表
skia_private::STArray<4, uint32_t> fBindingVisibilities;   // 绑定可见性
skia_private::STArray<4, const GrVkSampler*> fImmutableSamplers;  // 不可变采样器
```

**资源句柄**：
```cpp
GR_DEFINE_RESOURCE_HANDLE_CLASS(Handle)  // 描述符集管理器句柄
```

### DescriptorPoolManager 内部类

```cpp
struct DescriptorPoolManager {
    VkDescriptorSetLayout fDescLayout;     // 描述符集布局
    VkDescriptorType fDescType;            // 描述符类型
    uint32_t fDescCountPerSet;             // 每个描述符集的描述符数量
    uint32_t fMaxDescriptors;              // 当前池最大描述符数
    uint32_t fCurrentDescriptorCount;      // 当前已分配描述符数
    GrVkDescriptorPool* fPool;             // 当前描述符池

    static constexpr size_t kMaxDescriptors = 1024;      // 最大描述符数
    static constexpr size_t kStartNumDescriptors = 16;   // 起始描述符数
};
```

管理描述符池的分配和增长，采用指数增长策略。

## 公共 API 函数

### 静态工厂方法

**CreateUniformManager**
```cpp
static GrVkDescriptorSetManager* CreateUniformManager(GrVkGpu* gpu);
```
创建 uniform buffer 描述符集管理器，顶点和片段着色器可见。

**CreateSamplerManager**
```cpp
static GrVkDescriptorSetManager* CreateSamplerManager(
    GrVkGpu* gpu,
    VkDescriptorType type,
    const GrVkUniformHandler& uniformHandler);
```
创建采样器描述符集管理器，根据 `uniformHandler` 配置绑定和不可变采样器。

**CreateZeroSamplerManager**
```cpp
static GrVkDescriptorSetManager* CreateZeroSamplerManager(GrVkGpu* gpu);
```
创建零采样器管理器，用于管道布局占位（没有实际采样器但需要布局）。

**CreateInputManager**
```cpp
static GrVkDescriptorSetManager* CreateInputManager(GrVkGpu* gpu);
```
创建 input attachment 描述符集管理器，仅片段着色器可见。

### 描述符集管理

**getDescriptorSet**
```cpp
const GrVkDescriptorSet* getDescriptorSet(GrVkGpu* gpu, const Handle& handle);
```
获取描述符集，优先从空闲列表复用，否则从池中分配新描述符集。

**recycleDescriptorSet**
```cpp
void recycleDescriptorSet(const GrVkDescriptorSet* descSet);
```
回收描述符集到空闲列表，供下次分配使用。

### 布局与兼容性

**layout**
```cpp
VkDescriptorSetLayout layout() const;
```
返回描述符集布局，用于创建管道布局。

**isCompatible**
```cpp
bool isCompatible(VkDescriptorType type, const GrVkUniformHandler* uniHandler) const;
```
检查是否与给定的类型和 uniform handler 兼容（类型、绑定数量、可见性、不可变采样器）。

**isZeroSampler**
```cpp
bool isZeroSampler() const;
```
判断是否为零采样器管理器。

### 资源释放

**release**
```cpp
void release(GrVkGpu* gpu);
```
释放所有 GPU 资源：描述符池、空闲描述符集、不可变采样器。

## 内部实现细节

### 描述符集布局创建

**get_layout_and_desc_count** 函数根据类型创建布局：

**采样器类型**：
```cpp
for (uint32_t i = 0; i < numBindings; ++i) {
    dsSamplerBindings[i].binding = i;
    dsSamplerBindings[i].descriptorType = type;
    dsSamplerBindings[i].descriptorCount = 1;
    dsSamplerBindings[i].stageFlags = visibility_to_vk_stage_flags(visibility);
    if (immutableSamplers[i]) {
        // YCbCr 不可变采样器可能占用多个描述符
        descCountPerSet += gpu->vkCaps().ycbcrCombinedImageSamplerDescriptorCount();
        dsSamplerBindings[i].pImmutableSamplers = immutableSamplers[i]->samplerPtr();
    } else {
        descCountPerSet++;
        dsSamplerBindings[i].pImmutableSamplers = nullptr;
    }
}
```

**Uniform buffer 类型**：
```cpp
dsUniBinding.binding = GrVkUniformHandler::kUniformBinding;
dsUniBinding.descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
dsUniBinding.descriptorCount = 1;
dsUniBinding.stageFlags = visibility_to_vk_stage_flags(visibilities[0]);
```

**Input attachment 类型**：
```cpp
dsInputBinding.binding = 0;
dsInputBinding.descriptorType = VK_DESCRIPTOR_TYPE_INPUT_ATTACHMENT;
dsInputBinding.descriptorCount = 1;
dsInputBinding.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
```

### 描述符集分配

**getDescriptorSet** 实现：
```cpp
const GrVkDescriptorSet* getDescriptorSet(GrVkGpu* gpu, const Handle& handle) {
    // 1. 优先从空闲列表获取
    if (fFreeSets.size() > 0) {
        const GrVkDescriptorSet* ds = fFreeSets.back();
        fFreeSets.pop_back();
        return ds;
    }

    // 2. 从描述符池分配新描述符集
    VkDescriptorSet vkDS;
    if (!fPoolManager.getNewDescriptorSet(gpu, &vkDS)) {
        return nullptr;
    }

    // 3. 创建 GrVkDescriptorSet 包装器
    return new GrVkDescriptorSet(gpu, vkDS, fPoolManager.fPool, handle);
}
```

### 描述符池增长策略

**DescriptorPoolManager::getNewPool** 实现：
```cpp
bool getNewPool(GrVkGpu* gpu) {
    if (fPool) {
        fPool->unref();
        // 指数增长：newSize = oldSize + oldSize/2
        uint32_t newPoolSize = fMaxDescriptors + ((fMaxDescriptors + 1) >> 1);
        if (newPoolSize < kMaxDescriptors) {
            fMaxDescriptors = newPoolSize;
        } else {
            fMaxDescriptors = kMaxDescriptors;  // 上限 1024
        }
    }
    fPool = gpu->resourceProvider().findOrCreateCompatibleDescriptorPool(
        fDescType, fMaxDescriptors);
    return SkToBool(fPool);
}
```

增长序列：16 → 24 → 36 → 54 → 81 → ... → 1024

### 描述符集分配逻辑

**DescriptorPoolManager::getNewDescriptorSet** 实现：
```cpp
bool getNewDescriptorSet(GrVkGpu* gpu, VkDescriptorSet* ds) {
    fCurrentDescriptorCount += fDescCountPerSet;
    if (!fPool || fCurrentDescriptorCount > fMaxDescriptors) {
        // 池已满或不存在，创建新池
        if (!this->getNewPool(gpu)) {
            return false;
        }
        fCurrentDescriptorCount = fDescCountPerSet;
    }

    // 从池中分配
    VkDescriptorSetAllocateInfo dsAllocateInfo = {
        .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool = fPool->descPool(),
        .descriptorSetCount = 1,
        .pSetLayouts = &fDescLayout
    };
    VkResult result;
    GR_VK_CALL_RESULT(gpu, result, AllocateDescriptorSets(..., ds));
    return result == VK_SUCCESS;
}
```

### 兼容性检查

**isCompatible** 实现：
```cpp
bool isCompatible(VkDescriptorType type, const GrVkUniformHandler* uniHandler) const {
    // 1. 检查类型
    if (type != fPoolManager.fDescType) {
        return false;
    }

    // 2. 检查绑定数量
    if (fBindingVisibilities.size() != uniHandler->numSamplers()) {
        return false;
    }

    // 3. 检查每个绑定的可见性和不可变采样器
    for (int i = 0; i < uniHandler->numSamplers(); ++i) {
        if (uniHandler->samplerVisibility(i) != fBindingVisibilities[i] ||
            uniHandler->immutableSampler(i) != fImmutableSamplers[i]) {
            return false;
        }
    }
    return true;
}
```

### 资源释放

**release** 实现：
```cpp
void release(GrVkGpu* gpu) {
    // 1. 释放描述符池和布局
    fPoolManager.freeGPUResources(gpu);

    // 2. 释放空闲描述符集
    for (auto* ds : fFreeSets) {
        ds->unref();
    }
    fFreeSets.clear();

    // 3. 释放不可变采样器
    for (auto* sampler : fImmutableSamplers) {
        if (sampler) {
            sampler->unref();
        }
    }
    fImmutableSamplers.clear();
}
```

## 依赖关系

### 内部依赖
- `GrVkGpu`: GPU 接口
- `GrVkResourceProvider`: 资源提供器（创建描述符池）
- `GrVkDescriptorPool`: 描述符池封装
- `GrVkDescriptorSet`: 描述符集封装
- `GrVkSampler`: 采样器（不可变采样器）
- `GrVkUniformHandler`: Uniform handler（提供绑定信息）
- `GrVkCaps`: Vulkan 能力查询（YCbCr 描述符数量）

### 外部依赖
- Vulkan API: `VkDescriptorSetLayout`, `VkDescriptorSet`, `VkDescriptorPool`

## 设计模式与设计决策

### 对象池模式

维护空闲描述符集列表，分配时优先复用，回收时放回列表，避免频繁创建和销毁。

### 描述符池增长策略

采用指数增长（+50%），在内存使用和分配次数之间平衡：
- 初始小池（16）适用于简单场景
- 逐步增长适应复杂场景
- 上限（1024）防止单个池过大

### 布局共享

同一配置的所有描述符集共享一个 `VkDescriptorSetLayout`，减少布局对象数量。

### 不可变采样器支持

通过构造时指定不可变采样器，支持 YCbCr 格式纹理（需要固定的采样器配置）。

### LSAN 抑制

使用 `__lsan::ScopedDisabler` 抑制 Leak Sanitizer 对 Vulkan 驱动内部分配的误报。

## 性能考量

### 描述符集复用

通过空闲列表复用描述符集，避免 `vkAllocateDescriptorSets` 开销：
- 分配快速（从列表取）
- 无需驱动层分配
- 减少描述符池压力

### 池大小渐进增长

起始池小，逐步增长：
- 简单应用不浪费内存
- 复杂应用自动扩容
- 避免频繁创建新池

### YCbCr 描述符计数

YCbCr 不可变采样器可能占用多个描述符位（某些驱动实现），通过 `ycbcrCombinedImageSamplerDescriptorCount()` 准确计算。

### 批量描述符分配

描述符池按批次分配，而非单个描述符集分配单个池，提高分配效率。

## 相关文件

### 核心实现文件
- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: Vulkan GPU 接口
- `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp`: 资源提供器
- `src/gpu/ganesh/vk/GrVkDescriptorPool.h/cpp`: 描述符池
- `src/gpu/ganesh/vk/GrVkDescriptorSet.h/cpp`: 描述符集
- `src/gpu/ganesh/vk/GrVkSampler.h/cpp`: 采样器
- `src/gpu/ganesh/vk/GrVkUniformHandler.h/cpp`: Uniform handler
- `src/gpu/ganesh/vk/GrVkCaps.h/cpp`: Vulkan 能力查询

### 工具类
- `src/gpu/ganesh/GrResourceHandle.h`: 资源句柄定义
