# include/gpu/ganesh/gl/egl - EGL 平台 OpenGL 接口

## 概述

`include/gpu/ganesh/gl/egl` 目录提供了在 EGL 平台（主要用于 Android 和 Linux）上创建 Ganesh
OpenGL 接口的入口。EGL（Embedded-System Graphics Library）是 Khronos Group 定义的用于连接
OpenGL ES 和本地窗口系统的接口层，在 Android 平台上是默认的 GL 上下文管理 API。

此目录仅包含一个头文件 `GrGLMakeEGLInterface.h`，提供了通过 EGL 环境获取 GL 函数指针并
创建 `GrGLInterface` 的工厂函数。创建的接口可以传递给 `GrDirectContexts::MakeGL()` 来
初始化 Ganesh OpenGL 后端。

EGL 接口适用于使用 OpenGL ES 的 Android 应用和使用 EGL 的 Linux 桌面应用。
在 Linux 上，如果应用程序不使用 X11/GLX 而是直接使用 EGL（如 Wayland 环境），则应使用此接口。

## 架构图

```
include/gpu/ganesh/gl/egl/
    |
    +-- GrGLMakeEGLInterface.h
            |
            +-- GrGLInterfaces::MakeEGL()
                    |
                    +--> sk_sp<const GrGLInterface>
                            |
                            +--> GrDirectContexts::MakeGL(interface)
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrGLMakeEGLInterface.h` | EGL 平台 GL 接口创建函数 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `GrGLInterfaces::MakeEGL()` 函数

```cpp
namespace GrGLInterfaces {
    sk_sp<const GrGLInterface> MakeEGL();
}
```

使用 EGL 的 `eglGetProcAddress` 获取 GL 函数指针，创建并返回完整的 `GrGLInterface`。
返回的接口适用于 OpenGL ES 上下文。

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/gl/GrGLInterface.h`
- **系统依赖**: EGL 库 (`libEGL.so`)
- **平台**: Android, Linux (with EGL)

## 相关文档与参考

- `include/gpu/ganesh/gl/` - GL 后端主目录
- `include/gpu/ganesh/gl/GrGLDirectContext.h` - GL 上下文创建
- EGL 规范: https://www.khronos.org/egl/
