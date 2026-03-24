# glx/ - GLX 平台 OpenGL 接口 (Linux/X11)

## 概述

`glx/` 目录提供基于 GLX (OpenGL Extension to the X Window System) 的 OpenGL 接口加载实现。GLX 是将 OpenGL 集成到 X Window System 中的标准协议扩展，主要用于 Linux 和其他 Unix-like 桌面系统。

与 EGL 版本不同，GLX 版本组装的是完整的桌面 OpenGL 接口，支持 OpenGL 的所有桌面特性。该实现通过 `glXGetProcAddress()` 获取所有 GL 函数指针。

## 文件分类索引

### 1. GLX 接口实现 — GLX Platform Interface

| 文件 | 说明 |
|------|------|
| GrGLMakeGLXInterface.cpp | GLX GL 接口创建核心实现（glXGetProcAddress） |
| GrGLMakeNativeInterface_glx.cpp | GLX 原生接口入口（旧版兼容） |

## 关键实现

### GrGLInterfaces::MakeGLX()

```cpp
static GrGLFuncPtr glx_get(void* ctx, const char name[]) {
    // 过滤EGL函数名，避免glXGetProcAddress返回无效指针
    if (0 == strncmp(name, "egl", 3)) {
        return nullptr;
    }
    SkASSERT(nullptr == ctx);
    SkASSERT(glXGetCurrentContext());
    return glXGetProcAddress(reinterpret_cast<const GLubyte*>(name));
}

namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeGLX() {
    if (nullptr == glXGetCurrentContext()) {
        return nullptr;
    }
    return GrGLMakeAssembledInterface(nullptr, glx_get);
}
}
```

**实现细节：**
1. 首先检查是否有活跃的 GLX 上下文（`glXGetCurrentContext()`）
2. 所有函数指针通过 `glXGetProcAddress()` 获取
3. **EGL 函数过滤：** 特别处理了以 `"egl"` 开头的函数名。某些 GL 实现的 `glXGetProcAddress` 会为 EGL 函数返回非空但无效的指针，因此需要主动过滤
4. 调用 `GrGLMakeAssembledInterface()` 自动检测版本并组装接口

**设计考虑：**
- 需要 `GLX_GLXEXT_PROTOTYPES` 宏以获取 `glXGetProcAddress` 的原型声明
- 使用 `nullptr` 作为上下文参数（GLX 不需要库句柄）
- 断言要求必须有活跃的 GLX 上下文

## 编译条件

- 需要 X11 和 GLX 头文件（`<GL/gl.h>`, `<GL/glx.h>`）
- 需要链接 GL 库（`-lGL`）和 X11 库（`-lX11`）
- 定义 `GLX_GLXEXT_PROTOTYPES` 宏

## 旧版兼容

`GrGLMakeNativeInterface_glx.cpp` 提供旧版 `GrGLMakeNativeInterface()` 接口，委托给 `GrGLInterfaces::MakeGLX()`。在未定义 `SK_DISABLE_LEGACY_GLXINTERFACE_FACTORY` 时编译旧版 `GrGLMakeGLXInterface()` 函数。

## 依赖关系

- **上游：** 由 Linux 桌面环境下的 Skia 初始化代码调用
- **下游：** 依赖 `GrGLMakeAssembledInterface()`（支持GL和GLES自动检测）
- **系统依赖：** X11, GLX, OpenGL (Mesa/NVIDIA/AMD驱动)

## 适用平台

- Linux + X11 桌面环境（GNOME, KDE 等）
- 其他使用 X Window System 的 Unix-like 系统
- 通过 XWayland 桥接的 Wayland 环境（部分支持）
