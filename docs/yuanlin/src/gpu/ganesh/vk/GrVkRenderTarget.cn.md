# GrVkRenderTarget

> 源文件
> - `src/gpu/ganesh/vk/GrVkRenderTarget.h`
> - `src/gpu/ganesh/vk/GrVkRenderTarget.cpp`

## 概述

`GrVkRenderTarget` 是 Skia Ganesh 渲染引擎中用于表示 Vulkan 渲染目标的核心类。它继承自 `GrRenderTarget`，负责管理颜色附件、解析附件（用于 MSAA）、模板附件，以及关联的帧缓冲对象和渲染通道。该类支持多种使用场景，包括普通渲染目标、MSAA 渲染目标、动态 MSAA (DMSAA)，以及包装次级命令缓冲区的外部帧缓冲。

## 架构位置

在 Skia GPU 架构中，`GrVkRenderTarget` 的层次结构如下：

```
GrSurface (基类)
    └── GrRenderTarget (渲染目标基类)
        └── GrVkRenderTarget (Vulkan 渲染目标实现)
            └── GrVkTextureRenderTarget (纹理+渲染目标组合)
```

该类位于 `src/gpu/ganesh/vk/` 目录下，与以下类紧密协作：
- `GrVkImage`: 封装底层 Vulkan 图像
- `GrVkFramebuffer`: 管理 Vulkan 帧缓冲对象
- `GrVkRenderPass`: 管理 Vulkan 渲染通道
- `GrVkGpu`: Vulkan GPU 接口

## 主要类与结构体

### GrVkRenderTarget 类

**核心成员变量**：
```cpp
sk_sp<GrVkImage> fColorAttachment;          // 颜色附件
sk_sp<GrVkImage> fResolveAttachment;        // 解析附件（MSAA）
sk_sp<GrVkImage> fDynamicMSAAAttachment;    // 动态 MSAA 附件（DMSAA）
sk_sp<const GrVkFramebuffer> fCachedFramebuffers[32];  // 缓存的帧缓冲
const GrVkDescriptorSet* fCachedInputDescriptorSet;    // 输入附件描述符集
sk_sp<GrVkFramebuffer> fExternalFramebuffer;  // 外部帧缓冲（次级命令缓冲区）
```

**常量定义**：
```cpp
static constexpr int kNumCachedFramebuffers = 32;
```

缓存 32 种不同配置的帧缓冲（5 个正交特性：resolve、stencil、input attachment、advanced blend、load from resolve，2^5 = 32）。

**枚举类型**：
```cpp
enum class CreateType {
    kDirectlyWrapped,  // 直接包装的外部图像，需要注册到缓存
    kFromTextureRT,    // 从 TextureRT 创建，由 TexRT 处理缓存注册
};
```

**类型别名**：
```cpp
using SelfDependencyFlags = GrVkRenderPass::SelfDependencyFlags;
using LoadFromResolve = GrVkRenderPass::LoadFromResolve;
```

## 公共 API 函数

### 静态工厂方法

**MakeWrappedRenderTarget**
```cpp
static sk_sp<GrVkRenderTarget> MakeWrappedRenderTarget(
    GrVkGpu* gpu,
    SkISize dimensions,
    int sampleCnt,
    const GrVkImageInfo& info,
    sk_sp<skgpu::MutableTextureState> mutableState);
```
包装外部 Vulkan 图像为渲染目标。验证样本数匹配，创建 `GrVkImage` 包装器，然后构造 `GrVkRenderTarget`。

**MakeSecondaryCBRenderTarget**
```cpp
static sk_sp<GrVkRenderTarget> MakeSecondaryCBRenderTarget(
    GrVkGpu* gpu,
    SkISize dimensions,
    const GrVkDrawableInfo& vkInfo);
```
为次级命令缓冲区创建渲染目标。查找兼容的外部渲染通道，创建包装图像和帧缓冲。用于 Skia 与外部 Vulkan 应用集成。

### 附件访问方法

**colorAttachment**
```cpp
GrVkImage* colorAttachment() const;
```
返回颜色附件。对于次级命令缓冲区会触发断言。

**resolveAttachment**
```cpp
GrVkImage* resolveAttachment() const;
```
返回解析附件（用于 MSAA 解析）。

**nonMSAAAttachment**
```cpp
GrVkImage* nonMSAAAttachment() const;
```
返回非 MSAA 附件：单采样返回颜色附件，多采样返回解析附件（可能为 null）。

**externalAttachment**
```cpp
GrVkImage* externalAttachment() const;
```
返回外部客户端使用的附件：优先返回解析附件，否则返回颜色附件。

**colorAttachmentView / resolveAttachmentView**
```cpp
const GrVkImageView* colorAttachmentView() const;
const GrVkImageView* resolveAttachmentView() const;
```
返回附件的图像视图。

### 渲染通道与帧缓冲管理

**getFramebuffer**
```cpp
const GrVkFramebuffer* getFramebuffer(
    bool withResolve,
    bool withStencil,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve);
```
获取指定配置的帧缓冲。首先查找缓存，未找到则创建新帧缓冲。

**getSimpleRenderPass**
```cpp
const GrVkRenderPass* getSimpleRenderPass(
    bool withResolve,
    bool withStencil,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve);
```
获取简单渲染通道。对于次级命令缓冲区返回外部渲染通道。

**compatibleRenderPassHandle**
```cpp
GrVkResourceProvider::CompatibleRPHandle compatibleRenderPassHandle(
    bool withResolve,
    bool withStencil,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve);
```
返回兼容渲染通道的句柄，用于管道状态缓存。

### 特性查询

**wrapsSecondaryCommandBuffer**
```cpp
bool wrapsSecondaryCommandBuffer() const;
```
判断是否包装次级命令缓冲区。

**canAttemptStencilAttachment**
```cpp
bool canAttemptStencilAttachment(bool useMSAASurface) const override;
```
判断是否可以附加模板缓冲。次级命令缓冲区不支持模板附加。

**backendFormat**
```cpp
GrBackendFormat backendFormat() const override;
```
返回后端格式。

**getBackendRenderTarget**
```cpp
GrBackendRenderTarget getBackendRenderTarget() const override;
```
返回后端渲染目标对象，用于跨层接口。

### 描述符重建

**getAttachmentsDescriptor**
```cpp
bool getAttachmentsDescriptor(
    GrVkRenderPass::AttachmentsDescriptor* desc,
    GrVkRenderPass::AttachmentFlags* flags,
    bool withResolve,
    bool withStencil);
```
获取附件描述符，包括格式和采样数。

**ReconstructAttachmentsDescriptor** (静态)
```cpp
static void ReconstructAttachmentsDescriptor(
    const GrVkCaps& vkCaps,
    const GrProgramInfo& programInfo,
    GrVkRenderPass::AttachmentsDescriptor* desc,
    GrVkRenderPass::AttachmentFlags* flags);
```
从程序信息重建附件描述符，用于渲染通道缓存查找。

## 内部实现细节

### 构造函数重载

**标准构造函数**：
```cpp
GrVkRenderTarget(GrVkGpu* gpu,
                 SkISize dimensions,
                 sk_sp<GrVkImage> colorAttachment,
                 sk_sp<GrVkImage> resolveAttachment,
                 CreateType createType,
                 std::string_view label);
```

初始化逻辑：
1. 虚继承 `GrSurface`，必须显式调用基类构造函数
2. 验证颜色附件存在且有 `VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT` 标志
3. 单采样且支持 input attachment 的颜色附件，同时设置为解析附件（用于 DMSAA）
4. 调用 `setFlags()` 设置 input attachment 支持标志
5. 根据 `CreateType` 决定是否注册到缓存

**次级命令缓冲区构造函数**：
```cpp
GrVkRenderTarget(GrVkGpu* gpu,
                 SkISize dimensions,
                 sk_sp<GrVkFramebuffer> externalFramebuffer,
                 std::string_view label);
```

特点：
- 不持有颜色附件（由外部帧缓冲管理）
- 样本数固定为 1
- 不支持 input attachment
- 始终注册为不可缓存

### 帧缓冲缓存机制

**renderpass_features_to_index** 函数计算缓存索引：
```cpp
static int renderpass_features_to_index(
    bool hasResolve,
    bool hasStencil,
    GrVkRenderPass::SelfDependencyFlags selfDepFlags,
    GrVkRenderPass::LoadFromResolve loadFromResolve);
```

索引计算（5 个正交特性）：
- Bit 0: `hasResolve` → +1
- Bit 1: `hasStencil` → +2
- Bit 2: `kForInputAttachment` → +4
- Bit 3: `kForNonCoherentAdvBlend` → +8
- Bit 4: `kLoad` from resolve → +16

总共 2^5 = 32 种组合。

**getFramebuffer** 实现：
```cpp
const GrVkFramebuffer* GrVkRenderTarget::getFramebuffer(...) {
    int cacheIndex = renderpass_features_to_index(...);
    if (auto fb = fCachedFramebuffers[cacheIndex]) {
        return fb.get();  // 缓存命中
    }
    this->createFramebuffer(...);  // 缓存未命中，创建新帧缓冲
    return fCachedFramebuffers[cacheIndex].get();
}
```

### 动态 MSAA (DMSAA) 支持

**dynamicMSAAAttachment** 方法：
```cpp
GrVkImage* GrVkRenderTarget::dynamicMSAAAttachment() {
    if (fDynamicMSAAAttachment) {
        return fDynamicMSAAAttachment.get();  // 已创建，直接返回
    }

    // 延迟创建 DMSAA 附件
    GrMemoryless memoryless =
        gpu->vkCaps().supportsMemorylessAttachments()
            ? GrMemoryless::kYes : GrMemoryless::kNo;

    sk_sp<GrAttachment> msaaAttachment =
        rp->getDiscardableMSAAAttachment(
            nonMSAAColorAttachment->dimensions(),
            format,
            gpu->caps()->internalMultisampleCount(format),
            GrProtected(...),
            memoryless);

    fDynamicMSAAAttachment = sk_sp<GrVkImage>(
        static_cast<GrVkImage*>(msaaAttachment.release()));
    return fDynamicMSAAAttachment.get();
}
```

DMSAA 特点：
- 延迟创建，仅在需要时分配
- 支持 memoryless 优化（硬件支持时使用瞬态内存）
- 可丢弃，渲染后不保留数据

**msaaAttachment** 方法：
```cpp
GrVkImage* GrVkRenderTarget::msaaAttachment() {
    return this->colorAttachment()->numSamples() == 1
        ? this->dynamicMSAAAttachment()  // 单采样，返回动态 MSAA
        : this->colorAttachment();       // 多采样，返回颜色附件
}
```

### 帧缓冲创建流程

**createFramebuffer** 实现：
```cpp
void GrVkRenderTarget::createFramebuffer(
    bool withResolve,
    bool withStencil,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve) {

    // 1. 创建渲染通道
    auto [renderPass, compatibleHandle] =
        this->createSimpleRenderPass(withResolve, withStencil,
                                    selfDepFlags, loadFromResolve);

    // 2. 选择附件
    GrVkImage* resolve = withResolve ? this->resolveAttachment() : nullptr;
    GrVkImage* colorAttachment = withResolve ? this->msaaAttachment()
                                              : this->colorAttachment();
    bool useMSAA = this->numSamples() > 1 || withResolve;
    GrVkImage* stencil = withStencil
        ? static_cast<GrVkImage*>(this->getStencilAttachment(useMSAA))
        : nullptr;

    // 3. 创建帧缓冲并缓存
    int cacheIndex = renderpass_features_to_index(...);
    fCachedFramebuffers[cacheIndex] =
        GrVkFramebuffer::Make(gpu, this->dimensions(),
                             sk_sp<const GrVkRenderPass>(renderPass),
                             colorAttachment, resolve, stencil,
                             compatibleHandle);
}
```

### 次级命令缓冲区支持

**MakeSecondaryCBRenderTarget** 实现：
```cpp
sk_sp<GrVkRenderTarget> GrVkRenderTarget::MakeSecondaryCBRenderTarget(...) {
    // 1. 查找兼容的外部渲染通道
    const GrVkRenderPass* rp = gpu->resourceProvider()
        .findCompatibleExternalRenderPass(
            vkInfo.fCompatibleRenderPass,
            vkInfo.fColorAttachmentIndex);

    // 2. 创建图像包装器（只设置布局和格式）
    GrVkImageInfo info;
    info.fImageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    info.fFormat = vkInfo.fFormat;
    info.fImageUsageFlags = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | ...;

    sk_sp<GrVkImage> colorAttachment = GrVkImage::MakeWrapped(...);

    // 3. 创建次级命令缓冲区对象
    std::unique_ptr<GrVkSecondaryCommandBuffer> scb(
        GrVkSecondaryCommandBuffer::Create(
            vkInfo.fSecondaryCommandBuffer, rp));

    // 4. 创建外部帧缓冲
    sk_sp<GrVkFramebuffer> framebuffer(
        new GrVkFramebuffer(gpu, std::move(colorAttachment),
                           sk_sp<const GrVkRenderPass>(rp),
                           std::move(scb)));

    // 5. 创建渲染目标
    return sk_sp<GrVkRenderTarget>(
        new GrVkRenderTarget(gpu, dimensions, std::move(framebuffer), ...));
}
```

次级命令缓冲区用于 Skia 与外部 Vulkan 应用的集成，允许 Skia 录制命令到外部提供的命令缓冲区中。

### 模板附件管理

**canAttemptStencilAttachment** 逻辑：
```cpp
bool GrVkRenderTarget::canAttemptStencilAttachment(bool useMSAASurface) const {
    // 验证 MSAA 状态一致性
    SkASSERT(!useMSAASurface || this->numSamples() > 1 ||
             this->getVkGpu()->vkCaps().supportsDiscardableMSAAForDMSAA());

    // 单采样渲染目标不能附加 MSAA 模板
    if (!useMSAASurface && this->numSamples() > 1) {
        return false;
    }

    // DMSAA 要求支持 input attachment
    bool validMSAA = true;
    if (useMSAASurface) {
        validMSAA = this->numSamples() > 1 ||
                    (this->getVkGpu()->vkCaps().supportsDiscardableMSAAForDMSAA() &&
                     this->colorAttachment()->supportsInputAttachmentUsage());
    }

    // 次级命令缓冲区不支持模板附加
    return validMSAA && !this->wrapsSecondaryCommandBuffer();
}
```

### 资源释放

**releaseInternalObjects** 方法：
```cpp
void GrVkRenderTarget::releaseInternalObjects() {
    fColorAttachment.reset();
    fResolveAttachment.reset();
    fDynamicMSAAAttachment.reset();

    for (int i = 0; i < kNumCachedFramebuffers; ++i) {
        fCachedFramebuffers[i].reset();
    }

    if (fCachedInputDescriptorSet) {
        fCachedInputDescriptorSet->recycle();
        fCachedInputDescriptorSet = nullptr;
    }

    fExternalFramebuffer.reset();
}
```

**onRelease** 和 **onAbandon** 都调用 `releaseInternalObjects()`，确保资源正确释放或放弃。

### Release Proc 转发

```cpp
void onSetRelease(sk_sp<RefCntedReleaseProc> releaseHelper) override {
    GrVkImage* attachment =
        fResolveAttachment ? fResolveAttachment.get() : fColorAttachment.get();
    attachment->setResourceRelease(std::move(releaseHelper));
}
```

将 release proc 转发给外部附件（优先解析附件），确保在 GPU 完成工作后调用。

## 依赖关系

### 内部依赖
- `GrVkImage`: 封装 Vulkan 图像对象
- `GrVkFramebuffer`: 管理帧缓冲对象
- `GrVkRenderPass`: 管理渲染通道
- `GrVkImageView`: 图像视图
- `GrVkGpu`: Vulkan GPU 接口
- `GrVkResourceProvider`: 资源提供器
- `GrVkDescriptorSet`: 描述符集
- `GrVkCaps`: Vulkan 能力查询

### 基类依赖
- `GrRenderTarget`: 渲染目标基类
- `GrSurface`: 表面基类
- `GrAttachment`: 附件基类

### 外部依赖
- `GrBackendRenderTarget`: 后端渲染目标接口
- `GrProgramInfo`: 程序信息
- `skgpu::MutableTextureState`: 可变纹理状态
- `GrVkDrawableInfo`: 次级命令缓冲区信息

## 设计模式与设计决策

### 虚继承模式

通过虚继承 `GrSurface`，支持菱形继承（`GrVkTextureRenderTarget` 同时继承 `GrVkTexture` 和 `GrVkRenderTarget`）：
```cpp
GrVkRenderTarget::GrVkRenderTarget(...)
    : GrSurface(gpu, dimensions, ..., label)  // 显式调用虚基类构造函数
    , GrRenderTarget(gpu, dimensions, ..., label)
    , ...
```

### 延迟创建策略

- **DMSAA 附件**：仅在实际使用时创建，节省内存
- **帧缓冲**：按需创建并缓存，避免预先分配所有组合
- **描述符集**：延迟分配 input attachment 描述符集

### 多级缓存机制

**帧缓冲缓存**：32 个槽位覆盖所有可能的渲染通道配置，避免重复创建：
```cpp
sk_sp<const GrVkFramebuffer> fCachedFramebuffers[32];
```

**渲染通道缓存**：通过 `GrVkResourceProvider` 全局缓存兼容的渲染通道。

### 统一附件接口

- `externalAttachment()`: 外部客户端使用的附件
- `nonMSAAAttachment()`: 非 MSAA 附件
- `msaaAttachment()`: MSAA 附件（可能是颜色或动态 MSAA）

不同场景使用合适的附件访问方法，简化上层逻辑。

### 次级命令缓冲区支持

通过 `fExternalFramebuffer` 标志区分普通渲染目标和次级命令缓冲区：
```cpp
bool wrapsSecondaryCommandBuffer() const {
    return SkToBool(fExternalFramebuffer);
}
```

大多数方法内部检查此标志，调整行为或触发断言。

### Memoryless 优化

对于支持瞬态内存的硬件（如移动 GPU），DMSAA 附件使用 memoryless 分配：
```cpp
GrMemoryless memoryless =
    gpu->vkCaps().supportsMemorylessAttachments()
        ? GrMemoryless::kYes : GrMemoryless::kNo;
```

Memoryless 附件不分配物理内存，仅存在于 tile memory 中，显著节省带宽。

## 性能考量

### 帧缓冲缓存策略

缓存 32 种帧缓冲配置，避免频繁创建和销毁 Vulkan 对象：
- 每种配置的帧缓冲创建开销较大（需要 Vulkan API 调用）
- 缓存命中率高（大多数绘制使用相同配置）
- 内存开销可控（每个帧缓冲仅存储引用）

### DMSAA 延迟分配

动态 MSAA 附件仅在需要时创建：
- 单采样渲染目标不分配 MSAA 附件
- 避免不必要的内存和带宽消耗
- 支持 memoryless 优化（移动设备）

### 样本数判断优化

```cpp
GrVkImage* GrVkRenderTarget::nonMSAAAttachment() const {
    if (fColorAttachment->numSamples() == 1) {
        return fColorAttachment.get();
    } else {
        return fResolveAttachment.get();
    }
}
```

简单的分支判断，编译器可优化为条件移动指令，避免分支预测失败。

### 附件选择逻辑

**createFramebuffer** 中根据 `withResolve` 选择附件：
```cpp
GrVkImage* colorAttachment = withResolve ? this->msaaAttachment()
                                          : this->colorAttachment();
```

- `withResolve=true`: 使用 MSAA 附件（可能是颜色或动态 MSAA）
- `withResolve=false`: 直接使用颜色附件

减少不必要的解析操作，提高渲染效率。

### GPU 内存统计

```cpp
size_t onGpuMemorySize() const override { return 0; }
```

渲染目标本身不统计内存，由附件（`GrVkImage`）负责。避免重复计数，简化内存管理。

### Input Attachment 描述符集缓存

```cpp
const GrVkDescriptorSet* fCachedInputDescriptorSet = nullptr;
```

缓存 input attachment 描述符集，避免每帧重新分配。Input attachment 用于 subpass 依赖，频繁使用时缓存效果显著。

## 相关文件

### 核心实现文件
- `src/gpu/ganesh/vk/GrVkImage.h/cpp`: Vulkan 图像封装
- `src/gpu/ganesh/vk/GrVkFramebuffer.h/cpp`: 帧缓冲管理
- `src/gpu/ganesh/vk/GrVkRenderPass.h/cpp`: 渲染通道管理
- `src/gpu/ganesh/vk/GrVkImageView.h/cpp`: 图像视图
- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: Vulkan GPU 接口
- `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp`: 资源提供器
- `src/gpu/ganesh/vk/GrVkTextureRenderTarget.h/cpp`: 纹理+渲染目标组合

### 基类文件
- `src/gpu/ganesh/GrRenderTarget.h/cpp`: 渲染目标基类
- `src/gpu/ganesh/GrSurface.h/cpp`: 表面基类
- `src/gpu/ganesh/GrAttachment.h/cpp`: 附件基类

### 工具类文件
- `src/gpu/ganesh/vk/GrVkUtil.h/cpp`: Vulkan 工具函数
- `src/gpu/ganesh/vk/GrVkCaps.h/cpp`: Vulkan 能力查询
- `src/gpu/ganesh/vk/GrVkDescriptorSet.h/cpp`: 描述符集管理
- `src/gpu/ganesh/vk/GrVkCommandBuffer.h/cpp`: 命令缓冲区

### 接口文件
- `include/gpu/ganesh/GrBackendSurface.h`: 后端表面接口
- `include/gpu/ganesh/vk/GrVkTypes.h`: Vulkan 类型定义
- `include/gpu/MutableTextureState.h`: 可变纹理状态
- `include/gpu/vk/VulkanTypes.h`: Vulkan 类型定义
