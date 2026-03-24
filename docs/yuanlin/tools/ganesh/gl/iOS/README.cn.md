# tools/ganesh/gl/iOS - iOS EAGL 平台 OpenGL ES 测试上下文

## 概述

`tools/ganesh/gl/iOS` 目录实现了 iOS 平台上基于 EAGL（Embedded Apple GL）的 OpenGL ES 测试上下文。EAGL 是 Apple 在 iOS 平台上提供的 OpenGL ES 上下文管理框架，用于创建和管理 OpenGL ES 渲染上下文。

本目录仅包含一个实现文件 `CreatePlatformGLTestContext_iOS.mm`（Objective-C++ 源文件），它提供了 `CreatePlatformGLTestContext()` 工厂函数的 iOS 平台实现。该实现使用 EAGL API 创建 OpenGL ES 上下文，并通过 Objective-C 运行时与 iOS 框架交互。

iOS 平台上 Skia 默认使用 OpenGL ES（而非桌面 GL），因此此实现仅支持 `kGLES_GrGLStandard` 标准。创建的上下文使用 EAGLContext 类管理 GL 状态，并通过 CAEAGLLayer 或离屏帧缓冲区进行渲染。

需要注意的是，Apple 已在 iOS 12 中弃用了 OpenGL ES，推荐使用 Metal。因此，本目录的代码主要用于维护对旧设备和旧版 iOS 的兼容性测试。新的 iOS GPU 工作应优先考虑 Metal 后端。

本目录的代码仅在 iOS 平台（`SK_BUILD_FOR_IOS`）上编译。

## 目录结构

```
tools/ganesh/gl/iOS/
├── BUILD.bazel                              # Bazel 构建配置
└── CreatePlatformGLTestContext_iOS.mm       # iOS EAGL 测试上下文实现
```

## 关键类与函数

### CreatePlatformGLTestContext（iOS 实现）
- **文件**: `CreatePlatformGLTestContext_iOS.mm`
- **语言**: Objective-C++（.mm 扩展名）
- **功能**: 创建 iOS 平台的 OpenGL ES 测试上下文
- **实现细节**:
  - 使用 `EAGLContext` 创建 OpenGL ES 上下文
  - 支持 GLES 2.0/3.0 版本
  - 实现 `onPlatformMakeCurrent()` 通过 `[EAGLContext setCurrentContext:]`
  - 通过 `dlsym` 查询 GL 函数指针

### 平台上下文管理
- `onPlatformMakeCurrent()` - 调用 `[EAGLContext setCurrentContext:]` 设置当前上下文
- `onPlatformMakeNotCurrent()` - 调用 `[EAGLContext setCurrentContext:nil]` 清除当前上下文
- `onPlatformGetAutoContextRestore()` - 保存并恢复之前的 EAGL 上下文

## 依赖关系

- **上游依赖**: `tools/ganesh/gl/GLTestContext.h`（基类）
- **平台依赖**: iOS SDK（OpenGLES.framework、`EAGLContext`）
- **编译条件**: 仅 iOS 平台编译（`SK_BUILD_FOR_IOS`）
- **被引用**: `tools/ganesh/gl/GLTestContext.h`（通过 `CreatePlatformGLTestContext` 调用）
- **GL 接口**: `include/gpu/ganesh/gl/ios/GrGLMakeIOSInterface.h`
- **注意**: Apple 已弃用 OpenGL ES，推荐使用 Metal（`tools/ganesh/mtl/`）

## EAGL 上下文创建流程

1. **选择 GLES 版本**: 根据请求的 GL 标准选择 GLES 2.0 或 3.0
2. **创建 EAGLContext**: 调用 `[[EAGLContext alloc] initWithAPI:]`
   - 支持通过 `sharegroup` 参数创建共享上下文
3. **激活上下文**: 调用 `[EAGLContext setCurrentContext:]`
4. **创建帧缓冲**: 设置离屏 Renderbuffer 用于渲染
5. **加载 GL 接口**: 通过 `GrGLMakeIOSInterface()` 获取 GL 函数指针

## 弃用与迁移

Apple 从 iOS 12 (2018) 开始弃用 OpenGL ES，推荐使用 Metal：
- 新应用应使用 `tools/ganesh/mtl/` 或 `tools/graphite/mtl/`
- 现有 OpenGL ES 应用可继续运行，但不会获得新功能和优化
- Skia 保留 iOS GL 支持主要用于旧版兼容性测试
- 未来版本的 iOS 可能移除 OpenGL ES 运行时

## iOS 平台限制

- 仅支持 OpenGL ES（不支持桌面 OpenGL）
- 不支持 EGL 图像互操作（`texture2DToEGLImage` 返回 nullptr）
- GL 函数指针通过 `dlsym(RTLD_DEFAULT, ...)` 从系统框架获取
- `onPlatformGetAutoContextRestore` 通过保存/恢复 `[EAGLContext currentContext]` 实现

## 相关文档与参考

- `tools/ganesh/gl/GLTestContext.h` - OpenGL 测试上下文基类
- `tools/ganesh/mtl/` - Metal 后端测试上下文（iOS 推荐替代方案）
- Apple 文档: EAGLContext Class Reference
- Apple 弃用声明: OpenGL ES 自 iOS 12 起被标记为弃用
