# tools/ganesh/gl/angle - ANGLE OpenGL ES 模拟层测试上下文

## 概述

`tools/ganesh/gl/angle` 目录实现了通过 ANGLE（Almost Native Graphics Layer Engine）创建 OpenGL ES 测试上下文的功能。ANGLE 是 Google 开发的跨平台 OpenGL ES 兼容层，能够将 OpenGL ES API 调用转换为其他图形 API（如 Direct3D 9、Direct3D 11、桌面 OpenGL 或 Metal）的调用。

在 Skia 的测试体系中，ANGLE 后端使得开发者能够在多种底层图形 API 上测试 OpenGL ES 代码路径，即使原生平台不直接支持 OpenGL ES。例如，在 Windows 上可以通过 D3D11 后端运行 GLES 测试，在 macOS 上可以通过 Metal 后端运行 GLES 测试。

`GLTestContext_angle.h` 定义了两个关键枚举和一个工厂函数。`ANGLEBackend` 枚举指定底层图形 API（`kD3D9`、`kD3D11`、`kOpenGL`、`kMetal`），`ANGLEContextVersion` 枚举指定 GLES 版本（`kES2` 或 `kES3`）。`MakeANGLETestContext()` 工厂函数根据这些参数创建对应配置的 ANGLE 测试上下文。

ANGLE 后端在 `GrContextFactory` 中注册了多种上下文类型，包括 `kANGLE_D3D9_ES2`、`kANGLE_D3D11_ES2`、`kANGLE_D3D11_ES3`、`kANGLE_GL_ES2`、`kANGLE_GL_ES3`、`kANGLE_Metal_ES2` 和 `kANGLE_Metal_ES3`。值得注意的是，D3D9 后端在 NVIDIA 驱动上存在已知的着色器链接问题，因此代码中包含了针对 NVIDIA 的特殊处理。

所有代码受 `SK_ANGLE` 编译宏保护。

## 目录结构

```
tools/ganesh/gl/angle/
├── GLTestContext_angle.h      # ANGLE 测试上下文声明
└── GLTestContext_angle.cpp    # ANGLE 测试上下文实现
```

## 关键类与函数

### ANGLEBackend 枚举
- `kD3D9` - 使用 Direct3D 9 作为底层渲染 API
- `kD3D11` - 使用 Direct3D 11 作为底层渲染 API
- `kOpenGL` - 使用桌面 OpenGL 作为底层渲染 API
- `kMetal` - 使用 Apple Metal 作为底层渲染 API

### ANGLEContextVersion 枚举
- `kES2` - 创建 OpenGL ES 2.0 上下文
- `kES3` - 创建 OpenGL ES 3.0 上下文

### MakeANGLETestContext
- **命名空间**: `sk_gpu_test`
- **签名**: `std::unique_ptr<GLTestContext> MakeANGLETestContext(ANGLEBackend, ANGLEContextVersion, GLTestContext* shareContext, void* display)`
- **功能**: 创建指定配置的 ANGLE 测试上下文
- **参数**: 后端类型、ES 版本、可选共享上下文和 EGL Display

### CreateANGLEGLInterface
- **签名**: `sk_sp<const GrGLInterface> CreateANGLEGLInterface()`
- **功能**: 为当前 ANGLE GLES 上下文创建 GrGLInterface 函数指针表

## 依赖关系

- **上游依赖**: `tools/ganesh/gl/GLTestContext.h`（基类）
- **ANGLE 依赖**: ANGLE 库（libEGL、libGLESv2）
- **编译条件**: 需要定义 `SK_ANGLE`
- **被引用**: `tools/ganesh/GrContextFactory.cpp`（通过多个 ANGLE ContextType 使用）
- **已知问题**: D3D9 后端在 NVIDIA 最新驱动上可能遇到着色器链接失败

## ANGLE 上下文类型列表

| ContextType | 后端 | GLES 版本 | 说明 |
|------------|------|----------|------|
| `kANGLE_D3D9_ES2` | Direct3D 9 | ES 2.0 | 仅 Windows；NVIDIA 驱动存在已知问题 |
| `kANGLE_D3D11_ES2` | Direct3D 11 | ES 2.0 | Windows 主要测试后端 |
| `kANGLE_D3D11_ES3` | Direct3D 11 | ES 3.0 | Windows 高级特性测试 |
| `kANGLE_GL_ES2` | 桌面 OpenGL | ES 2.0 | 跨平台 GLES 模拟 |
| `kANGLE_GL_ES3` | 桌面 OpenGL | ES 3.0 | 跨平台高级 GLES 模拟 |
| `kANGLE_Metal_ES2` | Apple Metal | ES 2.0 | macOS/iOS GLES 模拟 |
| `kANGLE_Metal_ES3` | Apple Metal | ES 3.0 | macOS/iOS 高级 GLES 模拟 |

## NVIDIA D3D9 兼容性说明

在 `GrContextFactory` 的实现中，当创建 `kANGLE_D3D9_ES2` 上下文时，代码会检测 NVIDIA 驱动。Chrome 仅在 2012 年及更早的 NVIDIA 驱动版本（<= 269.73）上支持 D3D9 后端。在较新的 NVIDIA 驱动上，使用此后端会导致着色器链接失败。因此，如果检测到 NVIDIA GPU，代码会直接返回空的 `ContextInfo`，跳过此后端的测试。

## 内部实现细节

ANGLE 测试上下文在内部使用 EGL API（ANGLE 提供的 EGL 实现）来管理 GL 上下文：
- 使用 `eglGetDisplay(EGL_DEFAULT_DISPLAY)` 获取 EGL 显示
- 通过 `eglBindAPI(EGL_OPENGL_ES_API)` 绑定 GLES API
- 使用 `eglCreateContext()` 创建指定 ES 版本的上下文
- GL 函数指针通过 `eglGetProcAddress()` 获取

## 相关文档与参考

- `tools/ganesh/gl/GLTestContext.h` - OpenGL 测试上下文基类
- `tools/ganesh/GrContextFactory.h` - 上下文工厂（注册了 7 种 ANGLE 上下文类型）
- ANGLE 项目: https://chromium.googlesource.com/angle/angle
- `include/gpu/ganesh/gl/GrGLInterface.h` - GL 接口定义
