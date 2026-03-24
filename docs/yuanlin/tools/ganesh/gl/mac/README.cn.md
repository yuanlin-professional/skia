# tools/ganesh/gl/mac - macOS CGL 平台 OpenGL 测试上下文

## 概述

`tools/ganesh/gl/mac` 目录实现了 macOS 平台上基于 CGL（Core OpenGL）的 OpenGL 测试上下文。CGL 是 Apple 在 macOS 上提供的底层 OpenGL 上下文管理 API，位于 NSOpenGL 之下，提供了直接的 C 语言接口来创建和管理 OpenGL 渲染上下文。

本目录包含 `CreatePlatformGLTestContext_mac.cpp`，它实现了 `CreatePlatformGLTestContext()` 工厂函数的 macOS 版本。`MacGLTestContext` 类使用 `CGLCreateContext` 和 `CGLChoosePixelFormat` 来创建 OpenGL 上下文，并通过 `dlsym(RTLD_DEFAULT, ...)` 在系统 OpenGL 框架中查询函数指针。

该实现的一个值得注意的细节是 GPU 选择策略：它首先尝试请求 Radeon eGPU（通过特定的像素格式属性），以便在拥有外置 GPU 的系统上使用高性能 GPU。如果此请求失败，则回退到默认的 GPU 选择。

由于 Apple 已在 macOS 10.14（Mojave）中弃用了 OpenGL，代码中使用了 `#pragma clang diagnostic ignored "-Wdeprecated-declarations"` 来抑制弃用警告。新的 macOS GPU 开发应优先使用 Metal 后端。

上下文切换通过 `CGLSetCurrentContext()` 和 `CGLGetCurrentContext()` 实现，GL 函数指针通过 `dlsym` 从系统 OpenGL 框架（`RTLD_DEFAULT`）中动态加载。

## 目录结构

```
tools/ganesh/gl/mac/
├── BUILD.bazel                              # Bazel 构建配置
└── CreatePlatformGLTestContext_mac.cpp      # macOS CGL 测试上下文实现
```

## 关键类与函数

### MacGLTestContext
- **基类**: `sk_gpu_test::GLTestContext`
- **功能**: 基于 CGL 的 macOS OpenGL 测试上下文
- **核心成员**:
  - `fContext` (`CGLContextObj`) - CGL 上下文对象
  - `fGLLibrary` (`void*`) - OpenGL 动态库句柄（默认 `RTLD_DEFAULT`）
- **上下文管理**:
  - `onPlatformMakeCurrent()` - 调用 `CGLSetCurrentContext(fContext)`
  - `onPlatformMakeNotCurrent()` - 调用 `CGLSetCurrentContext(nullptr)`
  - `onPlatformGetProcAddress()` - 通过 `dlsym()` 查询 GL 函数指针
- **GPU 选择**: 优先选择 Radeon eGPU，失败后回退到默认 GPU

### context_restorer 函数
- 保存当前 `CGLGetCurrentContext()` 的返回值
- 返回 lambda 用于恢复先前的 CGL 上下文

### 像素格式配置
- 支持 OpenGL 核心配置文件（3.2 Core Profile）
- 尝试支持外置 GPU（eGPU）
- 回退到基础像素格式配置

## 依赖关系

- **上游依赖**: `tools/ganesh/gl/GLTestContext.h`（基类）
- **平台依赖**: macOS OpenGL 框架（`OpenGL/OpenGL.h`）、`dlfcn.h`
- **GL 接口**: `include/gpu/ganesh/gl/mac/GrGLMakeMacInterface.h`
- **编译条件**: 仅 macOS 平台编译（`SK_BUILD_FOR_MAC`）
- **弃用说明**: Apple 已弃用 NSOpenGL/CGL，代码抑制了相关编译警告

## CGL 上下文创建流程

1. **配置像素格式**: 设置 `CGLPixelFormatAttribute` 数组
   - 首次尝试包含 eGPU 偏好设置
   - 失败后使用基础配置重试
2. **选择像素格式**: 调用 `CGLChoosePixelFormat()` 获取最佳匹配
3. **创建上下文**: 调用 `CGLCreateContext()` 创建 CGL 上下文
   - 支持通过 `shareContext` 参数创建共享上下文
4. **激活上下文**: 调用 `CGLSetCurrentContext()` 激活
5. **加载 GL 接口**: 通过 `GrGLMakeMacInterface()` 获取 GL 函数指针

## GPU 选择策略

`MacGLTestContext` 在创建时实施了一个两阶段 GPU 选择策略：

1. **首选 eGPU**: 首先尝试请求 Radeon eGPU（包括 HD7000 系列及以上），这覆盖了所有已知的 eGPU 配置。通过设置特定的 `CGLPixelFormatAttribute` 来引导系统选择外置 GPU。

2. **回退默认**: 如果 eGPU 不可用（未连接或不支持），则回退到基础像素格式配置，让系统选择默认 GPU。

## 弃用与迁移

Apple 从 macOS 10.14 Mojave (2018) 开始弃用 OpenGL：
- 代码中使用 `#pragma clang diagnostic ignored "-Wdeprecated-declarations"` 抑制警告
- 推荐迁移到 `tools/ganesh/mtl/` 或 `tools/graphite/mtl/`
- macOS 14+ 的某些功能可能不再通过 GL 暴露

## 相关文档与参考

- `tools/ganesh/gl/GLTestContext.h` - OpenGL 测试上下文基类
- `tools/ganesh/mtl/` - Metal 后端测试上下文（macOS 推荐替代方案）
- Apple 文档: CGL (Core OpenGL) Reference
- Apple 弃用声明: OpenGL 自 macOS 10.14 起被标记为弃用
