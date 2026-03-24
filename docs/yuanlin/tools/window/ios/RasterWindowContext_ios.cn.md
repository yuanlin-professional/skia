# RasterWindowContext_ios - iOS 光栅化窗口上下文

> 源文件: `tools/window/ios/RasterWindowContext_ios.mm`

## 概述

`RasterWindowContext_ios` 实现了 iOS 平台上的软件光栅化渲染窗口上下文。值得注意的是，尽管名为"光栅化"，它实际上继承自 `GLWindowContext` 而非 `RasterWindowContext`，因为 iOS 没有直接将 CPU 像素缓冲区呈现到屏幕的 API。它在 CPU 上完成 Skia 绘制，然后通过 OpenGL ES 将结果传输到屏幕。

## 架构位置

- 继承自 `skwindow::internal::GLWindowContext`（出于历史原因）
- 由工厂函数 `MakeRasterForIOS` 创建
- 使用混合策略：CPU 绘制 + GPU 呈现

## 主要类与结构体

### `RasterView`（Objective-C）
- 继承自 `MainView`，覆盖 `+layerClass` 返回 `CAEAGLLayer`

### `RasterWindowContext_ios`（匿名命名空间）
- 继承自 `GLWindowContext`
- 额外成员：
  - `fRasterView` - UI 视图
  - `fGLContext` - EAGLContext（与基类独立管理）
  - `fFramebuffer`, `fRenderbuffer` - GL 帧缓冲对象
  - `fBackbufferSurface` - CPU 端光栅化表面

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeRasterForIOS(IOSWindowInfo&, params)` | 工厂函数 |
| `getBackbufferSurface()` | 返回 CPU 端光栅化表面 |

## 内部实现细节

### 初始化流程
与 `GLWindowContext_ios` 类似设置 EAGLContext 和 FBO，但额外创建 CPU 端的光栅化表面：
```
fBackbufferSurface = SkSurfaces::Raster(info);
```

### 帧交换 (`onSwapBuffers`) - 核心差异
1. 从 CPU 光栅化表面截取图像快照
2. 获取 GL 后台缓冲表面
3. 将 CPU 图像绘制到 GPU 表面
4. 刷新并提交 GL 上下文
5. 通过 `presentRenderbuffer` 呈现到屏幕

这是一个两步传输过程：CPU 像素 -> GPU 纹理 -> 屏幕。

### 后台缓冲区重写
`getBackbufferSurface()` 覆盖基类返回 CPU 表面而非 GL 表面，使得 Skia 绑定在 CPU 上进行光栅化绘制。

## 依赖关系

- `tools/window/GLWindowContext.h` - GL 基类
- `include/gpu/ganesh/GrDirectContext.h` - Ganesh 上下文（用于传输）
- `include/core/SkCanvas.h` - 绘制 API
- `tools/ToolUtils.h` - 工具函数
- `<OpenGLES/ES3/gl.h>`, `<UIKit/UIKit.h>`

## 设计模式与设计决策

- **混合渲染策略**: CPU 光栅化 + GL 呈现，因为 iOS 缺乏直接的光栅化显示路径
- **源码注释的 TODO**: 开发者明确标注这是"出于历史原因"的设计，建议未来使用纯光栅化后端
- **覆盖 getBackbufferSurface**: 关键设计点，使外部调用者看到的是 CPU 表面
- **额外数据拷贝**: CPU -> GPU 的传输是必要的架构开销

## 性能考量

- CPU 光栅化后需要额外的 GPU 传输步骤，引入了延迟和带宽开销
- `makeImageSnapshot()` 创建图像快照可能触发内存拷贝
- `drawImage` + `flushAndSubmit` 将像素上传到 GPU 并等待完成
- 性能不如直接的 GPU 渲染或直接的帧缓冲访问
- 适用于需要验证 CPU 光栅化正确性的测试场景

## 相关文件

- `tools/window/ios/GLWindowContext_ios.mm` - 纯 GL 版本
- `tools/window/ios/MetalWindowContext_ios.mm` - Metal 替代方案
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 工厂声明
- `tools/window/RasterWindowContext.h` - 其他平台使用的光栅化基类
