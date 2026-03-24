# CanvasKit WebGL 后端模块 (webgl.js)

> 源文件: `modules/canvaskit/webgl.js`

## 概述

`webgl.js` 是 CanvasKit 的 WebGL 渲染后端实现，提供了 WebGL 上下文创建与管理、GPU 渲染表面创建、纹理管理以及从各种 Web 媒体源（图片、视频、Canvas、VideoFrame）创建 Skia Image 的功能。该模块是 CanvasKit GPU 加速渲染的核心，与 `cpu.js` 互补，共同提供 CanvasKit 的平台适配层。

## 架构位置

该文件位于 CanvasKit 的 JavaScript 辅助层，通过 Emscripten 的 GL 库与底层 WebGL 上下文交互，同时调用 C++ 绑定创建 Skia GPU 资源。

```
JavaScript 应用
  └── CanvasKit.MakeWebGLCanvasSurface() / MakeCanvasSurface()
      └── CanvasKit.GetWebGLContext()  → WebGL 上下文
      └── CanvasKit.MakeWebGLContext() → GrDirectContext (Skia GPU 上下文)
      └── CanvasKit.MakeOnScreenGLSurface() → SkSurface
          └── C++ Skia GPU 渲染管线
```

## 主要类与结构体

### GrDirectContext（原型扩展）

Skia 的 GPU 直接上下文，管理 GPU 资源缓存：

| 方法 | 说明 |
|------|------|
| `getResourceCacheLimitBytes()` | 获取资源缓存大小限制 |
| `getResourceCacheUsageBytes()` | 获取当前资源缓存使用量 |
| `releaseResourcesAndAbandonContext()` | 释放所有 GPU 资源并放弃上下文 |
| `setResourceCacheLimitBytes(maxResourceBytes)` | 设置资源缓存大小限制 |

### Surface（原型扩展）

渲染表面，支持纹理创建和更新：

| 方法 | 说明 |
|------|------|
| `makeImageFromTexture(tex, info)` | 从 WebGL 纹理创建 SkImage |
| `makeImageFromTextureSource(src, info, srcIsPremul)` | 从 Web 媒体源创建纹理支持的 SkImage |
| `updateTextureFromSource(img, src, srcIsPremul)` | 用新的媒体源数据更新已有 Image 的纹理 |

## 公共 API 函数

### 上下文管理

| 函数 | 说明 |
|------|------|
| `CanvasKit.GetWebGLContext(canvas, attrs)` | 从 HTML Canvas 创建 WebGL 上下文并返回句柄 |
| `CanvasKit.deleteContext(handle)` | 删除 WebGL 上下文 |
| `CanvasKit.MakeWebGLContext(ctx)` | 从 WebGL 上下文创建 Skia GrDirectContext |
| `CanvasKit.MakeGrContext(ctx)` | `MakeWebGLContext` 的别名 |
| `CanvasKit.setCurrentContext(ctx)` | 切换当前活跃的 WebGL 上下文 |
| `CanvasKit.getCurrentGrDirectContext()` | 获取当前上下文关联的 GrDirectContext |

### 表面创建

| 函数 | 说明 |
|------|------|
| `CanvasKit.MakeOnScreenGLSurface(grCtx, w, h, colorspace, sc, st)` | 创建屏上 GL 渲染表面 |
| `CanvasKit.MakeRenderTarget(grCtx, ...)` | 创建离屏渲染目标（支持 WH 或 ImageInfo 参数） |
| `CanvasKit.MakeWebGLCanvasSurface(idOrElement, colorSpace, attrs)` | 一站式创建 Canvas 绑定的 WebGL 表面 |
| `CanvasKit.MakeCanvasSurface` | `MakeWebGLCanvasSurface` 的别名 |

### 纹理与图像

| 函数 | 说明 |
|------|------|
| `CanvasKit.MakeLazyImageFromTextureSource(src, info, srcIsPremul)` | 创建延迟加载的纹理 Image（首次绘制时才上传纹理） |

## 内部实现细节

### WebGL 上下文创建

`GetWebGLContext` 配置大量 WebGL 上下文属性，包括 alpha、depth、stencil 缓冲区等。默认尝试 WebGL 2（通过检测 `WebGL2RenderingContext` 是否存在），回退到 WebGL 1。创建后立即启用 `WEBGL_debug_renderer_info` 扩展以处理 GPU 边角情况。

### 纹理生命周期管理

- **`pushTexture(tex)`**: 将 WebGL 纹理注册到 Emscripten 的 `GL.textures` 数组中，获取唯一句柄。使用 `GL.getNewId` 确保不与 Skia 内部创建的纹理冲突
- **`_setTextureCleanup`**: 注册清理回调，当 Skia 端删除纹理时，同步删除 WebGL 纹理对象
- **纹理更新**: `updateTextureFromSource` 实现了一个复杂的指针交换机制——创建新 SkImage，交换内部指针，删除旧 Image。这是为了绕过 Skia 对 Image 不可变性的假设

### 预乘 Alpha 处理

`setupTexture` 和 `resetTexture` 在上传纹理前后管理 `UNPACK_PREMULTIPLY_ALPHA_WEBGL` 状态。当源未预乘但目标要求预乘时，在上传时自动完成预乘转换。

### GPU 回退到软件渲染

`MakeWebGLCanvasSurface` 在 GPU 表面创建失败时，会克隆 Canvas 元素、替换原有元素，并回退到 `MakeSWCanvasSurface` 软件渲染。新 Canvas 会添加 `ck-replaced` CSS 类供应用检测。

### 延迟纹理创建

`MakeLazyImageFromTextureSource` 返回一个延迟 Image，其纹理仅在首次绘制时通过 `makeTexture` 回调创建。对于 VideoFrame 类型的源，还注册 `freeSrc` 回调在 Image 删除时调用 `src.close()`。

### 上下文绑定

多个方法（如 `MakeWebGLContext`, `MakeOnScreenGLSurface`）在操作前调用 `setCurrentContext` 确保指向正确的 WebGL 上下文。`GrDirectContext.delete` 被包装以在删除前切换到正确的上下文。

### 媒体源尺寸检测

`getHeight`/`getWidth` 辅助函数按优先级检测多种 Web 对象的尺寸：`naturalHeight`（`<img>`）> `videoHeight`（`<video>`）> `displayHeight`（VideoFrame）> `height`（Canvas/ImageBitmap/ImageData）。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| Emscripten GL 库 | `GL.createContext`, `GL.makeContextCurrent`, `GL.textures`, `GL.getNewId` |
| C++ 绑定 | `_MakeGrContext`, `_MakeOnScreenGLSurface`, `_MakeRenderTargetWH/II`, `_makeImageFromTexture`, `_makeFromGenerator`, `_resetContext` |
| `CanvasKit.MakeSWCanvasSurface` | GPU 回退时使用（定义在 `cpu.js`） |
| `CanvasKit.ColorType` / `AlphaType` / `ColorSpace` | 图像信息常量 |

## 设计模式与设计决策

- **优雅降级**: GPU 渲染失败时自动回退到软件渲染，对用户透明
- **延迟初始化**: `MakeLazyImageFromTextureSource` 延迟纹理上传到首次绘制时，适用于预加载大量图像的场景
- **上下文亲和性**: 每个 Surface 和 GrDirectContext 记录其关联的 WebGL 上下文 `_context`，操作前自动切换
- **指针交换技巧**: `updateTextureFromSource` 通过交换 Emscripten embind 内部指针（`$$. ptr`）来"就地更新"一个不可变对象，是对 Skia Image 不可变性约束的务实绕过
- **纹理注册管理**: 通过 `pushTexture` 统一管理纹理在 Emscripten GL 状态中的注册，避免 ID 冲突
- **默认 WebGL 优先**: `MakeCanvasSurface` 默认指向 `MakeWebGLCanvasSurface`，优先使用 GPU 加速

## 性能考量

- WebGL 上下文创建是重量级操作，应避免频繁创建/销毁
- `makeImageFromTextureSource` 在每次调用时都会创建新纹理并上传像素数据，适合一次性创建
- `updateTextureFromSource` 重用现有纹理对象，仅更新内容，适合视频帧连续更新场景
- `MakeLazyImageFromTextureSource` 延迟纹理上传，减少初始化时的 GPU 负载
- `GrDirectContext` 的资源缓存管理允许应用控制 GPU 内存使用上限
- 预乘 Alpha 在 GPU 上传时一次性完成，避免逐像素 CPU 处理
- 多个上下文场景需要频繁调用 `setCurrentContext`，有一定的状态切换开销

## 相关文件

- `modules/canvaskit/cpu.js` — CPU/软件渲染后端（互补实现）
- `modules/canvaskit/canvaskit_bindings.cpp` — C++ 端 GPU 相关绑定
- `modules/canvaskit/memory.js` — 内存管理工具
- `include/gpu/GrDirectContext.h` — Skia GPU 上下文头文件
- `include/core/SkSurface.h` — Skia 渲染表面头文件
