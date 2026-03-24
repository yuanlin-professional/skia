# GrGLMakeWinInterface

> 源文件
> - include/gpu/ganesh/gl/win/GrGLMakeWinInterface.h
> - src/gpu/ganesh/gl/win/GrGLMakeWinInterface.cpp

## 概述

`GrGLMakeWinInterface` 模块为 Ganesh 渲染引擎提供 Windows 平台的 OpenGL 接口创建功能。该模块通过 Windows OpenGL（WGL）API 动态加载 OpenGL 函数指针，并创建适用于 Skia 的 `GrGLInterface` 对象。

该模块是 Skia 在 Windows 平台上使用 OpenGL 的桥梁，负责从系统的 `opengl32.dll` 库中加载函数，并根据当前 OpenGL 上下文的版本（桌面 GL 或 ES）组装相应的接口。

## 架构位置

该模块位于 Ganesh OpenGL 后端的平台特定层：

```
Skia Graphics Library
└── GPU (Ganesh)
    └── OpenGL Backend
        ├── GrGLInterface          ← 抽象接口
        ├── GrGLAssembleInterface  ← 接口组装器
        └── Platform Implementations
            ├── GrGLMakeWinInterface   ← 当前模块（Windows）
            ├── GrGLMakeEGLInterface   ← EGL
            ├── GrGLMakeGLXInterface   ← Linux/X11
            └── GrGLMakeEpoxyEGLInterface ← Epoxy
```

## 主要类与结构体

该模块不定义类，仅提供工厂函数。

## 公共 API 函数

### GrGLInterfaces 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `sk_sp<const GrGLInterface> MakeWin()` | 创建 Windows OpenGL 接口对象 |

**返回值**:
- 成功: 返回包含所有 OpenGL 函数指针的 `GrGLInterface` 智能指针
- 失败: 返回 `nullptr`（无当前上下文、无法加载 DLL 等）

## 内部实现细节

### 上下文检查

函数首先检查是否存在当前 WGL 上下文：

```cpp
if (nullptr == wglGetCurrentContext()) {
    return nullptr;
}
```

没有活动的 OpenGL 上下文时无法查询函数指针。

### DLL 加载

使用 RAII 包装器自动管理 DLL 生命周期：

```cpp
struct FreeModule {
    void operator()(HMODULE m) { (void)FreeLibrary(m); }
};

std::unique_ptr<typename std::remove_pointer<HMODULE>::type, FreeModule> module(
    LoadLibraryExA("opengl32.dll", NULL, LOAD_LIBRARY_SEARCH_SYSTEM32));

if (!module) {
    return nullptr;
}
```

**关键点**:
- 使用 `LOAD_LIBRARY_SEARCH_SYSTEM32` 标志确保从系统目录加载，防止 DLL 劫持攻击
- 自定义删除器 `FreeModule` 确保异常安全

### 函数指针获取策略

定义 Lambda 函数作为函数指针获取器：

```cpp
const GrGLGetProc win_get_gl_proc = [](void* ctx, const char* name) {
    SkASSERT(wglGetCurrentContext());
    // 1. 首先尝试从 opengl32.dll 获取（核心函数）
    if (GrGLFuncPtr p = (GrGLFuncPtr)GetProcAddress((HMODULE)ctx, name)) {
        return p;
    }
    // 2. 然后尝试从 WGL 获取（扩展函数）
    if (GrGLFuncPtr p = (GrGLFuncPtr)wglGetProcAddress(name)) {
        return p;
    }
    return (GrGLFuncPtr)nullptr;
};
```

**查找顺序**:
1. **核心函数**: 从 `opengl32.dll` 的导出表获取（如 `glGetString`）
2. **扩展函数**: 通过 `wglGetProcAddress` 获取（如 `glBindBuffer`）

这种顺序确保核心函数的获取更快，避免不必要的 WGL 调用。

### OpenGL 版本检测

在组装接口前，先检测 OpenGL 版本以确定是桌面 GL 还是 ES：

```cpp
GrGLGetStringFn* getString =
    (GrGLGetStringFn*)win_get_gl_proc((void*)module.get(), "glGetString");
if (!getString) {
    return nullptr;
}
const char* verStr = reinterpret_cast<const char*>(getString(GR_GL_VERSION));
GrGLStandard standard = GrGLGetStandardInUseFromString(verStr);
```

### 接口组装

根据检测到的标准调用相应的组装函数：

```cpp
if (GR_IS_GR_GL_ES(standard)) {
    return GrGLMakeAssembledGLESInterface((void*)module.get(), win_get_gl_proc);
} else if (GR_IS_GR_GL(standard)) {
    return GrGLMakeAssembledGLInterface((void*)module.get(), win_get_gl_proc);
}
return nullptr;
```

**组装过程**:
- 遍历所有 Skia 需要的 OpenGL 函数
- 使用 `win_get_gl_proc` 查找每个函数的地址
- 填充 `GrGLInterface` 结构体的函数指针表
- 验证必需的函数是否都已找到

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrGLInterface` | 提供 OpenGL 接口抽象 |
| `GrGLAssembleInterface` | 提供接口组装函数 |
| `GrGLUtil` | 提供 OpenGL 工具函数（版本检测等） |
| `SkLeanWindows` | 提供精简的 Windows 头文件 |
| `SkTypes` | 提供 Skia 基础类型 |
| `SkRefCnt` | 提供智能指针支持 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrContext` | 创建 Windows OpenGL 上下文 |
| `SkSurface` | 创建 Windows OpenGL 表面 |
| 应用程序 | 初始化 Skia GPU 支持 |

## 设计模式与设计决策

### 1. 工厂模式

`MakeWin()` 是工厂函数，负责创建和初始化复杂的 `GrGLInterface` 对象。

### 2. RAII 模式

使用 `std::unique_ptr` 和自定义删除器管理 DLL 句柄，确保资源自动释放。

### 3. 策略模式

通过 Lambda 函数传递函数指针获取策略，允许不同平台使用不同的实现。

### 4. 依赖注入

将 `module` 指针作为上下文传递给 Lambda，避免全局变量。

### 5. 防御性编程

每个关键步骤都有失败检查，返回 `nullptr` 表示初始化失败。

### 6. 安全 DLL 加载

使用 `LOAD_LIBRARY_SEARCH_SYSTEM32` 标志防止 DLL 劫持攻击，符合 Windows 安全最佳实践。

## 性能考量

### 1. 延迟加载

仅在需要时加载 `opengl32.dll`，避免不必要的启动开销。

### 2. 函数指针缓存

创建的 `GrGLInterface` 对象缓存所有函数指针，避免重复查找。

### 3. 快速路径优化

优先从 DLL 导出表查找核心函数，比 `wglGetProcAddress` 更快。

### 4. 智能指针开销

使用 `sk_sp` 智能指针管理接口生命周期，引用计数开销可忽略。

### 5. Lambda 内联

简单的 Lambda 函数可以被编译器内联，消除函数调用开销。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 接口抽象定义 |
| `include/gpu/ganesh/gl/GrGLAssembleInterface.h` | 接口组装函数声明 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | OpenGL 工具函数 |
| `src/base/SkLeanWindows.h` | 精简的 Windows API 头文件 |
| `include/core/SkTypes.h` | Skia 基础类型定义 |
| `include/core/SkRefCnt.h` | 智能指针定义 |
| `src/gpu/ganesh/gl/GrGLDefines.h` | OpenGL 常量定义 |
