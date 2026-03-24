# include/third_party/vulkan - Vulkan SDK 第三方头文件

## 概述

`include/third_party/vulkan` 目录包含 Skia 内置的 Vulkan SDK 头文件副本。这些头文件来源于 Khronos Group 官方的 Vulkan 头文件仓库，Skia 将其内置以确保在没有系统 Vulkan SDK 的环境中也能正常编译 Vulkan 后端。这些头文件遵循 Apache 2.0 许可证。

Skia 通过 `SK_USE_INTERNAL_VULKAN_HEADERS` 预处理器宏控制是否使用这些内置头文件。在标准 Skia 构建中（非 Google3 环境），默认使用此目录中的头文件。当 Skia 作为外部库被集成到拥有自己 Vulkan SDK 的项目中时，可以通过不定义该宏来使用系统路径下的 Vulkan 头文件。

当前内置的 Vulkan 头文件版本为 1.4，头文件版本号为 313（`VK_HEADER_VERSION 313`）。这些头文件定义了 Vulkan 的完整 API，包括核心 API、各平台扩展（Android、Windows、macOS/iOS、Linux/X11/Wayland 等）、视频编解码扩展以及加载器/驱动接口（ICD）和验证层接口。

目录结构分为两层：外层包含 `BUILD.bazel`、`LICENSE`（Apache 2.0 许可证）和 `vulkan` 子目录，内层 `vulkan/` 子目录包含实际的 Vulkan 头文件。Skia 的 Vulkan 后端（通过 `include/private/gpu/vk/SkiaVulkan.h`）主要引用 `vulkan_core.h`，在 Android 平台上额外引用 `vulkan_android.h`。

这些头文件由 Khronos Group 从 Vulkan XML 规范自动生成，Skia 通过定期同步确保与最新 Vulkan 规范保持一致。如果 Skia 需要使用新的 Vulkan 特性，需要先更新这些头文件。

## 目录结构

```
include/third_party/vulkan/
├── BUILD.bazel                     # Bazel 构建配置
├── LICENSE                         # Apache 2.0 许可证
└── vulkan/                         # Vulkan 头文件目录
    ├── vulkan.h                    # Vulkan 主入口（包含核心及平台扩展）
    ├── vulkan_core.h               # Vulkan 核心 API 定义（最重要）
    ├── vk_platform.h               # 平台相关调用约定和类型
    ├── vk_icd.h                    # 加载器-驱动 (ICD) 接口
    ├── vk_layer.h                  # 加载器-验证层接口
    ├── vulkan_android.h            # Android 平台扩展
    ├── vulkan_beta.h               # Beta 扩展（试验性功能）
    ├── vulkan_directfb.h           # DirectFB 平台扩展
    ├── vulkan_fuchsia.h            # Fuchsia 平台扩展
    ├── vulkan_ggp.h                # Google Games Platform 扩展
    ├── vulkan_ios.h                # iOS 平台扩展（MoltenVK）
    ├── vulkan_macos.h              # macOS 平台扩展（MoltenVK）
    ├── vulkan_metal.h              # Metal 互操作扩展
    ├── vulkan_screen.h             # QNX Screen 平台扩展
    ├── vulkan_vi.h                 # Nintendo 平台扩展
    ├── vulkan_wayland.h            # Wayland 平台扩展
    ├── vulkan_win32.h              # Windows 平台扩展
    ├── vulkan_xcb.h                # XCB（X11）平台扩展
    ├── vulkan_xlib.h               # Xlib（X11）平台扩展
    ├── vulkan_xlib_xrandr.h        # Xlib+XRandR 扩展
    └── vk_video/                   # 视频编解码扩展
        ├── vulkan_video_codecs_common.h      # 视频编解码通用定义
        ├── vulkan_video_codec_h264std.h      # H.264 标准定义
        ├── vulkan_video_codec_h264std_decode.h  # H.264 解码
        ├── vulkan_video_codec_h264std_encode.h  # H.264 编码
        ├── vulkan_video_codec_h265std.h      # H.265/HEVC 标准定义
        ├── vulkan_video_codec_h265std_decode.h  # H.265 解码
        ├── vulkan_video_codec_h265std_encode.h  # H.265 编码
        ├── vulkan_video_codec_av1std.h       # AV1 标准定义
        ├── vulkan_video_codec_av1std_decode.h   # AV1 解码
        └── vulkan_video_codec_av1std_encode.h   # AV1 编码
```

## 关键类与函数

### vulkan_core.h - Vulkan 核心 API
这是最重要的文件，定义了 Vulkan 的全部核心类型和函数：

- **版本信息**:
  - `VK_API_VERSION_1_0` / `VK_API_VERSION_1_1` / `VK_API_VERSION_1_2` / `VK_API_VERSION_1_3`: Vulkan API 版本宏
  - `VK_HEADER_VERSION`: 当前头文件版本号（313）
  - `VK_MAKE_API_VERSION(variant, major, minor, patch)`: 版本号构造宏

- **核心句柄类型**: `VkInstance`、`VkPhysicalDevice`、`VkDevice`、`VkQueue`、`VkCommandBuffer`、`VkBuffer`、`VkImage`、`VkSemaphore`、`VkFence`、`VkDeviceMemory`、`VkRenderPass`、`VkPipeline`、`VkDescriptorSet` 等

- **核心枚举**: `VkFormat`（像素格式）、`VkImageUsageFlagBits`（图像用途标志）、`VkMemoryPropertyFlagBits`（内存属性）、`VkPipelineStageFlagBits`（管线阶段）等

### vk_platform.h - 平台调用约定
- **`VKAPI_ATTR`/`VKAPI_CALL`/`VKAPI_PTR`**: 平台相关的函数调用约定宏
  - Windows: 使用 `__stdcall`
  - Android ARM32: 使用 `__attribute__((pcs("aapcs-vfp")))` 硬浮点调用约定
  - 其他平台: 使用默认调用约定

### vk_icd.h - 驱动接口
- **`CURRENT_LOADER_ICD_INTERFACE_VERSION`**: 当前 ICD 接口版本（7）
- 定义了 Vulkan 加载器与驱动程序（ICD）之间的协商接口

### vk_layer.h - 验证层接口
- **`CURRENT_LOADER_LAYER_INTERFACE_VERSION`**: 当前层接口版本（2）
- 定义了 Vulkan 加载器与验证层之间的接口，包括 `VkNegotiateLayerInterface` 结构体

### vulkan_android.h - Android 扩展
- **`VK_ANDROID_external_memory_android_hardware_buffer`**: 从 AHardwareBuffer 导入 Vulkan 内存
- **`VkAndroidHardwareBufferPropertiesANDROID`**: AHardwareBuffer 的 Vulkan 属性查询结构

### vk_video/ - 视频编解码
- 支持 H.264、H.265/HEVC 和 AV1 三种编解码标准
- 每种标准提供通用定义、编码和解码三个头文件

## 依赖关系

- **上游来源**: [Khronos Vulkan-Headers](https://github.com/KhronosGroup/Vulkan-Headers) - 官方 Vulkan 头文件仓库
- **被引用于**: `include/private/gpu/vk/SkiaVulkan.h`（Skia 内部的 Vulkan 头文件入口）
- **下游消费者**: `include/gpu/vk/`（Vulkan 公共 API）、`src/gpu/vk/`（Vulkan 后端实现）、`src/gpu/ganesh/vk/`（Ganesh Vulkan）、`src/gpu/graphite/vk/`（Graphite Vulkan）
- **控制宏**: `SK_USE_INTERNAL_VULKAN_HEADERS`（使用内置头文件）、`SK_BUILD_FOR_GOOGLE3`（Google 内部构建）

## 相关文档与参考

- [Vulkan 规范](https://registry.khronos.org/vulkan/) - Khronos 官方 Vulkan 规范
- [Vulkan-Headers GitHub](https://github.com/KhronosGroup/Vulkan-Headers) - 官方头文件仓库
- [Vulkan Tutorial](https://vulkan-tutorial.com/) - Vulkan 入门教程
- [Vulkan 视频扩展](https://www.khronos.org/blog/an-introduction-to-vulkan-video) - 视频编解码扩展介绍
- `include/private/gpu/vk/SkiaVulkan.h` - Skia 内部 Vulkan 引用入口
- `include/gpu/vk/` - Skia Vulkan 公共 API
- `include/android/vk/` - Android Vulkan 内存分配器
