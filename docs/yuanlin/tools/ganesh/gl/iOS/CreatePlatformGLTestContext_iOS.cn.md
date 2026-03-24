# CreatePlatformGLTestContext_iOS.mm - iOS GL 测试上下文

> 源文件: `tools/ganesh/gl/iOS/CreatePlatformGLTestContext_iOS.mm`

## 概述

此文件实现了 iOS 平台上的 OpenGL ES 测试上下文。通过 `IOSGLTestContext` 类封装 `EAGLContext` 的创建和管理,支持 GL ES 3.0(优先)和 GL ES 2.0(回退),以及共享上下文。

## 架构位置

属于 Skia GPU 测试基础设施的 iOS 平台适配层,实现了 `sk_gpu_test::GLTestContext` 的 iOS 特化版本。仅支持 GL ES(请求桌面 GL 时返回 NULL)。

## 主要类与结构体

- **`IOSGLTestContext`**: 继承自 `sk_gpu_test::GLTestContext`,持有 `EAGLContext` 和 GL 动态库句柄

## 公共 API 函数

- **`sk_gpu_test::CreatePlatformGLTestContext()`**: 工厂函数,创建 iOS GL ES 测试上下文

## 内部实现细节

使用 `sk_cfp<EAGLContext*>` 管理 Objective-C 对象的生命周期。通过 `dlopen` 加载 OpenGL 框架库,`dlsym` 查找 GL 函数地址。上下文销毁时显式将当前上下文设为 nil 以确保立即释放。

## 依赖关系

- `<OpenGLES/EAGL.h>`: iOS EAGL 框架
- `GrGLInterfaces::MakeIOS()`: 创建 iOS GL 接口
- `sk_cfp`: Core Foundation 智能指针

## 设计模式与设计决策

- 优先尝试 GL ES 3.0,失败后回退到 GL ES 2.0
- 使用 `SkScopeExit` 保证上下文恢复
- 通过 `dlsym` 实现 `onPlatformGetProcAddress`,支持运行时函数查找

## 性能考量

GL 库仅加载一次,函数查找通过 `dlsym` 按需执行。

## 相关文件

- `include/gpu/ganesh/gl/ios/GrGLMakeIOSInterface.h`
- `tools/ganesh/gl/GLTestContext.h`
