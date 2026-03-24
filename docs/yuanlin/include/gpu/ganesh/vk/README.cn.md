# include/gpu/ganesh/vk - Ganesh Vulkan 后端公共 API

## 概述

`include/gpu/ganesh/vk` 目录包含 Ganesh 渲染引擎中 Vulkan 后端特有的公共 API。此目录中的
类型建立在 `include/gpu/vk/` 中共享的 Vulkan 基础类型之上，提供了 Ganesh 特有的 Vulkan
图像信息、后端表面工厂、信号量以及上下文创建入口。

Ganesh 的 Vulkan 后端是一个成熟的实现，广泛应用于 Android（通过 Vulkan 1.1+）和桌面
Linux/Windows 平台。核心类型 `GrVkImageInfo` 封装了 `VkImage` 及其关联的内存分配、
图像布局、格式、使用标志、采样数、mip级别等完整信息。

`GrVkDrawableInfo` 提供了一种高级机制，允许客户端的 `SkDrawable` 直接向 Vulkan 辅助命令
缓冲区注入 Vulkan 绘制命令，这在需要混合 Skia 渲染和原生 Vulkan 渲染的场景中非常有用。

创建 Ganesh Vulkan 上下文需要客户端预先设置好 Vulkan 实例、设备和队列，然后通过
`skgpu::VulkanBackendContext` 传递给 `GrDirectContexts::MakeVulkan()`。

## 架构图

```
include/gpu/ganesh/vk/
    |
    +-- GrVkTypes.h                 <-- Ganesh Vulkan 类型定义
    |       |
    |       +-- GrVkImageInfo           (VkImage 完整信息)
    |       +-- GrVkDrawableInfo        (辅助命令缓冲区注入)
    |       +-- GrVkSurfaceInfo         (表面信息)
    |
    +-- GrVkBackendSurface.h        <-- Vulkan 后端纹理/渲染目标工厂
    +-- GrVkBackendSemaphore.h      <-- Vulkan 后端信号量
    +-- GrVkDirectContext.h         <-- Vulkan 上下文创建入口
    +-- GrBackendDrawableInfo.h     <-- Drawable 信息封装
    |
    +-- (依赖) include/gpu/vk/     <-- 共享 Vulkan 类型
            +-- VulkanBackendContext.h
            +-- VulkanMemoryAllocator.h
            +-- VulkanTypes.h
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrVkTypes.h` | `GrVkImageInfo`、`GrVkDrawableInfo`、`GrVkSurfaceInfo` |
| `GrVkBackendSurface.h` | Vulkan 后端纹理和渲染目标的创建与查询工厂方法 |
| `GrVkBackendSemaphore.h` | Vulkan 后端信号量封装（`VkSemaphore`） |
| `GrVkDirectContext.h` | `GrDirectContexts::MakeVulkan()` 工厂方法 |
| `GrBackendDrawableInfo.h` | `GrBackendDrawableInfo` 封装 |

## 关键类与函数

### `GrVkImageInfo` 结构体

```cpp
struct GrVkImageInfo {
    VkImage           fImage;
    skgpu::VulkanAlloc fAlloc;
    VkImageTiling     fImageTiling;
    VkImageLayout     fImageLayout;
    VkFormat          fFormat;
    VkImageUsageFlags fImageUsageFlags;
    uint32_t          fSampleCount;
    uint32_t          fLevelCount;
    uint32_t          fCurrentQueueFamily;
    skgpu::Protected  fProtected;
    skgpu::VulkanYcbcrConversionInfo fYcbcrConversionInfo;
    VkSharingMode     fSharingMode;
};
```

### `GrVkDrawableInfo` 结构体

```cpp
struct GrVkDrawableInfo {
    VkCommandBuffer fSecondaryCommandBuffer;  // 辅助命令缓冲区
    uint32_t        fColorAttachmentIndex;     // 颜色附件索引
    VkRenderPass    fCompatibleRenderPass;     // 兼容的渲染通道
    VkFormat        fFormat;                   // 颜色附件格式
    VkRect2D*       fDrawBounds;               // 绘制边界（可选输出）
};
```

### 上下文创建

```cpp
namespace GrDirectContexts {
    sk_sp<GrDirectContext> MakeVulkan(const skgpu::VulkanBackendContext&, const GrContextOptions&);
    sk_sp<GrDirectContext> MakeVulkan(const skgpu::VulkanBackendContext&);
}
```

Vulkan 上下文（VkQueue、VkDevice、VkInstance）必须在 GrDirectContext 销毁之前保持活跃。

## 依赖关系

- **上游依赖**: `include/gpu/vk/VulkanTypes.h`, `include/gpu/vk/VulkanBackendContext.h`
- **上游依赖**: `include/gpu/ganesh/GrTypes.h`, `include/gpu/GpuTypes.h`
- **外部依赖**: Vulkan SDK (Vulkan 1.1+)
- **实现代码**: `src/gpu/ganesh/vk/`

## 相关文档与参考

- `include/gpu/vk/` - 共享 Vulkan 类型（Ganesh + Graphite）
- `include/gpu/ganesh/` - Ganesh 引擎主目录
- `include/gpu/graphite/vk/` - Graphite Vulkan 后端
- Vulkan 规范: https://www.khronos.org/vulkan/
