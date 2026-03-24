# include/gpu/ganesh/gl/win - Windows WGL 平台 OpenGL 接口

## 概述

`include/gpu/ganesh/gl/win` 目录提供了在 Windows 平台上通过 WGL (Windows GL) 创建 Ganesh
OpenGL 接口的入口。WGL 是 Windows 操作系统上 OpenGL 的本地接口层，负责在 Win32 设备上下文
（HDC）和 OpenGL 渲染上下文之间建立连接。

此目录仅包含一个头文件 `GrGLMakeWinInterface.h`，提供了通过 WGL 环境获取 GL 函数指针并
创建 `GrGLInterface` 的工厂函数。在 Windows 平台上，OpenGL 的核心函数和扩展函数的获取方式
不同，此接口封装了这些差异。

注意：在 Windows 上获取 OpenGL 扩展函数指针需要一个有效的 OpenGL 渲染上下文已被创建和绑定。

## 架构图

```
include/gpu/ganesh/gl/win/
    |
    +-- GrGLMakeWinInterface.h
            |
            +-- GrGLInterfaces::MakeWin()
                    |
                    +--> sk_sp<const GrGLInterface>
                            |
                            +--> GrDirectContexts::MakeGL(interface)
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrGLMakeWinInterface.h` | Windows WGL 平台 GL 接口创建函数 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `GrGLInterfaces::MakeWin()` 函数

```cpp
namespace GrGLInterfaces {
    sk_sp<const GrGLInterface> MakeWin();
}
```

通过 `wglGetProcAddress` 和 `GetProcAddress(opengl32.dll)` 获取 GL 函数指针，
创建并返回完整的 `GrGLInterface`。返回的接口适用于桌面 OpenGL 上下文。

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/gl/GrGLInterface.h`
- **系统依赖**: `opengl32.dll`, WGL
- **平台**: Windows

## 相关文档与参考

- `include/gpu/ganesh/gl/` - GL 后端主目录
- WGL 文档: https://docs.microsoft.com/en-us/windows/win32/opengl/wgl-functions
