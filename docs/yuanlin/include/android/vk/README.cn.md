# include/android/vk - Android Vulkan 专用接口

## 概述

`include/android/vk` 目录包含 Skia 在 Android 平台上使用 Vulkan 图形 API 时的专用接口。当前该目录仅包含 `AndroidVulkanMemoryAllocator.h` 一个头文件，提供了为 Android 平台定制的 Vulkan 内存分配器实现。

Vulkan 与 OpenGL/OpenGL ES 的一个重要区别在于 Vulkan 要求应用程序自行管理 GPU 内存分配。这意味着应用程序需要查询内存类型、分配设备内存、管理内存池、处理内存碎片等复杂任务。Skia 通过 `skgpu::VulkanMemoryAllocator` 抽象接口将这一职责封装起来，而本目录中的 `AndroidVulkanMemoryAllocator.h` 则为 Android 平台提供了一个开箱即用的具体实现。

该内存分配器基于 Vulkan Memory Allocator（VMA）库实现，使用了一组针对 Android 平台优化的硬编码配置参数。Android Framework 可以直接使用此实现来快速集成 Skia 的 Vulkan 后端，也可以选择实现自定义的 `skgpu::VulkanMemoryAllocator` 以获得更精细的内存控制。

`SkiaVMA` 命名空间下的接口设计简洁明了，通过 `Options` 结构体提供最基本的配置选项（如线程安全性），使得集成方可以以最小的代码量启用 Vulkan 内存管理。

## 目录结构

```
include/android/vk/
└── AndroidVulkanMemoryAllocator.h   # Android Vulkan 内存分配器工厂
```

## 关键类与函数

### SkiaVMA 命名空间

- **`SkiaVMA::Options`**: 内存分配器配置选项结构体。
  - `fThreadSafe` (`bool`, 默认 `true`): 是否启用线程安全模式。当设为 `true` 时，分配器内部会使用互斥锁保护共享状态，允许从多个线程并发进行内存分配和释放操作。在单线程使用场景下可设为 `false` 以提升性能。

- **`SkiaVMA::Make()`**: 工厂函数，创建并返回 Android 平台的 Vulkan 内存分配器实例。
  - **参数**:
    - `const skgpu::VulkanBackendContext&`: Vulkan 后端上下文，包含 VkInstance、VkPhysicalDevice、VkDevice 等 Vulkan 核心对象的引用，分配器需要这些信息来查询设备内存属性和执行内存分配。
    - `Options`: 分配器配置选项。
  - **返回值**: `sk_sp<skgpu::VulkanMemoryAllocator>`，智能指针管理的内存分配器实例。
  - **实现细节**: 内部使用 VMA（Vulkan Memory Allocator）库，配置了适合 Android 设备的默认参数。

### skgpu::VulkanMemoryAllocator（接口类）

`SkiaVMA::Make()` 返回的对象实现了以下核心接口（定义在 `include/gpu/vk/` 中）：
- **内存分配**: 根据缓冲区或图像的内存需求分配设备内存
- **内存映射**: 将 GPU 内存映射到 CPU 地址空间（用于数据上传/下载）
- **内存释放**: 释放不再使用的 GPU 内存
- **内存统计**: 查询当前内存使用情况

### 使用模式

```
典型的集成流程：
1. 创建 VulkanBackendContext（包含 VkInstance、VkDevice 等）
2. 调用 SkiaVMA::Make() 创建内存分配器
3. 将分配器设置到 VulkanBackendContext 中
4. 使用该上下文创建 Skia 的 GPU 上下文（GrDirectContext 或 graphite::Context）
5. 分配器在 Skia 内部自动被用于所有 Vulkan 内存操作
```

### 与自定义分配器的关系
- Android Framework 可以选择不使用此默认实现，转而实现自定义的 `skgpu::VulkanMemoryAllocator`
- 自定义实现可以集成到 Android 的全局内存管理策略中，例如与低内存杀手（Low Memory Killer）协调
- 如果 Framework 决定自定义实现，只需停止调用 `SkiaVMA::Make()` 即可

### VMA 库简介
Vulkan Memory Allocator (VMA) 是 AMD GPUOpen 开源的 Vulkan 内存管理库，Skia 在 `third_party/vulkanmemoryallocator/` 目录中包含了该库的副本。VMA 提供以下核心功能：
- **内存池管理**: 将多个小分配合并到少量大的 `VkDeviceMemory` 分配中，减少驱动开销
- **自动内存类型选择**: 根据使用需求自动选择最优的内存类型（设备本地、主机可见等）
- **碎片整理**: 对已分配的内存进行碎片整理，提高内存利用率
- **统计与调试**: 提供详细的内存使用统计和泄漏检测工具

### 线程安全性考量
`Options::fThreadSafe` 参数控制 VMA 内部的互斥锁行为：
- **`true`（默认）**: VMA 内部使用互斥锁保护所有共享数据结构，允许从多线程并发调用 `vmaAllocateMemory`、`vmaFreeMemory` 等函数。这是 Android Framework 的典型使用模式，因为渲染命令录制和内存管理可能发生在不同线程。
- **`false`**: 禁用内部互斥锁，所有操作必须由调用者保证线程安全。适用于确认所有 Vulkan 操作都在单一线程上执行的场景，可减少锁竞争开销。

## 依赖关系

- **上游依赖**: `include/core/SkRefCnt.h`、`include/private/base/SkAPI.h`
- **GPU 依赖**: `skgpu::VulkanBackendContext`（Vulkan 上下文定义）、`skgpu::VulkanMemoryAllocator`（内存分配器接口）
- **实现依赖**: VMA（Vulkan Memory Allocator）第三方库（在 `third_party/` 中）
- **平台依赖**: Vulkan SDK / Android NDK Vulkan 支持
- **下游消费者**: Android Framework 的 Vulkan 渲染路径

## 相关文档与参考

- [Vulkan Memory Allocator](https://gpuopen.com/vulkan-memory-allocator/) - AMD GPUOpen VMA 库文档
- [Vulkan 内存管理](https://www.vulkan.org/learn#memory-management) - Vulkan 官方内存管理指南
- [Android Vulkan 开发](https://developer.android.com/ndk/guides/graphics/getting-started) - Android NDK Vulkan 指南
- `include/gpu/vk/` - Skia Vulkan 公共 API（包含 VulkanMemoryAllocator 接口定义）
- `include/android/` - Android 平台 API 总目录
- `include/private/gpu/vk/` - Vulkan 私有头文件
- `third_party/vulkanmemoryallocator/` - VMA 库源码

## 使用注意事项

### 集成步骤
在 Android 项目中集成 Skia Vulkan 内存分配器的典型步骤：
```
1. 初始化 Vulkan 实例和设备
2. 构建 skgpu::VulkanBackendContext 结构
3. 调用 SkiaVMA::Make(backendContext, options) 获取分配器
4. 将分配器赋值给 backendContext.fMemoryAllocator
5. 使用配置好的 backendContext 创建 Skia GPU 上下文
```

### 内存压力处理
在 Android 设备上运行时，应注意 GPU 内存压力管理。VMA 分配器会尽量复用已释放的内存块，但在内存紧张时可能需要：
- 释放未使用的 Skia 资源（通过 `GrDirectContext::freeGpuResources()`）
- 降低纹理缓存大小
- 响应 Android 的 `onTrimMemory()` 回调
