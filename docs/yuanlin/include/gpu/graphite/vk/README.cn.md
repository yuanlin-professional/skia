# include/gpu/graphite/vk - Graphite Vulkan 后端公共 API

## 概述

`include/gpu/graphite/vk` 目录包含 Graphite 渲染引擎中 Vulkan 后端的公共 API。Graphite
的 Vulkan 后端是面向 Android 和桌面 Linux/Windows 的高性能渲染后端，利用 Vulkan 的低级
特性（如显式内存管理、管线缓存、命令缓冲区并行编码）实现高效渲染。

`VulkanTextureInfo` 继承自 `TextureInfo::Data`，封装了 `VkFormat`、`VkImageTiling`、
`VkImageUsageFlags`、`VkSharingMode`、`VkImageAspectFlags` 以及 `VulkanYcbcrConversionInfo`
等 Vulkan 特有的纹理属性。通过 `VkImageCreateFlags` 可以指定保护位和多采样渲染到单采样
位等标志。

Graphite 的 Vulkan 后端复用了 `include/gpu/vk/` 中的共享类型（如 `VulkanBackendContext`、
`VulkanMemoryAllocator`），因此初始化流程与 Ganesh 的 Vulkan 后端类似：客户端需要预先创建
Vulkan 实例、设备和队列，提供内存分配器，然后通过 `ContextFactory::MakeVulkan()` 创建
Graphite Context。

此目录还包含一个 `precompile/` 子目录，提供 Vulkan 特有的预编译着色器（如 YCbCr 图像）。

## 架构图

```
include/gpu/graphite/vk/
    |
    +-- VulkanGraphiteTypes.h      <-- Vulkan 纹理类型 + 工厂方法
    |       |
    |       +-- VulkanTextureInfo      (VkFormat, Tiling, Usage, YCbCr)
    |       +-- TextureInfos::MakeVulkan()
    |       +-- BackendTextures::MakeVulkan()
    |       +-- BackendSemaphores::MakeVulkan()
    |
    +-- VulkanGraphiteContext.h    <-- Vulkan 上下文创建入口
    |       |
    |       +-- ContextFactory::MakeVulkan()
    |
    +-- VulkanGraphiteUtils.h      <-- (重定向到 VulkanGraphiteContext.h)
    |
    +-- precompile/                <-- Vulkan 特有预编译着色器
    |   +-- VulkanPrecompileShader.h
    |
    +-- (依赖) include/gpu/vk/   <-- 共享 Vulkan 类型
            +-- VulkanBackendContext.h
            +-- VulkanMemoryAllocator.h
            +-- VulkanTypes.h
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `VulkanGraphiteTypes.h` | `VulkanTextureInfo` 类和纹理/信号量工厂方法 |
| `VulkanGraphiteContext.h` | `ContextFactory::MakeVulkan()` 工厂方法 |
| `VulkanGraphiteUtils.h` | 重定向头文件 |
| `precompile/` | Vulkan 特有的预编译着色器 |

## 关键类与函数

### `VulkanTextureInfo` 类

```cpp
class VulkanTextureInfo final : public TextureInfo::Data {
    VkImageCreateFlags fFlags;        // VK_IMAGE_CREATE_PROTECTED_BIT 等
    VkFormat           fFormat;
    VkImageTiling      fImageTiling;
    VkImageUsageFlags  fImageUsageFlags;
    VkSharingMode      fSharingMode;
    VkImageAspectFlags fAspectMask;
    VulkanYcbcrConversionInfo fYcbcrConversionInfo;

    static constexpr BackendApi kBackend = BackendApi::kVulkan;
    Protected isProtected() const;
};
```

### 上下文创建

```cpp
namespace skgpu::graphite::ContextFactory {
    std::unique_ptr<Context> MakeVulkan(const skgpu::VulkanBackendContext&,
                                         const ContextOptions&);
}
```

### 纹理信息工厂

```cpp
namespace skgpu::graphite::TextureInfos {
    TextureInfo MakeVulkan(const VulkanTextureInfo&);
    bool GetVulkanTextureInfo(const TextureInfo&, VulkanTextureInfo*);
}
```

### 后端纹理工厂

```cpp
namespace skgpu::graphite::BackendTextures {
    BackendTexture MakeVulkan(SkISize dimensions,
                               const VulkanTextureInfo&,
                               VkImageLayout,
                               uint32_t queueFamilyIndex,
                               VkImage,
                               VulkanAlloc);
}
```

### 后端信号量工厂

```cpp
namespace skgpu::graphite::BackendSemaphores {
    BackendSemaphore MakeVulkan(VkSemaphore);
    VkSemaphore GetVkSemaphore(const BackendSemaphore&);
}
```

## 依赖关系

- **上游依赖**: `include/gpu/vk/VulkanTypes.h`, `include/gpu/vk/VulkanBackendContext.h`
- **上游依赖**: `include/gpu/graphite/TextureInfo.h`, `include/gpu/graphite/BackendTexture.h`
- **外部依赖**: Vulkan SDK (Vulkan 1.1+)
- **子目录**: `precompile/` (Vulkan 特有预编译)
- **实现代码**: `src/gpu/graphite/vk/`

## 相关文档与参考

- `include/gpu/vk/` - 共享 Vulkan 类型（Ganesh + Graphite）
- `include/gpu/graphite/` - Graphite 引擎主目录
- `include/gpu/graphite/vk/precompile/` - Vulkan 预编译着色器
- `include/gpu/ganesh/vk/` - Ganesh Vulkan 后端
- Vulkan 规范: https://www.khronos.org/vulkan/
