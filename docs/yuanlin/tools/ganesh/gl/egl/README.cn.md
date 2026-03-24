# tools/ganesh/gl/egl - EGL 平台 OpenGL/GLES 测试上下文

## 概述

`tools/ganesh/gl/egl` 目录实现了基于 EGL（Embedded-System Graphics Library）的 OpenGL/OpenGL ES 测试上下文。EGL 是 Khronos 定义的跨平台图形上下文管理 API，主要用于 Linux（包括 Android）和嵌入式系统平台，提供了统一的 OpenGL ES 上下文创建和管理接口。

本目录包含 `CreatePlatformGLTestContext_egl.cpp`，它是 `CreatePlatformGLTestContext()` 工厂函数在 EGL 平台上的具体实现。`EGLGLTestContext` 类继承自 `GLTestContext`，使用 EGL API 管理 GL 上下文的生命周期，包括 EGLDisplay、EGLSurface 和 EGLContext 的创建和销毁。

该实现的一个重要特性是支持受保护内容（Protected Content）。当全局变量 `gCreateProtectedContext` 为 true 时，上下文会启用 `EGL_PROTECTED_CONTENT_EXT` 扩展，这对于 DRM（Digital Rights Management）内容的渲染测试非常重要。

此外，`EGLGLTestContext` 还完整实现了 EGL 图像互操作功能：`texture2DToEGLImage()` 将 GL 2D 纹理包装为 EGL 图像，`eglImageToExternalTexture()` 将 EGL 图像包装为 `GL_TEXTURE_EXTERNAL_OES` 纹理。这些功能用于测试跨 API 的纹理共享。

上下文恢复功能通过捕获当前的 EGL Display、Surface 和 Context，并在析构时恢复来实现，确保测试上下文的切换不会影响其他 GL 代码的执行。

## 目录结构

```
tools/ganesh/gl/egl/
├── BUILD.bazel                              # Bazel 构建配置
└── CreatePlatformGLTestContext_egl.cpp      # EGL 平台 GL 测试上下文实现
```

## 关键类与函数

### EGLGLTestContext
- **基类**: `sk_gpu_test::GLTestContext`
- **功能**: 基于 EGL 的 OpenGL/GLES 测试上下文
- **核心特性**:
  - 支持 GL 和 GLES 两种标准
  - 支持受保护内容（`EGL_PROTECTED_CONTENT_EXT`）
  - 支持 EGL 图像互操作
  - 支持上下文共享组
- **EGL 图像方法**:
  - `texture2DToEGLImage(GrGLuint texID)` - 将 GL 2D 纹理封装为 EGLImage
  - `destroyEGLImage(GrEGLImage)` - 销毁 EGLImage
  - `eglImageToExternalTexture(GrEGLImage)` - 将 EGLImage 封装为外部纹理
- **上下文管理**:
  - `onPlatformMakeCurrent()` - 调用 `eglMakeCurrent()` 设置当前上下文
  - `onPlatformMakeNotCurrent()` - 解除当前上下文绑定
  - `onPlatformGetAutoContextRestore()` - 捕获并恢复之前的 EGL 状态
  - `onPlatformGetProcAddress()` - 通过 `eglGetProcAddress()` 查询函数指针

### context_restorer 函数
- 捕获当前 EGL 显示设备、绘制/读取表面和上下文
- 返回一个 lambda 用于在 RAII 析构时恢复先前状态

## 依赖关系

- **上游依赖**: `tools/ganesh/gl/GLTestContext.h`（基类）
- **EGL 依赖**: `EGL/egl.h`、`EGL/eglext.h`（EGL 库头文件）
- **GL 依赖**: `include/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.h`
- **编译条件**: EGL 可用的平台（主要是 Linux/Android）
- **被引用**: `tools/ganesh/gl/GLTestContext.h`（通过 `CreatePlatformGLTestContext` 调用）

## EGL 初始化流程

`EGLGLTestContext` 的构造函数按以下步骤初始化：

1. **获取 EGL Display**: 调用 `eglGetDisplay(EGL_DEFAULT_DISPLAY)`
2. **初始化 EGL**: 调用 `eglInitialize()` 获取 EGL 版本
3. **选择配置**: 通过 `eglChooseConfig()` 选择合适的帧缓冲配置
   - 如果启用受保护内容，配置中包含 `EGL_PROTECTED_CONTENT_EXT` 属性
4. **创建表面**: 使用 `eglCreatePbufferSurface()` 创建离屏 P-Buffer 表面
5. **创建上下文**: 通过 `eglCreateContext()` 创建 GL/GLES 上下文
   - 支持通过 `shareContext` 参数创建共享上下文
6. **激活上下文**: 调用 `eglMakeCurrent()` 绑定上下文
7. **加载接口**: 通过 `GrGLMakeEGLInterface()` 创建 GrGLInterface

## 受保护内容支持

当 `gCreateProtectedContext` 全局变量为 true 时：
- EGL 配置包含 `EGL_PROTECTED_CONTENT_EXT = EGL_TRUE`
- P-Buffer 表面创建时添加受保护内容属性
- 上下文创建时启用受保护内容支持
- 此功能主要用于 Android 上的 DRM 视频解码和渲染测试

## 相关文档与参考

- `tools/ganesh/gl/GLTestContext.h` - OpenGL 测试上下文基类
- EGL 规范: https://www.khronos.org/egl
- `EGL_PROTECTED_CONTENT_EXT` 扩展用于 DRM 内容保护测试
- `tools/gpu/ProtectedUtils.h` - 受保护内容测试工具
