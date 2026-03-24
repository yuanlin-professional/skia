# GrVkTexture

> 源文件
> - `src/gpu/ganesh/vk/GrVkTexture.h`
> - `src/gpu/ganesh/vk/GrVkTexture.cpp`

## 概述

`GrVkTexture` 是 Skia 的 Ganesh 渲染引擎中用于表示 Vulkan 纹理资源的核心类。它继承自 `GrTexture`，负责封装和管理底层的 Vulkan 图像对象（`VkImage`），并提供纹理采样、描述符集缓存等功能。该类是 Vulkan 后端纹理系统的基础，支持创建新纹理、包装外部纹理以及管理 Mipmap 层级。

## 架构位置

在 Skia 的 GPU 架构中，`GrVkTexture` 位于以下层次：

```
GrSurface (基类)
    └── GrTexture (纹理基类)
        └── GrVkTexture (Vulkan 纹理实现)
            └── GrVkTextureRenderTarget (纹理+渲染目标组合类)
```

该类位于 `src/gpu/ganesh/vk/` 目录下，属于 Ganesh 渲染引擎的 Vulkan 后端实现。它与 `GrVkImage`（封装 `VkImage`）、`GrVkImageView`（图像视图）、`GrVkDescriptorSet`（描述符集）等类紧密协作，共同构成 Vulkan 纹理管理体系。

## 主要类与结构体

### GrVkTexture 类

核心成员变量：
- `sk_sp<GrVkImage> fTexture`: 持有底层的 Vulkan 图像对象
- `SkLRUCache<..., DescriptorCacheEntry> fDescSetCache`: LRU 缓存，用于缓存纹理/采样器描述符集

关键常量：
- `kMaxCachedDescSets = 8`: 最多缓存 8 个描述符集

### DescriptorCacheEntry 结构体

```cpp
struct DescriptorCacheEntry {
    const GrVkDescriptorSet* fDescriptorSet;
    GrVkGpu* fGpu;
};
```

用于缓存描述符集，析构时自动回收描述符资源。

### SamplerHash 结构体

```cpp
struct SamplerHash {
    uint32_t operator()(GrSamplerState state) const {
        return state.asKey(/*anisoIsOrthogonal=*/true);
    }
};
```

提供采样器状态的哈希函数，用于描述符集缓存的键值计算。

## 公共 API 函数

### 静态工厂方法

**MakeNewTexture**
```cpp
static sk_sp<GrVkTexture> MakeNewTexture(
    GrVkGpu* gpu,
    skgpu::Budgeted budgeted,
    SkISize dimensions,
    VkFormat format,
    uint32_t mipLevels,
    GrProtected isProtected,
    GrMipmapStatus mipmapStatus,
    std::string_view label);
```
创建新的 Vulkan 纹理。首先通过 `GrVkImage::MakeTexture` 创建底层图像，然后构造 `GrVkTexture` 对象。

**MakeWrappedTexture**
```cpp
static sk_sp<GrVkTexture> MakeWrappedTexture(
    GrVkGpu* gpu,
    SkISize dimensions,
    GrWrapOwnership wrapOwnership,
    GrWrapCacheable cacheable,
    GrIOType ioType,
    const GrVkImageInfo& info,
    sk_sp<skgpu::MutableTextureState> mutableState);
```
包装外部 Vulkan 图像。支持借用（borrow）或采用（adopt）语义，处理外部格式（如 YCbCr 转换）和 DRM 格式修饰符。

### 纹理访问方法

**getBackendTexture**
```cpp
GrBackendTexture getBackendTexture() const override;
```
返回包含 Vulkan 图像信息的后端纹理对象，用于跨层接口通信。

**textureImage**
```cpp
GrVkImage* textureImage() const { return fTexture.get(); }
```
获取底层的 `GrVkImage` 对象指针。

**textureView**
```cpp
const GrVkImageView* textureView();
```
获取纹理的图像视图，用于着色器采样。

**backendFormat**
```cpp
GrBackendFormat backendFormat() const override {
    return fTexture->backendFormat();
}
```
返回纹理的后端格式信息。

### 描述符集缓存管理

**cachedSingleDescSet**
```cpp
const GrVkDescriptorSet* cachedSingleDescSet(GrSamplerState state);
```
查找缓存中匹配给定采样器状态的描述符集。返回的指针不增加引用计数，调用者需要自行管理。

**addDescriptorSetToCache**
```cpp
void addDescriptorSetToCache(const GrVkDescriptorSet* descSet,
                              GrSamplerState state);
```
将描述符集添加到缓存中。会增加描述符集的引用计数。

### 生命周期管理

**textureParamsModified**
```cpp
void textureParamsModified() override {}
```
空实现，因为 Vulkan 纹理参数通过描述符集管理，无需额外处理。

## 内部实现细节

### 构造函数重载

类提供三个私有构造函数，分别用于不同场景：

1. **预算分配的新纹理**：接受 `skgpu::Budgeted` 参数，调用 `registerWithCache(budgeted)` 注册到缓存系统。

2. **包装的外部纹理**：接受 `GrWrapCacheable` 和 `GrIOType` 参数，根据 IO 类型设置只读属性，调用 `registerWithCacheWrapped(cacheable)` 注册。

3. **纹理渲染目标组合**：由 `GrVkTextureRenderTarget` 子类调用，不支持 YCbCr 转换（因为渲染目标不支持）。

### 初始化逻辑

所有构造函数都执行以下验证：
```cpp
SkASSERT((GrMipmapStatus::kNotAllocated == mipmapStatus) ==
         (1 == fTexture->mipLevels()));
SkASSERT(SkToBool(fTexture->vkUsageFlags() & VK_IMAGE_USAGE_SAMPLED_BIT));
```

确保 Mipmap 状态与实际层级数匹配，且图像支持采样使用标志。

对于压缩格式纹理，调用 `setReadOnly()` 设置为只读：
```cpp
if (skgpu::VkFormatIsCompressed(fTexture->imageFormat())) {
    this->setReadOnly();
}
```

### 外部格式处理

在包装纹理时，判断是否为外部格式：
```cpp
bool isExternal = info.fYcbcrConversionInfo.isValid() &&
                  info.fYcbcrConversionInfo.hasExternalFormat();
isExternal |= (info.fImageTiling == VK_IMAGE_TILING_DRM_FORMAT_MODIFIER_EXT);
```

外部格式包括 YCbCr 转换外部格式和 DRM 格式修饰符。

### 资源释放机制

**onRelease** 正常释放资源：
```cpp
void GrVkTexture::onRelease() {
    fTexture.reset();
    fDescSetCache.reset();
    GrTexture::onRelease();
}
```

**onAbandon** 放弃资源（无需清理 GPU 资源）：
```cpp
void GrVkTexture::onAbandon() {
    fTexture.reset();
    fDescSetCache.reset();
    GrTexture::onAbandon();
}
```

两者都重置 `fTexture` 和 `fDescSetCache`，区别在于 `onRelease` 会实际销毁 Vulkan 对象。

### 描述符集缓存机制

使用 LRU 缓存策略，最多缓存 8 个描述符集：
```cpp
SkLRUCache<const GrSamplerState,
           std::unique_ptr<DescriptorCacheEntry>,
           SamplerHash> fDescSetCache;
```

缓存键为 `GrSamplerState`，值为 `DescriptorCacheEntry` 智能指针。`DescriptorCacheEntry` 析构时自动调用 `recycle()` 回收描述符集。

添加缓存时增加引用计数：
```cpp
void GrVkTexture::addDescriptorSetToCache(...) {
    SkASSERT(!fDescSetCache.find(state));
    descSet->ref();
    fDescSetCache.insert(state,
        std::make_unique<DescriptorCacheEntry>(descSet, this->getVkGpu()));
}
```

查找缓存时不增加引用计数，调用者需要自行 `ref()`：
```cpp
const GrVkDescriptorSet* GrVkTexture::cachedSingleDescSet(GrSamplerState state) {
    if (std::unique_ptr<DescriptorCacheEntry>* e = fDescSetCache.find(state)) {
        return (*e)->fDescriptorSet;
    }
    return nullptr;
}
```

### Release Proc 转发

纹理的 release proc 转发给底层 `GrVkImage`：
```cpp
void onSetRelease(sk_sp<RefCntedReleaseProc> releaseHelper) override {
    fTexture->setResourceRelease(std::move(releaseHelper));
}
```

这确保在 GPU 完成所有工作后才调用释放回调。

## 依赖关系

### 内部依赖

- `GrVkImage`: 封装底层 `VkImage` 和内存分配
- `GrVkImageView`: 提供纹理的图像视图
- `GrVkDescriptorSet`: 管理描述符集对象
- `GrVkGpu`: GPU 接口，提供 Vulkan 命令执行能力
- `GrSamplerState`: 采样器状态封装

### 外部依赖

- `GrTexture`: 纹理基类，提供通用纹理接口
- `GrSurface`: 表面基类，提供尺寸、格式等基础属性
- `GrBackendTexture`: 跨后端纹理表示
- `skgpu::MutableTextureState`: 可变纹理状态管理

### 头文件依赖

核心 Skia 头文件：
- `include/core/SkRefCnt.h`
- `include/gpu/ganesh/GrBackendSurface.h`
- `include/gpu/ganesh/GrTypes.h`
- `include/private/gpu/vk/SkiaVulkan.h`

实用工具：
- `src/core/SkLRUCache.h`: LRU 缓存实现
- `src/gpu/ganesh/GrSamplerState.h`: 采样器状态

## 设计模式与设计决策

### 虚继承模式

`GrVkTexture` 通过虚继承 `GrSurface`，支持多重继承（如 `GrVkTextureRenderTarget` 同时继承 `GrVkTexture` 和 `GrVkRenderTarget`）：
```cpp
// 构造函数必须显式调用 GrSurface 的构造函数
GrVkTexture::GrVkTexture(...)
    : GrSurface(gpu, dimensions, ..., label)
    , GrTexture(gpu, dimensions, ..., label)
    , ...
```

### 工厂方法模式

提供两个静态工厂方法 `MakeNewTexture` 和 `MakeWrappedTexture`，将复杂的对象创建逻辑封装起来，调用者无需了解底层 Vulkan 细节。

### LRU 缓存策略

使用 `SkLRUCache` 缓存描述符集，避免频繁创建和销毁 Vulkan 对象。LRU 策略确保最近使用的描述符集保留在缓存中，提高渲染性能。

### 智能指针资源管理

使用 `sk_sp<GrVkImage>` 管理底层图像，使用 `std::unique_ptr<DescriptorCacheEntry>` 管理缓存条目，确保资源自动释放，避免内存泄漏。

### 只读纹理优化

对于压缩格式纹理和只读 IO 类型纹理，调用 `setReadOnly()` 标记为只读，避免不必要的同步和状态转换。

### Release Proc 转发机制

将 release proc 转发给底层 `GrVkImage`，确保回调在 GPU 完成所有工作后执行，符合 Vulkan 异步执行模型。

## 性能考量

### 描述符集缓存

频繁创建和销毁 Vulkan 描述符集开销较大。通过 LRU 缓存最多 8 个描述符集，减少描述符池分配次数，提高渲染帧率。

### 采样器状态哈希优化

使用 `SamplerHash` 将 `GrSamplerState` 转换为整数键，哈希计算考虑各向异性过滤参数（`anisoIsOrthogonal=true`），确保不同采样器状态正确区分。

### Mipmap 层级管理

在构造时验证 Mipmap 状态与实际层级数匹配：
```cpp
SkASSERT((GrMipmapStatus::kNotAllocated == mipmapStatus) ==
         (1 == fTexture->mipLevels()));
```

避免运行时 Mipmap 状态不一致导致的性能问题。

### 压缩格式特殊处理

对压缩格式纹理设置只读标志：
```cpp
if (skgpu::VkFormatIsCompressed(fTexture->imageFormat())) {
    this->setReadOnly();
}
```

压缩格式纹理无法直接写入，标记为只读避免不必要的布局转换和同步。

### 引用计数优化

`cachedSingleDescSet` 返回的指针不增加引用计数，避免短期访问导致的原子操作开销。调用者需要长期持有时才调用 `ref()`。

### 外部格式延迟判断

在包装纹理时才判断是否为外部格式，避免在普通纹理创建路径上执行不必要的检查。

## 相关文件

### 核心实现文件
- `src/gpu/ganesh/vk/GrVkImage.h/cpp`: 封装 Vulkan 图像对象
- `src/gpu/ganesh/vk/GrVkImageView.h/cpp`: 图像视图管理
- `src/gpu/ganesh/vk/GrVkDescriptorSet.h/cpp`: 描述符集管理
- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: Vulkan GPU 接口实现
- `src/gpu/ganesh/vk/GrVkTextureRenderTarget.h/cpp`: 纹理+渲染目标组合类

### 基类文件
- `src/gpu/ganesh/GrTexture.h/cpp`: 纹理基类
- `src/gpu/ganesh/GrSurface.h/cpp`: 表面基类

### 工具类文件
- `src/core/SkLRUCache.h`: LRU 缓存实现
- `src/gpu/ganesh/GrSamplerState.h`: 采样器状态定义
- `src/gpu/ganesh/vk/GrVkUtil.h/cpp`: Vulkan 工具函数
- `src/gpu/vk/VulkanUtilsPriv.h`: Vulkan 私有工具

### 接口文件
- `include/gpu/ganesh/GrBackendSurface.h`: 后端表面接口
- `include/gpu/ganesh/vk/GrVkTypes.h`: Vulkan 类型定义
- `include/gpu/MutableTextureState.h`: 可变纹理状态接口
