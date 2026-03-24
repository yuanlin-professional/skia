# GrAHardwareBufferUtils — Android 硬件缓冲区工具

> 源文件: `src/gpu/ganesh/GrAHardwareBufferUtils.cpp`

## 概述

`GrAHardwareBufferUtils` 命名空间提供了将 Android `AHardwareBuffer` 转换为 Skia Ganesh 后端纹理和格式的实用函数。它是连接 Android 原生硬件缓冲区系统与 Skia GPU 渲染管线的桥梁，支持 OpenGL 和 Vulkan 两种后端 API。该文件是 Android 平台特有的功能，仅在 `SK_BUILD_FOR_ANDROID` 且 API 级别 >= 26 时编译。

## 架构位置

```
Android 原生层 (AHardwareBuffer)
    └── GrAHardwareBufferUtils (本文件 - 分发层)
        ├── GL 路径: MakeGLBackendTexture / GetGLBackendFormat
        └── Vulkan 路径: MakeVulkanBackendTexture / GetVulkanBackendFormat
            └── Ganesh 后端 (GrBackendTexture / GrBackendFormat)
```

此文件充当后端无关的分发层，根据当前 `GrDirectContext` 使用的 GPU API 将请求路由到对应的 GL 或 Vulkan 实现。

## 主要类与结构体

本文件未定义新类，而是在 `GrAHardwareBufferUtils` 命名空间中定义了自由函数。涉及的关键类型：

| 类型 | 描述 |
|------|------|
| `AHardwareBuffer` | Android 原生硬件缓冲区句柄 |
| `GrBackendFormat` | Skia 后端纹理格式 |
| `GrBackendTexture` | Skia 后端纹理对象 |
| `GrDirectContext` | Ganesh 直接渲染上下文 |
| `DeleteImageProc` | 图像删除回调函数指针类型 |
| `UpdateImageProc` | 图像更新回调函数指针类型 |
| `TexImageCtx` | 纹理图像上下文 |

## 公共 API 函数

### `GetBackendFormat()`

```cpp
GrBackendFormat GetBackendFormat(GrDirectContext* dContext,
                                 AHardwareBuffer* hardwareBuffer,
                                 uint32_t bufferFormat,
                                 bool requireKnownFormat);
```

将 Android 硬件缓冲区格式转换为 Skia 后端格式。根据上下文使用的 GPU 后端分发到 `GetGLBackendFormat()` 或 `GetVulkanBackendFormat()`。若不支持的后端或编译时未启用对应 API，返回空的 `GrBackendFormat`。

### `MakeBackendTexture()`

```cpp
GrBackendTexture MakeBackendTexture(GrDirectContext* dContext,
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

从 Android 硬件缓冲区创建 Skia 后端纹理。支持保护内容、可渲染标志和 Android 窗口来源标志。调用者通过 `deleteProc`/`updateProc` 回调管理纹理生命周期。

## 内部实现细节

1. **条件编译**: 整个文件由 `SK_BUILD_FOR_ANDROID && __ANDROID_API__ >= 26` 保护。内部函数通过 `SK_GL` 和 `SK_VULKAN` 宏进一步限制编译路径。

2. **遗留 API 标记**: 两个公共函数均由 `SK_DISABLE_LEGACY_ANDROID_HW_UTILS` 宏控制，表明这些 API 正处于弃用过渡期。

3. **分发逻辑**: 通过 `dContext->backend()` 查询当前后端类型，使用简单的 if-else 分支路由到具体实现。对于不支持的后端一律返回空对象。

4. **安全检查**: `MakeBackendTexture` 在调用前验证 `dContext` 非空且未废弃 (`abandoned()`)。

5. **Vulkan 独有参数**: `fromAndroidWindow` 参数仅传递给 Vulkan 路径，GL 路径不使用该参数。

## 依赖关系

- **`include/android/GrAHardwareBufferUtils.h`**: 公共头文件声明
- **`include/gpu/ganesh/GrDirectContext.h`**: GPU 上下文（遗留路径）
- **`<android/hardware_buffer.h>`**: Android NDK 硬件缓冲区 API
- **GL 后端**: `GetGLBackendFormat()`, `MakeGLBackendTexture()` (编译时可选)
- **Vulkan 后端**: `GetVulkanBackendFormat()`, `MakeVulkanBackendTexture()` (编译时可选)

## 设计模式与设计决策

1. **策略模式分发**: 根据运行时后端类型选择不同的实现策略，结合编译时条件编译确保未启用的后端不会产生链接依赖。

2. **优雅降级**: 当特定后端未编译时，返回默认构造的空对象而非崩溃，允许调用者检查返回值有效性。

3. **回调式生命周期管理**: 通过 `DeleteImageProc` 和 `UpdateImageProc` 函数指针，将纹理资源的清理责任交给特定后端实现。

4. **弃用过渡**: 使用 `SK_DISABLE_LEGACY_ANDROID_HW_UTILS` 宏为未来移除这些函数做准备，新代码应直接使用特定后端的函数。

## 性能考量

- 函数调用频率较低（通常在纹理初始化时一次性调用），因此 if-else 分发的开销可忽略。
- 底层 `AHardwareBuffer` 的导入操作可能涉及 GPU 驱动层的同步操作，是真正的性能瓶颈所在。

## 相关文件

- `include/android/GrAHardwareBufferUtils.h` — 公共 API 头文件声明
- `src/gpu/ganesh/gl/AHardwareBufferGL.cpp` — OpenGL 后端具体实现
- `src/gpu/ganesh/vk/AHardwareBufferVk.cpp` — Vulkan 后端具体实现
- `src/gpu/ganesh/surface/SkSurface_AndroidFactories.cpp` — Android Surface 工厂
- `src/gpu/ganesh/image/SkImage_GaneshFactories_Android.cpp` — Android Image 工厂
