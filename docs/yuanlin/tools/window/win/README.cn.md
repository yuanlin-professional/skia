# tools/window/win/ - Windows 平台窗口上下文实现

## 概述

`tools/window/win/` 目录包含了 Skia 窗口渲染上下文在 Windows 平台上的所有具体实现。该目录为 Windows 提供了最丰富的图形 API 支持，包括 OpenGL（通过 WGL）、Vulkan、ANGLE（OpenGL ES 模拟）、Direct3D 12、Graphite+Dawn（支持 D3D11/D3D12/Vulkan/OpenGLES 后端）、Graphite+Vulkan 以及软件光栅化。

每个 `*WindowContext_win.cpp` 文件实现了对应图形 API 在 Windows 上的初始化逻辑，包括设备选择、Surface 创建和交换链管理。`WindowContextFactory_win.h` 声明了所有工厂函数，由 `sk_app::Window_win::attach()` 根据请求的后端类型调用。

Windows 平台独有的 Direct3D 12 支持（`D3D12WindowContext_win.cpp`）和多种 Dawn 后端变体使其成为 Skia 跨平台渲染测试中覆盖范围最广的平台。Windows 也是唯一同时支持 ANGLE（将 OpenGL ES 转译到 Direct3D）和原生 Direct3D 12 的平台。

## 架构图

```
+----------------------------------------------------------+
|           Windows 窗口上下文工厂体系                        |
|                                                           |
|  WindowContextFactory_win.h (所有工厂函数声明)              |
|    |                                                      |
|    +-- MakeGLForWin(HWND, DisplayParams*)                 |
|    |     --> GLWindowContext_win.cpp                       |
|    |     基于 WGL 创建 OpenGL 上下文                       |
|    |                                                      |
|    +-- MakeVulkanForWin(HWND, DisplayParams*)             |
|    |     --> VulkanWindowContext_win.cpp                   |
|    |     vkCreateWin32SurfaceKHR + Swapchain              |
|    |                                                      |
|    +-- MakeANGLEForWin(HWND, DisplayParams*)              |
|    |     --> ANGLEWindowContext_win.cpp                    |
|    |     EGL + GLES on Direct3D (ANGLE 库)                |
|    |                                                      |
|    +-- MakeD3D12ForWin(HWND, DisplayParams*)              |
|    |     --> D3D12WindowContext_win.cpp                    |
|    |     D3D12Device + DXGI SwapChain                     |
|    |                                                      |
|    +-- MakeGraphiteDawnD3D11ForWin(HWND, DisplayParams*)  |
|    +-- MakeGraphiteDawnD3D12ForWin(HWND, DisplayParams*)  |
|    +-- MakeGraphiteDawnVulkanForWin(HWND, DisplayParams*) |
|    |     --> GraphiteDawnWindowContext_win.cpp             |
|    |     Dawn WebGPU 实现，多种后端                        |
|    |                                                      |
|    +-- MakeGraphiteVulkanForWin(HWND, DisplayParams*)     |
|    |     --> GraphiteVulkanWindowContext_win.cpp           |
|    |     Graphite 原生 Vulkan 后端                         |
|    |                                                      |
|    +-- MakeRasterForWin(HWND, DisplayParams*)             |
|          --> RasterWindowContext_win.cpp                   |
|          CPU 软件光栅化 + StretchDIBits 显示               |
+----------------------------------------------------------+
```

## 目录结构

```
tools/window/win/
|-- WindowContextFactory_win.h            # 所有 Windows 工厂函数声明
|-- GLWindowContext_win.cpp               # OpenGL 窗口上下文 (WGL)
|-- VulkanWindowContext_win.cpp           # Vulkan 窗口上下文 (Win32 Surface)
|-- ANGLEWindowContext_win.cpp            # ANGLE (EGL/GLES on D3D) 窗口上下文
|-- D3D12WindowContext_win.cpp            # Direct3D 12 窗口上下文 (Windows 独有)
|-- GraphiteDawnWindowContext_win.cpp     # Graphite + Dawn (多后端) 窗口上下文
|-- GraphiteVulkanWindowContext_win.cpp   # Graphite + 原生 Vulkan 窗口上下文
+-- RasterWindowContext_win.cpp           # 软件光栅化窗口上下文 (GDI)
```

## 关键函数

### WindowContextFactory_win.h 工厂函数

```cpp
// tools/window/win/WindowContextFactory_win.h
namespace skwindow {

// Ganesh 后端
std::unique_ptr<WindowContext> MakeGLForWin(HWND, const DisplayParams*);
std::unique_ptr<WindowContext> MakeVulkanForWin(HWND, const DisplayParams*);
std::unique_ptr<WindowContext> MakeANGLEForWin(HWND, const DisplayParams*);
std::unique_ptr<WindowContext> MakeD3D12ForWin(HWND, const DisplayParams*);

// Graphite 后端
std::unique_ptr<WindowContext> MakeGraphiteDawnD3D11ForWin(HWND, const DisplayParams*);
std::unique_ptr<WindowContext> MakeGraphiteDawnD3D12ForWin(HWND, const DisplayParams*);
std::unique_ptr<WindowContext> MakeGraphiteDawnVulkanForWin(HWND, const DisplayParams*);
std::unique_ptr<WindowContext> MakeGraphiteVulkanForWin(HWND, const DisplayParams*);

// 软件后端
std::unique_ptr<WindowContext> MakeRasterForWin(HWND, const DisplayParams*);

}
```

### 各后端初始化要点

| 后端 | 文件 | 关键初始化步骤 |
|------|------|---------------|
| OpenGL | `GLWindowContext_win.cpp` | GetDC -> ChoosePixelFormat -> SetPixelFormat -> wglCreateContext |
| Vulkan | `VulkanWindowContext_win.cpp` | vkCreateWin32SurfaceKHR -> VulkanWindowContext 基类处理 Swapchain |
| ANGLE | `ANGLEWindowContext_win.cpp` | eglGetDisplay -> eglCreateWindowSurface -> eglMakeCurrent |
| D3D12 | `D3D12WindowContext_win.cpp` | D3D12CreateDevice -> CreateSwapChainForHwnd |
| Dawn | `GraphiteDawnWindowContext_win.cpp` | dawn::native 设备创建 -> wgpu Surface |
| Raster | `RasterWindowContext_win.cpp` | 创建 DIB Section -> SkSurface::MakeRasterDirect |

## 依赖关系

```
tools/window/win/
    |
    +---> Win32 API
    |       +---> HWND, HDC, GetDC/ReleaseDC
    |       +---> StretchDIBits (Raster 后端显示)
    |
    +---> WGL (OpenGL 后端)
    |       +---> wglCreateContext, wglMakeCurrent
    |       +---> ChoosePixelFormat, SetPixelFormat
    |
    +---> Vulkan SDK
    |       +---> VK_KHR_win32_surface
    |       +---> vkCreateWin32SurfaceKHR
    |
    +---> ANGLE 库
    |       +---> EGL + OpenGL ES 2.0/3.0
    |       +---> D3D9/D3D11 后端转译
    |
    +---> Direct3D 12 + DXGI
    |       +---> D3D12CreateDevice
    |       +---> IDXGISwapChain
    |
    +---> Dawn (WebGPU 实现)
    |       +---> dawn::native
    |       +---> D3D11/D3D12/Vulkan/OpenGLES 后端
    |
    +---> skwindow::WindowContext 基类
    +---> skwindow::DisplayParams
```

## 设计模式分析

### 抽象工厂模式 (Abstract Factory)

`WindowContextFactory_win.h` 声明了一组工厂函数，共同构成 Windows 平台的抽象工厂。所有函数共享 `(HWND, const DisplayParams*)` 参数签名，返回 `unique_ptr<WindowContext>`。`Window_win::attach()` 通过 switch-case 根据 `BackendType` 调用对应的工厂。

### 模板方法模式 (Template Method)

OpenGL 后端的 Windows 实现继承自通用的 `GLWindowContext`，只需提供 `onInitializeContext()`（创建 WGL 上下文）和 `onDestroyContext()`（销毁 WGL 上下文）两个钩子方法，初始化的通用流程由基类处理。

### 平台独有后端

D3D12 是 Windows 独有的渲染后端。Skia 通过 Direct3D 12 的 `ID3D12Device` 和 DXGI SwapChain 直接进行 GPU 渲染，这是在 Windows 上获得最佳性能的选择之一。

## 相关文档与参考

- **窗口上下文框架**: `tools/window/README.md`
- **Windows 应用框架**: `tools/sk_app/win/README.md`
- **Direct3D 12 文档**: https://learn.microsoft.com/en-us/windows/win32/direct3d12/
- **ANGLE 项目**: https://chromium.googlesource.com/angle/angle
- **Vulkan Win32 WSI**: `VK_KHR_win32_surface` 扩展
- **WGL 文档**: https://learn.microsoft.com/en-us/windows/win32/opengl/wgl-functions
