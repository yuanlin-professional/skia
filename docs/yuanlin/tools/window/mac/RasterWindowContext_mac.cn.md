# RasterWindowContext_mac

> 源文件: `tools/window/mac/RasterWindowContext_mac.h`, `tools/window/mac/RasterWindowContext_mac.mm`

## 概述

RasterWindowContext_mac 是 macOS 平台上的光栅化（CPU）窗口渲染上下文实现。尽管名为"Raster"，其实现实际上使用 NSOpenGL 上下文将 CPU 渲染的内容上传到屏幕。客户端在 CPU 端的 SkSurface 上绘制，然后在缓冲交换时将内容快照为图片并通过 GL 绘制到屏幕。

这是一种混合方案：渲染在 CPU 上完成（光栅化 SkSurface），但显示输出通过 OpenGL 管线完成。

## 架构位置

```
WindowContext
  +-- GLWindowContext (GL 窗口上下文基类)
       +-- RasterWindowContext_mac (macOS CPU 渲染 + GL 显示) <-- 本文件
```

## 主要类与结构体

### `RasterWindowContext_mac`（匿名命名空间内）
- **继承**: `GLWindowContext`
- **成员**:
  - `fMainView`: NSView 指针
  - `fGLContext`: NSOpenGLContext
  - `fPixelFormat`: NSOpenGLPixelFormat
  - `fBackbufferSurface`: CPU 渲染的 SkSurface

### 工厂函数
- `skwindow::MakeRasterForMac(info, params)`: 创建 macOS 光栅窗口上下文

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeRasterForMac(info, params)` | 工厂函数 |
| `getBackbufferSurface()` | 返回 CPU 端的 `fBackbufferSurface` |

## 内部实现细节

### 初始化流程（onInitializeContext）
1. 创建 NSOpenGLPixelFormat（OpenGL 3.2 Core Profile，24位颜色 + 8位 Alpha + 8位模板 + 可选 MSAA）
2. 创建 NSOpenGLContext 并关联到视图
3. 配置 VSync（通过 `NSOpenGLCPSwapInterval`）
4. 启用 Retina 最佳分辨率（`setWantsBestResolutionOpenGLSurface`）
5. 创建 CPU 端光栅 SkSurface（`SkSurfaces::Raster`）

### 缓冲交换（onSwapBuffers）
1. 从 `fBackbufferSurface` 创建图像快照
2. 获取 GL 后端的 SkSurface（通过 `GLWindowContext::getBackbufferSurface()`）
3. 将快照绘制到 GL Surface 上
4. 调用 `skgpu::ganesh::Flush` 刷新 Ganesh 管线
5. 调用 `[fGLContext flushBuffer]` 呈现

### 窗口调整（resize）
调用 `[fGLContext update]` 更新 GL 上下文，然后通过父类重建上下文。

### 已弃用 API 处理
所有 NSOpenGL 相关调用被包裹在 `#pragma clang diagnostic ignored "-Wdeprecated-declarations"` 中，因为 macOS 已弃用 NSOpenGL 转向 Metal。

## 依赖关系

- **Cocoa/OpenGL**: `<Cocoa/Cocoa.h>`, `<OpenGL/gl.h>`
- **Ganesh GL**: `GrGLInterface`, `GrGLMakeMacInterface`, `SkSurfaceGanesh`
- **Skia 核心**: `SkCanvas`, `SkSurface`, `SkImage`
- **工具**: `GLWindowContext`, `ToolUtils`, `MacWindowInfo`

## 设计模式与设计决策

1. **双缓冲架构**: CPU 渲染 -> 快照 -> GL 上传 -> 呈现，解耦 CPU 渲染与显示输出
2. **历史遗留方案**: 源码注释明确表示纯光栅后端会更好，当前使用 GL 是历史原因
3. **NSOpenGL 弃用容忍**: 通过编译器 pragma 抑制弃用警告

## 性能考量

- 每帧需要创建图像快照并上传到 GPU，引入额外的 CPU-GPU 数据传输开销
- 纯光栅后端（未来改进方向）可避免 GL 依赖和数据传输开销
- Retina 显示器下像素数量翻倍，CPU 渲染和上传负担加重

## 相关文件

- `tools/window/GLWindowContext.h` - GL 窗口上下文基类
- `tools/window/mac/MacWindowInfo.h` - macOS 窗口信息
- `include/gpu/ganesh/gl/mac/GrGLMakeMacInterface.h` - macOS GL 接口创建
