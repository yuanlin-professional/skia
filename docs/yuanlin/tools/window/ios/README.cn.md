# tools/window/ios/ - iOS 平台窗口上下文实现

## 概述

`tools/window/ios/` 目录包含了 Skia 窗口渲染上下文在 iOS 平台上的所有具体实现。iOS 平台通过 UIView（及其底层的 CALayer）提供原生渲染目标，支持以下渲染后端：OpenGL ES（通过 CAEAGLLayer/EGL）、Metal（通过 CAMetalLayer）、Graphite+Metal 以及软件光栅化。

由于 iOS 不支持 Vulkan 原生驱动（Apple 推广 Metal 作为唯一的低级 GPU API），也不支持 Dawn 后端，iOS 的渲染后端选择比其他平台更有限。Metal 是 iOS 上的首选 GPU 后端，从 iOS 8 开始就获得了原生支持，并且是 Apple 持续投资的图形 API。

需要注意的是，Apple 已在 iOS 12 中废弃了 OpenGL ES。虽然 Skia 仍提供 OpenGL ES 窗口上下文的实现，但在新版 iOS 上推荐使用 Metal 后端。Graphite+Metal 是 Skia 新一代 GPU 后端在 iOS 上的最佳选择。

所有实现文件以 `.mm`（Objective-C++）编写，以便同时调用 UIKit/Metal API 和 C++ Skia 代码。`WindowContextFactory_ios.h` 声明了工厂函数，以 UIView 指针作为渲染目标参数。

## 架构图

```
+----------------------------------------------------------+
|           iOS 窗口上下文体系                                 |
|                                                           |
|  WindowContextFactory_ios.h (工厂函数)                     |
|                                                           |
|  OpenGL ES 后端 (已废弃):                                   |
|  +-- GLWindowContext_ios.mm                               |
|  |     CAEAGLLayer + EAGLContext                          |
|  |     Framebuffer 对象渲染                                |
|                                                           |
|  Metal 后端 (推荐):                                        |
|  +-- MetalWindowContext_ios.mm                            |
|  |     CAMetalLayer + MTLDevice                           |
|  |     Ganesh GrDirectContext                              |
|                                                           |
|  Graphite Metal 后端 (最新):                                |
|  +-- GraphiteMetalWindowContext_ios.mm                    |
|        CAMetalLayer + MTLDevice                            |
|        Graphite Context + Recorder                         |
|                                                           |
|  软件后端:                                                  |
|  +-- RasterWindowContext_ios.mm                           |
|        CPU 渲染 + Core Graphics 显示                       |
+----------------------------------------------------------+
```

## 目录结构

```
tools/window/ios/
|-- WindowContextFactory_ios.h            # iOS 工厂函数声明
|-- GLWindowContext_ios.mm                # OpenGL ES (EAGL + CAEAGLLayer)
|-- MetalWindowContext_ios.mm             # Ganesh + Metal (CAMetalLayer)
|-- GraphiteMetalWindowContext_ios.mm     # Graphite + Metal (CAMetalLayer)
+-- RasterWindowContext_ios.mm            # 软件光栅化 (Core Graphics)
```

## 关键函数

### WindowContextFactory_ios.h

```cpp
namespace skwindow {
// OpenGL ES 后端（iOS 12+ 已废弃 OpenGL ES）
std::unique_ptr<WindowContext> MakeGLForIOS(UIView*, const DisplayParams*);

// Metal 后端（推荐）
std::unique_ptr<WindowContext> MakeMetalForIOS(UIView*, const DisplayParams*);

// Graphite Metal 后端（最新一代 GPU 后端）
std::unique_ptr<WindowContext> MakeGraphiteMetalForIOS(UIView*, const DisplayParams*);

// 软件光栅化后端
std::unique_ptr<WindowContext> MakeRasterForIOS(UIView*, const DisplayParams*);
}
```

### 各后端初始化要点

| 后端 | 文件 | 关键初始化步骤 |
|------|------|---------------|
| OpenGL ES | `GLWindowContext_ios.mm` | CAEAGLLayer 配置 -> EAGLContext 创建 -> Renderbuffer 绑定 |
| Metal | `MetalWindowContext_ios.mm` | MTLCreateSystemDefaultDevice -> CAMetalLayer 配置 -> GrDirectContext |
| Graphite Metal | `GraphiteMetalWindowContext_ios.mm` | MTLDevice -> CAMetalLayer -> Graphite Context + Recorder |
| Raster | `RasterWindowContext_ios.mm` | SkSurface::MakeRaster -> CGBitmapContext 显示到 CALayer |

## 依赖关系

```
tools/window/ios/
    |
    +---> UIKit 框架
    |       +---> UIView (渲染目标容器)
    |       +---> CALayer (底层渲染表面)
    |
    +---> Metal 框架
    |       +---> MTLDevice, MTLCommandQueue
    |       +---> CAMetalLayer (Metal 渲染表面)
    |
    +---> OpenGL ES (已废弃)
    |       +---> EAGLContext
    |       +---> CAEAGLLayer
    |
    +---> Core Graphics (Raster 后端)
    |       +---> CGBitmapContext
    |
    +---> skwindow::WindowContext 基类
    +---> skwindow::DisplayParams
```

## 设计模式分析

### 工厂方法模式

四个工厂函数共享 `(UIView*, const DisplayParams*)` 签名，由 `Window_ios::attach()` 根据 BackendType 选择调用。

### CALayer 继承体系利用

iOS 的不同渲染后端利用了 Core Animation 的 CALayer 子类体系：
- Metal: `CAMetalLayer`（提供 `nextDrawable` 获取可绘制纹理）
- OpenGL ES: `CAEAGLLayer`（提供 Renderbuffer 存储）
- Raster: 基础 `CALayer`（通过 `contents` 属性显示 CGImage）

### 废弃 API 的兼容处理

OpenGL ES 实现虽然保留，但在编译时可能需要抑制废弃警告。Metal 后端和 Graphite+Metal 后端是 iOS 上的推荐选择。

## 相关文档与参考

- **窗口上下文框架**: `tools/window/README.md`
- **iOS 应用框架**: `tools/sk_app/ios/README.md`
- **Apple Metal for iOS**: https://developer.apple.com/metal/
- **CAMetalLayer**: https://developer.apple.com/documentation/quartzcore/cametallayer
- **Apple OpenGL ES 废弃通知**: https://developer.apple.com/documentation/opengles
- **Core Animation**: https://developer.apple.com/documentation/quartzcore
