# LoadDynamicLibrary_posix.cpp

> 源文件: tools/library/LoadDynamicLibrary_posix.cpp

## 概述

`LoadDynamicLibrary_posix.cpp` 是 Skia 动态库加载工具在 POSIX 兼容系统（Unix、Linux、macOS、Android）上的实现文件。该文件使用 POSIX 标准的 `dlfcn.h` 接口（dlopen、dlsym、dlclose）实现了跨平台动态库加载接口。

## 架构位置

```
tools/library/
  ├── LoadDynamicLibrary.h          # 跨平台接口声明
  ├── LoadDynamicLibrary_posix.cpp  # POSIX 实现（本文件）
  └── LoadDynamicLibrary_win.cpp    # Windows 实现
```

## 主要类与结构体

无类定义，仅实现三个全局函数。

## 公共 API 函数

### SkLoadDynamicLibrary
```cpp
void* SkLoadDynamicLibrary(const char* libraryName) {
    return dlopen(libraryName, RTLD_LAZY);
}
```
**功能**：加载共享库（.so 或 .dylib）。
**实现**：调用 `dlopen`，使用 RTLD_LAZY 标志（延迟符号解析）。
**参数说明**：
- `RTLD_LAZY`：仅在首次调用时解析未定义符号
- 替代：`RTLD_NOW` 会立即解析所有符号

### SkGetProcedureAddress
```cpp
void* SkGetProcedureAddress(void* library, const char* functionName) {
    return dlsym(library, functionName);
}
```
**功能**：获取符号地址。
**实现**：直接调用 `dlsym`，返回符号指针。

### SkFreeDynamicLibrary
```cpp
bool SkFreeDynamicLibrary(void* library) {
    return dlclose(library) == 0;
}
```
**功能**：卸载共享库。
**实现**：调用 `dlclose`，成功时返回 0，映射为 true。
**注意**：`dlclose` 的返回值语义与 Windows FreeLibrary 相反（0 表示成功）。

## 内部实现细节

### 条件编译保护
```cpp
#if !defined(SK_BUILD_FOR_WIN)
// ... 实现 ...
#endif
```
排除 Windows 平台，适用于所有其他系统。

### RTLD_LAZY 选择
使用延迟符号解析策略：
- 加载快速
- 节省内存
- 符号错误延迟到使用时

## 依赖关系

**系统依赖**：
- `<dlfcn.h>`：POSIX 动态链接器接口
- 系统库（libdl）：Unix/Linux 上可能需要链接 -ldl

**Skia 依赖**：
- `include/core/SkTypes.h`
- `tools/library/LoadDynamicLibrary.h`

## 设计模式与设计决策

### POSIX 标准兼容性
使用标准 POSIX API，确保在所有 POSIX 兼容系统上工作：
- Linux（glibc、musl）
- macOS
- FreeBSD、OpenBSD
- Android（Bionic libc）

### 错误处理
函数返回 nullptr 或 false 表示失败。详细错误信息可通过 `dlerror()` 获取（未在此实现中暴露）。

## 性能考量

RTLD_LAZY 相比 RTLD_NOW：
- 更快的加载时间
- 更低的初始内存占用
- 适合工具程序和插件系统

## 相关文件

- `tools/library/LoadDynamicLibrary.h`：接口声明
- `tools/library/LoadDynamicLibrary_win.cpp`：Windows 平台实现
