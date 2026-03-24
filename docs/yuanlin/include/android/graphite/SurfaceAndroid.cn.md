# SurfaceAndroid

> 源文件: `include/android/graphite/SurfaceAndroid.h`

## 概述

`SurfaceAndroid.h` 是 Skia 图形库中专门为 Android 平台提供的 Graphite 后端表面（Surface）创建接口。该头文件定义了一个工厂函数 `WrapAndroidHardwareBuffer`，用于将 Android 的 `AHardwareBuffer`（硬件缓冲区）封装为 Skia 的 `SkSurface` 对象，从而使应用程序能够直接在 Android 硬件缓冲区上进行 Skia 的 GPU 加速绘制。

此接口属于 Android Framework 的私有 API，不面向一般应用开发者，仅供 Android Framework 内部使用。它是 Skia Graphite 渲染后端在 Android 平台上的关键桥梁，使得 Android 系统合成器和 UI 框架能够利用 Graphite 的高效渲染管线。

`AHardwareBuffer` 是 Android NDK 提供的跨进程共享 GPU 缓冲区抽象，广泛用于 Android 的合成器（SurfaceFlinger）、相机、视频解码器等组件之间的零拷贝数据传递。该文件需要 Android API Level 26 或更高版本，因为 `AHardwareBuffer` API 从该版本开始引入。

## 架构位置

在 Skia 的整体架构中，此文件位于以下层次：

```
应用层 / Android Framework (SurfaceFlinger / HardwareRenderer)
        |
        v
SkSurfaces::WrapAndroidHardwareBuffer()   <-- 本文件定义的公共 API
        |
        v
Graphite Recorder / BackendTexture         <-- Graphite 后端层
        |
        v
Vulkan / Dawn 等 GPU 后端驱动              <-- 底层图形 API
        |
        v
AHardwareBuffer (Android NDK)             <-- 平台硬件缓冲区
```

该头文件属于 `include/android/graphite/` 目录，是 Android 特定的 Graphite 扩展接口。它与 Ganesh 后端的对应接口 `include/android/SkSurfaceAndroid.h` 功能类似，但针对的是新一代 Graphite 渲染后端。

此函数声明位于 `SkSurfaces` 命名空间中，与 Skia 其他 Surface 工厂函数（如 `SkSurfaces::RenderTarget`、`SkSurfaces::WrapBackendTexture`）保持一致的命名风格。

## 主要类与结构体

### 类型别名

#### `ReleaseContext`
```cpp
using ReleaseContext = void*;
```
释放上下文类型，是一个通用的 `void*` 指针。当硬件缓冲区可以安全释放时，该上下文会被传递给释放回调函数。调用方可以用它来携带任意的用户数据。

#### `BufferReleaseProc`
```cpp
using BufferReleaseProc = void (*)(ReleaseContext);
```
缓冲区释放回调函数类型。这是一个函数指针，接受 `ReleaseContext` 作为参数。当 Skia 的 GPU 后端不再需要使用该硬件缓冲区时，会调用此回调通知调用方可以安全地释放或回收缓冲区。

### 前向声明的外部类型

- **`AHardwareBuffer`**: Android NDK 提供的硬件缓冲区结构体，代表可在不同硬件组件之间共享的图形缓冲区。
- **`SkColorSpace`**: Skia 的颜色空间描述类，定义颜色的解释方式（如 sRGB、Display P3 等）。
- **`SkSurface`**: Skia 的绘制表面，是所有绘制操作的目标。
- **`SkSurfaceProps`**: 表面属性，包含 LCD 条纹方向和设备无关字体等设置。
- **`skgpu::graphite::Recorder`**: Graphite 后端的录制器，负责记录和提交 GPU 命令。

## 公共 API 函数

### `SkSurfaces::WrapAndroidHardwareBuffer`

```cpp
SK_API sk_sp<SkSurface> WrapAndroidHardwareBuffer(
    skgpu::graphite::Recorder* recorder,
    AHardwareBuffer* hardwareBuffer,
    sk_sp<SkColorSpace> colorSpace,
    const SkSurfaceProps* surfaceProps,
    BufferReleaseProc = nullptr,
    ReleaseContext = nullptr,
    bool fromWindow = false);
```

**功能**: 将一个 Android `AHardwareBuffer` 包装为 Skia 的 `SkSurface`，使其可以作为 Graphite 渲染目标使用。

**参数说明**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `recorder` | `skgpu::graphite::Recorder*` | Graphite 录制器实例，不可为空 |
| `hardwareBuffer` | `AHardwareBuffer*` | Android 硬件缓冲区指针，不可为空 |
| `colorSpace` | `sk_sp<SkColorSpace>` | 颜色空间，可为 `nullptr`（使用默认值） |
| `surfaceProps` | `const SkSurfaceProps*` | 表面属性（LCD 条纹方向等），可为 `nullptr` |
| `bufferReleaseProc` | `BufferReleaseProc` | 缓冲区释放回调，默认 `nullptr` |
| `ReleaseContext` | `ReleaseContext` | 传递给释放回调的上下文，默认 `nullptr` |
| `fromWindow` | `bool` | 是否来自 Android Window，默认 `false` |

**返回值**: 成功时返回 `sk_sp<SkSurface>` 智能指针；失败时返回 `nullptr`。

**前置条件**:
- 硬件缓冲区必须同时具有 `AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT` 和 `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE` 用途标志。
- 不支持屏蔽 alpha 通道的格式（如 `AHARDWAREBUFFER_FORMAT_R8G8B8X8_UNORM`）。

**释放回调行为**:
- 创建成功时：当 GPU 后端不再使用该缓冲区时调用 `bufferReleaseProc`。
- 创建失败时：在函数返回前立即调用 `bufferReleaseProc`。

## 内部实现细节

实际实现位于 `src/gpu/graphite/surface/Surface_AndroidFactories.cpp` 中。其内部流程如下：

1. **参数校验**: 检查 `recorder` 和 `hardwareBuffer` 是否为空。
2. **缓冲区描述获取**: 调用 `AHardwareBuffer_describe` 获取缓冲区的元数据（尺寸、格式、用途标志）。
3. **格式与用途验证**: 确认缓冲区具有 GPU 颜色输出和采样能力，并排除 `AHARDWAREBUFFER_FORMAT_R8G8B8X8_UNORM` 等不支持的格式。这与 `SkSurfaces::RenderTarget` 不允许 `kRGB_888x` 等屏蔽 alpha 通道的颜色类型作为渲染目标的行为一致。需要注意的是，某些 AHB 格式在导入到 Vulkan/GL 后端时可能映射到不屏蔽 alpha 通道的格式（例如 `AHB_FORMAT_R8G8B8X8_UNORM` 映射到 `VK_FORMAT_R8G8B8A8_UNORM`）。
4. **受保护内容检测**: 检查 `AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT` 标志以确定是否为受保护内容。
5. **窗口来源处理**: `fromWindow` 参数仅在 `SK_BUILD_FOR_ANDROID_FRAMEWORK` 编译配置下生效，非 Framework 构建中会被强制设为 `false`。目前仅影响 Vulkan 后端的行为。
6. **后端纹理创建**: 通过 `Recorder::createBackendTexture` 将硬件缓冲区导入为 GPU 后端纹理，此时传入缓冲区尺寸、渲染能力标志和受保护内容标志。
7. **Surface 封装**: 调用 `SkSurfaces::WrapBackendTexture` 将后端纹理封装为 `SkSurface`。

若任一步骤失败，且提供了释放回调，则会在返回前调用该回调。

## 依赖关系

### 直接依赖
- **`include/core/SkRefCnt.h`**: 提供 `sk_sp` 智能指针和引用计数基础设施。

### 前向声明依赖
- **`AHardwareBuffer`** (Android NDK `<android/hardware_buffer.h>`): Android 硬件缓冲区。
- **`SkColorSpace`** (`include/core/SkColorSpace.h`): 颜色空间管理。
- **`SkSurface`** (`include/core/SkSurface.h`): Skia 绘制表面。
- **`SkSurfaceProps`** (`include/core/SkSurfaceProps.h`): 表面属性。
- **`skgpu::graphite::Recorder`** (`include/gpu/graphite/Recorder.h`): Graphite 录制器。

### 平台要求
- Android API Level >= 26（`AHardwareBuffer` 的最低支持版本）。

## 设计模式与设计决策

### 工厂函数模式
该 API 采用命名空间级别的工厂函数（而非类的静态方法）来创建 `SkSurface` 实例。这与 Skia 最新的 API 设计风格一致，所有 Surface 工厂函数均位于 `SkSurfaces` 命名空间中。

### 回调式资源释放
通过 `BufferReleaseProc` 回调机制实现异步资源释放。这种设计允许调用方在 GPU 真正完成对缓冲区的使用后再释放资源，避免了提前释放导致的竞态问题。同时，无论创建成功还是失败，回调都保证会被调用，避免资源泄漏。

### 私有 API 定位
该接口明确标注为 Android Framework 私有接口（"Private; only to be used by Android Framework"）。这一设计决策使得 Skia 可以在不影响公共 API 稳定性的前提下，针对 Android 系统内部需求进行特定优化和调整。虽然使用了 `SK_API` 导出宏，但其预期使用范围是受限的。

### 默认参数设计
后三个参数提供了合理的默认值（`nullptr`、`nullptr` 和 `false`），简化了不需要释放回调或非窗口缓冲区场景下的调用代码，同时保留了完整的控制能力。

## 性能考量

- **零拷贝渲染**: 通过直接包装 `AHardwareBuffer`，避免了缓冲区数据的复制。GPU 可以直接在硬件缓冲区上进行渲染，这对于 Android 系统合成和窗口渲染的性能至关重要。
- **受保护内容支持**: 支持 `AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT` 标志，允许在受 DRM 保护的内容上进行渲染，这对于视频播放等场景非常重要。
- **延迟释放**: 释放回调的异步调用机制确保 GPU 操作完成后才释放缓冲区，避免了不必要的 GPU 同步等待。
- **窗口来源优化**: `fromWindow` 参数允许 Vulkan 后端针对来自 Android Window 的缓冲区进行特定优化，例如特殊的图像布局转换和同步逻辑。
- **双重用途缓冲区**: 要求缓冲区同时具有输出和采样能力，意味着 GPU 可以同时将其用作渲染目标和纹理，支持后续的合成操作而无需额外拷贝。

## 相关文件

- **`include/android/SkSurfaceAndroid.h`**: Ganesh 后端的对应接口，提供类似的硬件缓冲区包装功能。
- **`src/gpu/graphite/surface/Surface_AndroidFactories.cpp`**: 本头文件中函数的具体实现。
- **`include/gpu/graphite/Surface.h`**: Graphite Surface 的通用工厂函数，包含 `WrapBackendTexture` 等。
- **`include/gpu/graphite/Recorder.h`**: Graphite 录制器，提供 `createBackendTexture` 方法。
- **`include/android/AHardwareBufferUtils.h`**: Android 硬件缓冲区格式转换等辅助工具。
- **`tests/graphite/AHardwareBufferTest.cpp`**: 相关的单元测试。
