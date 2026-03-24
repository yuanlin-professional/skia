# tools/ganesh/gl/glx - X11 GLX 平台 OpenGL 测试上下文

## 概述

`tools/ganesh/gl/glx` 目录实现了基于 GLX（OpenGL Extension to the X Window System）的 OpenGL 测试上下文。GLX 是 X Window System 上的 OpenGL 扩展，提供了在 X11 窗口中创建和管理 OpenGL 渲染上下文的功能。

本目录包含 `CreatePlatformGLTestContext_glx.cpp`，它是 `CreatePlatformGLTestContext()` 工厂函数在 X11/Linux 桌面平台上的实现。该实现使用 GLX API 创建 OpenGL 上下文，包括打开 X11 Display 连接、选择合适的 Visual 配置、创建 GLX 上下文和 Pixmap 离屏渲染表面。

GLX 是 Linux 桌面环境中传统的 OpenGL 上下文管理方式。与 EGL 相比，GLX 更紧密地绑定到 X11 窗口系统，但可以直接支持桌面 OpenGL（而非仅 GLES）。在现代 Linux 系统中，EGL 后端（`tools/ganesh/gl/egl/`）通常是更通用的选择，因为它同时支持 GL 和 GLES，且不依赖于 X11。

该实现通过 `glXGetCurrentContext()` 和 `glXMakeCurrent()` 管理上下文的激活状态，通过 `glXGetProcAddress()` 查询 GL 函数指针。GLX 上下文支持共享组（share groups），允许多个上下文共享纹理和其他 GL 对象。

本目录的代码在 Linux/X11 平台上编译，需要 X11 和 GLX 库支持。

## 目录结构

```
tools/ganesh/gl/glx/
├── BUILD.bazel                              # Bazel 构建配置
└── CreatePlatformGLTestContext_glx.cpp      # X11 GLX 测试上下文实现
```

## 关键类与函数

### GLXGLTestContext（内部类）
- **基类**: `sk_gpu_test::GLTestContext`
- **功能**: 基于 GLX 的 X11 OpenGL 测试上下文
- **核心成员**:
  - X11 Display 连接
  - GLX Context 对象
  - GLX Pixmap 离屏渲染表面
- **上下文管理**:
  - `onPlatformMakeCurrent()` - 调用 `glXMakeCurrent()`
  - `onPlatformMakeNotCurrent()` - 调用 `glXMakeCurrent(display, None, nullptr)`
  - `onPlatformGetProcAddress()` - 调用 `glXGetProcAddress()`

### CreatePlatformGLTestContext（GLX 实现）
- 打开 X11 Display 连接
- 选择合适的 GLX FBConfig/Visual
- 创建 GLX 上下文和离屏 Pixmap
- 支持上下文共享

### 上下文恢复
- 保存当前 GLX Display、Drawable 和 Context
- 在析构时恢复先前的 GLX 状态

## 依赖关系

- **上游依赖**: `tools/ganesh/gl/GLTestContext.h`（基类）
- **平台依赖**: X11 库（`libX11`）、GLX 库（`libGL`）
- **GL 接口**: `include/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.h`
- **编译条件**: Linux/X11 平台
- **替代方案**: `tools/ganesh/gl/egl/` 在现代 Linux 上是更通用的选择

## GLX 上下文创建流程

1. **打开 Display**: 调用 `XOpenDisplay(nullptr)` 连接到 X Server
2. **选择 FBConfig**: 使用 `glXChooseFBConfig()` 选择帧缓冲配置
   - 请求 RGBA 颜色缓冲
   - 请求模板缓冲
   - 支持 Pixmap 和窗口渲染
3. **创建上下文**: 调用 `glXCreateNewContext()` 或 `glXCreateContextAttribsARB()`
   - 后者可请求核心配置文件或特定 GL 版本
   - 支持共享上下文用于跨上下文共享 GL 对象
4. **创建 Pixmap**: 创建 X11 Pixmap 和 GLX Pixmap 作为离屏渲染目标
5. **激活上下文**: 调用 `glXMakeCurrent()` 绑定上下文到 Pixmap

## GLX vs EGL 对比

| 特性 | GLX | EGL |
|------|-----|-----|
| 窗口系统 | 仅 X11 | 平台无关 |
| GL 标准 | 桌面 GL | GL + GLES |
| API 风格 | X11 集成 | 独立接口 |
| Wayland 支持 | 不支持 | 支持 |
| 离屏渲染 | Pixmap | PBuffer |
| 函数查询 | `glXGetProcAddress` | `eglGetProcAddress` |

在现代 Linux 桌面上，EGL 通常是更好的选择，因为它：
- 不依赖 X11（支持 Wayland）
- 同时支持 GL 和 GLES
- 在无头（headless）环境中更容易使用

GLX 后端主要用于需要直接 X11 集成的场景，或在某些只提供 GLX 的旧系统上使用。

## 相关文档与参考

- `tools/ganesh/gl/GLTestContext.h` - OpenGL 测试上下文基类
- `tools/ganesh/gl/egl/` - EGL 平台实现（更现代的替代方案）
- GLX 规范: https://www.khronos.org/registry/OpenGL/specs/gl/glx1.4.pdf
- X11 文档: https://www.x.org/wiki/
