# egl/ - EGL 平台 OpenGL ES 接口

## 概述

`egl/` 目录提供基于 EGL (Embedded-System Graphics Library) 的 OpenGL ES 接口加载实现。EGL 是 Khronos 定义的用于管理 OpenGL ES 图形上下文的平台无关 API，广泛用于 Android、Linux 嵌入式系统和部分桌面 Linux 环境。

该目录的实现采用混合策略：核心 GL 函数通过编译时链接直接获取，扩展函数通过 `eglGetProcAddress()` 在运行时动态获取。这种方式确保了核心函数的调用效率，同时保持了对扩展的灵活支持。

## 文件分类索引

### 1. EGL 接口实现 — EGL Platform Interface

| 文件 | 说明 |
|------|------|
| GrGLMakeEGLInterface.cpp | EGL GL 接口创建核心实现（混合链接 + eglGetProcAddress） |
| GrGLMakeNativeInterface_egl.cpp | EGL 原生接口入口（旧版兼容） |

## 关键实现

### GrGLInterfaces::MakeEGL()

```cpp
static GrGLFuncPtr egl_get_gl_proc(void* ctx, const char name[]) {
    SkASSERT(nullptr == ctx);
    #define M(X) if (0 == strcmp(#X, name)) { return (GrGLFuncPtr) X; }
    GR_GL_CORE_FUNCTIONS_EACH(M)
    #undef M
    return eglGetProcAddress(name);
}

namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeEGL() {
    return GrGLMakeAssembledInterface(nullptr, egl_get_gl_proc);
}
}
```

**函数加载策略：**
1. **核心函数：** 通过 `GR_GL_CORE_FUNCTIONS_EACH` 宏展开，直接使用编译时链接的函数符号（如 `glBindTexture`、`glDrawArrays` 等）
2. **扩展函数：** 通过 `eglGetProcAddress()` 在运行时按名称查找
3. 调用 `GrGLMakeAssembledInterface()` 自动检测 GL 标准类型并组装对应接口

**`GR_GL_CORE_FUNCTIONS_EACH` 宏的作用：**
该宏定义在 `GrGLCoreFunctions.h` 中，列举了所有 GL 核心函数。在编译时，这些函数会被直接解析为 GLES 头文件中声明的符号（需要 `GL_GLEXT_PROTOTYPES` 宏）。

## 编译条件

- 需要链接 EGL 库（`-lEGL`）和 GLES 库（`-lGLESv2`）
- 需要定义 `GL_GLEXT_PROTOTYPES` 以获取 GLES 扩展函数声明
- 包含 `<EGL/egl.h>` 和 `<GLES2/gl2.h>` 头文件

## 旧版兼容

`GrGLMakeNativeInterface_egl.cpp` 提供了 `GrGLMakeNativeInterface()` 的兼容实现，仅在未定义 `SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE` 时编译。

## 依赖关系

- **上游：** 由 Android 和 Linux 环境下的 Skia 初始化代码调用
- **下游：** 依赖 `GrGLMakeAssembledInterface()` 和 `GrGLCoreFunctions.h`
- **系统依赖：** EGL 库, GLES2/GLES3 库
- **被复用：** `android/GrGLMakeNativeInterface_android.cpp` 直接 `#include` 本目录的实现文件

## 适用平台

- Android（主要使用场景）
- Linux + Mesa EGL
- Raspberry Pi 等嵌入式 Linux
- ChromeOS
