# GrGLAssembleInterface

> 源文件
> - include/gpu/ganesh/gl/GrGLAssembleInterface.h
> - src/gpu/ganesh/gl/GrGLAssembleInterface.cpp

## 概述

`GrGLAssembleInterface` 模块负责在运行时动态组装 OpenGL 或 OpenGL ES 接口。它是 Skia Ganesh OpenGL 后端初始化的核心组件,通过函数指针查找机制,将平台特定的 OpenGL 函数地址绑定到统一的 `GrGLInterface` 对象中。

该模块提供了多个工厂函数,用于不同的 OpenGL 变体:
- **GrGLMakeAssembledInterface**: 自动检测 OpenGL 版本并组装对应接口
- **GrGLMakeAssembledGLInterface**: 专门组装桌面 OpenGL 接口
- **GrGLMakeAssembledGLESInterface**: 专门组装 OpenGL ES 接口
- **GrGLMakeAssembledWebGLInterface**: 专门组装 WebGL 接口

这种设计使得 Skia 能够在不同平台(Windows、macOS、Linux、Android、iOS、Web)和不同 OpenGL 实现(NVIDIA、AMD、Intel、ARM Mali、Adreno 等)上运行,无需编译时绑定特定的 OpenGL 库。

## 架构位置

在 OpenGL 后端初始化流程中的位置:

```
应用程序创建 GrDirectContext
    ↓
GrDirectContexts::MakeGL
    ↓
GrGLMakeAssembledInterface ← 当前模块
    ↓
├─ 检测 OpenGL 版本
├─ GrGLMakeAssembledGLInterface (桌面 GL)
├─ GrGLMakeAssembledGLESInterface (移动 ES)
└─ GrGLMakeAssembledWebGLInterface (Web)
    ↓
创建 GrGLInterface 对象
    ↓
GrGLGpu 使用接口调用 OpenGL 函数
```

## 主要类与结构体

该模块不定义类,主要提供函数指针类型和工厂函数。

### 核心类型定义

**GrGLGetProc:**
```cpp
typedef GrGLFuncPtr (*GrGLGetProc)(void* ctx, const char name[]);
```
函数指针获取器类型,用于动态查找 OpenGL 函数地址。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `sk_sp<const GrGLInterface> GrGLMakeAssembledInterface(void*, GrGLGetProc)` | 自动检测并组装 OpenGL/ES/WebGL 接口 |
| `sk_sp<const GrGLInterface> GrGLMakeAssembledGLInterface(void*, GrGLGetProc)` | 专门组装桌面 OpenGL 接口 |
| `sk_sp<const GrGLInterface> GrGLMakeAssembledGLESInterface(void*, GrGLGetProc)` | 专门组装 OpenGL ES 接口 |
| `sk_sp<const GrGLInterface> GrGLMakeAssembledWebGLInterface(void*, GrGLGetProc)` | 专门组装 WebGL 接口 |
| `const GrGLInterface* GrGLAssembleInterface(void*, GrGLGetProc)` | 已废弃的版本,返回裸指针 |

### 函数参数说明

- `ctx`: 上下文指针,传递给 `GrGLGetProc` 回调
- `get`: 函数指针获取器,根据函数名返回对应的函数地址

## 内部实现细节

### 自动检测 OpenGL 变体

`GrGLMakeAssembledInterface` 的实现逻辑:

```cpp
sk_sp<const GrGLInterface> GrGLMakeAssembledInterface(void *ctx, GrGLGetProc get) {
    // 首先获取 glGetString 函数
    GET_PROC_LOCAL(GetString);
    if (nullptr == GetString) {
        return nullptr;
    }

    // 查询 GL_VERSION 字符串
    const char* verStr = reinterpret_cast<const char*>(GetString(GR_GL_VERSION));
    if (nullptr == verStr) {
        return nullptr;
    }

    // 根据版本字符串判断 OpenGL 类型
    GrGLStandard standard = GrGLGetStandardInUseFromString(verStr);

    if (GR_IS_GR_GL_ES(standard)) {
        return GrGLMakeAssembledGLESInterface(ctx, get);
    } else if (GR_IS_GR_GL(standard)) {
        return GrGLMakeAssembledGLInterface(ctx, get);
    } else if (GR_IS_GR_WEBGL(standard)) {
        return GrGLMakeAssembledWebGLInterface(ctx, get);
    }
    return nullptr;
}
```

### 函数指针查找宏

使用 `GET_PROC_LOCAL` 宏简化函数查找:

```cpp
#define GET_PROC_LOCAL(F) GrGL##F##Fn* F = (GrGL##F##Fn*)get(ctx, "gl" #F)
```

例如 `GET_PROC_LOCAL(GetString)` 展开为:
```cpp
GrGLGetStringFn* GetString = (GrGLGetStringFn*)get(ctx, "glGetString")
```

### 版本字符串解析

通过 `GrGLGetStandardInUseFromString()` 解析版本字符串,识别:
- 桌面 OpenGL: "3.3.0 NVIDIA 384.76"
- OpenGL ES: "OpenGL ES 3.0 v1.r32"
- WebGL: "WebGL 2.0"

### 已废弃接口兼容性

```cpp
const GrGLInterface* GrGLAssembleInterface(void *ctx, GrGLGetProc get) {
    return GrGLMakeAssembledInterface(ctx, get).release();
}
```

保留旧接口以兼容现有代码,但返回裸指针需要调用者管理生命周期。

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrGLInterface` | 目标接口类,存储所有 OpenGL 函数指针 |
| `GrGLFunctions` | 定义 OpenGL 函数指针类型 |
| `GrGLTypes` | 定义 OpenGL 基础类型 |
| `GrGLDefines` | 定义 OpenGL 常量(如 `GR_GL_VERSION`) |
| `GrGLUtil` | 提供 `GrGLGetStandardInUseFromString` 等工具函数 |
| `SkRefCnt` | 智能指针支持 |
| `SkTemplates` | 模板工具(如 `sk_ignore_unused_variable`) |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| `GrDirectContexts::MakeGL` | 创建 OpenGL 直接上下文时组装接口 |
| 平台特定初始化代码 | 各平台提供 `GrGLGetProc` 实现 |
| `GrGLGpu` | 使用组装好的接口调用 OpenGL 函数 |
| 测试和示例代码 | 创建测试用的 OpenGL 上下文 |

## 设计模式与设计决策

### 工厂方法模式

提供多个工厂函数创建 `GrGLInterface` 对象:
- 自动检测工厂: `GrGLMakeAssembledInterface`
- 特定类型工厂: `GrGLMakeAssembledGLInterface`、`GrGLMakeAssembledGLESInterface`、`GrGLMakeAssembledWebGLInterface`

### 策略模式

通过 `GrGLGetProc` 回调参数化函数查找策略:
- Windows: 使用 `wglGetProcAddress`
- Linux: 使用 `glXGetProcAddress` 或 `eglGetProcAddress`
- macOS: 使用 `dlsym` 或 Core Foundation
- Web: 使用 Emscripten 的符号查找

### 依赖注入

调用者提供 `GrGLGetProc` 和上下文指针,而非硬编码平台特定代码,使得模块可测试且平台无关。

### 智能指针管理生命周期

返回 `sk_sp<const GrGLInterface>` 而非裸指针,自动管理内存:
- 引用计数自动管理
- 避免内存泄漏
- 线程安全的引用计数

### 编译时条件编译

使用 `SK_ASSUME_GL_ES` 等宏优化特定平台:

```cpp
// standard can be unused if SK_ASSUME_GL_ES is set
sk_ignore_unused_variable(standard);
```

在明确只支持 ES 的平台(如 Android)上,可以省略检测逻辑。

## 性能考量

### 一次性初始化

接口组装只在上下文创建时执行一次,不影响渲染性能。

### 函数指针直接调用

组装后的接口通过函数指针直接调用,无需虚函数或间接查找:
```cpp
interface->fFunctions.fClear(r, g, b, a);  // 直接调用
```

### 避免字符串比较

函数查找通过哈希表或平台特定机制,不是线性字符串比较。

### 缓存版本检测结果

版本字符串只解析一次,结果存储在 `GrGLInterface` 中。

### 条件编译优化

在只支持单一 OpenGL 变体的平台上,未使用的组装函数可被优化掉。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | 目标接口类定义 |
| `src/gpu/ganesh/gl/GrGLAssembleGLInterface.cpp` | 桌面 OpenGL 接口组装实现 |
| `src/gpu/ganesh/gl/GrGLAssembleGLESInterface.cpp` | OpenGL ES 接口组装实现 |
| `src/gpu/ganesh/gl/GrGLAssembleWebGLInterface.cpp` | WebGL 接口组装实现 |
| `include/gpu/ganesh/gl/GrGLFunctions.h` | OpenGL 函数指针类型定义 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | OpenGL 工具函数 |
| `include/gpu/ganesh/gl/GrGLDirectContext.h` | 使用此模块创建上下文 |
| 平台特定文件 (如 `src/gpu/ganesh/gl/win/GrGLMakeNativeInterface_win.cpp`) | 提供平台特定的 `GrGLGetProc` 实现 |
