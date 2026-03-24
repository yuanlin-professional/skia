# Skia 动态库加载工具

## 概述

`tools/library` 提供了跨平台的动态库（共享库）加载抽象层。该模块封装了 POSIX 系统的 `dlopen`/`dlsym`/`dlclose` 和 Windows 系统的 `LoadLibrary`/`GetProcAddress`/`FreeLibrary`，提供统一的 API 接口。这是 Skia 在运行时加载可选依赖库（如 GPU 驱动程序、编解码器等）时使用的底层工具。

## 目录结构

```
tools/library/
├── BUILD.bazel                    # Bazel 构建配置
├── LoadDynamicLibrary.h           # 跨平台 API 声明
├── LoadDynamicLibrary_posix.cpp   # POSIX 实现（Linux、macOS、Android）
└── LoadDynamicLibrary_win.cpp     # Windows 实现
```

## API 接口

`LoadDynamicLibrary.h` 定义了三个核心函数：

```cpp
// 加载动态库，返回库句柄（失败返回 nullptr）
void* SkLoadDynamicLibrary(const char* libraryName);

// 获取函数地址，返回函数指针（失败返回 nullptr）
void* SkGetProcedureAddress(void* library, const char* functionName);

// 释放动态库，成功返回 true
bool SkFreeDynamicLibrary(void* library);
```

## 平台实现

### POSIX 实现（LoadDynamicLibrary_posix.cpp）

适用于 Linux、macOS、Android 等 POSIX 兼容系统：

```cpp
void* SkLoadDynamicLibrary(const char* libraryName) {
    return dlopen(libraryName, RTLD_LAZY);  // 延迟绑定
}

void* SkGetProcedureAddress(void* library, const char* functionName) {
    return dlsym(library, functionName);
}

bool SkFreeDynamicLibrary(void* library) {
    return dlclose(library) == 0;
}
```

- 使用 `RTLD_LAZY` 标志进行延迟符号解析
- 仅在非 Windows 平台编译（`!defined(SK_BUILD_FOR_WIN)`）

### Windows 实现（LoadDynamicLibrary_win.cpp）

适用于 Windows 平台：

- 使用 `LoadLibraryA()` 加载 DLL
- 使用 `GetProcAddress()` 获取函数地址
- 使用 `FreeLibrary()` 释放 DLL

## 使用示例

```cpp
#include "tools/library/LoadDynamicLibrary.h"

// 运行时加载 OpenGL 库
void* glLib = SkLoadDynamicLibrary("libGL.so");
if (glLib) {
    // 获取 OpenGL 函数指针
    auto glClear = (void(*)(unsigned int))
        SkGetProcedureAddress(glLib, "glClear");

    if (glClear) {
        glClear(GL_COLOR_BUFFER_BIT);
    }

    // 使用完毕后释放
    SkFreeDynamicLibrary(glLib);
}
```

## 构建

```bash
# Bazel 构建
bazel build //tools/library:library
```

## 设计特点

- **简洁接口**: 仅三个函数，覆盖动态库的完整生命周期
- **平台透明**: 调用方无需关心底层平台差异
- **延迟绑定**: POSIX 实现使用 RTLD_LAZY，仅在函数首次调用时解析符号
- **条件编译**: 通过 `SK_BUILD_FOR_WIN` 宏自动选择正确的实现

## 与其他模块的关系

- **src/gpu/**: GPU 后端在运行时加载 OpenGL/Vulkan/Metal 驱动
- **src/ports/**: 各平台端口可能动态加载系统库
- **tools/ganesh/gl/**: GL 测试上下文使用动态库加载 GL 函数
