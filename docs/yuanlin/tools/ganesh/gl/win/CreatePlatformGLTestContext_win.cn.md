# CreatePlatformGLTestContext_win.cpp - Windows GL 测试上下文

> 源文件: `tools/ganesh/gl/win/CreatePlatformGLTestContext_win.cpp`

## 概述

此文件实现了 Windows 平台上的 OpenGL 测试上下文工厂函数 `CreatePlatformGLTestContext`。它通过 `WinGLTestContext` 类封装了 Windows 窗口创建、WGL 上下文管理和 GL 接口初始化的完整流程。

## 架构位置

属于 Skia GPU 测试基础设施的平台适配层,实现了 `sk_gpu_test::GLTestContext` 的 Windows 特化版本。在 ARM64 平台上返回 nullptr(不支持)。

## 主要类与结构体

- **`WinGLTestContext`**: 继承自 `sk_gpu_test::GLTestContext`,管理 Windows GL 上下文生命周期
  - 持有 `HWND`、`HDC`、`HGLRC` 和可选的 `SkWGLPbufferContext`

## 公共 API 函数

- **`sk_gpu_test::CreatePlatformGLTestContext(GrGLStandard, GLTestContext*)`**: 工厂函数,创建 Windows GL 测试上下文

## 内部实现细节

构造过程: 注册窗口类 -> 创建隐藏窗口 -> 获取设备上下文 -> 尝试创建 Pbuffer 上下文(优先) -> 回退到窗口上下文 -> 设为当前上下文 -> 创建 GrGLInterface -> 验证接口。使用 `SkScopeExit` 保证上下文切换的安全恢复。

## 依赖关系

- `SkWGL.h`: WGL 扩展封装
- `GLTestContext.h`: 基类
- `GrGLMakeNativeInterface()`: 创建原生 GL 接口

## 设计模式与设计决策

- 优先使用 Pbuffer 以避免创建不必要的可见窗口
- 使用兼容性配置文件(而非核心配置文件)以解决 Intel Iris GPU 上的 `glMultiDrawArraysIndirect` 兼容性问题
- 支持共享上下文用于资源共享

## 性能考量

窗口类通过静态 `ATOM` 仅注册一次,Pbuffer 路径避免了不必要的窗口资源占用。

## 相关文件

- `tools/ganesh/gl/win/SkWGL.h`, `tools/ganesh/gl/win/SkWGL_win.cpp`
- `tools/ganesh/gl/GLTestContext.h`
