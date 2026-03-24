# include/gpu/ganesh/gl/glx - GLX 平台 OpenGL 接口

## 概述

`include/gpu/ganesh/gl/glx` 目录提供了在 GLX 平台（X11/Linux 桌面）上创建 Ganesh OpenGL
接口的入口。GLX 是 X Window System 上 OpenGL 的扩展，用于在 X11 环境中管理 OpenGL 渲染上下文。

此目录仅包含一个头文件 `GrGLMakeGLXInterface.h`，提供了通过 GLX 环境获取 GL 函数指针并
创建 `GrGLInterface` 的工厂函数。创建的接口适用于使用 X11 窗口系统的 Linux 桌面应用程序。

对于使用 Wayland 或不依赖 X11 的 Linux 环境，应使用 EGL 接口替代。

## 架构图

```
include/gpu/ganesh/gl/glx/
    |
    +-- GrGLMakeGLXInterface.h
            |
            +-- GrGLInterfaces::MakeGLX()
                    |
                    +--> sk_sp<const GrGLInterface>
                            |
                            +--> GrDirectContexts::MakeGL(interface)
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrGLMakeGLXInterface.h` | GLX 平台 GL 接口创建函数 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `GrGLInterfaces::MakeGLX()` 函数

```cpp
namespace GrGLInterfaces {
    sk_sp<const GrGLInterface> MakeGLX();
}
```

使用 GLX 的 `glXGetProcAddress` / `glXGetProcAddressARB` 获取 GL 函数指针，
创建并返回完整的 `GrGLInterface`。返回的接口适用于桌面 OpenGL 上下文。

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/gl/GrGLInterface.h`
- **系统依赖**: GLX 库 (`libGL.so`), X11
- **平台**: Linux (X11)

## 相关文档与参考

- `include/gpu/ganesh/gl/` - GL 后端主目录
- `include/gpu/ganesh/gl/egl/` - EGL 平台接口（Wayland/Android）
- GLX 规范: https://www.khronos.org/opengl/wiki/Programming_OpenGL_in_Linux:_GLX
