# include/gpu/ganesh/gl/mac - macOS CGL 平台 OpenGL 接口

## 概述

`include/gpu/ganesh/gl/mac` 目录提供了在 macOS 平台上通过 CGL (Core OpenGL) 创建 Ganesh
OpenGL 接口的入口。CGL 是 macOS 上 OpenGL 的底层 C 语言接口，提供了 OpenGL 渲染上下文的
创建和管理功能。

此目录仅包含一个头文件 `GrGLMakeMacInterface.h`，提供了通过 macOS 的 OpenGL 框架获取
GL 函数指针并创建 `GrGLInterface` 的工厂函数。

注意：Apple 已在 macOS 10.14 中弃用 OpenGL，推荐使用 Metal 替代。Skia 的 Metal 后端
（`include/gpu/ganesh/mtl/` 和 `include/gpu/graphite/mtl/`）是 Apple 平台上更推荐的选择。

## 架构图

```
include/gpu/ganesh/gl/mac/
    |
    +-- GrGLMakeMacInterface.h
            |
            +-- GrGLInterfaces::MakeMac()
                    |
                    +--> sk_sp<const GrGLInterface>
                            |
                            +--> GrDirectContexts::MakeGL(interface)
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrGLMakeMacInterface.h` | macOS CGL 平台 GL 接口创建函数 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `GrGLInterfaces::MakeMac()` 函数

```cpp
namespace GrGLInterfaces {
    sk_sp<const GrGLInterface> MakeMac();
}
```

通过 macOS OpenGL 框架获取 GL 函数指针，创建并返回完整的 `GrGLInterface`。
返回的接口适用于桌面 OpenGL 上下文。

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/gl/GrGLInterface.h`
- **系统依赖**: macOS OpenGL 框架
- **平台**: macOS (已弃用，推荐 Metal)

## 相关文档与参考

- `include/gpu/ganesh/gl/` - GL 后端主目录
- `include/gpu/ganesh/mtl/` - Metal 后端（macOS 推荐）
- Apple OpenGL 弃用说明: https://developer.apple.com/library/archive/documentation/GraphicsImaging/Conceptual/OpenGL-MacOS/
