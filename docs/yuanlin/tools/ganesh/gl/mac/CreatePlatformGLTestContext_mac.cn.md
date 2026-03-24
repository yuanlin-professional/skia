# CreatePlatformGLTestContext_mac.cpp - macOS GL 测试上下文

> 源文件: `tools/ganesh/gl/mac/CreatePlatformGLTestContext_mac.cpp`

## 概述

实现 macOS 平台的 OpenGL 测试上下文,通过 CGL (Core OpenGL) API 创建 OpenGL 3.2 Core Profile 上下文。支持 eGPU(外部 GPU)优先选择。

## 架构位置

Skia GPU 测试基础设施的 macOS 平台适配层。仅支持桌面 GL(不支持 GL ES)。

## 主要类与结构体

- **`MacGLTestContext`**: 继承自 `GLTestContext`,持有 `CGLContextObj` 和 GL 库句柄

## 公共 API 函数

- **`CreatePlatformGLTestContext()`**: 工厂函数,仅接受桌面 GL 标准

## 内部实现细节

像素格式选择分两步:首先尝试带 eGPU 参数(Radeon HD7000+)的配置,失败后回退到基础配置。通过 `dlopen` 加载 OpenGL 框架库。所有 NSOpenGL 弃用警告被静默处理。

## 依赖关系

- `<OpenGL/OpenGL.h>`: CGL API
- `GrGLInterfaces::MakeMac()`: macOS GL 接口

## 设计模式与设计决策

- eGPU 优先策略,自动降级到内置 GPU
- 使用 3.2 Core Profile 确保现代 GL 功能可用

## 性能考量

eGPU 优先选择可利用更强的外部 GPU 硬件。

## 相关文件

- `include/gpu/ganesh/gl/mac/GrGLMakeMacInterface.h`
