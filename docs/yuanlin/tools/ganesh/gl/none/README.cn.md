# tools/ganesh/gl/none - 空 OpenGL 测试上下文实现

## 概述

`tools/ganesh/gl/none` 目录提供了 `CreatePlatformGLTestContext()` 工厂函数的空实现（stub）。当 Skia 在不支持 OpenGL 的平台上编译，或者 GL 支持被明确禁用时，此实现会被链接进来。

该空实现非常简单：`CreatePlatformGLTestContext()` 函数直接返回 `nullptr`，表示无法创建任何 GL 测试上下文。这使得 `GrContextFactory` 在请求 GL 上下文时能够优雅地失败（返回空的 `ContextInfo`），而不是产生链接错误。

这种设计模式在 Skia 中很常见：为每个平台特定的功能提供一个空实现，确保在不支持该功能的平台上代码仍然能够编译和链接，同时通过返回空值或错误码来通知调用者该功能不可用。

本目录通常在以下场景中使用：仅启用 Vulkan 或 Metal 后端而不需要 GL 支持的构建配置；嵌入式或特殊平台上没有可用的 GL 窗口系统（EGL、GLX、WGL 等）。

## 目录结构

```
tools/ganesh/gl/none/
├── BUILD.bazel                               # Bazel 构建配置
└── CreatePlatformGLTestContext_none.cpp      # 空 GL 测试上下文实现
```

## 关键类与函数

### CreatePlatformGLTestContext（空实现）
- **命名空间**: `sk_gpu_test`
- **签名**: `GLTestContext* CreatePlatformGLTestContext(GrGLStandard, GLTestContext*)`
- **行为**: 始终返回 `nullptr`
- **用途**: 为不支持 GL 的平台提供链接兼容性

## 依赖关系

- **上游依赖**: `tools/ganesh/gl/GLTestContext.h`（函数声明）
- **无平台依赖**: 不需要任何 GL 库或窗口系统
- **使用场景**: 在没有 GL 支持的平台构建配置中自动选择

## 设计意图

此空实现是 Skia 中常见的"空后端"设计模式的一个实例。该模式确保：

1. **编译兼容性**: 无论目标平台是否支持 GL，引用 `CreatePlatformGLTestContext` 的代码都能成功编译和链接
2. **优雅降级**: 调用者通过检查返回值（nullptr）即可知道 GL 不可用，无需额外的编译时检查
3. **统一接口**: `GrContextFactory` 可以使用相同的代码路径处理所有后端，通过返回值区分可用性

## 使用场景

- 仅启用 Vulkan 后端的 Android 构建
- 仅启用 Metal 后端的 Apple 平台构建
- 嵌入式系统上没有窗口系统支持的场景
- 构建参数明确禁用 GL 的配置（`skia_use_gl = false`）

## 实现细节

空实现的代码极其简洁：

```cpp
namespace sk_gpu_test {
GLTestContext* CreatePlatformGLTestContext(GrGLStandard, GLTestContext*) {
    return nullptr;
}
}  // namespace sk_gpu_test
```

当 `GrContextFactory::getContextInfoInternal()` 收到 nullptr 时，它会返回空的 `ContextInfo` 对象，测试框架据此跳过 GL 相关的测试。

## 与其他平台实现的对比

| 平台实现 | 返回值 | 创建的对象 |
|---------|--------|-----------|
| `egl/` | 有效 `GLTestContext*` | EGL 上下文 + PBuffer |
| `glx/` | 有效 `GLTestContext*` | GLX 上下文 + Pixmap |
| `mac/` | 有效 `GLTestContext*` | CGL 上下文 |
| `win/` | 有效 `GLTestContext*` | WGL 上下文 + 隐藏窗口 |
| `iOS/` | 有效 `GLTestContext*` | EAGL 上下文 |
| **`none/`** | **`nullptr`** | **无** |

## 相关文档与参考

- `tools/ganesh/gl/GLTestContext.h` - OpenGL 测试上下文基类及工厂函数声明
- `tools/ganesh/gl/egl/` - EGL 平台实现（Linux/Android）
- `tools/ganesh/gl/mac/` - macOS CGL 平台实现
- `tools/ganesh/gl/win/` - Windows WGL 平台实现
- `tools/ganesh/gl/glx/` - X11 GLX 平台实现
