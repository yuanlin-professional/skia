# SkiaGLContext.mm - OpenGL ES 渲染上下文

> 源文件: `tools/skottie_ios_app/SkiaGLContext.mm`

## 概述

实现了基于 OpenGL ES 的 Skia GPU 渲染上下文。使用 GLKView (GLKit) 配合 Skia Ganesh GL 后端进行硬件加速渲染,作为 Metal 不可用时的替代方案。

## 架构位置

Skottie iOS 应用的 GL ES 渲染后端,在 Metal 之后的第二优先级。

## 主要类与结构体

- **`SkiaGLView`**: GLKView 子类,使用 GL 后端渲染
- **`SkiaGLContext`**: SkiaContext 子类,管理 EAGLContext 和 GrDirectContext

## 公共 API 函数

- **`MakeSkiaGLContext()`**: 工厂函数
- **`configure_glkview_for_skia()`**: 配置 GLKView 的颜色/深度/模板格式
- **`make_gl_surface()`**: 从当前 GL 帧缓冲创建 SkSurface

## 内部实现细节

通过 `GrBackendRenderTargets::MakeGL` 包装当前绑定的帧缓冲对象(FBO),创建 `SkSurface` 用于渲染。优先尝试 GL ES 3.0,回退到 GL ES 2.0。使用 `kBottomLeft_GrSurfaceOrigin` 适配 GL 的坐标系。

## 依赖关系

- GLKit.framework, OpenGLES.framework
- `GrGLDirectContext.h`: Ganesh GL 上下文
- `SkSurfaceGanesh.h`: Ganesh Surface 工具

## 设计模式与设计决策

- 使用 FBO 包装而非创建独立的 GL 纹理
- 30fps 帧率限制通过 NSTimer 实现

## 性能考量

GL ES 路径比 Metal 略慢但兼容性更广。渲染完成后调用 `flushAndSubmit` 确保 GPU 同步。

## 相关文件

- `tools/skottie_ios_app/SkiaContext.h`
