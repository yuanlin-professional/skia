# tools/window/mac/ - macOS 平台窗口上下文实现

## 概述

`tools/window/mac/` 目录包含了 Skia 窗口渲染上下文在 macOS 平台上的所有具体实现。macOS 平台的特殊之处在于它是 Metal 和 Graphite+Metal 后端的主要开发平台，因此该目录提供了丰富的 Metal 相关上下文实现。

该目录支持以下渲染后端：Ganesh+OpenGL（通过 NSOpenGLContext）、Ganesh+ANGLE（OpenGL ES 在 Metal 上的模拟）、Ganesh+Metal、Graphite+Dawn+Metal、Graphite 原生 Metal 以及软件光栅化。每个实现以 `.mm` 文件（Objective-C++）编写，以便同时使用 Cocoa/Metal API 和 C++ Skia 代码。

`MacWindowInfo.h` 定义了一个轻量结构体，封装了 macOS 窗口渲染所需的原生对象（如 NSView 指针），在工厂函数间传递。`MacWindowGLUtils.h` 提供了 macOS 特有的 OpenGL 辅助功能。

值得注意的是，macOS 实现为每种后端提供了独立的头文件和实现文件对（如 `GaneshGLWindowContext_mac.h` + `.mm`），这比其他平台更加模块化，便于选择性编译和减少不必要的依赖。

## 架构图

```
+----------------------------------------------------------+
|           macOS 窗口上下文体系                               |
|                                                           |
|  MacWindowInfo.h: { NSView* fMainView; }                  |
|                                                           |
|  Ganesh 后端:                                              |
|  +-- GaneshGLWindowContext_mac.h/mm                       |
|  |     NSOpenGLContext + NSOpenGLPixelFormat               |
|  +-- GaneshANGLEWindowContext_mac.h/mm                    |
|  |     ANGLE EGL + GLES on Metal 后端                     |
|  +-- GaneshMetalWindowContext_mac.h/mm                    |
|        MTLDevice + CAMetalLayer                            |
|                                                           |
|  Graphite 后端:                                            |
|  +-- GraphiteDawnMetalWindowContext_mac.h/mm              |
|  |     Dawn WebGPU Metal 后端 + Graphite                  |
|  +-- GraphiteNativeMetalWindowContext_mac.h/mm            |
|        Graphite 直接使用 Metal API                         |
|                                                           |
|  软件后端:                                                  |
|  +-- RasterWindowContext_mac.h/mm                         |
|        CPU 渲染 + Core Graphics 显示                       |
+----------------------------------------------------------+
```

## 目录结构

```
tools/window/mac/
|-- MacWindowInfo.h                           # macOS 窗口信息结构体 (NSView*)
|-- MacWindowGLUtils.h                        # macOS GL 辅助工具函数
|-- GaneshGLWindowContext_mac.h/mm            # Ganesh + OpenGL (NSOpenGLContext)
|-- GaneshANGLEWindowContext_mac.h/mm         # Ganesh + ANGLE (EGL on Metal)
|-- GaneshMetalWindowContext_mac.h/mm         # Ganesh + Metal (CAMetalLayer)
|-- GraphiteDawnMetalWindowContext_mac.h/mm   # Graphite + Dawn + Metal
|-- GraphiteNativeMetalWindowContext_mac.h/mm # Graphite + 原生 Metal
+-- RasterWindowContext_mac.h/mm              # 软件光栅化 (Core Graphics)
```

## 关键结构体与函数

### MacWindowInfo

```cpp
// tools/window/mac/MacWindowInfo.h
struct MacWindowInfo {
    NSView* fMainView;  // 主渲染视图，由 Window_mac 提供
};
```

### 各后端初始化要点

| 后端 | 文件 | 关键初始化步骤 |
|------|------|---------------|
| OpenGL | `GaneshGLWindowContext_mac.mm` | NSOpenGLPixelFormat -> NSOpenGLContext -> [view setOpenGLContext:] |
| ANGLE | `GaneshANGLEWindowContext_mac.mm` | ANGLE EGL 初始化 -> Metal 后端转译 |
| Metal | `GaneshMetalWindowContext_mac.mm` | MTLCreateSystemDefaultDevice -> CAMetalLayer 配置 |
| Dawn+Metal | `GraphiteDawnMetalWindowContext_mac.mm` | Dawn 设备创建(Metal 后端) -> Graphite Context |
| 原生 Metal | `GraphiteNativeMetalWindowContext_mac.mm` | MTLDevice -> Graphite Context + Recorder |
| Raster | `RasterWindowContext_mac.mm` | SkSurface::MakeRaster -> CGBitmapContext 显示 |

## 依赖关系

```
tools/window/mac/
    |
    +---> Cocoa 框架
    |       +---> NSView (渲染目标)
    |       +---> NSOpenGLContext, NSOpenGLPixelFormat (GL 后端)
    |
    +---> Metal 框架
    |       +---> MTLDevice, MTLCommandQueue
    |       +---> CAMetalLayer (Metal/Graphite 后端)
    |
    +---> Core Graphics
    |       +---> CGBitmapContext (Raster 后端显示)
    |
    +---> ANGLE 库 (EGL + GLES on Metal)
    +---> Dawn (WebGPU Metal 后端)
    +---> skwindow::WindowContext 基类
    +---> skwindow::DisplayParams
```

## 设计模式分析

### 工厂方法模式

每个头文件声明一个工厂函数（如 `MakeGaneshGLForMac`），接收 `MacWindowInfo` 和 `DisplayParams` 作为参数。命名约定清晰地标识了 GPU 后端组合。

### 模块化编译

每种后端都是独立的编译单元（`.mm` 文件），通过构建系统按需链接。如果某个 GPU 后端不可用（如未安装 Vulkan SDK），对应的文件不参与编译，不会产生链接错误。

### Objective-C++ 混合编程

`.mm` 文件使用 Objective-C++ 编写，在同一文件中混合使用 Objective-C（Cocoa/Metal API 调用）和 C++（Skia API 调用），这是 macOS 平台集成的标准做法。

## 相关文档与参考

- **窗口上下文框架**: `tools/window/README.md`
- **macOS 应用框架**: `tools/sk_app/mac/README.md`
- **Apple Metal 文档**: https://developer.apple.com/metal/
- **Apple OpenGL (已废弃)**: https://developer.apple.com/opengl/
- **CAMetalLayer**: https://developer.apple.com/documentation/quartzcore/cametallayer
