# GrGLMakeNativeInterface (GLX)

> 源文件
> - src/gpu/ganesh/gl/glx/GrGLMakeNativeInterface_glx.cpp

## 概述

GLX（OpenGL Extension to the X Window System）平台的 OpenGL 接口创建实现。GLX 是 X Window System（主要用于 Linux 和 Unix 桌面环境）的 OpenGL 扩展，提供了窗口系统与 OpenGL 的集成。该文件实现了在使用 X11 的 Linux 系统上创建原生 OpenGL 接口。

## 公共 API 函数

### GrGLMakeNativeInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface();
```

**功能**：创建 GLX 平台的 OpenGL 接口。

**返回值**：调用 `GrGLInterfaces::MakeGLX()` 返回的接口对象。

**实现代码**：
```cpp
#if !defined(SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE)
#include "include/gpu/ganesh/gl/GrGLInterface.h"
#include "include/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.h"

sk_sp<const GrGLInterface> GrGLMakeNativeInterface() {
    return GrGLInterfaces::MakeGLX();
}
#endif
```

## 内部实现细节

### 简单委托

与 EGL 实现类似，该文件仅作为平台入口点：
- 直接转发到 `GrGLInterfaces::MakeGLX()`
- 不包含平台特定逻辑
- 实际实现在 `GrGLMakeGLXInterface.h/.cpp` 中

### GLX 函数加载

虽然此文件中未直接体现，但 `MakeGLX()` 通常：
- 使用 `glXGetProcAddress` 或 `glXGetProcAddressARB` 查找函数
- 支持核心 OpenGL 和扩展函数
- 处理多个 X11 显示和屏幕

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | GL 函数指针表 |
| `GrGLMakeGLXInterface` | GLX 特定的接口创建实现 |
| `SkTypes` | 基础类型定义 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| Linux X11 应用程序 | 桌面 OpenGL 初始化 |
| `GrDirectContext` | 创建 GL 上下文 |

## 设计模式与设计决策

### 平台检测

该文件在使用 X11 的 Linux 系统上编译：
- 通常通过构建系统检测（CMake, GN）
- 与 EGL 版本互斥（同一平台只使用一个）

### 委托模式

```
GrGLMakeNativeInterface (平台入口)
    ↓
GrGLInterfaces::MakeGLX (GLX 特定)
    ↓
glXGetProcAddress (X11 API)
```

## 性能考量

### 函数内联

简单的转发可能被编译器内联：
- 零函数调用开销
- 等同于直接调用 `MakeGLX()`

### GLX 函数查找

`glXGetProcAddress` 的特性：
- 返回函数指针（查找后缓存）
- 支持扩展动态加载
- 线程安全

## GLX 特定考虑

### X11 集成

GLX 提供：
- OpenGL 与 X Window 的集成
- 视觉选择（visual selection）
- 双缓冲和同步控制
- 多显示器支持

### 与 EGL 的关系

在现代 Linux 系统上：
- **GLX**：传统 X11 桌面环境
- **EGL**：Wayland、嵌入式、跨平台代码

许多应用同时支持两者，运行时选择。

### OpenGL 版本支持

GLX 支持：
- Legacy OpenGL（1.x, 2.x）
- 现代 OpenGL（3.x, 4.x）
- Core Profile 和 Compatibility Profile

### 扩展

GLX 扩展通过 `glXQueryExtensionsString` 查询：
- `GLX_ARB_create_context`：创建现代上下文
- `GLX_EXT_swap_control`：垂直同步控制
- `GLX_SGI_video_sync`：视频同步

## Linux 桌面环境

### X11 vs Wayland

| 特性 | X11 + GLX | Wayland + EGL |
|------|-----------|---------------|
| 协议 | X11 Protocol | Wayland Protocol |
| OpenGL 接口 | GLX | EGL |
| 成熟度 | 成熟稳定 | 新兴标准 |
| 性能 | 略低（协议开销） | 更高（直接渲染） |

### 发行版支持

主要 Linux 发行版：
- **Ubuntu/Debian**：两者都支持，默认 X11
- **Fedora**：Wayland 优先
- **Arch Linux**：用户选择

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 接口定义 |
| `include/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.h` | GLX 接口创建函数 |
| `src/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.cpp` | GLX 具体实现 |
| `include/core/SkTypes.h` | 基础类型和宏 |
| X11 GLX 头文件 | 系统 GLX API（`<GL/glx.h>`） |
