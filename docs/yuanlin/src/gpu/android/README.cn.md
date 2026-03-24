# android - Skia GPU Android 平台工具

## 概述

`src/gpu/android` 目录包含 Skia 图形库中 Android 平台特定的 GPU 工具代码。这些代码处理 Android 平台上独有的图形资源类型,主要是 `AHardwareBuffer` 的格式转换以及 Android 平台上 Vulkan 内存分配器的便捷创建接口。

`AHardwareBuffer` (AHB) 是 Android NDK 中的一个关键概念,它代表了可在多个 Android 系统组件之间共享的 GPU 内存缓冲区,包括相机、媒体编解码器、Surface 合成器和 GPU 渲染器。Skia 需要能够将 AHardwareBuffer 作为纹理源或渲染目标使用,这就要求在 AHB 的像素格式与 Skia 的内部颜色类型之间进行转换。

`AHardwareBufferUtils.cpp` 提供了 `GetSkColorTypeFromBufferFormat()` 函数,将 AHardwareBuffer 的格式代码(`AHARDWAREBUFFER_FORMAT_*`)映射为对应的 `SkColorType`。这个转换涵盖了 Android 平台常见的像素格式,包括 RGBA_8888、RGB_565、RGBA_F16、RGBA_1010102 等。对于无法直接映射的外部格式(如 YUV 格式),返回 `kExternalFormatColorType`,表示该纹理只能作为外部纹理使用。

`AndroidVulkanMemoryAllocator.cpp` 则提供了 `SkiaVMA::Make()` 函数,这是一个面向 Android 平台的简化 Vulkan 内存分配器创建入口。它将 Android 端的选项参数(`Options`)转换为 Skia 内部的 `ThreadSafe` 枚举,然后委托给 `VulkanMemoryAllocators::Make()` 完成实际创建。

这两个文件分别服务于不同的子系统:AHardwareBuffer 工具被 Ganesh 和 Graphite 的 GL/Vulkan 后端共同使用,而 Vulkan 内存分配器入口则专门为 Vulkan 后端服务。两者共同构成了 Skia 在 Android 平台上与 GPU 交互的基础工具层。

该目录的代码依赖于 Android NDK API level 26 及以上版本(AHardwareBuffer 在 API 26 引入),部分功能(如 `R8_UNORM` 和 `R10G10B10A10_UNORM` 格式)需要更高的 API level(分别为 33 和 34)。

## 架构图

```
+----------------------------------------------------------+
|            Android 应用 / 系统组件                        |
|  (Camera, MediaCodec, SurfaceFlinger, ...)               |
+----------------------------------------------------------+
        |                              |
        v                              v
+------------------+    +---------------------------+
| AHardwareBuffer  |    | Vulkan on Android         |
| (共享GPU内存)    |    | (设备, 实例, 队列)         |
+-------+----------+    +-------------+-------------+
        |                              |
+-------v----------+    +-------------v-------------+
| AHardwareBuffer  |    | AndroidVulkanMemory       |
| Utils.cpp        |    | Allocator.cpp             |
|                  |    |                           |
| 格式映射:        |    | SkiaVMA::Make()           |
| AHARDWAREBUFFER  |    |   --> VulkanMemory        |
| _FORMAT_* -->    |    |       Allocators::Make()  |
| SkColorType      |    +-------------+-------------+
+-------+----------+                  |
        |                  +-----------v-----------+
        v                  | VulkanAMDMemory       |
+------------------+       | Allocator (VMA封装)   |
| Skia 渲染管线    |       +-----------------------+
| (Ganesh/Graphite)|
| 使用 AHB 作为   |
| 纹理源/渲染目标  |
+------------------+
```

## 目录结构

```
src/gpu/android/
|-- BUILD.bazel                          # Bazel 构建配置
|-- AHardwareBufferUtils.cpp             # AHardwareBuffer 格式转换工具
|-- AndroidVulkanMemoryAllocator.cpp     # Android Vulkan 内存分配器入口
```

## 关键类与函数

### `GetSkColorTypeFromBufferFormat()` (AHardwareBufferUtils.cpp)

将 Android `AHardwareBuffer` 的像素格式转换为 Skia 的 `SkColorType`:

```cpp
namespace AHardwareBufferUtils {
SkColorType GetSkColorTypeFromBufferFormat(uint32_t bufferFormat);
}
```

**完整格式映射表:**

| AHardwareBuffer 格式 | SkColorType | Android API |
|-----------------------|-------------|-------------|
| `AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM` | `kRGBA_8888_SkColorType` | 26+ |
| `AHARDWAREBUFFER_FORMAT_R8G8B8X8_UNORM` | `kRGB_888x_SkColorType` | 26+ |
| `AHARDWAREBUFFER_FORMAT_R16G16B16A16_FLOAT` | `kRGBA_F16_SkColorType` | 26+ |
| `AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM` | `kRGB_565_SkColorType` | 26+ |
| `AHARDWAREBUFFER_FORMAT_R8G8B8_UNORM` | `kRGB_888x_SkColorType` | 26+ |
| `AHARDWAREBUFFER_FORMAT_R10G10B10A2_UNORM` | `kRGBA_1010102_SkColorType` | 26+ |
| `AHARDWAREBUFFER_FORMAT_R8_UNORM` | `kAlpha_8_SkColorType` | 33+ |
| `AHARDWAREBUFFER_FORMAT_R10G10B10A10_UNORM` | `kRGBA_10x6_SkColorType` | 34+ |
| 其他(未知/YUV等) | `kExternalFormatColorType` | - |

**关于 `kExternalFormatColorType`**: 当 AHardwareBuffer 的格式无法直接映射到标准 Skia 颜色类型时(例如 YUV 格式),返回此特殊值。这些纹理只能通过外部纹理(OES)机制使用,不支持直接读取像素数据。

**API 版本条件编译**: 部分格式使用 `#if __ANDROID_API__ >= XX` 进行条件编译,确保只在支持该格式的 Android 版本上编译相关代码。

### `SkiaVMA::Make()` (AndroidVulkanMemoryAllocator.cpp)

Android 平台的 Vulkan 内存分配器便捷创建函数:

```cpp
namespace SkiaVMA {
sk_sp<skgpu::VulkanMemoryAllocator> Make(
    const skgpu::VulkanBackendContext& ctx,
    Options opts);
}
```

**`Options` 结构体** (定义在 `include/android/vk/AndroidVulkanMemoryAllocator.h`):
- `fThreadSafe` - 是否需要线程安全的内存分配

**实现流程**:
```cpp
sk_sp<skgpu::VulkanMemoryAllocator> Make(
    const skgpu::VulkanBackendContext& ctx, Options opts) {
    skgpu::ThreadSafe threadSafe =
        opts.fThreadSafe ? skgpu::ThreadSafe::kYes : skgpu::ThreadSafe::kNo;
    return skgpu::VulkanMemoryAllocators::Make(ctx, threadSafe);
}
```

该函数是 `skgpu::VulkanMemoryAllocators::Make()` 的薄封装,将 Android 端的布尔参数转换为 Skia 内部的 `ThreadSafe` 枚举类型。最终创建的是基于 AMD VMA 的 `VulkanAMDMemoryAllocator` 实例。

## 依赖关系

```
src/gpu/android/ 依赖:
  +-- <android/hardware_buffer.h> (Android NDK, API 26+)
  +-- include/android/AHardwareBufferUtils.h (公共AHB工具接口)
  +-- include/android/vk/AndroidVulkanMemoryAllocator.h (Android VMA入口)
  +-- include/gpu/vk/VulkanMemoryAllocator.h (内存分配器接口)
  +-- include/gpu/vk/VulkanBackendContext.h (Vulkan后端上下文)
  +-- src/gpu/GpuTypesPriv.h (GPU类型私有定义)
  +-- src/gpu/vk/vulkanmemoryallocator/VulkanMemoryAllocatorPriv.h (VMA工厂)

被以下模块使用:
  +-- src/gpu/ganesh/gl/ (Ganesh OpenGL后端, AHB纹理)
  +-- src/gpu/ganesh/vk/ (Ganesh Vulkan后端, AHB纹理+VMA)
  +-- src/gpu/graphite/vk/ (Graphite Vulkan后端)
  +-- Android 系统集成层
```

## 设计模式分析

### 1. 适配器模式 (Adapter Pattern)

`GetSkColorTypeFromBufferFormat()` 是典型的适配器,将 Android 平台的格式枚举 (`AHARDWAREBUFFER_FORMAT_*`) 适配为 Skia 内部的颜色类型枚举 (`SkColorType`)。这使得 Skia 的渲染管线无需了解 Android 特定的格式定义。

### 2. 外观模式 (Facade Pattern)

`SkiaVMA::Make()` 为 Android 开发者提供了一个简化的入口,隐藏了 Skia 内部 `ThreadSafe` 枚举、`VulkanBackendContext` 验证和 `VulkanInterface` 创建等复杂细节。开发者只需传入后端上下文和一个简单的选项结构体即可获得完整的内存分配器。

### 3. 平台适配层 (Platform Adaptation Layer)

该目录本身就是平台适配层的体现。所有 Android 特定代码被隔离在此目录中,通过条件编译(`__ANDROID_API__`)和构建系统配置确保不会影响非 Android 平台的编译。

### 4. 渐进增强 (Progressive Enhancement)

格式映射函数使用条件编译支持不同 Android API 版本:
- API 26+: 基础格式支持 (RGBA_8888, RGB_565 等)
- API 33+: 新增 R8_UNORM 支持
- API 34+: 新增 R10G10B10A10_UNORM 支持

这种设计确保了 Skia 在低版本 Android 上仍能正常工作,同时在高版本上利用新功能。

### 5. 默认回退策略

对于未知的 AHardwareBuffer 格式,`GetSkColorTypeFromBufferFormat()` 返回 `kExternalFormatColorType` 而非报错。代码注释解释道:由于这些纹理仅作为源使用,颜色类型不会影响 Skia 的纹理使用方式。唯一的潜在影响是在非 OES 绑定时 SKP 回读可能得到无效结果。

## 数据流

```
1. AHardwareBuffer 纹理导入流:
   Android 系统组件 (Camera/MediaCodec)
        |
   AHardwareBuffer 对象 (包含像素数据)
        |
   AHardwareBuffer_describe() 获取 bufferFormat
        |
   GetSkColorTypeFromBufferFormat(bufferFormat)
        |
   返回 SkColorType (如 kRGBA_8888_SkColorType)
        |
   Skia GPU 后端创建纹理包装:
        |-- Ganesh: GrAHardwareBufferUtils::MakeBackendTexture()
        |-- Graphite: 类似的纹理导入流程
        |
   纹理可用于 Skia 渲染管线

2. Android Vulkan 内存分配器创建流:
   Android 应用初始化 Vulkan
        |
   构建 VulkanBackendContext:
        |-- VkInstance, VkPhysicalDevice, VkDevice
        |-- VkQueue, getProc 回调
        |
   SkiaVMA::Make(ctx, {.fThreadSafe = true})
        |
   skgpu::VulkanMemoryAllocators::Make(ctx, ThreadSafe::kYes)
        |-- 创建 VulkanInterface (加载函数指针)
        |-- VulkanAMDMemoryAllocator::Make()
        |     |-- vmaCreateAllocator() (4MB块, Vulkan 1.1)
        |
   返回 sk_sp<VulkanMemoryAllocator>
        |
   传入 Ganesh/Graphite Context 创建

3. AHardwareBuffer Vulkan 互操作流 (在 src/gpu/vk/VulkanUtilsPriv.h 中定义):
   AHardwareBuffer 对象
        |
   GetAHardwareBufferProperties()
        |-- vkGetAndroidHardwareBufferPropertiesANDROID()
        |-- 获取 VkAndroidHardwareBufferFormatPropertiesANDROID
        |
   GetYcbcrConversionInfoFromFormatProps()
        |-- 提取 YCbCr 转换信息 (色彩模型/范围/色度位置)
        |-- 填充 VulkanYcbcrConversionInfo
        |
   AllocateAndBindImageMemory()
        |-- 选择兼容的内存类型
        |-- vkAllocateMemory() + vkBindImageMemory()
        |
   VkImage 可用于 Vulkan 渲染
```

## 相关文档与参考

- **Android AHardwareBuffer**: https://developer.android.com/ndk/reference/group/a-hardware-buffer
- **AHardwareBuffer 像素格式**: https://developer.android.com/ndk/reference/group/a-hardware-buffer#ahardwarebuffer_format
- **VK_ANDROID_external_memory_android_hardware_buffer**: Vulkan 扩展文档
- **Android NDK API levels**: API 26 (Android 8.0), API 33 (Android 13), API 34 (Android 14)
- **SkColorType 参考**: `include/core/SkColorType.h`
- **Vulkan 内存分配器接口**: `include/gpu/vk/VulkanMemoryAllocator.h`
- **VMA 集成详细文档**: `src/gpu/vk/vulkanmemoryallocator/` - AMD VMA 封装
- **Vulkan AHB 互操作工具**: `src/gpu/vk/VulkanUtilsPriv.h` 中的 Android 专用函数
- **Ganesh AHB 集成**: `src/gpu/ganesh/` 中的 AHardwareBuffer 纹理支持
- **公共 Android 头文件**: `include/android/` - 面向客户端的 Android API 接口
