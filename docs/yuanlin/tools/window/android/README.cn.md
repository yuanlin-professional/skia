# tools/window/android/ - Android 平台窗口上下文实现

## 概述

`tools/window/android/` 目录包含了 Skia 窗口渲染上下文在 Android 平台上的所有具体实现。Android 平台通过 ANativeWindow（来自 Android NDK）提供原生窗口句柄，支持以下渲染后端：OpenGL ES（通过 EGL）、Vulkan（Android 原生 Vulkan 驱动）、Graphite+Dawn、Graphite+Vulkan 以及软件光栅化。

Android 是 Vulkan 支持最早的移动平台之一（从 Android 7.0 / API 24 开始），因此 Vulkan 和 Graphite+Vulkan 后端在 Android 上是重要的测试目标。`WindowContextFactory_android.h` 声明了所有工厂函数，以 ANativeWindow 指针作为平台原生窗口参数。

由于 Android 的 Surface 具有动态生命周期（可以在 Activity 暂停/恢复时销毁和重建），这些窗口上下文实现需要能够正确处理底层 ANativeWindow 的创建和销毁事件。这要求每个实现在 `setDisplayParams()` 调用时能够完全重新初始化 GPU 资源。

Android 不支持 Metal 和 Direct3D 后端。ANGLE 在 Android 上作为系统组件存在，但 Skia 工具未直接使用 Android 系统 ANGLE。

## 架构图

```
+----------------------------------------------------------+
|           Android 窗口上下文体系                             |
|                                                           |
|  WindowContextFactory_android.h (工厂函数)                 |
|                                                           |
|  OpenGL ES 后端:                                           |
|  +-- GLWindowContext_android.cpp                          |
|  |     EGL 初始化 -> eglCreateWindowSurface(ANativeWindow)|
|  |     EGLContext + EGLSurface                            |
|                                                           |
|  Vulkan 后端:                                              |
|  +-- VulkanWindowContext_android.cpp                      |
|  |     vkCreateAndroidSurfaceKHR + Swapchain              |
|                                                           |
|  Graphite 后端:                                            |
|  +-- GraphiteDawnWindowContext_android.cpp                 |
|  |     Dawn WebGPU (Vulkan 后端) + Android Surface        |
|  +-- GraphiteVulkanWindowContext_android.cpp               |
|        Graphite 原生 Vulkan                                |
|                                                           |
|  软件后端:                                                  |
|  +-- RasterWindowContext_android.cpp                      |
|        CPU 渲染 + ANativeWindow_Buffer 显示                |
+----------------------------------------------------------+
```

## 目录结构

```
tools/window/android/
|-- WindowContextFactory_android.h           # Android 工厂函数声明
|-- GLWindowContext_android.cpp              # OpenGL ES (EGL) 窗口上下文
|-- VulkanWindowContext_android.cpp          # Vulkan 窗口上下文
|-- GraphiteDawnWindowContext_android.cpp    # Graphite + Dawn 窗口上下文
|-- GraphiteVulkanWindowContext_android.cpp  # Graphite + Vulkan 窗口上下文
+-- RasterWindowContext_android.cpp          # 软件光栅化窗口上下文
```

## 关键函数

### WindowContextFactory_android.h

```cpp
namespace skwindow {
std::unique_ptr<WindowContext> MakeGLForAndroid(ANativeWindow*, const DisplayParams*);
std::unique_ptr<WindowContext> MakeVulkanForAndroid(ANativeWindow*, const DisplayParams*);
std::unique_ptr<WindowContext> MakeGraphiteDawnForAndroid(ANativeWindow*, const DisplayParams*);
std::unique_ptr<WindowContext> MakeGraphiteVulkanForAndroid(ANativeWindow*, const DisplayParams*);
std::unique_ptr<WindowContext> MakeRasterForAndroid(ANativeWindow*, const DisplayParams*);
}
```

### 各后端初始化要点

| 后端 | 文件 | 关键初始化步骤 |
|------|------|---------------|
| OpenGL ES | `GLWindowContext_android.cpp` | eglGetDisplay -> eglCreateWindowSurface(ANativeWindow) -> eglMakeCurrent |
| Vulkan | `VulkanWindowContext_android.cpp` | vkCreateAndroidSurfaceKHR -> VulkanWindowContext 基类 Swapchain |
| Dawn | `GraphiteDawnWindowContext_android.cpp` | Dawn Vulkan 后端 -> Android Surface 绑定 |
| 原生 Vulkan | `GraphiteVulkanWindowContext_android.cpp` | vkCreateAndroidSurfaceKHR -> Graphite Context |
| Raster | `RasterWindowContext_android.cpp` | ANativeWindow_lock -> CPU 渲染 -> ANativeWindow_unlockAndPost |

## 依赖关系

```
tools/window/android/
    |
    +---> Android NDK
    |       +---> ANativeWindow (native_window.h)
    |       +---> ANativeWindow_lock/unlock (Raster 后端)
    |
    +---> EGL (OpenGL ES 后端)
    |       +---> eglGetDisplay, eglCreateWindowSurface
    |       +---> eglMakeCurrent, eglSwapBuffers
    |
    +---> Vulkan SDK
    |       +---> VK_KHR_android_surface
    |       +---> vkCreateAndroidSurfaceKHR
    |
    +---> Dawn (WebGPU Vulkan 后端)
    +---> skwindow::WindowContext 基类
    +---> skwindow::DisplayParams
```

## 设计模式分析

### 工厂方法模式

所有工厂函数接收 ANativeWindow 指针，这是 Android 平台唯一的原生窗口句柄类型。工厂函数内部创建对应的 GPU 上下文并配置 Swapchain。

### Surface 生命周期管理

Android 的 ANativeWindow 可能在运行时被销毁和重建。Raster 后端使用 `ANativeWindow_lock` / `ANativeWindow_unlockAndPost` 进行直接像素缓冲区访问，这要求每次绘制时确保 ANativeWindow 仍然有效。

## 相关文档与参考

- **窗口上下文框架**: `tools/window/README.md`
- **Android 应用框架**: `tools/sk_app/android/README.md`
- **Android NDK ANativeWindow**: https://developer.android.com/ndk/reference/group/a-native-window
- **Android EGL**: https://developer.android.com/reference/android/opengl/EGL14
- **Android Vulkan**: https://developer.android.com/ndk/guides/graphics/
