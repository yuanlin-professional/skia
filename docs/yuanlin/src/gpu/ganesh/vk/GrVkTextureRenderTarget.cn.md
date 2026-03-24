# GrVkTextureRenderTarget

> 源文件
> - `src/gpu/ganesh/vk/GrVkTextureRenderTarget.h`
> - `src/gpu/ganesh/vk/GrVkTextureRenderTarget.cpp`

## 概述

`GrVkTextureRenderTarget` 是 Skia Ganesh Vulkan 后端中同时支持纹理采样和渲染目标功能的组合类。它通过多重继承同时继承 `GrVkTexture` 和 `GrVkRenderTarget`，实现了可作为纹理使用（如采样）又可作为渲染目标使用（如绘制）的 GPU 表面。该类适用于需要渲染到纹理（render-to-texture）的场景，如后处理效果、阴影贴图等。

## 架构位置

在 Skia GPU 架构中的继承层次：

```
      GrSurface (虚基类)
       /      \
GrTexture   GrRenderTarget
      |          |
 GrVkTexture  GrVkRenderTarget
       \        /
   GrVkTextureRenderTarget
```

通过虚继承 `GrSurface` 解决菱形继承问题，避免重复基类成员。

## 主要类与结构体

### GrVkTextureRenderTarget 类

核心特点：
- 多重继承 `GrVkTexture` 和 `GrVkRenderTarget`
- 持有三个图像对象：纹理图像、颜色附件、解析附件（MSAA）
- 单采样时纹理和颜色附件共享同一图像
- 多采样时纹理作为解析附件，颜色附件为 MSAA 图像

## 公共 API 函数

**MakeNewTextureRenderTarget** (静态工厂方法)
```cpp
static sk_sp<GrVkTextureRenderTarget> MakeNewTextureRenderTarget(
    GrVkGpu* gpu,
    skgpu::Budgeted budgeted,
    SkISize dimensions,
    VkFormat format,
    uint32_t mipLevels,
    int sampleCnt,
    GrMipmapStatus mipmapStatus,
    GrProtected isProtected,
    std::string_view label);
```
创建新的纹理渲染目标。单采样时纹理直接用作颜色附件，多采样时创建额外的 MSAA 附件。

**MakeWrappedTextureRenderTarget** (静态工厂方法)
```cpp
static sk_sp<GrVkTextureRenderTarget> MakeWrappedTextureRenderTarget(
    GrVkGpu* gpu,
    SkISize dimensions,
    int sampleCnt,
    GrWrapOwnership wrapOwnership,
    GrWrapCacheable cacheable,
    const GrVkImageInfo& info,
    sk_sp<skgpu::MutableTextureState> mutableState);
```
包装外部 Vulkan 图像为纹理渲染目标。

**backendFormat**
```cpp
GrBackendFormat backendFormat() const override;
```
返回后端格式，转发给 `GrVkTexture::backendFormat()`。

**onGpuMemorySize**
```cpp
size_t onGpuMemorySize() const override;
```
计算 GPU 内存大小。纹理附件大小由纹理报告，MSAA 附件单独计算。

## 内部实现细节

### 构造函数设计

两个私有构造函数：
1. **预算分配构造函数**：调用 `registerWithCache(budgeted)`
2. **包装构造函数**：调用 `registerWithCacheWrapped(cacheable)`

关键：传递 `CreateType::kFromTextureRT` 给 `GrVkRenderTarget`，避免重复注册到缓存。

### 附件创建逻辑

**create_rt_attachments** 辅助函数：
```cpp
bool create_rt_attachments(...) {
    if (sampleCnt > 1) {
        // 多采样：创建 MSAA 附件 + 纹理作为解析附件
        sk_sp<GrAttachment> msaaAttachment = rp->makeMSAAAttachment(...);
        *colorAttachment = sk_sp<GrVkImage>(static_cast<GrVkImage*>(...));
        *resolveAttachment = std::move(texture);
    } else {
        // 单采样：纹理直接作为颜色附件
        *colorAttachment = std::move(texture);
    }
    return true;
}
```

### 资源释放顺序

**onAbandon / onRelease**：
```cpp
void onAbandon() override {
    GrVkTexture::onAbandon();     // 先调用纹理释放
    GrVkRenderTarget::onAbandon(); // 再调用渲染目标释放
}
```

顺序很重要：纹理的 idle procs 必须先调用。

### Release Proc 转发

```cpp
void onSetRelease(sk_sp<RefCntedReleaseProc> releaseHelper) override {
    GrVkTexture::onSetRelease(std::move(releaseHelper));
}
```

转发给纹理，因为纹理图像是外部可见的主要对象。

### GPU 内存计算

```cpp
size_t onGpuMemorySize() const {
    // 非 MSAA 附件大小为 0（由纹理报告）
    SkASSERT(this->nonMSAAAttachment()->gpuMemorySize() == 0);
    // MSAA 附件有独立大小
    if (this->numSamples() > 1) {
        SkASSERT(this->colorAttachment()->gpuMemorySize() == ...);
    }
    // 只返回纹理大小（包含 mipmap）
    return GrSurface::ComputeSize(this->backendFormat(), this->dimensions(),
                                  1, this->mipmapped());
}
```

避免重复计数：纹理附件大小设为 0，只由纹理对象报告。

## 依赖关系

### 基类依赖
- `GrVkTexture`: 纹理功能
- `GrVkRenderTarget`: 渲染目标功能
- `GrSurface`: 虚基类

### 内部依赖
- `GrVkGpu`: GPU 接口
- `GrVkImage`: Vulkan 图像封装
- `GrAttachment`: 附件基类
- `GrResourceProvider`: 资源提供器（创建 MSAA 附件）

## 设计模式与设计决策

### 多重继承模式

利用多重继承实现接口组合，避免代码重复。Windows 编译器会对菱形继承发出 dominance 警告，通过 `#pragma warning(disable: 4250)` 抑制。

### 虚继承解决菱形继承

`GrSurface` 使用虚继承，确保只有一份基类成员实例。

### 延迟 MSAA 附件创建

单采样时不创建额外附件，直接使用纹理图像，节省内存和带宽。

### 缓存注册委托

通过 `CreateType` 标志通知 `GrVkRenderTarget` 跳过缓存注册，由 `GrVkTextureRenderTarget` 统一管理。

### 资源管理顺序

Release/abandon 时先调用纹理方法，确保纹理 idle procs 正确执行。

## 性能考量

### 单采样优化

单采样时纹理和渲染目标共享同一 `VkImage`，避免不必要的图像拷贝和内存分配。

### MSAA 解析

多采样时纹理作为解析目标，渲染完成后自动解析到纹理，无需额外 blit 操作。

### 内存统计

避免重复计数：附件图像大小设为 0，由纹理对象统一报告。

## 相关文件

### 基类文件
- `src/gpu/ganesh/vk/GrVkTexture.h/cpp`: Vulkan 纹理
- `src/gpu/ganesh/vk/GrVkRenderTarget.h/cpp`: Vulkan 渲染目标
- `src/gpu/ganesh/GrSurface.h/cpp`: 表面基类

### 核心依赖
- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: Vulkan GPU 接口
- `src/gpu/ganesh/vk/GrVkImage.h/cpp`: Vulkan 图像封装
- `src/gpu/ganesh/GrResourceProvider.h/cpp`: 资源提供器
- `src/gpu/ganesh/GrAttachment.h/cpp`: 附件基类
