# Surface_AndroidFactories - Android AHardwareBuffer Surface 工厂

> 源文件: `src/gpu/graphite/surface/Surface_AndroidFactories.cpp`

## 概述

`Surface_AndroidFactories.cpp` 实现了 Skia Graphite 在 Android 平台上通过 `AHardwareBuffer` 创建 `SkSurface` 的工厂函数。`AHardwareBuffer` 是 Android NDK 提供的跨进程共享 GPU 缓冲区抽象，广泛用于相机预览、视频解码、合成器（SurfaceFlinger）等场景。该文件将 AHB 包装为 Graphite 后端纹理并创建可渲染的 Surface。

## 架构位置

```
Android 平台集成
  ├── AHardwareBuffer (Android NDK)
  │     └── SkSurfaces::WrapAndroidHardwareBuffer() (本文件)
  │           ├── Recorder::createBackendTexture() (AHB → 后端纹理)
  │           └── SkSurfaces::WrapBackendTexture() (后端纹理 → Surface)
  └── Graphite 后端
        ├── Vulkan (AHB → VkImage)
        └── Dawn/GL (AHB → 对应纹理)
```

## 主要类与结构体

本文件不定义新类，实现了 `SkSurfaces` 命名空间中的工厂函数。

## 公共 API 函数

### `SkSurfaces::WrapAndroidHardwareBuffer`

```cpp
sk_sp<SkSurface> WrapAndroidHardwareBuffer(
    Recorder* recorder,                // Graphite 录制器
    AHardwareBuffer* hardwareBuffer,   // Android 硬件缓冲区
    sk_sp<SkColorSpace> colorSpace,    // 颜色空间
    const SkSurfaceProps* surfaceProps, // Surface 属性
    BufferReleaseProc releaseP,         // 释放回调函数
    ReleaseContext releaseC,            // 释放回调上下文
    bool fromWindow                     // 是否来自窗口（仅 Framework 有效）
);
```

返回包装了 AHB 的 `SkSurface`，失败时返回 `nullptr`。

## 内部实现细节

### 条件编译

整个文件被 `#if __ANDROID_API__ >= 26` 包围，因为 `AHardwareBuffer` API 从 Android API 26（Android 8.0 Oreo）开始可用。

### 参数验证

函数首先验证关键参数：

```cpp
if (!recorder || !hardwareBuffer) {
    return nullptr;
}
```

### AHB 格式和用途检查

```cpp
AHardwareBuffer_Desc bufferDesc;
AHardwareBuffer_describe(hardwareBuffer, &bufferDesc);
```

验证 AHB 满足以下要求：
1. **GPU 颜色输出**: `AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT`
2. **GPU 采样**: `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE`
3. **非不透明格式**: `R8G8B8X8_UNORM` 被拒绝

#### R8G8B8X8_UNORM 排除原因

注释详细解释了排除 X8 格式的原因：
- AHB 格式如 `R8G8B8X8_UNORM` 会掩盖 Alpha 通道
- 但在 Vulkan/GL 导入时，它们可能映射到 `VK_FORMAT_R8G8B8A8_UNORM`（不掩盖 Alpha）
- 这种不一致使得渲染结果不可预测
- 与 `SkSurfaces::RenderTarget()` 不允许 `kRGB_888x` 的策略一致

### 受保护内容检测

```cpp
const bool isProtectedContent =
    SkToBool(bufferDesc.usage & AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT);
```

检测 AHB 是否标记为受保护内容（如 DRM 视频帧），将此信息传递给后端纹理创建。

### fromWindow 参数处理

```cpp
#if !defined(SK_BUILD_FOR_ANDROID_FRAMEWORK)
fromWindow = false; // 非 Framework 构建时忽略
#endif
```

`fromWindow` 参数仅在 Android Framework 构建中有意义，用于指示 AHB 来自窗口系统，可能影响后端纹理的创建方式。

### 后端纹理创建

```cpp
BackendTexture backendTexture = recorder->createBackendTexture(
    hardwareBuffer,
    /* isRenderable= */ true,
    isProtectedContent,
    dims,
    fromWindow);
```

通过 Recorder 将 AHB 导入为后端特定的纹理对象（如 Vulkan 的 `VkImage`）。

### Surface 创建

```cpp
return SkSurfaces::WrapBackendTexture(
    recorder, backendTexture,
    std::move(colorSpace), surfaceProps,
    releaseP, releaseC);
```

最终将后端纹理包装为标准的 `SkSurface`。

### 释放回调保证

在所有失败路径中，如果提供了 `releaseP` 回调，函数确保调用它：

```cpp
if (releaseP) {
    releaseP(releaseC);
}
```

这确保了即使 Surface 创建失败，调用者也能正确释放 AHB 相关资源。

## 依赖关系

- **include/android/AHardwareBufferUtils.h**: AHB 工具函数
- **include/android/graphite/SurfaceAndroid.h**: 函数声明
- **include/core/SkColorSpace.h**: 颜色空间
- **include/gpu/graphite/BackendTexture.h**: 后端纹理
- **include/gpu/graphite/Recorder.h**: Recorder（AHB 纹理导入）
- **include/gpu/graphite/Surface.h**: WrapBackendTexture 函数
- **src/gpu/graphite/Caps.h**: GPU 能力查询
- **src/gpu/graphite/RecorderPriv.h**: Recorder 内部访问
- **src/gpu/graphite/TextureFormat.h**: 纹理格式
- **src/gpu/graphite/TextureInfoPriv.h**: 纹理信息
- **\<android/hardware_buffer.h\>**: Android NDK AHB API

## 设计模式与设计决策

### 两阶段包装

AHB 包装分为两个步骤：
1. `createBackendTexture()`: AHB -> 后端纹理（平台特定）
2. `WrapBackendTexture()`: 后端纹理 -> SkSurface（平台无关）

这种分离允许不同的后端（Vulkan、Dawn）在第一步提供各自的 AHB 导入逻辑，而第二步完全复用。

### 防御性释放回调

无论失败原因如何，都保证调用释放回调。这是典型的 RAII 补充模式——在非所有权转移的失败路径中手动清理。

### Framework 条件区分

`fromWindow` 参数和 `SK_BUILD_FOR_ANDROID_FRAMEWORK` 宏的使用体现了 Skia 作为 Android 系统库的双重身份：既是独立的图形库，也是 Android Framework 的内部组件。

## 性能考量

- AHB 包装避免了像素数据拷贝——GPU 直接操作 AHB 底层的内存
- 受保护内容路径可能禁用某些优化（如 CPU 回读）
- 单个函数调用完成所有验证和创建，无中间分配
- 失败路径尽早返回（fail-fast），避免不必要的工作

## 相关文件

- `include/android/graphite/SurfaceAndroid.h` - 函数声明
- `include/gpu/graphite/Surface.h` - WrapBackendTexture 声明
- `include/gpu/graphite/Recorder.h` - createBackendTexture 声明
- `src/gpu/graphite/vk/VulkanGraphiteUtils.cpp` - Vulkan 后端的 AHB 导入实现
- `src/gpu/graphite/Caps.h` - 格式兼容性查询
