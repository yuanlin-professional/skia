# LoadDynamicLibrary_win.cpp

> 源文件: tools/library/LoadDynamicLibrary_win.cpp

## 概述

`LoadDynamicLibrary_win.cpp` 是 Skia 动态库加载工具在 Windows 平台上的实现文件。该文件使用 Windows API（LoadLibraryA、GetProcAddress、FreeLibrary）实现了跨平台动态库加载接口的 Windows 版本。代码非常简洁，主要作用是将 Windows 特定的 API 包装为 Skia 统一的接口。

## 架构位置

```
tools/library/
  ├── LoadDynamicLibrary.h          # 跨平台接口声明
  ├── LoadDynamicLibrary_win.cpp    # Windows 实现（本文件）
  └── LoadDynamicLibrary_posix.cpp  # POSIX 实现
```

## 主要类与结构体

无类定义，仅实现三个全局函数。

## 公共 API 函数

### SkLoadDynamicLibrary
```cpp
void* SkLoadDynamicLibrary(const char* libraryName) {
    return LoadLibraryA(libraryName);
}
```
**功能**：加载 DLL 文件。
**实现**：直接调用 Windows API `LoadLibraryA`，返回 HMODULE 句柄（转换为 void*）。

### SkGetProcedureAddress
```cpp
void* SkGetProcedureAddress(void* library, const char* functionName) {
    return reinterpret_cast<void*>(::GetProcAddress((HMODULE)library, functionName));
}
```
**功能**：获取函数地址。
**实现**：将 void* 转换回 HMODULE，调用 `GetProcAddress`，返回函数指针。

### SkFreeDynamicLibrary
```cpp
bool SkFreeDynamicLibrary(void* library) {
    return FreeLibrary((HMODULE)library);
}
```
**功能**：卸载 DLL。
**实现**：调用 `FreeLibrary`，其返回值（BOOL）直接映射为 bool。

## 内部实现细节

### 条件编译保护
```cpp
#if defined(SK_BUILD_FOR_WIN)
// ... 实现 ...
#endif
```
确保仅在 Windows 平台编译此文件。

### SkLeanWindows 使用
```cpp
#include "src/base/SkLeanWindows.h"
```
使用 Skia 的精简 Windows 头文件包装，避免包含大量不需要的定义。

## 依赖关系

**系统依赖**：
- Windows API（kernel32.dll）：LoadLibraryA、GetProcAddress、FreeLibrary

**Skia 依赖**：
- `include/core/SkTypes.h`
- `src/base/SkLeanWindows.h`
- `tools/library/LoadDynamicLibrary.h`

## 设计模式与设计决策

### 薄包装层
直接转发到 Windows API，无额外逻辑。

### LoadLibraryA vs LoadLibraryW
选择 ANSI 版本（A）而非 Unicode 版本（W）：
- 接口参数为 `const char*`，与 ANSI 版本匹配
- 简化实现，无需字符串转换
- 对于库名称，ASCII 足够

## 性能考量

函数调用开销极小，仅进行类型转换和转发到系统 API。

## 相关文件

- `tools/library/LoadDynamicLibrary.h`：接口声明
- `tools/library/LoadDynamicLibrary_posix.cpp`：POSIX 平台实现
- `src/base/SkLeanWindows.h`：Windows 头文件包装
