# include/gpu/ganesh/gl/epoxy - libepoxy EGL 平台 OpenGL 接口

## 概述

`include/gpu/ganesh/gl/epoxy` 目录提供了通过 libepoxy 库在 EGL 环境下创建 Ganesh OpenGL
接口的入口。libepoxy 是一个 OpenGL 函数指针管理库，它简化了 GL 函数的加载过程，自动处理
扩展和版本差异，在 Linux 桌面环境（如 GNOME/GTK 应用）中被广泛使用。

此目录仅包含一个头文件 `GrGLMakeEpoxyEGLInterface.h`，提供了通过 libepoxy 的 EGL 模块
获取 GL 函数指针并创建 `GrGLInterface` 的工厂函数。

当应用程序已经使用 libepoxy 管理 GL 函数加载时（如基于 GTK 的应用），使用此接口可以确保
Skia 与应用程序使用相同的 GL 函数指针，避免潜在的冲突。

## 架构图

```
include/gpu/ganesh/gl/epoxy/
    |
    +-- GrGLMakeEpoxyEGLInterface.h
            |
            +-- GrGLInterfaces::MakeEpoxyEGL()
                    |
                    +--> sk_sp<const GrGLInterface>
                            |
                            +--> GrDirectContexts::MakeGL(interface)
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrGLMakeEpoxyEGLInterface.h` | libepoxy EGL 平台 GL 接口创建函数 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `GrGLInterfaces::MakeEpoxyEGL()` 函数

```cpp
namespace GrGLInterfaces {
    sk_sp<const GrGLInterface> MakeEpoxyEGL();
}
```

使用 libepoxy 的 EGL 集成获取 GL 函数指针，创建并返回完整的 `GrGLInterface`。

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/gl/GrGLInterface.h`
- **系统依赖**: libepoxy (`libepoxy.so`)
- **平台**: Linux (with libepoxy)

## 相关文档与参考

- `include/gpu/ganesh/gl/` - GL 后端主目录
- `include/gpu/ganesh/gl/egl/` - 标准 EGL 接口
- libepoxy: https://github.com/anholt/libepoxy
