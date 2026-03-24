# include/gpu/vk - Vulkan 公共 API

## 概述

`include/gpu/vk` 目录包含 Skia 中 Vulkan 相关的公共类型定义。这些类型被 Ganesh 和 Graphite
两个渲染引擎共同使用，提供了 Vulkan 后端所需的基础设施，包括后端上下文、内存分配器、扩展管理、
纹理状态、YCbCr 颜色转换信息以及首选特性管理等。

此目录中的头文件遵循 Vulkan 1.1 作为最低版本要求。所有 Vulkan 特定的类型封装都位于 `skgpu`
命名空间下，确保与 Skia 其他部分的命名约定一致。客户端在初始化 Vulkan 后端时，需要先创建好
Vulkan 实例、物理设备和逻辑设备等对象，然后通过 `VulkanBackendContext` 结构体将这些对象
传递给 Skia。

`VulkanMemoryAllocator` 是一个关键的抽象接口，Skia 要求客户端必须提供其实现。该分配器负责
管理所有使用 `VkDeviceMemory` 的 Vulkan 资源的内存分配。Skia 并不内置特定的内存分配策略，
而是将这一决策交给客户端，通常建议使用 Vulkan Memory Allocator (VMA) 库。

`VulkanPreferredFeatures` 是一个较新的辅助类（2025年添加），帮助应用程序在 Vulkan 设备初始化
流程中让 Skia 有机会请求它所需的扩展和特性。通过分步骤调用 `addToInstanceExtensions`、
`addFeaturesToQuery` 和 `addFeaturesToEnable`，Skia 可以在不干扰应用程序自身配置的情况下
请求额外的功能支持。

`VulkanYcbcrConversionInfo` 提供了 YCbCr 采样器转换的完整配置，这在处理 Android 硬件缓冲区
（AHardwareBuffer）中的视频纹理时尤为重要。

## 架构图

```
include/gpu/vk/
    |
    +-- VulkanTypes.h               <-- 基础 Vulkan 类型定义
    |       |
    |       +-- VulkanGetProc          (函数指针获取回调)
    |       +-- VulkanBackendMemory    (内存句柄)
    |       +-- VulkanAlloc            (内存分配信息)
    |       +-- VulkanYcbcrConversionInfo  (YCbCr 转换配置)
    |       +-- VulkanDeviceLostProc   (设备丢失回调)
    |
    +-- VulkanBackendContext.h      <-- Vulkan 后端初始化上下文
    |       |
    |       +-- VkInstance, VkDevice, VkQueue
    |       +-- VulkanExtensions*, VulkanMemoryAllocator
    |
    +-- VulkanExtensions.h          <-- Vulkan 扩展查询辅助
    |
    +-- VulkanMemoryAllocator.h     <-- 内存分配器抽象接口
    |       |
    |       +-- allocateImageMemory()
    |       +-- allocateBufferMemory()
    |       +-- mapMemory() / unmapMemory()
    |
    +-- VulkanMutableTextureState.h <-- Vulkan 特定可变纹理状态
    |
    +-- VulkanPreferredFeatures.h   <-- Skia 首选 Vulkan 特性
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `VulkanTypes.h` | Vulkan 基础类型、VulkanAlloc、VulkanYcbcrConversionInfo、回调定义 |
| `VulkanBackendContext.h` | Vulkan 后端上下文结构体，包含 VkInstance/VkDevice/VkQueue 等 |
| `VulkanExtensions.h` | Vulkan 扩展查询与管理辅助类 |
| `VulkanMemoryAllocator.h` | Vulkan 内存分配器的抽象基类 |
| `VulkanMutableTextureState.h` | Vulkan 纹理可变状态（VkImageLayout + QueueFamilyIndex） |
| `VulkanPreferredFeatures.h` | Skia 在 Vulkan 初始化中请求首选扩展和特性的辅助类 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `skgpu::VulkanBackendContext` 结构体

```cpp
struct VulkanBackendContext {
    VkInstance       fInstance;
    VkPhysicalDevice fPhysicalDevice;
    VkDevice         fDevice;
    VkQueue          fQueue;
    uint32_t         fGraphicsQueueIndex;
    uint32_t         fMaxAPIVersion;        // 必须 >= VK_API_VERSION_1_1
    const VulkanExtensions* fVkExtensions;
    const VkPhysicalDeviceFeatures* fDeviceFeatures;   // 二选一
    const VkPhysicalDeviceFeatures2* fDeviceFeatures2; // 优先使用
    sk_sp<VulkanMemoryAllocator> fMemoryAllocator;     // 必须提供
    VulkanGetProc fGetProc;
    Protected fProtectedContext;
    VulkanDeviceLostContext fDeviceLostContext;  // 可选
    VulkanDeviceLostProc fDeviceLostProc;       // 可选
};
```

### `skgpu::VulkanMemoryAllocator` 抽象类

```cpp
class VulkanMemoryAllocator : public SkRefCnt {
    virtual VkResult allocateImageMemory(VkImage, uint32_t flags, VulkanBackendMemory*) = 0;
    virtual VkResult allocateBufferMemory(VkBuffer, BufferUsage, uint32_t flags, VulkanBackendMemory*) = 0;
    virtual void getAllocInfo(const VulkanBackendMemory&, VulkanAlloc*) const = 0;
    virtual VkResult mapMemory(const VulkanBackendMemory&, void** data);
    virtual void unmapMemory(const VulkanBackendMemory&) = 0;
    virtual void freeMemory(const VulkanBackendMemory&) = 0;
    virtual std::pair<uint64_t, uint64_t> totalAllocatedAndUsedMemory() const = 0;
};
```

`BufferUsage` 枚举：`kGpuOnly`, `kCpuWritesGpuReads`, `kTransfersFromCpuToGpu`, `kTransfersFromGpuToCpu`

### `skgpu::VulkanYcbcrConversionInfo` 结构体

提供创建 `VkSamplerYcbcrConversion` 对象所需的信息。支持 `VkExternalFormatANDROID` 外部格式
和标准 `VkFormat`。包含色度模型、范围、偏移、滤波器和分量映射等完整配置。

### `skgpu::VulkanPreferredFeatures` 类

```cpp
class VulkanPreferredFeatures {
    void init(uint32_t appAPIVersion);
    void addToInstanceExtensions(const VkExtensionProperties*, size_t, std::vector<const char*>&);
    void addFeaturesToQuery(const VkExtensionProperties*, size_t, VkPhysicalDeviceFeatures2&);
    void addFeaturesToEnable(std::vector<const char*>&, VkPhysicalDeviceFeatures2&);
};
```

Skia 可能请求的 Vulkan 特性包括：
- `VkPhysicalDeviceVulkan11Features` ~ `Vulkan14Features`
- 光栅化顺序附件访问、高级混合操作、扩展动态状态
- 图形管线库、YCbCr 采样器转换、动态渲染等

### `skgpu::MutableTextureStates` 命名空间函数

```cpp
MutableTextureState MakeVulkan(VkImageLayout layout, uint32_t queueFamilyIndex);
VkImageLayout GetVkImageLayout(const MutableTextureState& state);
uint32_t GetVkQueueFamilyIndex(const MutableTextureState& state);
```

## 依赖关系

- **上游依赖**: `include/gpu/GpuTypes.h`, `include/core/SkRefCnt.h`
- **外部依赖**: Vulkan SDK 头文件 (`vulkan/vulkan.h`, 要求 Vulkan 1.1+)
- **被引用**: `include/gpu/ganesh/vk/` (Ganesh Vulkan 后端)
- **被引用**: `include/gpu/graphite/vk/` (Graphite Vulkan 后端)
- **内部实现**: `include/private/gpu/vk/SkiaVulkan.h`

## 相关文档与参考

- `include/gpu/ganesh/vk/` - Ganesh 引擎的 Vulkan 后端 API
- `include/gpu/graphite/vk/` - Graphite 引擎的 Vulkan 后端 API
- `include/gpu/GpuTypes.h` - GPU 共享基础类型
- Vulkan 规范: https://www.khronos.org/vulkan/
- Vulkan Memory Allocator (VMA): https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator
