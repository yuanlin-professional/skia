# AHardwareBufferVk — Vulkan 后端 AHardwareBuffer 集成

> 源文件: `src/gpu/ganesh/vk/AHardwareBufferVk.cpp`

## 概述

本文件实现了 Android `AHardwareBuffer` 与 Vulkan GPU 后端的集成，是 Ganesh 渲染管线在 Android 平台上使用 Vulkan 渲染到硬件缓冲区的底层实现。主要功能包括：将 Android 缓冲区格式映射为 Vulkan 格式、通过 Vulkan 外部内存扩展导入硬件缓冲区为 VkImage、以及管理 Vulkan 图像资源的生命周期。此文件仅在 Android API >= 26 时编译。

## 架构位置

```
GrAHardwareBufferUtils (分发层)
    └── AHardwareBufferVk (本文件 - Vulkan 实现)
        ├── GetVulkanBackendFormat() ─→ 格式映射
        └── MakeVulkanBackendTexture() ─→ VkImage 创建
            ├── Vulkan 外部内存扩展
            │   ├── VkExternalMemoryImageCreateInfo
            │   ├── VkExternalFormatANDROID
            │   └── AllocateAndBindImageMemory()
            ├── VulkanCleanupHelper (资源清理)
            └── GrBackendTextures::MakeVk()
```

## 主要类与结构体

### VulkanCleanupHelper

内部辅助类，管理 Vulkan 图像和内存的生命周期：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fDevice` | `VkDevice` | Vulkan 逻辑设备 |
| `fImage` | `VkImage` | Vulkan 图像句柄 |
| `fMemory` | `VkDeviceMemory` | 设备内存句柄 |
| `fDestroyImage` | `PFN_vkDestroyImage` | 图像销毁函数指针 |
| `fFreeMemory` | `PFN_vkFreeMemory` | 内存释放函数指针 |

析构函数按顺序调用 `vkDestroyImage` 和 `vkFreeMemory`。

## 公共 API 函数

### GetVulkanBackendFormat()

```cpp
GrBackendFormat GetVulkanBackendFormat(GrDirectContext* dContext,
                                        AHardwareBuffer* hardwareBuffer,
                                        uint32_t bufferFormat,
                                        bool requireKnownFormat);
```

将 Android 硬件缓冲区格式映射为 Vulkan 后端格式。

**格式映射表**:

| Android 格式 | VkFormat | 条件 |
|-------------|----------|------|
| RGBA_8888 | R8G8B8A8_UNORM | |
| R10G10B10A10 | R10X6G10X6B10X6A10X6_UNORM_4PACK16 | API >= 34 |
| RGBA_FP16 | R16G16B16A16_SFLOAT | |
| RGB_565 | R5G6B5_UNORM_PACK16 | |
| RGBA_1010102 | A2B10G10R10_UNORM_PACK32 | |
| RGBX_8888 | R8G8B8A8_UNORM | |
| RGB_888 | R8G8B8_UNORM | |
| R8 | R8_UNORM | API >= 33 |

若已知格式不可纹理化，或格式未知，回退到使用 Vulkan 外部格式 + YCbCr 转换。

### MakeVulkanBackendTexture()

```cpp
GrBackendTexture MakeVulkanBackendTexture(GrDirectContext* dContext,
                                           AHardwareBuffer* hardwareBuffer,
                                           int width, int height,
                                           DeleteImageProc* deleteProc,
                                           UpdateImageProc* updateProc,
                                           TexImageCtx* imageCtx,
                                           bool isProtectedContent,
                                           const GrBackendFormat& backendFormat,
                                           bool isRenderable,
                                           bool fromAndroidWindow);
```

从 AHardwareBuffer 创建 Vulkan 后端纹理。验证上下文和保护内容支持后，委托给 `make_vk_backend_texture()`。

## 内部实现细节

### make_vk_backend_texture() 核心流程

1. **格式验证**: 提取 VkFormat，判断是否使用外部格式导入
2. **HWB 属性查询**: 通过 `GetAHardwareBufferProperties()` 获取 Vulkan 层面的格式属性
3. **格式一致性检查**: 确保查询到的 VkFormat 与预期一致（外部格式除外）
4. **外部格式设置**: 若使用外部格式，验证 YCbCr 转换有效性并设置 `VkExternalFormatANDROID`
5. **可渲染验证**: 外部格式不可渲染；已知格式需检查 `isFormatRenderable()`
6. **创建 VkImage**: 构造 `VkImageCreateInfo`，链接外部内存信息
7. **分配和绑定内存**: `AllocateAndBindImageMemory()` 从硬件缓冲区导入设备内存
8. **构建 GrVkImageInfo**: 填充 Vulkan 图像元数据，包括队列族、保护状态、YCbCr 信息
9. **设置清理回调**: 创建 `VulkanCleanupHelper` 通过回调确保资源释放

### 外部格式处理

当标准 VkFormat 不支持所需特性时，使用 Vulkan 外部格式扩展：
- `VK_STRUCTURE_TYPE_EXTERNAL_FORMAT_ANDROID` 结构体链接到图像创建信息
- YCbCr 采样器转换 (`VkSamplerYcbcrConversion`) 用于色彩空间转换
- 外部格式的图像只能采样，不能作为传输源/目标或渲染目标

### VK_CALL 宏

```cpp
#define VK_CALL(X) gpu->vkInterface()->fFunctions.f##X
```

通过 Skia 的 Vulkan 函数表间接调用 Vulkan API，避免直接链接 Vulkan 库。

### 队列族设置

`fCurrentQueueFamily = VK_QUEUE_FAMILY_EXTERNAL`，表示硬件缓冲区来自外部队列族。注释提到 `VK_QUEUE_FAMILY_FOREIGN_EXT` 可能更正确，但当前 Adreno GPU 不支持。

### Android Framework 特殊标记

```cpp
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
imageInfo.fPartOfSwapchainOrAndroidWindow = fromAndroidWindow;
#endif
```

在 Android Framework 构建中，标记图像是否属于 swapchain 或 Android 窗口。

## 依赖关系

**Vulkan**:
- `include/gpu/ganesh/vk/GrVkBackendSurface.h` — Vulkan 后端表面
- `include/gpu/ganesh/vk/GrVkTypes.h` — `GrVkImageInfo`
- `include/gpu/vk/VulkanTypes.h` — `VulkanYcbcrConversionInfo`
- `src/gpu/ganesh/vk/GrVkCaps.h` — Vulkan 能力查询
- `src/gpu/ganesh/vk/GrVkGpu.h` — Vulkan GPU 实现
- `src/gpu/vk/VulkanUtilsPriv.h` — `GetAHardwareBufferProperties`, `AllocateAndBindImageMemory`

**Android**:
- `<android/hardware_buffer.h>` — AHardwareBuffer API

## 设计模式与设计决策

1. **外部格式回退**: 当已知 VkFormat 不支持必要特性时，自动回退到外部格式导入。这确保了对各种 Android 设备和驱动的最大兼容性。

2. **RAII 资源管理**: `VulkanCleanupHelper` 通过 RAII 确保 VkImage 和 VkDeviceMemory 在回调触发时正确释放。

3. **间接函数调用**: 通过 `VK_CALL` 宏使用函数指针表，支持 Vulkan 动态加载和不同版本的 API。

4. **丰富的错误日志**: 使用 `SKIA_LOG_E` 在关键错误点输出详细的诊断信息，包含 VkFormat 值等具体参数。

5. **条件 API 级别**: `R10G10B10A10_UNORM` (API 34) 和 `R8_UNORM` (API 33) 仅在对应 API 级别下编译。

## 性能考量

- 硬件缓冲区导入操作是一次性的，VkImage 创建和内存绑定涉及驱动级操作。
- 使用 `VK_IMAGE_TILING_OPTIMAL` 最大化 GPU 纹理访问性能。
- 外部格式导入可能比已知格式慢，因为需要额外的 YCbCr 采样器转换。
- `VK_QUEUE_FAMILY_EXTERNAL` 可能触发队列族所有权转移操作。
- 保护内容 (`VK_IMAGE_CREATE_PROTECTED_BIT`) 在支持的设备上启用 DRM 保护。

## 相关文件

- `src/gpu/ganesh/GrAHardwareBufferUtils.cpp` — 分发层，路由到本文件
- `src/gpu/ganesh/gl/AHardwareBufferGL.cpp` — OpenGL 版本的对应实现
- `src/gpu/ganesh/vk/GrVkGpu.h` — Vulkan GPU 接口
- `src/gpu/ganesh/vk/GrVkCaps.h` — Vulkan 能力查询
- `src/gpu/vk/VulkanUtilsPriv.h` — Vulkan 工具函数
- `src/gpu/ganesh/surface/SkSurface_AndroidFactories.cpp` — Android Surface 工厂
