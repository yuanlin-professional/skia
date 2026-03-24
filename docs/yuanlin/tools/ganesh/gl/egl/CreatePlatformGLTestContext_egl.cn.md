# CreatePlatformGLTestContext_egl.cpp - EGL GL 测试上下文

> 源文件: `tools/ganesh/gl/egl/CreatePlatformGLTestContext_egl.cpp`

## 概述

实现基于 EGL 的 OpenGL/OpenGL ES 测试上下文,支持桌面 GL 和 GL ES,包含 EGL Image 操作、受保护内容上下文创建等高级功能。是 Linux/Android 等平台的 GL 测试上下文实现。

## 架构位置

属于 Skia GPU 测试基础设施的 EGL 平台适配层,实现了 `sk_gpu_test::GLTestContext` 的 EGL 特化版本,是功能最完整的 GL 测试上下文实现之一。

## 主要类与结构体

- **`EGLGLTestContext`**: 继承自 `GLTestContext`,持有 `EGLContext`、`EGLDisplay`、`EGLSurface`,支持 EGL Image 扩展

## 公共 API 函数

- **`CreatePlatformGLTestContext()`**: 工厂函数
- **`texture2DToEGLImage()`**: 将 2D 纹理转换为 EGL Image
- **`destroyEGLImage()`**: 销毁 EGL Image
- **`eglImageToExternalTexture()`**: 将 EGL Image 转换为外部纹理
- **`makeNew()`**: 创建新的独立上下文

## 内部实现细节

构造函数遍历 GL 和 GL ES 标准,自动选择可用的 API。支持 `EGL_EXT_protected_content` 受保护内容扩展。使用 1x1 Pbuffer 作为渲染表面。支持 `GR_EGL_TRY_GLES3_THEN_GLES2` 宏控制 GL ES 版本策略。

## 依赖关系

- EGL/eglext.h: EGL 核心和扩展 API
- `GrGLInterfaces::MakeEGL()`: 创建 EGL GL 接口

## 设计模式与设计决策

- 自动协商 API 类型(GL vs GL ES)
- 受保护上下文通过全局标志 `gCreateProtectedContext` 控制
- EGL Image 扩展函数通过 `eglGetProcAddress` 动态加载

## 性能考量

使用最小化的 1x1 Pbuffer 表面,减少资源占用。EGL Image 操作为零拷贝纹理共享。

## 相关文件

- `include/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.h`
- `tools/ganesh/gl/GLTestContext.h`
