# GrGLMakeNativeInterface (EGL)

> 源文件
> - src/gpu/ganesh/gl/egl/GrGLMakeNativeInterface_egl.cpp

## 概述

EGL 平台的 OpenGL 接口创建实现。EGL（Embedded-System Graphics Library）是跨平台的 OpenGL 和 OpenGL ES 接口层，广泛用于 Linux、Android、嵌入式系统等。该文件提供了最简单的实现，直接转发到 EGL 特定的接口创建函数。

## 公共 API 函数

### GrGLMakeNativeInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface();
```

**功能**：创建 EGL 平台的 OpenGL 接口。

**返回值**：调用 `GrGLMakeEGLInterface()` 返回的接口对象。

**实现代码**：
```cpp
#if !defined(SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE)
sk_sp<const GrGLInterface> GrGLMakeNativeInterface() {
    return GrGLMakeEGLInterface();
}
#endif
```

## 内部实现细节

### 最简实现

该文件是所有平台实现中最简单的：
- 无条件编译分支
- 无平台特定逻辑
- 直接委托给 `GrGLMakeEGLInterface()`

实际的 EGL 函数加载逻辑在 `GrGLMakeEGLInterface()` 中实现。

### EGL 查找机制

虽然此文件中未直接体现，但 `GrGLMakeEGLInterface()` 通常：
- 使用 `eglGetProcAddress` 查找 OpenGL 函数
- 支持 OpenGL 和 OpenGL ES
- 跨平台兼容

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | GL 函数指针表 |
| `GrGLMakeEGLInterface` | EGL 特定的接口创建实现 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| Linux 应用程序 | 使用 EGL 的 GL 初始化 |
| 嵌入式系统 | OpenGL ES 支持 |
| `GrDirectContext` | 创建 GL 上下文 |

## 设计模式与设计决策

### 单一职责原则

该文件职责单一：
- 仅作为平台检测的入口点
- 不包含具体实现逻辑
- 保持代码简洁

### 委托模式

将实际工作委托给专门的函数：
```
GrGLMakeNativeInterface (平台检测)
    ↓
GrGLMakeEGLInterface (EGL 特定逻辑)
    ↓
eglGetProcAddress (EGL API)
```

## 性能考量

### 零开销

函数调用可能被内联：
- 编译器优化后等同于直接调用 `GrGLMakeEGLInterface()`
- 无额外开销

### EGL 函数查找

`eglGetProcAddress` 的性能特性：
- 查找后缓存指针
- 支持扩展函数动态加载
- 跨驱动兼容

## EGL 特定考虑

### 跨平台支持

EGL 可用于多个平台：
- Linux（桌面和嵌入式）
- Android
- Wayland
- DirectFB
- 其他 Unix 系统

### OpenGL vs OpenGL ES

EGL 同时支持：
- 完整 OpenGL（桌面）
- OpenGL ES（移动/嵌入式）

具体使用哪个由上下文创建时决定。

### 扩展支持

EGL 通过 `eglGetProcAddress` 提供扩展查找：
- 核心函数
- 标准扩展
- 厂商特定扩展

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 接口定义 |
| `include/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.h` | EGL 接口创建函数 |
| `src/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.cpp` | EGL 具体实现 |
