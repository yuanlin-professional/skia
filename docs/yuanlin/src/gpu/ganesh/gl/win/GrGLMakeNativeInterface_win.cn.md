# GrGLMakeNativeInterface (Windows)

> 源文件
> - src/gpu/ganesh/gl/win/GrGLMakeNativeInterface_win.cpp

## 概述

Windows 平台的 OpenGL 原生接口创建实现。该文件定义了 `GrGLMakeNativeInterface()` 函数，用于在 Windows 系统上创建 OpenGL 接口对象。Windows 的 OpenGL 实现使用 `__stdcall` 调用约定，与其他平台的 `__cdecl` 不同。该实现在 ARM64 架构上不支持 OpenGL。

## 公共 API 函数

### GrGLMakeNativeInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface();
```

**功能**：创建 Windows 平台的 OpenGL 接口。

**返回值**：
- x86/x64 架构：调用 `GrGLInterfaces::MakeWin()` 返回接口对象
- ARM64 架构：返回 `nullptr`（不支持）

**实现代码**：
```cpp
#if defined(_M_ARM64)
sk_sp<const GrGLInterface> GrGLMakeNativeInterface() { return nullptr; }
#else
sk_sp<const GrGLInterface> GrGLMakeNativeInterface() {
    return GrGLInterfaces::MakeWin();
}
#endif
```

## 内部实现细节

### Windows 调用约定

注释中说明了关键限制：
```cpp
/*
 * Windows makes the GL funcs all be __stdcall instead of __cdecl :(
 * This implementation will only work if GR_GL_FUNCTION_TYPE is __stdcall.
 * Otherwise, a springboard would be needed that hides the calling convention.
 */
```

**问题**：Windows OpenGL 函数使用 `__stdcall`，与标准 C 的 `__cdecl` 不同。

**解决方案**：要求 `GR_GL_FUNCTION_TYPE` 宏定义为 `__stdcall`，确保函数指针类型匹配。

**替代方案**：如果类型不匹配，需要"跳板"（springboard）函数来隐藏调用约定差异。

### ARM64 支持

Windows ARM64 平台不支持传统的 OpenGL：
- 返回 `nullptr` 表示不可用
- ARM64 Windows 设备通常使用 DirectX 或其他图形 API

### 编译条件

```cpp
#if !defined(SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE)
```

允许应用程序禁用该函数，使用自定义接口加载逻辑。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | GL 函数指针表定义 |
| `GrGLMakeWinInterface` | Windows 特定的接口创建实现 |
| `SkTypes` | 基础类型定义 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| Windows 应用程序 | 初始化 Skia OpenGL 支持 |
| `GrDirectContext` | 创建 GL 上下文 |

## 设计模式与设计决策

### 架构特定编译

使用 `_M_ARM64` 预处理器宏在编译时选择不同实现：
- 避免运行时架构检测开销
- 代码更清晰

### 委托模式

实际实现委托给 `GrGLInterfaces::MakeWin()`：
- 分离接口和实现
- 便于测试和维护

## 性能考量

### 零开销抽象

- 函数调用在优化构建中可能内联
- 直接转发到平台实现，无额外开销

### ARM64 快速路径

ARM64 直接返回 `nullptr`，避免任何初始化尝试。

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `include/gpu/ganesh/gl/win/GrGLMakeWinInterface.h` | Windows 接口创建函数声明 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 接口定义 |
| `include/core/SkTypes.h` | 基础类型和宏 |
