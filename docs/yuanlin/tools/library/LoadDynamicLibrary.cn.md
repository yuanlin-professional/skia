# LoadDynamicLibrary.h

> 源文件: tools/library/LoadDynamicLibrary.h

## 概述

`LoadDynamicLibrary.h` 定义了 Skia 工具库中用于动态加载共享库的跨平台接口。该头文件声明了三个核心函数，用于在运行时加载动态链接库（Windows 上的 DLL，Unix/Linux 上的 .so，macOS 上的 .dylib）、获取函数指针和卸载库。这些函数抽象了不同操作系统的动态库加载 API，为 Skia 提供了统一的接口。

典型应用场景包括：
- 运行时加载可选的图形驱动程序
- 插件系统实现
- 延迟加载第三方库以减少启动时间
- 测试工具中动态加载不同版本的库

## 架构位置

在 Skia 工具库中的位置：

```
tools/
  └── library/
      ├── LoadDynamicLibrary.h          # 跨平台接口（本文件）
      ├── LoadDynamicLibrary_win.cpp    # Windows 实现
      └── LoadDynamicLibrary_posix.cpp  # POSIX 实现（Unix/Linux/macOS）
```

平台实现选择由构建系统根据 `SK_BUILD_FOR_WIN` 宏决定。

## 主要类与结构体

本文件不定义类或结构体，仅声明函数接口。

## 公共 API 函数

### SkLoadDynamicLibrary

```cpp
void* SkLoadDynamicLibrary(const char* libraryName);
```

**功能**：加载动态链接库到进程地址空间。

**参数**：
- `libraryName`：库文件名或路径
  - Windows：`"opengl32.dll"`、`"C:\\path\\to\\library.dll"`
  - Unix/Linux：`"libGL.so.1"`、`"/usr/lib/libGL.so"`
  - macOS：`"libGL.dylib"`、`"/System/Library/Frameworks/OpenGL.framework/OpenGL"`

**返回值**：
- 成功：库句柄（不透明指针）
- 失败：`nullptr`

**平台实现**：
- **Windows**：调用 `LoadLibraryA()`
- **POSIX**：调用 `dlopen(libraryName, RTLD_LAZY)`

**使用示例**：
```cpp
void* glLibrary = SkLoadDynamicLibrary("libGL.so.1");
if (!glLibrary) {
    // 加载失败，处理错误
    return;
}
```

### SkGetProcedureAddress

```cpp
void* SkGetProcedureAddress(void* library, const char* functionName);
```

**功能**：从已加载的库中获取函数或符号的地址。

**参数**：
- `library`：库句柄（由 `SkLoadDynamicLibrary` 返回）
- `functionName`：函数或符号名称（C 风格字符串）

**返回值**：
- 成功：函数指针（`void*`，需要转换为正确的函数类型）
- 失败：`nullptr`（符号不存在或库无效）

**平台实现**：
- **Windows**：调用 `GetProcAddress()`
- **POSIX**：调用 `dlsym()`

**使用示例**：
```cpp
typedef void (*glClearColorFunc)(float, float, float, float);
glClearColorFunc glClearColor =
    (glClearColorFunc)SkGetProcedureAddress(glLibrary, "glClearColor");
if (glClearColor) {
    glClearColor(1.0f, 0.0f, 0.0f, 1.0f);
}
```

### SkFreeDynamicLibrary

```cpp
bool SkFreeDynamicLibrary(void* library);
```

**功能**：卸载动态链接库，释放其占用的资源。

**参数**：
- `library`：库句柄（由 `SkLoadDynamicLibrary` 返回）

**返回值**：
- `true`：成功卸载
- `false`：卸载失败

**平台实现**：
- **Windows**：调用 `FreeLibrary()`，返回值直接映射
- **POSIX**：调用 `dlclose()`，成功时返回 0，映射为 `true`

**使用示例**：
```cpp
if (!SkFreeDynamicLibrary(glLibrary)) {
    // 卸载失败，可能仍有引用
}
```

**注意事项**：
- 卸载后不应再使用从该库获取的函数指针
- 某些系统可能使用引用计数，需要多次调用才能真正卸载
- 未卸载的库会在进程终止时自动清理

## 内部实现细节

### Windows 实现（LoadDynamicLibrary_win.cpp）

```cpp
#include "src/base/SkLeanWindows.h"

void* SkLoadDynamicLibrary(const char* libraryName) {
    return LoadLibraryA(libraryName);
}

void* SkGetProcedureAddress(void* library, const char* functionName) {
    return reinterpret_cast<void*>(::GetProcAddress((HMODULE)library, functionName));
}

bool SkFreeDynamicLibrary(void* library) {
    return FreeLibrary((HMODULE)library);
}
```

**关键点**：
- 使用 `LoadLibraryA`（ANSI 版本）而非 `LoadLibraryW`（Unicode）
- 库句柄类型为 `HMODULE`
- `FreeLibrary` 成功返回非零值，直接映射为 bool

### POSIX 实现（LoadDynamicLibrary_posix.cpp）

```cpp
#include <dlfcn.h>

void* SkLoadDynamicLibrary(const char* libraryName) {
    return dlopen(libraryName, RTLD_LAZY);
}

void* SkGetProcedureAddress(void* library, const char* functionName) {
    return dlsym(library, functionName);
}

bool SkFreeDynamicLibrary(void* library) {
    return dlclose(library) == 0;
}
```

**关键点**：
- `RTLD_LAZY`：延迟符号解析（仅在首次调用时解析）
- `dlclose` 成功返回 0，需要映射为 `true`
- 支持 Linux、macOS、Android 等 POSIX 兼容系统

### 平台选择机制

```cpp
// LoadDynamicLibrary_win.cpp
#if defined(SK_BUILD_FOR_WIN)
// ... Windows 实现 ...
#endif

// LoadDynamicLibrary_posix.cpp
#if !defined(SK_BUILD_FOR_WIN)
// ... POSIX 实现 ...
#endif
```

构建系统根据目标平台选择编译相应的实现文件。

## 依赖关系

**Windows 平台**：
- `src/base/SkLeanWindows.h`：精简的 Windows 头文件包装
- Windows API：`LoadLibraryA`、`GetProcAddress`、`FreeLibrary`

**POSIX 平台**：
- `<dlfcn.h>`：动态链接器接口
- POSIX API：`dlopen`、`dlsym`、`dlclose`

**Skia 内部**：
- `include/core/SkTypes.h`：基本类型和宏定义

**被依赖者**：
- 动态加载 OpenGL/Vulkan 驱动
- 测试工具和示例程序
- 插件系统实现

## 设计模式与设计决策

### 跨平台抽象

**目标**：提供统一的 C 风格接口，隐藏平台差异

**实现策略**：
- 使用 `void*` 作为通用句柄类型
- 函数签名在所有平台上相同
- 平台差异在实现文件中封装

### 最小化依赖

仅依赖系统标准库，无需第三方库，简化构建和移植。

### C 风格接口

使用 C 风格函数而非 C++ 类：
- 简单直接，易于理解
- 与系统 API 风格一致
- 方便与 C 代码互操作

### RTLD_LAZY 选择

POSIX 实现使用 `RTLD_LAZY`：
- **优点**：加载速度快，仅在需要时解析符号
- **缺点**：符号不存在的错误延迟到首次调用
- **替代方案**：`RTLD_NOW`（立即解析所有符号）

### 错误处理策略

函数通过返回 `nullptr` 或 `false` 指示失败，不抛出异常：
- 符合 C 风格错误处理
- 调用者需要检查返回值
- 可通过平台 API 获取详细错误信息（Windows：`GetLastError()`，POSIX：`dlerror()`）

## 性能考量

### RTLD_LAZY vs RTLD_NOW

```cpp
dlopen(libraryName, RTLD_LAZY);  // 当前实现
```

**RTLD_LAZY**：
- 加载时间短
- 内存占用低（未使用的符号不解析）
- 可能在运行时遇到符号解析错误

**RTLD_NOW**：
- 加载时间长
- 立即发现所有符号错误
- 内存占用稍高

对于工具程序，RTLD_LAZY 是合理选择。

### 函数指针调用开销

通过 `SkGetProcedureAddress` 获取的函数指针调用与直接调用相比：
- 无额外开销（一旦获取）
- 可能错失编译器优化（内联等）
- 对于图形 API 调用（如 OpenGL），这是标准做法

### 库加载开销

- 首次加载：加载文件、解析依赖、重定位（几毫秒到几十毫秒）
- 重复加载：某些系统缓存已加载的库，开销很小
- 建议在初始化时加载，而非频繁加载/卸载

## 相关文件

**实现文件**：
- `tools/library/LoadDynamicLibrary_win.cpp`：Windows 实现
- `tools/library/LoadDynamicLibrary_posix.cpp`：POSIX 实现

**使用者**（可能）：
- OpenGL/Vulkan 函数加载器
- 测试工具（如 DM、nanobench）
- 动态后端选择器

**类似功能**：
- `src/gpu/ganesh/gl/GrGLInterface.cpp`：OpenGL 函数加载
- `include/gpu/vk/VulkanBackendContext.h`：Vulkan 扩展加载

**平台特定头文件**：
- `src/base/SkLeanWindows.h`：Windows 平台头文件包装

该接口为 Skia 提供了跨平台的动态库加载能力，是实现插件系统和可选功能的基础。
