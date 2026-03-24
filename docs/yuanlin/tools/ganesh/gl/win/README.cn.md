# tools/ganesh/gl/win - Windows WGL 平台 OpenGL 测试上下文

## 概述

`tools/ganesh/gl/win` 目录实现了 Windows 平台上基于 WGL（Windows GL）扩展的 OpenGL 测试上下文。WGL 是 Windows 平台的原生 OpenGL 上下文管理 API，用于创建和管理 OpenGL 渲染上下文。

本目录的核心组件是 `SkWGL` 类，它封装了 WGL 扩展函数的查询和使用。由于 WGL 扩展的使用存在一个"鸡生蛋"问题——需要先有 GL 上下文才能获取扩展函数指针，但又想用扩展函数来创建上下文——`SkWGL` 通过创建一个临时占位 GL 上下文来解决此问题。

`CreatePlatformGLTestContext_win.cpp` 实现了 `CreatePlatformGLTestContext()` 工厂函数的 Windows 版本。它创建一个隐藏窗口，配置像素格式（通过 `SkWGLExtensions` 选择最佳配置，支持 MSAA、核心配置文件等），然后创建 WGL 渲染上下文。

`SkWGL.h` 定义了大量 WGL 扩展常量（如 `SK_WGL_DRAW_TO_WINDOW`、`SK_WGL_CONTEXT_CORE_PROFILE_BIT` 等），以及 `SkWGLExtensions` 类，该类提供了扩展查询、像素格式选择和上下文创建等功能。这些封装使得 Skia 能够在 Windows 上创建支持核心配置文件和 ES 兼容模式的 OpenGL 上下文。

本目录的代码仅在 Windows 平台（`SK_BUILD_FOR_WIN`）上编译。

## 目录结构

```
tools/ganesh/gl/win/
├── BUILD.bazel                              # Bazel 构建配置
├── SkWGL.h                                  # WGL 扩展封装声明
├── SkWGL_win.cpp                            # WGL 扩展封装实现
└── CreatePlatformGLTestContext_win.cpp       # Windows GL 测试上下文实现
```

## 关键类与函数

### SkWGLExtensions
- **功能**: 封装 WGL 扩展函数的查询和调用
- **核心方法**:
  - `hasExtension(HDC, const char*)` - 检查指定扩展是否可用
  - `selectFormat()` - 选择最佳像素格式（支持 MSAA 等特性）
  - `createContextAttribsARB()` - 使用 `WGL_ARB_create_context` 创建高级上下文
- **初始化**: 构造函数内部创建临时上下文以加载扩展函数指针

### WGL 常量定义
- `SK_WGL_CONTEXT_CORE_PROFILE_BIT` - OpenGL 核心配置文件
- `SK_WGL_CONTEXT_COMPATIBILITY_PROFILE_BIT` - 兼容性配置文件
- `SK_WGL_CONTEXT_ES2_PROFILE_BIT` - ES2 兼容配置文件
- `SK_WGL_CONTEXT_MAJOR/MINOR_VERSION` - 上下文版本控制
- `SK_WGL_SAMPLE_BUFFERS` / `SK_WGL_SAMPLES` - MSAA 采样控制

### CreatePlatformGLTestContext（Windows 实现）
- 创建隐藏窗口作为 GL 渲染目标
- 使用 `SkWGLExtensions` 配置像素格式和上下文属性
- 支持 GL 核心配置文件和共享上下文

## 依赖关系

- **上游依赖**: `tools/ganesh/gl/GLTestContext.h`（基类）
- **平台依赖**: Windows API（`windows.h`、`opengl32.dll`）、WGL 扩展
- **编译条件**: 仅 Windows 平台编译
- **被引用**: `tools/ganesh/gl/GLTestContext.h`（通过 `CreatePlatformGLTestContext` 调用）
- **GL 接口**: `include/gpu/ganesh/gl/win/GrGLMakeWinInterface.h`

## WGL 上下文创建流程

1. **注册窗口类**: 注册一个隐藏的 Windows 窗口类
2. **创建窗口**: 创建一个不可见的窗口作为 GL 渲染目标
3. **加载 WGL 扩展**: 通过 `SkWGLExtensions` 创建临时上下文获取扩展函数
4. **选择像素格式**: 使用 `wglChoosePixelFormatARB()` 选择最佳格式
   - 支持 MSAA（多重采样抗锯齿）
   - 支持 sRGB 帧缓冲
5. **创建上下文**: 使用 `wglCreateContextAttribsARB()` 创建高级上下文
   - 支持 OpenGL 核心配置文件
   - 支持 ES 兼容配置文件
6. **设为当前**: 调用 `wglMakeCurrent()` 激活上下文

## 高性能 GPU 选择

在 Windows 笔记本上，代码通过导出特殊符号来请求使用独立 GPU：
- `NvOptimusEnablement = 1` - 请求 NVIDIA 独立 GPU（Optimus 技术）
- `AmdPowerXpressRequestHighPerformance = 1` - 请求 AMD 独立 GPU
这些符号在 `GrContextFactory.cpp` 中定义（受 `SK_ENABLE_DISCRETE_GPU` 宏保护）。

## 相关文档与参考

- `tools/ganesh/gl/GLTestContext.h` - OpenGL 测试上下文基类
- `include/gpu/ganesh/gl/win/GrGLMakeWinInterface.h` - Windows GL 接口创建
- WGL 扩展规范: https://www.khronos.org/registry/OpenGL/extensions/ARB/WGL_ARB_create_context.txt
- `HPBUFFER` 类型: 用于支持 P-Buffer 离屏渲染
