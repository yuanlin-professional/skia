# surface - Surface 管理（Android 平台工厂）

## 概述

`src/gpu/graphite/surface/` 目录包含 Skia Graphite 后端中与 Surface 创建相关的平台特定工厂实现。当前该目录仅包含 Android 平台的 Surface 工厂函数 `Surface_AndroidFactories.cpp`，负责从 Android `AHardwareBuffer` 创建 Graphite 后端的 `SkSurface` 对象。

Surface 是 Skia 中绘制操作的目标抽象，在 Graphite 架构中，`SkSurface` 代表一个可以通过 `Recorder` 记录绘制命令并最终提交到 GPU 执行的渲染目标。与传统 Ganesh 后端不同，Graphite 的 Surface 生命周期与 GPU 预算管理紧密集成：当客户端持有 Surface 引用时，其底层 GPU 资源不计入预算；当 Surface 被释放后，底层 GPU 对象可能成为 scratch（可复用）资源并被计入预算。

Android 平台的 Surface 工厂函数 `WrapAndroidHardwareBuffer()` 实现了从 Android 硬件缓冲区（`AHardwareBuffer`）到 Skia 渲染表面的桥接。Android 硬件缓冲区是一种跨进程共享的 GPU 内存抽象，广泛用于 Android 的窗口系统（SurfaceFlinger）、相机、视频解码器等子系统。通过该工厂函数，Skia 能够直接将渲染输出写入 Android 的图形管线，避免不必要的内存拷贝。

该工厂函数内部首先验证硬件缓冲区的有效性和兼容性（必须同时支持 `GPU_COLOR_OUTPUT` 和 `GPU_SAMPLED_IMAGE` 用途标志），然后通过 `Recorder::createBackendTexture()` 将硬件缓冲区包装为后端纹理，最后调用通用的 `SkSurfaces::WrapBackendTexture()` 完成 Surface 的创建。该函数还处理了受保护内容（`AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT`）和来自窗口的缓冲区（`fromWindow`）等 Android 特有的场景。

跨平台的 Surface 创建接口（如 `SkSurfaces::RenderTarget()` 和 `SkSurfaces::WrapBackendTexture()`）定义在 `include/gpu/graphite/Surface.h` 中。这些接口提供了创建独立渲染目标和包装已有后端纹理两种方式。Graphite 的 Surface API 相比传统 API 有一项重要变更：不再支持写时复制（copy-on-write）行为。创建 Surface 的图像快照时，客户端必须显式选择是共享底层资源（`AsImage()`）还是创建副本（`AsImageCopy()`）。

Surface 管理模块虽然当前代码量较小，但它在 Graphite 架构中扮演着连接平台图形系统与 Skia 渲染管线的关键桥梁角色。随着 Graphite 对更多平台的支持扩展，预计该目录将包含更多平台特定的 Surface 工厂实现。

## 架构图

```
  平台图形系统                    Skia Graphite 渲染管线
  ============                    ====================

  +------------------+
  | AHardwareBuffer  |  <-- Android 硬件缓冲区
  | - width, height  |
  | - format         |
  | - usage flags    |
  +--------+---------+
           |
           | WrapAndroidHardwareBuffer()
           v
  +------------------+
  | 验证与配置         |
  | - 检查 usage 标志 |
  | - 检查格式兼容性   |
  | - 检测受保护内容   |
  +--------+---------+
           |
           v
  +------------------+
  | Recorder::       |
  | createBackend    |
  | Texture()        |  <-- 从 AHB 创建后端纹理
  +--------+---------+
           |
           v
  +------------------+         +-------------------+
  | BackendTexture   |         | SkSurfaces::      |
  | (Vulkan/Metal    |-------->| WrapBackendTexture|
  |  纹理句柄)       |         +--------+----------+
  +------------------+                  |
                                        v
                               +-------------------+
                               |    SkSurface      |
                               | (渲染目标)         |
                               +--------+----------+
                                        |
                               +--------+----------+
                               |    Recorder       |
                               | (记录绘制命令)     |
                               +--------+----------+
                                        |
                               +--------+----------+
                               |   Recording       |
                               | (GPU 命令快照)     |
                               +-------------------+

  Surface 创建方式总览:
  +------------------------------------------------------+
  |  SkSurfaces::RenderTarget()                          |
  |    -> 创建新的渲染目标（指定 ImageInfo）               |
  |                                                      |
  |  SkSurfaces::WrapBackendTexture()                    |
  |    -> 包装已有的后端纹理（跨平台通用）                 |
  |                                                      |
  |  SkSurfaces::WrapAndroidHardwareBuffer()             |
  |    -> Android 专用：从 AHardwareBuffer 创建           |
  +------------------------------------------------------+

  Surface 图像快照模式:
  +------------------------------------------------------+
  |  SkSurfaces::AsImage()                               |
  |    -> 共享底层纹理，客户端需管理内容一致性             |
  |                                                      |
  |  SkSurfaces::AsImageCopy()                           |
  |    -> 创建副本，支持子集裁剪和 mipmap 添加            |
  +------------------------------------------------------+
```

## 目录结构

```
src/gpu/graphite/surface/
|-- BUILD.bazel                          # Bazel 构建配置
|-- Surface_AndroidFactories.cpp         # Android AHardwareBuffer Surface 工厂实现
```

相关头文件（不在本目录中）:

```
include/gpu/graphite/Surface.h           # 跨平台 Surface 公共接口
include/android/graphite/SurfaceAndroid.h # Android Surface 公共接口
```

## 关键类与函数

### WrapAndroidHardwareBuffer()
Android 平台的核心工厂函数，从 AHardwareBuffer 创建 SkSurface。

```cpp
namespace SkSurfaces {

sk_sp<SkSurface> WrapAndroidHardwareBuffer(
    Recorder* recorder,                    // Graphite Recorder
    AHardwareBuffer* hardwareBuffer,       // Android 硬件缓冲区
    sk_sp<SkColorSpace> colorSpace,        // 颜色空间（可为 nullptr）
    const SkSurfaceProps* surfaceProps,     // Surface 属性（LCD 方向等）
    BufferReleaseProc releaseP,            // 缓冲区释放回调
    ReleaseContext releaseC,               // 释放回调上下文
    bool fromWindow);                      // 是否来自 Android Window

}  // namespace SkSurfaces
```

### RenderTarget()
创建新的独立渲染目标。

```cpp
namespace SkSurfaces {

sk_sp<SkSurface> RenderTarget(
    skgpu::graphite::Recorder*,
    const SkImageInfo& imageInfo,
    skgpu::Mipmapped = skgpu::Mipmapped::kNo,
    const SkSurfaceProps* surfaceProps = nullptr,
    std::string_view label = {});

}  // namespace SkSurfaces
```

### WrapBackendTexture()
包装已有的后端纹理为 SkSurface（两个重载版本）。

```cpp
namespace SkSurfaces {

// 新版本：颜色类型从后端纹理格式推导
sk_sp<SkSurface> WrapBackendTexture(
    skgpu::graphite::Recorder*,
    const skgpu::graphite::BackendTexture&,
    sk_sp<SkColorSpace> colorSpace,
    const SkSurfaceProps* props,
    TextureReleaseProc = nullptr,
    ReleaseContext = nullptr,
    std::string_view label = {});

// 旧版本（已废弃）：显式指定颜色类型
sk_sp<SkSurface> WrapBackendTexture(
    skgpu::graphite::Recorder*,
    const skgpu::graphite::BackendTexture&,
    SkColorType colorType,
    sk_sp<SkColorSpace> colorSpace,
    const SkSurfaceProps* props,
    TextureReleaseProc = nullptr,
    ReleaseContext = nullptr,
    std::string_view label = {});

}  // namespace SkSurfaces
```

### AsImage() / AsImageCopy()
Graphite 特有的 Surface 图像快照 API，替代传统的 `makeImageSnapshot()`。

```cpp
namespace SkSurfaces {

// 共享底层纹理（零拷贝，但客户端需保证内容一致性）
sk_sp<SkImage> AsImage(sk_sp<const SkSurface>);

// 创建副本（安全但有额外开销，支持子集和 mipmap）
sk_sp<SkImage> AsImageCopy(
    sk_sp<const SkSurface>,
    const SkIRect* subset = nullptr,
    skgpu::Mipmapped = skgpu::Mipmapped::kNo);

}  // namespace SkSurfaces
```

### AHardwareBuffer 验证逻辑
工厂函数内部的关键验证步骤：

```cpp
// 必须支持 GPU 颜色输出和采样
if (!SkToBool(bufferDesc.usage & AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT) ||
    !SkToBool(bufferDesc.usage & AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE) ||
    bufferDesc.format == AHARDWAREBUFFER_FORMAT_R8G8B8X8_UNORM) {
    // 拒绝不兼容的缓冲区
    return nullptr;
}

// 检测受保护内容标志
const bool isProtectedContent =
    SkToBool(bufferDesc.usage & AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT);
```

## 依赖关系

### 上游依赖（本目录依赖的模块）

| 模块 | 说明 |
|------|------|
| `include/gpu/graphite/Recorder.h` | Graphite Recorder，创建后端纹理 |
| `include/gpu/graphite/BackendTexture.h` | 后端纹理抽象 |
| `include/gpu/graphite/Surface.h` | 跨平台 Surface 接口 |
| `include/core/SkSurface.h` | SkSurface 核心类 |
| `include/core/SkColorSpace.h` | 颜色空间 |
| `include/android/AHardwareBufferUtils.h` | Android 硬件缓冲区工具函数 |
| `src/gpu/graphite/Caps.h` | GPU 能力查询 |
| `src/gpu/graphite/RecorderPriv.h` | Recorder 内部接口 |
| `src/gpu/graphite/TextureFormat.h` | 纹理格式定义 |
| `src/gpu/graphite/TextureInfoPriv.h` | 纹理信息内部接口 |
| `<android/hardware_buffer.h>` | Android NDK 硬件缓冲区 API |

### 下游依赖（依赖本目录的模块）

| 模块 | 说明 |
|------|------|
| Android 应用层 | 通过 `SkSurfaces::WrapAndroidHardwareBuffer()` 创建渲染目标 |
| Android Framework | 使用 `fromWindow` 参数支持窗口系统集成 |
| Skia 测试框架 | 用于 Android 平台的集成测试 |

## 设计模式分析

### 1. 工厂方法模式（Factory Method Pattern）
所有 Surface 创建函数都是经典的工厂方法。`WrapAndroidHardwareBuffer()` 作为 Android 平台的具体工厂，封装了 AHardwareBuffer 到 SkSurface 的完整转换逻辑。客户端无需了解底层后端纹理的创建细节，只需提供 AHardwareBuffer 即可获得可用的渲染表面。

### 2. 桥接模式（Bridge Pattern）
Surface 的设计体现了桥接模式：平台特定的资源创建（`AHardwareBuffer` -> `BackendTexture`）与通用的 Surface 包装（`WrapBackendTexture()`）被分离为两个独立的步骤。这种分离使得添加新平台支持时只需实现从平台资源到 `BackendTexture` 的转换，而复用通用的 Surface 创建逻辑。

### 3. 资源获取即初始化（RAII）
`BufferReleaseProc` / `TextureReleaseProc` 回调机制确保了资源的安全释放。如果 Surface 创建失败，工厂函数保证在返回前调用释放回调；如果创建成功，释放回调将在 Surface 销毁或后端不再需要该资源时被调用。

### 4. 显式资源管理（Explicit Resource Management）
Graphite 的 Surface API 摒弃了 Ganesh 时代的写时复制语义，转而要求客户端显式选择共享（`AsImage()`）或拷贝（`AsImageCopy()`）。这种设计减少了隐式拷贝带来的性能不确定性，给予客户端更精确的资源控制能力。

### 5. 平台抽象层（Platform Abstraction Layer）
该目录的组织方式（以 `Surface_<Platform>Factories.cpp` 命名）体现了平台抽象层的设计思想。每个平台的 Surface 工厂实现集中在独立的文件中，通过条件编译（`#if __ANDROID_API__ >= 26`）控制可用性，与核心代码完全解耦。

## 数据流

```
1. Android 应用创建 Surface:
   AHardwareBuffer* buffer = ...;  // 从 SurfaceFlinger/Camera/等获取
     |
     v
2. 调用工厂函数:
   SkSurfaces::WrapAndroidHardwareBuffer(recorder, buffer, colorSpace, ...)
     |
     v
3. 验证阶段:
   AHardwareBuffer_describe(buffer, &desc)
     |-- 检查 AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT
     |-- 检查 AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE
     |-- 排除 R8G8B8X8_UNORM 格式（Alpha 通道屏蔽）
     |-- 检测 PROTECTED_CONTENT
     |
     v
4. 后端纹理创建:
   recorder->createBackendTexture(buffer, isRenderable, isProtected, dims, fromWindow)
     |-- Vulkan: 创建 VkImage 从 AHB 导入
     |-- 或: 使用平台特定的纹理导入路径
     |
     v
5. Surface 包装:
   SkSurfaces::WrapBackendTexture(recorder, backendTexture, colorSpace, ...)
     |-- 创建 TextureProxy
     |-- 推导 SkColorType 从纹理格式
     |-- 创建 Device 和 Surface
     |
     v
6. 渲染使用:
   surface->getCanvas()->drawRect(...)  <-- 通过 Recorder 记录
     |
     v
7. 提交执行:
   recording = recorder->snap();
   context->insertRecording({recording});
   context->submit();  <-- GPU 渲染到 AHardwareBuffer
     |
     v
8. 呈现:
   Android 窗口系统读取 AHardwareBuffer 内容并合成显示
```

## 相关文档与参考

- `include/gpu/graphite/Surface.h` - Graphite Surface 公共 API
- `include/android/graphite/SurfaceAndroid.h` - Android Surface 公共 API
- `include/core/SkSurface.h` - SkSurface 核心类定义
- `include/gpu/graphite/BackendTexture.h` - 后端纹理抽象
- `include/gpu/graphite/Recorder.h` - Graphite Recorder
- `include/gpu/graphite/Context.h` - Graphite Context
- `include/android/AHardwareBufferUtils.h` - AHardwareBuffer 工具函数
- `src/gpu/graphite/Caps.h` - GPU 能力查询
- `src/gpu/graphite/TextureProxy.h` - 纹理代理
- `src/gpu/graphite/Device.h` - Graphite 设备实现
- Android NDK 文档: `AHardwareBuffer` API
- Vulkan 扩展: `VK_ANDROID_external_memory_android_hardware_buffer`
