# include/private/gpu/vk - Vulkan 私有头文件

## 概述

`include/private/gpu/vk` 目录包含 Skia Vulkan 后端的私有头文件。当前该目录仅包含一个核心文件 `SkiaVulkan.h`，它作为 Skia 内部引用 Vulkan API 头文件的统一入口点。该文件解决了 Vulkan 头文件引用的平台差异性问题，根据构建配置决定使用 Skia 内置的 Vulkan 头文件还是系统提供的头文件。

Vulkan 是 Skia 支持的主要 GPU 后端之一，提供了低开销、跨平台的 GPU 访问能力。Skia 的 Vulkan 后端（通过 Ganesh 和 Graphite 两个渲染引擎）利用 Vulkan API 实现高效的 2D 图形渲染，包括纹理管理、着色器编译、命令缓冲区录制和同步原语操作等功能。

`SkiaVulkan.h` 的设计考虑了多种构建场景：标准 Skia 构建使用 `include/third_party/vulkan/` 目录中内置的 Vulkan 头文件（通过 `SK_USE_INTERNAL_VULKAN_HEADERS` 宏控制），而 Google3（Google 内部构建系统）等环境则使用系统路径下的 Vulkan 头文件。此外，在 Android 平台上（`SK_BUILD_FOR_ANDROID`），该文件还会额外引入 `vulkan_android.h` 以获取 Android 扩展支持，包括外部内存导入等关键功能。

此统一入口机制确保了 Skia 代码库中对 Vulkan 类型和函数的引用方式一致，避免了头文件路径的分散和冗余。

## 目录结构

```
include/private/gpu/vk/
├── SkiaVulkan.h     # Skia 统一 Vulkan 头文件引入点
└── BUILD.bazel      # Bazel 构建配置
```

## 关键类与函数

### SkiaVulkan.h - Vulkan 头文件统一入口

该文件不定义新的类或函数，而是通过条件编译有选择地引入正确的 Vulkan 头文件：

- **标准构建路径** (`SK_USE_INTERNAL_VULKAN_HEADERS` && !`SK_BUILD_FOR_GOOGLE3`):
  - 引入 `include/third_party/vulkan/vulkan/vulkan_core.h` - Vulkan 核心 API 定义
  - 在 Android 上额外引入 `include/third_party/vulkan/vulkan/vulkan_android.h` - Android Vulkan 扩展

- **Google3/系统路径**:
  - 引入 `<vulkan/vulkan_core.h>` - 系统 Vulkan 核心头文件
  - 在 Android 上额外引入 `<vulkan/vulkan_android.h>` - 系统 Android Vulkan 扩展

### 引入的关键 Vulkan 类型
通过此头文件间接可用的 Vulkan 核心类型包括：
- **`VkInstance`/`VkDevice`/`VkPhysicalDevice`**: Vulkan 实例、逻辑设备和物理设备句柄
- **`VkQueue`/`VkCommandBuffer`**: 命令队列和命令缓冲区
- **`VkImage`/`VkImageView`/`VkBuffer`**: 图像、图像视图和缓冲区资源
- **`VkSemaphore`/`VkFence`**: 同步原语
- **`VkFormat`**: 纹理格式枚举
- **`VkRenderPass`/`VkFramebuffer`**: 渲染通道和帧缓冲区

### Android 扩展支持
在 Android 平台上，额外引入的 `vulkan_android.h` 提供：
- **`VkAndroidHardwareBufferPropertiesANDROID`**: Android 硬件缓冲区属性查询
- **`VkImportAndroidHardwareBufferInfoANDROID`**: 导入 AHardwareBuffer 到 Vulkan
- **`VkAndroidHardwareBufferFormatPropertiesANDROID`**: 硬件缓冲区格式属性
- **`VK_ANDROID_external_memory_android_hardware_buffer`**: 外部内存扩展

### 编译控制宏
- **`SK_USE_INTERNAL_VULKAN_HEADERS`**: 控制是否使用 Skia 内置的 Vulkan 头文件。在标准 Skia 构建中默认定义。
- **`SK_BUILD_FOR_GOOGLE3`**: Google 内部构建标识。定义此宏时即使 `SK_USE_INTERNAL_VULKAN_HEADERS` 被定义也使用系统路径。
- **`SK_BUILD_FOR_ANDROID`**: Android 平台构建标识。定义此宏时额外引入 Android Vulkan 扩展头文件。

### IWYU Pragma 说明
文件使用 `// IWYU pragma: begin_exports` 和 `// IWYU pragma: end_exports` 标记，告知 Include-What-You-Use 工具将此文件视为这些 Vulkan 头文件的导出点。这意味着包含 `SkiaVulkan.h` 的代码不需要再单独包含 `vulkan_core.h` 或 `vulkan_android.h`。

### Skia 中 Vulkan 的使用场景
Skia 的 Vulkan 后端在以下场景中使用本头文件引入的 Vulkan 类型：
- **纹理管理**: `VkImage`、`VkImageView`、`VkFormat` 用于 GPU 纹理的创建和管理
- **命令录制**: `VkCommandBuffer`、`VkRenderPass` 用于绘制命令的录制和提交
- **同步**: `VkSemaphore`、`VkFence` 用于 GPU/CPU 之间以及不同 GPU 队列之间的同步
- **内存管理**: `VkDeviceMemory`、`VkBuffer` 用于 GPU 内存的分配和缓冲区操作
- **Android 互操作**: `VkAndroidHardwareBufferPropertiesANDROID` 用于 AHardwareBuffer 导入

## 依赖关系

- **上游依赖**: `include/core/SkTypes.h`（平台检测）、`include/third_party/vulkan/`（内置 Vulkan 头文件）或系统 Vulkan SDK
- **下游消费者**: `include/gpu/vk/`（Vulkan 公共 API）、`src/gpu/vk/`（Vulkan 后端实现）、`src/gpu/ganesh/vk/`（Ganesh Vulkan 实现）、`src/gpu/graphite/vk/`（Graphite Vulkan 实现）、`include/android/`（Android Vulkan 集成）
- **同级目录**: `include/private/gpu/ganesh/`（Ganesh GPU 私有类型）

## 相关文档与参考

- [Vulkan 规范](https://www.vulkan.org/learn) - Khronos Group 官方 Vulkan 文档
- [Skia Vulkan 后端](https://skia.org/docs/user/api/skcanvas_overview/#vulkan) - Skia Vulkan 使用指南
- [Android Vulkan](https://developer.android.com/ndk/guides/graphics/getting-started) - Android NDK Vulkan 开发
- `include/third_party/vulkan/` - Skia 内置 Vulkan 头文件
- `include/gpu/vk/` - Skia Vulkan 公共 API
- `include/android/vk/` - Android Vulkan 内存分配器
- `src/gpu/vk/` - Vulkan 后端实现源码
- `include/android/vk/AndroidVulkanMemoryAllocator.h` - Android Vulkan 内存分配器

## 使用注意事项

### 头文件引用规范
Skia 内部代码在需要使用 Vulkan 类型时，应始终通过 `SkiaVulkan.h` 引入，而不是直接包含 `vulkan_core.h` 或其他 Vulkan 头文件。这确保了跨平台和跨构建系统的一致性。正确的引用方式为：
```cpp
#include "include/private/gpu/vk/SkiaVulkan.h"
```

### 版本同步
当 Skia 需要使用新的 Vulkan API 特性时，需要先更新 `include/third_party/vulkan/` 中的头文件到足够新的版本。`SkiaVulkan.h` 本身不需要修改，因为它只是一个转发层。

### 与 Dawn 的关系
Skia 的 Graphite 引擎也可以通过 Dawn（WebGPU 的 Vulkan 后端实现）间接使用 Vulkan。在这种情况下，Vulkan 头文件的引入由 Dawn 管理，而非通过 `SkiaVulkan.h`。本文件仅服务于 Skia 直接使用 Vulkan API 的场景。

### Vulkan 版本支持
Skia 的 Vulkan 后端要求至少支持 Vulkan 1.1。当前内置的头文件支持到 Vulkan 1.4（`VK_HEADER_VERSION 313`）。较新的 Vulkan 特性可能通过扩展（而非核心版本升级）来使用，具体取决于目标平台的驱动支持情况。在 Android 平台上，Vulkan 1.1 从 Android 10（API Level 29）开始广泛支持。Skia 会在运行时检测设备支持的 Vulkan 版本和扩展，并据此调整渲染策略。对于不支持某些可选扩展的设备，Skia 会自动回退到兼容的代码路径。

Skia 在 Android 上常用的 Vulkan 扩展包括 `VK_ANDROID_external_memory_android_hardware_buffer`（AHardwareBuffer 导入）和 `VK_KHR_external_semaphore`（跨进程同步）。
