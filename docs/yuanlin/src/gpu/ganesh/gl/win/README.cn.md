# win/ - Windows 平台 OpenGL 接口

## 概述

`win/` 目录提供 Windows 平台上的原生 OpenGL 接口加载实现。该目录通过 Windows 的动态链接机制（`LoadLibraryExA`/`GetProcAddress`）加载系统的 `opengl32.dll`，并结合 WGL 扩展加载机制（`wglGetProcAddress`）获取完整的 GL 函数指针集合。

Windows 上的 GL 实现需要同时使用两种函数获取方式：核心函数通过 `GetProcAddress` 从 `opengl32.dll` 获取，扩展函数通过 `wglGetProcAddress` 从当前 GL 上下文获取。该目录还支持自动检测当前上下文是桌面 GL 还是 GL ES（例如通过 ANGLE 运行的情况）。

**注意：** ARM64 Windows 不支持 OpenGL，相关函数会直接返回 `nullptr`。

## 文件分类索引

### 1. Windows GL 接口 — Windows Platform Interface

| 文件 | 说明 |
|------|------|
| GrGLMakeNativeInterface_win.cpp | Windows 原生接口入口（含 ARM64 空实现） |
| GrGLMakeWinInterface.cpp | Windows GL 接口创建核心实现（LoadLibrary + wglGetProcAddress） |

## 关键实现

### GrGLInterfaces::MakeWin()

```cpp
namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeWin() {
    if (nullptr == wglGetCurrentContext()) {
        return nullptr;
    }
    // 加载 opengl32.dll
    std::unique_ptr<...> module(
        LoadLibraryExA("opengl32.dll", NULL, LOAD_LIBRARY_SEARCH_SYSTEM32));
    // 函数加载器：先尝试 GetProcAddress，再尝试 wglGetProcAddress
    const GrGLGetProc win_get_gl_proc = [](void* ctx, const char* name) {
        if (GrGLFuncPtr p = (GrGLFuncPtr)GetProcAddress((HMODULE)ctx, name)) return p;
        if (GrGLFuncPtr p = (GrGLFuncPtr)wglGetProcAddress(name)) return p;
        return (GrGLFuncPtr)nullptr;
    };
    // 自动检测 GL 标准类型
    GrGLStandard standard = GrGLGetStandardInUseFromString(verStr);
    if (GR_IS_GR_GL_ES(standard))
        return GrGLMakeAssembledGLESInterface(...);
    else if (GR_IS_GR_GL(standard))
        return GrGLMakeAssembledGLInterface(...);
}
}
```

**实现细节：**
1. 首先检查是否有活跃的 WGL 上下文（`wglGetCurrentContext()`）
2. 使用 `LoadLibraryExA` 并指定 `LOAD_LIBRARY_SEARCH_SYSTEM32` 安全地加载系统 GL 库
3. 函数加载采用两级策略：先从 DLL 导出表查找，再从 WGL 扩展查找
4. 通过 `glGetString(GL_VERSION)` 自动判断当前是 Desktop GL 还是 GL ES
5. 根据检测结果调用对应的接口组装函数

### ARM64 特殊处理

在 `GrGLMakeNativeInterface_win.cpp` 中，`_M_ARM64` 平台的 `GrGLMakeNativeInterface()` 直接返回 `nullptr`，因为 ARM64 Windows 不提供原生 OpenGL 支持。

### Windows 调用约定

Windows 的 GL 函数使用 `__stdcall` 调用约定而非标准的 `__cdecl`。Skia 的 `GR_GL_FUNCTION_TYPE` 宏需要匹配此调用约定才能正确工作。

## 依赖关系

- **上游：** 由 `GrGLDirectContext.cpp` 或用户代码调用
- **下游：** 依赖 `GrGLMakeAssembledGLInterface()` 和 `GrGLMakeAssembledGLESInterface()`
- **系统依赖：** Windows `opengl32.dll`, `SkLeanWindows.h` (精简版 `windows.h`)
