# tools/window/unix/ - Linux/X11 平台窗口上下文实现

## 概述

`tools/window/unix/` 目录包含了 Skia 窗口渲染上下文在 Linux 平台上的所有具体实现。该平台基于 X Window System (X11/Xlib)，支持以下渲染后端：Ganesh+OpenGL（通过 GLX）、Ganesh+Vulkan、Graphite+Dawn+Xlib、Graphite 原生 Vulkan 以及软件光栅化。

Linux 平台没有原生的 Metal 支持，因此 Metal 相关的上下文在此平台上不可用。取而代之的是完善的 Vulkan 支持（包括 Ganesh 和 Graphite 两种后端）以及通过 Dawn 的 Vulkan 后端。这使得 Linux 成为 Vulkan 渲染路径的重要测试平台。

`XlibWindowInfo.h` 定义了 X11 窗口渲染所需的原生信息结构体，包括 Display 指针、Window ID、GLXFBConfig 和 XVisualInfo 等，在工厂函数间传递这些信息以避免重复查询 X11 服务器。

与 macOS 类似，每种后端都有独立的头文件和实现文件对，命名约定统一为 `*WindowContext_unix.h/cpp`。

## 架构图

```
+----------------------------------------------------------+
|           Linux/X11 窗口上下文体系                          |
|                                                           |
|  XlibWindowInfo.h:                                        |
|    { Display*, XWindow, GLXFBConfig*, XVisualInfo*,       |
|      int width, int height }                              |
|                                                           |
|  Ganesh 后端:                                              |
|  +-- GaneshGLWindowContext_unix.h/cpp                     |
|  |     GLX 上下文创建 (glXCreateContext)                   |
|  |     glXSwapBuffers 交换缓冲                             |
|  +-- GaneshVulkanWindowContext_unix.h/cpp                  |
|        vkCreateXlibSurfaceKHR + Swapchain                 |
|                                                           |
|  Graphite 后端:                                            |
|  +-- GraphiteDawnXlibWindowContext_unix.h/cpp              |
|  |     Dawn WebGPU Vulkan 后端 + X11 Surface              |
|  +-- GraphiteNativeVulkanWindowContext_unix.h/cpp          |
|        Graphite 直接使用 Vulkan API                        |
|                                                           |
|  软件后端:                                                  |
|  +-- RasterWindowContext_unix.h/cpp                       |
|        CPU 渲染 + XPutImage/XShmPutImage 显示             |
+----------------------------------------------------------+
```

## 目录结构

```
tools/window/unix/
|-- XlibWindowInfo.h                                # X11 窗口信息结构体
|-- GaneshGLWindowContext_unix.h/cpp                # Ganesh + OpenGL (GLX)
|-- GaneshVulkanWindowContext_unix.h/cpp            # Ganesh + Vulkan (X11 Surface)
|-- GraphiteDawnXlibWindowContext_unix.h/cpp        # Graphite + Dawn + X11
|-- GraphiteNativeVulkanWindowContext_unix.h/cpp    # Graphite + 原生 Vulkan
+-- RasterWindowContext_unix.h/cpp                  # 软件光栅化 (XPutImage)
```

## 关键结构体

### XlibWindowInfo

```cpp
// tools/window/unix/XlibWindowInfo.h
struct XlibWindowInfo {
    Display*     fDisplay;      // X11 显示连接
    XWindow      fWindow;       // X11 窗口 ID
    GLXFBConfig* fFBConfig;     // GLX 帧缓冲配置（OpenGL 后端使用）
    XVisualInfo* fVisualInfo;   // X11 视觉信息
    int          fWidth;        // 窗口宽度（像素）
    int          fHeight;       // 窗口高度（像素）
};
```

### 各后端初始化要点

| 后端 | 文件 | 关键初始化步骤 |
|------|------|---------------|
| OpenGL | `GaneshGLWindowContext_unix.cpp` | glXChooseFBConfig -> glXCreateContext -> glXMakeCurrent |
| Vulkan | `GaneshVulkanWindowContext_unix.cpp` | vkCreateXlibSurfaceKHR -> VulkanWindowContext 基类 Swapchain |
| Dawn | `GraphiteDawnXlibWindowContext_unix.cpp` | Dawn 设备创建(Vulkan 后端) -> X11 Surface 绑定 |
| 原生 Vulkan | `GraphiteNativeVulkanWindowContext_unix.cpp` | vkCreateXlibSurfaceKHR -> Graphite Context |
| Raster | `RasterWindowContext_unix.cpp` | XCreateImage -> SkSurface::MakeRasterDirect -> XPutImage |

## 依赖关系

```
tools/window/unix/
    |
    +---> X11 / Xlib
    |       +---> Display, XWindow
    |       +---> XCreateImage, XPutImage (Raster 后端)
    |
    +---> GLX (OpenGL 后端)
    |       +---> glXChooseFBConfig, glXCreateContext
    |       +---> glXMakeCurrent, glXSwapBuffers
    |
    +---> Vulkan SDK
    |       +---> VK_KHR_xlib_surface
    |       +---> vkCreateXlibSurfaceKHR
    |
    +---> Dawn (WebGPU Vulkan 后端)
    +---> skwindow::WindowContext 基类
    +---> skwindow::DisplayParams
```

## 设计模式分析

### 参数对象模式 (Parameter Object)

`XlibWindowInfo` 将多个 X11 参数打包为结构体，简化工厂函数签名。避免了传递 6 个独立参数的复杂性。

### 模板方法模式

GLX 实现继承通用 `GLWindowContext`，只提供 `onInitializeContext()`（创建 GLX 上下文并返回 GrGLInterface）和 `onDestroyContext()`（销毁 GLX 上下文）钩子。

### X11 共享内存扩展

Raster 后端可以选择使用 X11 共享内存扩展（XShm）来加速 CPU 渲染结果到屏幕的传输，避免通过 X11 协议逐像素传输。

## 相关文档与参考

- **窗口上下文框架**: `tools/window/README.md`
- **Linux 应用框架**: `tools/sk_app/unix/README.md`
- **GLX 规范**: https://www.khronos.org/registry/OpenGL/specs/gl/
- **Vulkan X11 WSI**: `VK_KHR_xlib_surface` 扩展
- **X11 编程**: https://www.x.org/releases/current/doc/
