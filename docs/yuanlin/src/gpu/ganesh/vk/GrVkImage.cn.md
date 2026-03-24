# GrVkImage

> 源文件
> - src/gpu/ganesh/vk/GrVkImage.h
> - src/gpu/ganesh/vk/GrVkImage.cpp

## 概述

`GrVkImage` 是 Skia 图形库中对 Vulkan `VkImage` 对象的完整封装类,继承自 `GrAttachment` 基类。它不仅管理 Vulkan 图像资源的生命周期、内存分配和布局转换,还负责处理图像视图、描述符集、队列族转换等复杂的 Vulkan 特性。该类支持多种图像类型,包括纹理、渲染目标、模板附件、MSAA 附件以及包装外部图像资源。

`GrVkImage` 是 Skia Vulkan 后端的核心资源类,封装了图像创建、布局管理、内存屏障、输入附件、YCbCr 转换等功能。它通过智能的布局跟踪和队列族管理,确保图像在不同渲染阶段之间的正确同步和转换。

## 架构位置

```
Skia 资源架构
├── GrSurface (表面基类)
│   └── GrAttachment (附件基类)
│       └── GrVkImage ← 当前类
│           ├── Resource (内部资源类)
│           │   └── BorrowedResource (借用资源)
│           ├── GrVkImageView (图像视图)
│           ├── VkImage (Vulkan 图像句柄)
│           ├── VulkanAlloc (内存分配)
│           └── MutableTextureState (可变状态)
```

`GrVkImage` 是以下类的基础:
- `GrVkTexture`: 纹理对象
- `GrVkRenderTarget`: 渲染目标(通过 GrVkTexture)
- 模板附件和 MSAA 附件直接使用 `GrVkImage`

## 主要类与结构体

### 继承关系
```
GrSurface (基类)
  ↑
GrAttachment (附件基类)
  ↑
GrVkImage (Vulkan 图像)
```

### ImageDesc 结构体

```cpp
struct ImageDesc {
    VkImageType         fImageType;      // 图像类型(2D/3D)
    VkFormat            fFormat;         // 图像格式
    uint32_t            fWidth;          // 宽度
    uint32_t            fHeight;         // 高度
    uint32_t            fLevels;         // mipmap 级别数
    uint32_t            fSamples;        // 采样数
    VkImageTiling       fImageTiling;    // tiling 模式
    VkImageUsageFlags   fUsageFlags;     // 使用标志
    VkFlags             fMemProps;       // 内存属性
    GrProtected         fIsProtected;    // 是否受保护
};
```

### Resource 内部类

负责管理 VkImage 和内存的实际释放:

```cpp
class Resource : public GrTextureResource {
public:
    Resource(const GrVkGpu* gpu, VkImage image,
             const skgpu::VulkanAlloc& alloc, VkImageTiling tiling);
private:
    void freeGPUData() const override;  // 释放 VkImage 和内存
    const GrVkGpu* fGpu;
    VkImage fImage;
    skgpu::VulkanAlloc fAlloc;
};
```

### BorrowedResource 借用资源类

用于包装外部创建的图像,析构时不释放 VkImage:

```cpp
class BorrowedResource : public Resource {
private:
    void freeGPUData() const override;  // 仅调用 release callback
};
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrVkImageInfo` | Vulkan 图像信息(句柄、格式、布局等) |
| `fInitialQueueFamily` | `uint32_t` | 初始队列族索引 |
| `fMutableState` | `sk_sp<MutableTextureState>` | 可变纹理状态(布局、队列族) |
| `fFramebufferView` | `sk_sp<const GrVkImageView>` | 帧缓冲区视图 |
| `fTextureView` | `sk_sp<const GrVkImageView>` | 纹理采样视图 |
| `fResource` | `Resource*` | 内部资源对象 |
| `fIsBorrowed` | `bool` | 是否为借用的图像 |
| `fCachedBlendingInputDescSet` | `gr_rp<const GrVkDescriptorSet>` | 混合输入附件描述符集缓存 |
| `fCachedMSAALoadInputDescSet` | `gr_rp<const GrVkDescriptorSet>` | MSAA 加载输入附件描述符集缓存 |

## 公共 API 函数

### 静态工厂方法

| 函数签名 | 功能说明 |
|---------|---------|
| `static sk_sp<GrVkImage> MakeStencil(GrVkGpu*, SkISize, int sampleCnt, VkFormat)` | 创建模板附件 |
| `static sk_sp<GrVkImage> MakeMSAA(GrVkGpu*, SkISize, int numSamples, VkFormat, GrProtected, GrMemoryless)` | 创建 MSAA 附件 |
| `static sk_sp<GrVkImage> MakeTexture(GrVkGpu*, SkISize, VkFormat, uint32_t mipLevels, GrRenderable, int numSamples, skgpu::Budgeted, GrProtected)` | 创建纹理 |
| `static sk_sp<GrVkImage> MakeWrapped(GrVkGpu*, SkISize, const GrVkImageInfo&, ...)` | 包装外部图像 |

### 图像信息访问

| 函数签名 | 功能说明 |
|---------|---------|
| `VkImage image() const` | 获取 VkImage 句柄 |
| `VkFormat imageFormat() const` | 获取图像格式 |
| `uint32_t mipLevels() const` | 获取 mipmap 级别数 |
| `const GrVkImageInfo& vkImageInfo() const` | 获取完整图像信息 |
| `GrBackendFormat backendFormat() const override` | 获取后端格式 |
| `bool isLinearTiled() const` | 是否为线性 tiling |
| `bool isBorrowed() const` | 是否为借用的图像 |

### 布局与队列族管理

| 函数签名 | 功能说明 |
|---------|---------|
| `VkImageLayout currentLayout() const` | 获取当前图像布局 |
| `void setImageLayout(const GrVkGpu*, VkImageLayout, VkAccessFlags, VkPipelineStageFlags, bool byRegion)` | 设置图像布局并添加内存屏障 |
| `void updateImageLayout(VkImageLayout)` | 仅更新布局跟踪(不添加屏障) |
| `uint32_t currentQueueFamilyIndex() const` | 获取当前队列族索引 |
| `void setQueueFamilyIndex(uint32_t)` | 设置队列族索引 |
| `void prepareForPresent(GrVkGpu*)` | 准备图像用于呈现 |
| `void prepareForExternal(GrVkGpu*)` | 准备图像用于外部使用 |

### 视图与描述符集

| 函数签名 | 功能说明 |
|---------|---------|
| `const GrVkImageView* framebufferView() const` | 获取帧缓冲区视图 |
| `const GrVkImageView* textureView() const` | 获取纹理采样视图 |
| `gr_rp<const GrVkDescriptorSet> inputDescSetForBlending(GrVkGpu*)` | 获取混合用输入附件描述符集 |
| `gr_rp<const GrVkDescriptorSet> inputDescSetForMSAALoad(GrVkGpu*)` | 获取 MSAA 加载用输入附件描述符集 |

### 静态工具函数

| 函数签名 | 功能说明 |
|---------|---------|
| `static bool InitImageInfo(GrVkGpu*, const ImageDesc&, GrVkImageInfo*)` | 初始化图像信息(创建 VkImage 和分配内存) |
| `static void DestroyImageInfo(const GrVkGpu*, GrVkImageInfo*)` | 销毁图像和释放内存 |
| `static VkPipelineStageFlags LayoutToPipelineSrcStageFlags(VkImageLayout)` | 布局到管线阶段标志映射 |
| `static VkAccessFlags LayoutToSrcAccessMask(VkImageLayout)` | 布局到访问掩码映射 |

## 内部实现细节

### 图像创建流程

```cpp
sk_sp<GrVkImage> GrVkImage::Make(
    GrVkGpu* gpu,
    SkISize dimensions,
    UsageFlags attachmentUsages,
    int sampleCnt,
    VkFormat format,
    uint32_t mipLevels,
    VkImageUsageFlags vkUsageFlags,
    GrProtected isProtected,
    GrMemoryless memoryless,
    skgpu::Budgeted budgeted) {

    // 1. 构建图像描述
    ImageDesc imageDesc;
    imageDesc.fImageType = VK_IMAGE_TYPE_2D;
    imageDesc.fFormat = format;
    imageDesc.fWidth = dimensions.width();
    imageDesc.fHeight = dimensions.height();
    imageDesc.fLevels = mipLevels;
    imageDesc.fSamples = sampleCnt;
    imageDesc.fImageTiling = VK_IMAGE_TILING_OPTIMAL;
    imageDesc.fUsageFlags = vkUsageFlags;
    imageDesc.fIsProtected = isProtected;

    // 2. 创建 VkImage 并分配内存
    GrVkImageInfo info;
    if (!InitImageInfo(gpu, imageDesc, &info)) {
        return nullptr;
    }

    // 3. 创建图像视图
    sk_sp<const GrVkImageView> framebufferView;
    sk_sp<const GrVkImageView> textureView;
    if (!make_views(gpu, info, attachmentUsages,
                    &framebufferView, &textureView)) {
        DestroyImageInfo(gpu, &info);
        return nullptr;
    }

    // 4. 创建可变状态对象
    auto mutableState = sk_make_sp<skgpu::MutableTextureState>(
        skgpu::MutableTextureStates::MakeVulkan(
            info.fImageLayout, info.fCurrentQueueFamily));

    // 5. 构造 GrVkImage 对象
    return sk_sp<GrVkImage>(new GrVkImage(
        gpu, dimensions, attachmentUsages, info,
        std::move(mutableState),
        std::move(framebufferView),
        std::move(textureView),
        budgeted, "MakeVkImage"));
}
```

### InitImageInfo - VkImage 创建

```cpp
bool GrVkImage::InitImageInfo(
    GrVkGpu* gpu,
    const ImageDesc& imageDesc,
    GrVkImageInfo* info) {

    // 1. 准备创建信息
    VkImageCreateFlags createflags = 0;
    if (imageDesc.fIsProtected == GrProtected::kYes) {
        createflags |= VK_IMAGE_CREATE_PROTECTED_BIT;
    }

    VkSampleCountFlagBits vkSamples;
    SampleCountToVkSampleCount(imageDesc.fSamples, &vkSamples);

    VkImageLayout initialLayout = (imageDesc.fImageTiling == VK_IMAGE_TILING_LINEAR)
        ? VK_IMAGE_LAYOUT_PREINITIALIZED
        : VK_IMAGE_LAYOUT_UNDEFINED;

    // 2. 创建 VkImage
    const VkImageCreateInfo imageCreateInfo = {
        .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .pNext = nullptr,
        .flags = createflags,
        .imageType = imageDesc.fImageType,
        .format = imageDesc.fFormat,
        .extent = {imageDesc.fWidth, imageDesc.fHeight, 1},
        .mipLevels = imageDesc.fLevels,
        .arrayLayers = 1,
        .samples = vkSamples,
        .tiling = imageDesc.fImageTiling,
        .usage = imageDesc.fUsageFlags,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE,
        .queueFamilyIndexCount = 0,
        .pQueueFamilyIndices = nullptr,
        .initialLayout = initialLayout
    };

    VkImage image;
    VkResult result;
    GR_VK_CALL_RESULT(gpu, result,
        CreateImage(gpu->device(), &imageCreateInfo, nullptr, &image));
    if (result != VK_SUCCESS) {
        return false;
    }

    // 3. 分配内存
    bool forceDedicatedMemory = gpu->vkCaps().shouldAlwaysUseDedicatedImageMemory();
    bool useLazyAllocation = (imageDesc.fUsageFlags & VK_IMAGE_USAGE_TRANSIENT_ATTACHMENT_BIT);

    skgpu::VulkanAlloc alloc;
    if (!skgpu::VulkanMemory::AllocImageMemory(
            gpu->memoryAllocator(), image,
            isProtected, forceDedicatedMemory, useLazyAllocation,
            checkResult, &alloc)) {
        VK_CALL(gpu, DestroyImage(gpu->device(), image, nullptr));
        return false;
    }

    // 4. 绑定内存
    GR_VK_CALL_RESULT(gpu, result,
        BindImageMemory(gpu->device(), image, alloc.fMemory, alloc.fOffset));
    if (result) {
        skgpu::VulkanMemory::FreeImageMemory(gpu->memoryAllocator(), alloc);
        VK_CALL(gpu, DestroyImage(gpu->device(), image, nullptr));
        return false;
    }

    // 5. 填充 GrVkImageInfo
    info->fImage = image;
    info->fAlloc = alloc;
    info->fImageTiling = imageDesc.fImageTiling;
    info->fImageLayout = initialLayout;
    info->fFormat = imageDesc.fFormat;
    info->fImageUsageFlags = imageDesc.fUsageFlags;
    info->fSampleCount = imageDesc.fSamples;
    info->fLevelCount = imageDesc.fLevels;
    info->fCurrentQueueFamily = VK_QUEUE_FAMILY_IGNORED;
    info->fProtected = (createflags & VK_IMAGE_CREATE_PROTECTED_BIT)
        ? GrProtected::kYes : GrProtected::kNo;
    info->fSharingMode = VK_SHARING_MODE_EXCLUSIVE;

    return true;
}
```

### 布局转换与内存屏障

```cpp
void GrVkImage::setImageLayoutAndQueueIndex(
    const GrVkGpu* gpu,
    VkImageLayout newLayout,
    VkAccessFlags dstAccessMask,
    VkPipelineStageFlags dstStageMask,
    bool byRegion,
    uint32_t newQueueFamilyIndex) {

    VkImageLayout currentLayout = this->currentLayout();
    uint32_t currentQueueIndex = this->currentQueueFamilyIndex();

    // 1. 处理队列族索引(独占共享模式)
    if (fInfo.fSharingMode == VK_SHARING_MODE_EXCLUSIVE) {
        if (newQueueFamilyIndex == VK_QUEUE_FAMILY_IGNORED) {
            newQueueFamilyIndex = gpu->queueIndex();
        }
        if (currentQueueIndex == VK_QUEUE_FAMILY_IGNORED) {
            currentQueueIndex = gpu->queueIndex();
        }
    }

    // 2. 优化:相同布局且为只读布局时,跳过屏障
    if (newLayout == currentLayout &&
        currentQueueIndex == newQueueFamilyIndex &&
        (currentLayout == VK_IMAGE_LAYOUT_DEPTH_STENCIL_READ_ONLY_OPTIMAL ||
         currentLayout == VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL ||
         currentLayout == VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL)) {
        return;
    }

    // 3. 计算源访问掩码和管线阶段
    VkAccessFlags srcAccessMask = LayoutToSrcAccessMask(currentLayout);
    VkPipelineStageFlags srcStageMask = LayoutToPipelineSrcStageFlags(currentLayout);

    // 4. 确定图像方面(颜色/深度/模板)
    VkImageAspectFlags aspectFlags = vk_format_to_aspect_flags(fInfo.fFormat);

    // 5. 创建图像内存屏障
    VkImageMemoryBarrier imageMemoryBarrier = {
        .sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
        .pNext = nullptr,
        .srcAccessMask = srcAccessMask,
        .dstAccessMask = dstAccessMask,
        .oldLayout = currentLayout,
        .newLayout = newLayout,
        .srcQueueFamilyIndex = currentQueueIndex,
        .dstQueueFamilyIndex = newQueueFamilyIndex,
        .image = fInfo.fImage,
        .subresourceRange = {
            .aspectMask = aspectFlags,
            .baseMipLevel = 0,
            .levelCount = fInfo.fLevelCount,
            .baseArrayLayer = 0,
            .layerCount = 1
        }
    };

    // 6. 添加屏障到命令缓冲区
    gpu->addImageMemoryBarrier(
        this->resource(), srcStageMask, dstStageMask,
        byRegion, &imageMemoryBarrier);

    // 7. 更新状态跟踪
    this->updateImageLayout(newLayout);
    this->setQueueFamilyIndex(newQueueFamilyIndex);
}
```

### 布局到管线阶段映射

```cpp
VkPipelineStageFlags GrVkImage::LayoutToPipelineSrcStageFlags(VkImageLayout layout) {
    switch (layout) {
        case VK_IMAGE_LAYOUT_GENERAL:
            return VK_PIPELINE_STAGE_ALL_COMMANDS_BIT;
        case VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL:
        case VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL:
            return VK_PIPELINE_STAGE_TRANSFER_BIT;
        case VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL:
            return VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        case VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL:
        case VK_IMAGE_LAYOUT_DEPTH_STENCIL_READ_ONLY_OPTIMAL:
            return VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT;
        case VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL:
            return VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT;
        case VK_IMAGE_LAYOUT_PREINITIALIZED:
            return VK_PIPELINE_STAGE_HOST_BIT;
        case VK_IMAGE_LAYOUT_PRESENT_SRC_KHR:
            return VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        case VK_IMAGE_LAYOUT_UNDEFINED:
        default:
            return VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT;
    }
}
```

### 输入附件描述符集

```cpp
gr_rp<const GrVkDescriptorSet> GrVkImage::inputDescSetForBlending(GrVkGpu* gpu) {
    // 1. 检查是否支持输入附件
    if (!this->supportsInputAttachmentUsage()) {
        return nullptr;
    }

    // 2. 返回缓存的描述符集
    if (fCachedBlendingInputDescSet) {
        return fCachedBlendingInputDescSet;
    }

    // 3. 创建新的描述符集
    fCachedBlendingInputDescSet.reset(
        gpu->resourceProvider().getInputDescriptorSet());
    if (!fCachedBlendingInputDescSet) {
        return nullptr;
    }

    // 4. 写入描述符集
    write_input_desc_set(
        gpu,
        this->framebufferView()->imageView(),
        VK_IMAGE_LAYOUT_GENERAL,  // 混合使用 GENERAL 布局
        *fCachedBlendingInputDescSet->descriptorSet());

    return fCachedBlendingInputDescSet;
}

// MSAA 加载版本(使用 SHADER_READ_ONLY_OPTIMAL 布局)
gr_rp<const GrVkDescriptorSet> GrVkImage::inputDescSetForMSAALoad(GrVkGpu* gpu) {
    if (!this->supportsInputAttachmentUsage()) {
        return nullptr;
    }
    if (fCachedMSAALoadInputDescSet) {
        return fCachedMSAALoadInputDescSet;
    }

    fCachedMSAALoadInputDescSet.reset(
        gpu->resourceProvider().getInputDescriptorSet());
    if (!fCachedMSAALoadInputDescSet) {
        return nullptr;
    }

    write_input_desc_set(
        gpu,
        this->framebufferView()->imageView(),
        VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
        *fCachedMSAALoadInputDescSet->descriptorSet());

    return fCachedMSAALoadInputDescSet;
}
```

### 资源释放

```cpp
void GrVkImage::Resource::freeGPUData() const {
    // 1. 调用 release callback(如果有)
    this->invokeReleaseProc();

    // 2. 销毁 VkImage
    VK_CALL(fGpu, DestroyImage(fGpu->device(), fImage, nullptr));

    // 3. 释放内存
    skgpu::VulkanMemory::FreeImageMemory(fGpu->memoryAllocator(), fAlloc);
}

// 借用资源版本:仅调用 callback,不销毁 VkImage
void GrVkImage::BorrowedResource::freeGPUData() const {
    this->invokeReleaseProc();
}
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrAttachment` | 基类,提供附件抽象 |
| `GrVkGpu` | GPU 对象,提供设备和接口 |
| `GrVkImageView` | 图像视图,用于访问图像 |
| `VulkanMemoryAllocator` | 内存分配器,管理图像内存 |
| `MutableTextureState` | 可变状态,跟踪布局和队列族 |
| `GrVkResourceProvider` | 资源提供者,提供描述符集 |
| `GrVkDescriptorSet` | 描述符集,用于输入附件 |
| `VulkanMemory` | 内存管理工具 |

### 被依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrVkTexture` | 纹理类包含 GrVkImage |
| `GrVkRenderTarget` | 渲染目标使用 GrVkImage 作为颜色附件 |
| `GrVkFramebuffer` | 帧缓冲区引用 GrVkImage 作为附件 |
| `GrVkOpsRenderPass` | 渲染通道访问图像的视图和布局 |

## 设计模式与设计决策

### 1. 工厂方法模式

提供多个静态工厂方法创建不同类型的图像:

```cpp
MakeStencil()   // 模板附件
MakeMSAA()      // MSAA 附件
MakeTexture()   // 纹理
MakeWrapped()   // 外部图像
```

### 2. RAII 资源管理

通过内部 `Resource` 类管理 VkImage 生命周期:

```cpp
class Resource : public GrTextureResource {
    ~Resource() { freeGPUData(); }
};
```

### 3. 策略模式 - BorrowedResource

区分自有资源和借用资源的销毁策略:

```cpp
// 自有资源:销毁 VkImage 和释放内存
class Resource {
    void freeGPUData() const {
        DestroyImage(...);
        FreeImageMemory(...);
    }
};

// 借用资源:仅调用 callback
class BorrowedResource : public Resource {
    void freeGPUData() const {
        invokeReleaseProc();  // 不销毁 VkImage
    }
};
```

### 4. 状态模式

使用 `MutableTextureState` 跟踪图像的可变状态:

```cpp
sk_sp<MutableTextureState> fMutableState;
// 封装:
// - VkImageLayout (当前布局)
// - uint32_t (队列族索引)
```

### 5. 享元模式 (Flyweight)

缓存描述符集,避免重复创建:

```cpp
gr_rp<const GrVkDescriptorSet> fCachedBlendingInputDescSet;
gr_rp<const GrVkDescriptorSet> fCachedMSAALoadInputDescSet;
```

### 6. 模板方法模式

基类定义 `onRelease()` 和 `onAbandon()`,派生类实现:

```cpp
void GrVkImage::onRelease() override {
    this->releaseImage();  // 释放 Vulkan 资源
    GrAttachment::onRelease();  // 调用基类
}
```

## 性能考量

### 1. 布局转换优化

```cpp
// 跳过不必要的屏障
if (newLayout == currentLayout && sameQueueFamily &&
    isReadOnlyLayout(currentLayout)) {
    return;  // 无需屏障
}
```

只读布局之间的转换可以跳过。

### 2. 描述符集缓存

```cpp
if (fCachedBlendingInputDescSet) {
    return fCachedBlendingInputDescSet;  // 复用
}
```

输入附件描述符集缓存在 `GrVkImage` 中,避免重复创建。

### 3. 内存分配策略

- **专用内存**: 大图像使用专用内存分配
- **懒分配**: 瞬态附件使用懒分配(lazily allocated)
- **内存池**: 小图像从内存池分配

### 4. 队列族管理

```cpp
// 独占模式下自动处理队列族
if (fInfo.fSharingMode == VK_SHARING_MODE_EXCLUSIVE) {
    if (newQueueFamilyIndex == VK_QUEUE_FAMILY_IGNORED) {
        newQueueFamilyIndex = gpu->queueIndex();
    }
}
```

减少显式队列族转换的需求。

### 5. 视图复用

```cpp
sk_sp<const GrVkImageView> fFramebufferView;  // 附件视图
sk_sp<const GrVkImageView> fTextureView;      // 采样视图
```

每个图像最多创建两个视图,缓存复用。

### 6. 懒分配支持

```cpp
bool useLazyAllocation =
    (imageDesc.fUsageFlags & VK_IMAGE_USAGE_TRANSIENT_ATTACHMENT_BIT);
```

瞬态附件(如可丢弃 MSAA)使用懒分配,节省内存。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/GrAttachment.h` | 基类定义 |
| `src/gpu/ganesh/vk/GrVkGpu.h/cpp` | GPU 对象 |
| `src/gpu/ganesh/vk/GrVkImageView.h/cpp` | 图像视图 |
| `src/gpu/ganesh/vk/GrVkTexture.h/cpp` | 纹理类(包含 GrVkImage) |
| `src/gpu/ganesh/vk/GrVkRenderTarget.h/cpp` | 渲染目标 |
| `src/gpu/ganesh/vk/GrVkFramebuffer.h/cpp` | 帧缓冲区 |
| `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp` | 资源提供者 |
| `src/gpu/ganesh/vk/GrVkDescriptorSet.h/cpp` | 描述符集 |
| `src/gpu/vk/VulkanMemory.h` | 内存管理工具 |
| `include/gpu/MutableTextureState.h` | 可变状态接口 |
| `include/gpu/vk/VulkanMemoryAllocator.h` | 内存分配器接口 |
