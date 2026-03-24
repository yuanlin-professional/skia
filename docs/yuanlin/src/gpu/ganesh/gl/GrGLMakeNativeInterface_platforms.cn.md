# GrGLMakeNativeInterface (平台特定实现)

> 源文件
> - src/gpu/ganesh/gl/win/GrGLMakeNativeInterface_win.cpp
> - src/gpu/ganesh/gl/webgl/GrGLMakeNativeInterface_webgl.cpp
> - src/gpu/ganesh/gl/iOS/GrGLMakeNativeInterface_iOS.cpp
> - src/gpu/ganesh/gl/egl/GrGLMakeNativeInterface_egl.cpp
> - src/gpu/ganesh/gl/mac/GrGLMakeNativeInterface_mac.cpp
> - src/gpu/ganesh/gl/android/GrGLMakeNativeInterface_android.cpp
> - src/gpu/ganesh/gl/glx/GrGLMakeNativeInterface_glx.cpp

## 概述

`GrGLMakeNativeInterface` 系列文件为不同平台提供了创建原生 OpenGL 接口的实现。这些文件定义了 `GrGLMakeNativeInterface()` 函数，该函数根据当前平台返回适当的 `GrGLInterface` 对象。每个平台使用不同的机制来加载 OpenGL 函数指针，包括动态库加载（dlopen/dlsym）、EGL、GLX 等。这是 Skia 跨平台 OpenGL 支持的关键基础设施。

## 架构位置

```
应用程序
    ↓
GrGLMakeNativeInterface() ← 平台特定实现
    ↓
GrGLInterface (函数指针表)
    ↓
OpenGL 驱动
```

该模块处于 Skia 和平台 OpenGL 驱动之间的接口层。

## 主要函数

所有平台文件都实现或转发以下函数：

```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface();
```

**功能**：创建当前平台的原生 OpenGL 接口。

**返回值**：
- 成功：包含所有必要 GL 函数指针的 `GrGLInterface` 对象
- 失败：`nullptr`

## 平台特定实现

### Windows 平台

**文件**：`GrGLMakeNativeInterface_win.cpp`

**实现细节**：
```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface() {
    return GrGLInterfaces::MakeWin();
}
```

**特殊处理**：
- ARM64 架构返回 `nullptr`（不支持）
- 使用 `__stdcall` 调用约定（Windows 特有）
- 注释说明需要 `GR_GL_FUNCTION_TYPE` 匹配调用约定

**编译条件**：
- 需要 `!SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE`
- ARM64 架构编译但返回 `nullptr`

### WebGL 平台

**文件**：`GrGLMakeNativeInterface_webgl.cpp`

**实现细节**：
```cpp
namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeWebGL() {
    return GrGLMakeAssembledWebGLInterface(nullptr, webgl_get_gl_proc);
}
}

sk_sp<const GrGLInterface> GrGLMakeNativeInterface() {
    return GrGLInterfaces::MakeWebGL();
}
```

**函数查找机制**：
```cpp
static GrGLFuncPtr webgl_get_gl_proc(void* ctx, const char name[]) {
    #define M(X) if (0 == strcmp(#X, name)) { return (GrGLFuncPtr) X; }
    M(glGetString)
    #undef M

    SkASSERTF(false, "Can't lookup fn %s\n", name);
    return nullptr;
}
```

**设计决策**：
- 不使用 `GetProcAddress`（代码体积大）
- Emscripten 提供所有 WebGL 函数指针
- 只需静态映射函数名到函数指针

**头文件**：
```cpp
#include <GLES3/gl32.h>
```

### iOS 平台

**文件**：`GrGLMakeNativeInterface_iOS.cpp`

**实现细节**：
```cpp
namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeIOS() {
    static const char kPath[] =
        "/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/libGL.dylib";
    std::unique_ptr<void, SkFunctionObject<dlclose>> lib(dlopen(kPath, RTLD_LAZY));
    return GrGLMakeAssembledGLESInterface(lib.get(), [](void* ctx, const char* name) {
            return (GrGLFuncPtr)dlsym(ctx ? ctx : RTLD_DEFAULT, name); });
}
}
```

**动态库加载**：
- 路径：`/System/Library/Frameworks/OpenGL.framework/.../libGL.dylib`
- 使用 `dlopen` 加载库
- 使用 `dlsym` 查找函数
- RAII 管理：`std::unique_ptr` + `SkFunctionObject<dlclose>`

**编译条件**：
```cpp
#ifdef SK_BUILD_FOR_IOS
```

### macOS 平台

**文件**：`GrGLMakeNativeInterface_mac.cpp`

**实现细节**：
与 iOS 几乎相同，区别在于：
- 使用 `GrGLMakeAssembledGLInterface`（完整 OpenGL）
- iOS 使用 `GrGLMakeAssembledGLESInterface`（OpenGL ES）

**编译条件**：
```cpp
#ifdef SK_BUILD_FOR_MAC
```

### EGL 平台

**文件**：`GrGLMakeNativeInterface_egl.cpp`

**实现细节**：
```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface() {
    return GrGLMakeEGLInterface();
}
```

**特点**：
- 最简单的实现
- 直接转发到 `GrGLMakeEGLInterface()`
- EGL 是跨平台的 OpenGL 接口层

### Android 平台

**文件**：`GrGLMakeNativeInterface_android.cpp`

**实现细节**：
```cpp
#include "src/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.cpp"
#include "src/gpu/ganesh/gl/egl/GrGLMakeNativeInterface_egl.cpp"
```

**特点**：
- 直接包含 EGL 实现文件
- Android 使用 EGL 作为 OpenGL 接口

### GLX 平台（Linux/X11）

**文件**：`GrGLMakeNativeInterface_glx.cpp`

**实现细节**：
```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface() {
    return GrGLInterfaces::MakeGLX();
}
```

**特点**：
- GLX 是 X Window System 的 OpenGL 扩展
- 用于 Linux 桌面环境

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | GL 函数指针表 |
| `GrGLAssembleInterface` | 组装接口工具 |
| `GrGLMakeEGLInterface` | EGL 接口创建 |
| `GrGLMakeGLXInterface` | GLX 接口创建 |
| `GrGLMakeWinInterface` | Windows 接口创建 |
| 平台特定库 | dlopen, dlsym (Unix), EGL, GLX 等 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrDirectContext` | 创建 OpenGL 上下文时调用 |
| 应用程序代码 | 初始化 Skia OpenGL 支持 |

## 设计模式与设计决策

### 条件编译策略

每个平台使用预处理器宏控制编译：
- `SK_BUILD_FOR_WIN`
- `SK_BUILD_FOR_MAC`
- `SK_BUILD_FOR_IOS`
- `SK_BUILD_FOR_ANDROID`
- WebGL 通过其他机制判断

### 统一接口

所有平台实现相同的函数签名：
```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface();
```

这允许上层代码无需关心平台差异。

### 命名空间组织

使用 `GrGLInterfaces` 命名空间组织平台特定实现：
```cpp
namespace GrGLInterfaces {
    sk_sp<const GrGLInterface> MakeMac();
    sk_sp<const GrGLInterface> MakeIOS();
    // ...
}
```

### Legacy 兼容性

所有实现都包裹在条件中：
```cpp
#if !defined(SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE)
```

允许应用程序禁用自动检测，使用自定义接口。

### RAII 资源管理

Unix 平台使用智能指针管理动态库句柄：
```cpp
std::unique_ptr<void, SkFunctionObject<dlclose>> lib(dlopen(...));
```

确保库在不再使用时自动关闭。

### 延迟加载 vs 静态链接

- **WebGL**：静态链接（Emscripten 提供）
- **macOS/iOS**：动态加载（`dlopen`）
- **Windows**：依赖平台实现
- **EGL/GLX**：使用系统接口

## 性能考量

### 函数指针查找

**WebGL**：
- 编译时确定函数地址
- 零运行时查找开销

**Unix 平台（macOS/iOS）**：
- 启动时通过 `dlsym` 查找
- 查找后缓存指针，无后续开销

**EGL/GLX**：
- 使用 `eglGetProcAddress` / `glXGetProcAddress`
- 查找后缓存

### 动态库加载

macOS/iOS 的 `dlopen` 调用：
- 延迟加载（`RTLD_LAZY`）
- 只在首次调用时解析符号
- 减少启动延迟

### 代码体积优化

WebGL 明确避免使用 `GetProcAddress`：
```cpp
// 我们明确不使用 GetProcAddress...因为其代码体积相当大
```

这对于 Web 环境的下载大小至关重要。

## 跨平台兼容性矩阵

| 平台 | 文件 | OpenGL 类型 | 加载机制 |
|------|------|-------------|----------|
| Windows (x86/x64) | `_win.cpp` | OpenGL | WGL |
| Windows (ARM64) | `_win.cpp` | 不支持 | - |
| macOS | `_mac.cpp` | OpenGL | dlopen/dlsym |
| iOS | `_iOS.cpp` | OpenGL ES | dlopen/dlsym |
| Android | `_android.cpp` | OpenGL ES | EGL |
| Linux (X11) | `_glx.cpp` | OpenGL | GLX |
| Linux (Wayland/Other) | `_egl.cpp` | OpenGL ES | EGL |
| WebAssembly | `_webgl.cpp` | WebGL | 静态链接 |

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 接口定义 |
| `include/gpu/ganesh/gl/GrGLAssembleInterface.h` | 接口组装工具 |
| `include/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.h` | EGL 特定实现 |
| `include/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.h` | GLX 特定实现 |
| `include/gpu/ganesh/gl/win/GrGLMakeWinInterface.h` | Windows 特定实现 |
| `include/gpu/ganesh/gl/mac/GrGLMakeMacInterface.h` | macOS 特定实现 |
| `include/gpu/ganesh/gl/ios/GrGLMakeIOSInterface.h` | iOS 特定实现 |
| `include/gpu/ganesh/gl/GrGLMakeWebGLInterface.h` | WebGL 特定实现 |
