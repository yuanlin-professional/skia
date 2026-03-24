# epoxy/ - libepoxy 封装的 EGL 接口

## 概述

`epoxy/` 目录提供基于 `libepoxy` 库封装的 EGL/OpenGL ES 接口加载实现。libepoxy 是一个开源的 GL 函数指针加载库，它提供了一种简洁的方式来管理 OpenGL 函数的加载和分发，自动处理不同 GL 版本和扩展之间的差异。

该实现适用于使用 libepoxy 而非直接链接 EGL/GLES 库的 Linux 环境。通过 libepoxy 的封装函数（`epoxy_` 前缀），实现了对底层 GL 函数的间接访问。

## 文件分类索引

### 1. Epoxy EGL 接口 — libepoxy Platform Interface

| 文件 | 说明 |
|------|------|
| GrGLMakeEpoxyEGLInterface.cpp | libepoxy EGL 接口创建实现 |

## 关键实现

### GrGLInterfaces::MakeEpoxyEGL()

```cpp
static GrGLFuncPtr epoxy_get_gl_proc(void* ctx, const char name[]) {
    SkASSERT(nullptr == ctx);
    #define M(X) if (0 == strcmp(#X, name)) { return (GrGLFuncPtr) epoxy_ ## X; }
    GR_GL_CORE_FUNCTIONS_EACH(M)
    #undef M
    return epoxy_eglGetProcAddress(name);
}

namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeEpoxyEGL() {
    return GrGLMakeAssembledInterface(nullptr, epoxy_get_gl_proc);
}
}
```

**与标准 EGL 实现的区别：**
1. 核心函数通过 `epoxy_` 前缀函数获取（如 `epoxy_glBindTexture` 替代 `glBindTexture`）
2. 扩展函数通过 `epoxy_eglGetProcAddress()` 而非 `eglGetProcAddress()` 获取
3. libepoxy 自动处理函数指针的延迟加载和版本分发

**`GR_GL_CORE_FUNCTIONS_EACH(M)` 宏展开：**
对于每个核心 GL 函数名 `X`，将函数指针映射到 `epoxy_X`。例如：
- `glBindTexture` -> `epoxy_glBindTexture`
- `glDrawArrays` -> `epoxy_glDrawArrays`

## libepoxy 的优势

- **自动延迟加载：** 函数指针在首次调用时才解析，避免了启动时的开销
- **版本无关：** 自动选择最佳的函数实现（核心 vs 扩展）
- **简化链接：** 不需要直接链接 GL/GLES 库
- **多上下文支持：** 正确处理不同 GL 上下文间的函数指针差异

## 编译条件

- 需要安装 libepoxy 开发库
- 包含 `<epoxy/egl.h>` 和 `<epoxy/gl.h>` 头文件
- 链接 `libepoxy` 库

## 依赖关系

- **上游：** 由配置使用 libepoxy 的 Linux 构建环境调用
- **下游：** 依赖 `GrGLMakeAssembledInterface()` 和 `GrGLCoreFunctions.h`
- **系统依赖：** libepoxy (https://github.com/anholt/libepoxy)

## 适用平台

- Linux 桌面环境（特别是 GNOME/GTK 生态，GTK 本身使用 libepoxy）
- Flatpak/Snap 沙箱应用（libepoxy 简化了 GL 加载的复杂性）
- 使用 Wayland + EGL 的现代 Linux 桌面
