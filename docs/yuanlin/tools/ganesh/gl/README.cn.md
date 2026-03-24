# tools/ganesh/gl - Ganesh OpenGL 后端测试上下文

## 概述

`tools/ganesh/gl` 目录实现了 Ganesh GPU 后端的 OpenGL 测试上下文框架。OpenGL 是 Skia 支持的最广泛的图形 API，本目录提供了一套跨平台的 OpenGL 上下文管理基础设施，支持桌面 GL、OpenGL ES 以及通过 ANGLE 模拟的多种后端。

`GLTestContext` 类继承自 `TestContext`，是所有 OpenGL 测试上下文的抽象基类。它封装了 `GrGLInterface`（OpenGL 函数指针表），提供了 EGL 图像集成测试支持（`texture2DToEGLImage`、`eglImageToExternalTexture`），以及版本覆盖功能（`overrideVersion`，用于模拟较低版本的 GLES）。该类还提供了类型安全的 GL 函数指针查询接口 `getGLProcAddress`。

`CreatePlatformGLTestContext()` 工厂函数根据运行平台和请求的 GL 标准（`kGL_GrGLStandard` 或 `kGLES_GrGLStandard`）创建对应的平台实现。每个平台的具体实现位于对应的子目录中：`egl/`（EGL/Linux/Android）、`glx/`（X11/Linux）、`mac/`（macOS CGL）、`win/`（Windows WGL）、`iOS/`（iOS EAGL）、`none/`（空实现）。

此外，`angle/` 子目录提供了 ANGLE（Almost Native Graphics Layer Engine）集成，允许通过 OpenGL ES 接口使用 D3D9、D3D11、OpenGL 或 Metal 作为底层实现。`interface/` 子目录则包含了 GrGLInterface 函数指针表的自动生成工具。

所有代码受 `SK_GL` 编译宏保护。

## 目录结构

```
tools/ganesh/gl/
├── BUILD.bazel                    # Bazel 构建配置
├── GLTestContext.h                # OpenGL 测试上下文基类声明
├── GLTestContext.cpp              # OpenGL 测试上下文基类实现
├── interface/                     # GrGLInterface 代码生成工具
│   ├── interface.json5            # GL 函数接口规范定义
│   ├── gen_interface.go           # Go 语言代码生成器
│   ├── templates.go               # 代码生成模板
│   ├── Makefile                   # 生成命令
│   └── README.md                  # 接口生成工具说明
├── angle/                         # ANGLE 后端集成
│   ├── GLTestContext_angle.h      # ANGLE 测试上下文声明
│   └── GLTestContext_angle.cpp    # ANGLE 测试上下文实现
├── egl/                           # EGL 平台实现（Linux/Android）
├── glx/                           # GLX 平台实现（X11/Linux）
├── mac/                           # CGL 平台实现（macOS）
├── win/                           # WGL 平台实现（Windows）
├── iOS/                           # EAGL 平台实现（iOS）
└── none/                          # 空平台实现（无 GL 支持）
```

## 关键类与函数

### GLTestContext
- **命名空间**: `sk_gpu_test`
- **基类**: `TestContext`
- **功能**: 所有 OpenGL 测试上下文的抽象基类
- **核心成员**:
  - `fOriginalGLInterface` - 原始 GL 接口函数指针表
  - `fGLInterface` - 当前使用的 GL 接口（可能经过版本覆盖）
- **核心方法**:
  - `backend()` - 返回 `GrBackendApi::kOpenGL`
  - `isValid()` - 检查 GL 上下文是否有效
  - `gl()` - 获取 `GrGLInterface` 指针
  - `overrideVersion()` - 覆盖 GL 版本和着色器语言版本字符串
  - `makeNew()` - 创建同类型的新 GL 上下文
  - `getGLProcAddress()` - 类型安全的 GL 函数指针查询
  - `texture2DToEGLImage()` / `eglImageToExternalTexture()` - EGL 图像互操作
- **纯虚方法**: `onPlatformGetProcAddress()` - 由各平台子类实现

### CreatePlatformGLTestContext
- **签名**: `GLTestContext* CreatePlatformGLTestContext(GrGLStandard, GLTestContext* shareContext)`
- **功能**: 创建平台特定的 OpenGL 测试上下文
- **参数**: `forcedGpuAPI` - 强制使用的 GL 标准（GL 或 GLES）

## 依赖关系

- **上游依赖**: `tools/ganesh/TestContext.h`（基类）
- **GL 依赖**: `include/gpu/ganesh/gl/GrGLInterface.h`、`src/gpu/ganesh/gl/GrGLUtil.h`
- **编译条件**: 需要定义 `SK_GL`
- **被引用**: `tools/ganesh/GrContextFactory.cpp`（通过多个 ContextType 使用）
- **平台子目录**: 每个平台子目录提供 `CreatePlatformGLTestContext` 的具体实现

## 平台支持矩阵

| 平台 | 子目录 | 窗口系统 | GL 标准 | 状态 |
|------|--------|----------|---------|------|
| Linux (X11) | `glx/` | GLX | 桌面 GL | 活跃 |
| Linux/Android | `egl/` | EGL | GL/GLES | 活跃 |
| macOS | `mac/` | CGL | 桌面 GL | 已弃用* |
| Windows | `win/` | WGL | 桌面 GL | 活跃 |
| iOS | `iOS/` | EAGL | GLES | 已弃用* |
| 无 GL | `none/` | 无 | 无 | 空实现 |
| ANGLE | `angle/` | EGL | GLES | 活跃 |

*注: Apple 已弃用 OpenGL/GLES，但 Skia 仍维护相关代码以支持旧版系统。

## EGL 图像互操作

`GLTestContext` 提供了 EGL 图像互操作的虚函数接口，主要用于测试跨 API 的纹理共享：
- `texture2DToEGLImage()` - 将 GL 2D 纹理封装为 EGL 图像
- `eglImageToExternalTexture()` - 将 EGL 图像封装为 `GL_TEXTURE_EXTERNAL_OES`
- 此功能目前仅由 EGL 后端实现，其他平台返回默认值

## 版本覆盖机制

`overrideVersion()` 方法允许在测试中伪造 GL 版本字符串，这对于测试低版本 GLES 代码路径非常有用。例如，`GrContextFactory` 的 `ContextOverrides::kFakeGLESVersionAs2` 选项会将 GLES 3.0 上下文的版本字符串替换为 "OpenGL ES 2.0"，从而触发 ES 2.0 的代码路径。

## 相关文档与参考

- `tools/ganesh/TestContext.h` - 测试上下文基类
- `include/gpu/ganesh/gl/GrGLInterface.h` - GL 函数指针接口
- `tools/ganesh/gl/interface/` - GL 接口代码生成工具
- `tools/ganesh/gl/angle/` - ANGLE 后端集成
- `src/gpu/ganesh/gl/` - Ganesh OpenGL 后端核心实现
