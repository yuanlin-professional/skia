# GLWindowContext_android

> 源文件: tools/window/android/GLWindowContext_android.cpp

## 概述

`GLWindowContext_android` 是 Skia Ganesh 渲染引擎在 Android 平台上使用 OpenGL ES 的窗口上下文实现。该文件通过 EGL (Embedded-System Graphics Library) 接口管理 OpenGL ES 上下文和 Surface，为 Android 应用提供硬件加速的 2D 图形渲染能力。

该实现支持 MSAA 多重采样、保护内容渲染、VSync 控制等高级特性，是 Android 平台上最成熟和兼容性最好的渲染后端之一。

## 架构位置

该文件位于 Skia 工具层的 Android 平台窗口实现中：

```
skia/
  tools/
    window/
      android/
        GLWindowContext_android.cpp     # 本文件
        WindowContextFactory_android.h  # Android 窗口工厂
      GLWindowContext.h                 # OpenGL 窗口上下文基类
      DisplayParams.h                   # 显示参数配置
  include/
    gpu/ganesh/gl/
      GrGLInterface.h                   # OpenGL 接口封装
  src/
    gpu/ganesh/                         # Ganesh 渲染引擎核心
```

在 Skia 架构层次：
- **平台层**: 与 Android NDK 的 ANativeWindow 和 EGL 交互
- **窗口系统层**: 实现跨平台窗口上下文接口
- **渲染后端层**: 连接 Ganesh 渲染引擎和 OpenGL ES
- **图形 API 层**: 通过 EGL 管理 OpenGL ES 上下文

## 主要类与结构体

### GLWindowContext_android

继承自 `skwindow::internal::GLWindowContext` 的 Android 平台实现类。

**核心成员变量**:
```cpp
EGLDisplay fDisplay;          // EGL 显示连接
EGLContext fEGLContext;       // OpenGL ES 渲染上下文
EGLSurface fSurfaceAndroid;   // 窗口 Surface
ANativeWindow* fNativeWindow; // Android 原生窗口
```

**核心方法**:
- `GLWindowContext_android()`: 构造函数，初始化 EGL 和上下文
- `~GLWindowContext_android()`: 析构函数，清理资源
- `onInitializeContext()`: 初始化 EGL 显示、上下文和 Surface
- `onDestroyContext()`: 销毁 EGL 资源
- `onSwapBuffers()`: 交换前后缓冲区

## 公共 API 函数

### MakeGLForAndroid

```cpp
std::unique_ptr<WindowContext> MakeGLForAndroid(
    ANativeWindow* window,
    std::unique_ptr<const DisplayParams> params)
```

**功能**: 创建 Android 平台的 OpenGL ES 窗口上下文工厂函数。

**参数**:
- `window`: Android 原生窗口指针
- `params`: 显示参数配置（MSAA、VSync、保护内容、色彩空间等）

**返回值**:
- 成功返回有效的 `WindowContext` 智能指针
- 失败返回 `nullptr`

**使用场景**: 在 Android 应用中创建 Skia Ganesh OpenGL ES 渲染上下文。

## 内部实现细节

### EGL 初始化流程

1. **获取窗口尺寸**:
   ```cpp
   fWidth = ANativeWindow_getWidth(fNativeWindow);
   fHeight = ANativeWindow_getHeight(fNativeWindow);
   ```

2. **获取并初始化 EGL 显示**:
   ```cpp
   fDisplay = eglGetDisplay(EGL_DEFAULT_DISPLAY);
   eglInitialize(fDisplay, &majorVersion, &minorVersion);
   ```

3. **检查保护内容支持**:
   ```cpp
   const char* extensions = eglQueryString(fDisplay, EGL_EXTENSIONS);
   if (fDisplayParams->createProtectedNativeBackend() &&
       !strstr(extensions, "EGL_EXT_protected_content")) {
       // 降级为非保护模式
   }
   ```

4. **绑定 OpenGL ES API**:
   ```cpp
   SkAssertResult(eglBindAPI(EGL_OPENGL_ES_API));
   ```

### EGL 配置选择

```cpp
const EGLint configAttribs[] = {
    EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
    EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
    EGL_RED_SIZE, 8,
    EGL_GREEN_SIZE, 8,
    EGL_BLUE_SIZE, 8,
    EGL_ALPHA_SIZE, 8,
    EGL_STENCIL_SIZE, 8,
    EGL_SAMPLE_BUFFERS, eglSampleCnt ? 1 : 0,
    EGL_SAMPLES, eglSampleCnt,
    EGL_NONE
};
```

**配置特点**:
- 支持 OpenGL ES 2.0 及以上
- RGBA8888 颜色格式，8 位模板缓冲
- 可选的 MSAA 支持
- PBuffer 表面类型

### OpenGL ES 上下文创建

```cpp
std::vector<EGLint> kEGLContextAttribsForOpenGLES = {
    EGL_CONTEXT_CLIENT_VERSION, 2,
};

if (fDisplayParams->createProtectedNativeBackend()) {
    kEGLContextAttribsForOpenGLES.push_back(EGL_PROTECTED_CONTENT_EXT);
    kEGLContextAttribsForOpenGLES.push_back(EGL_TRUE);
}

kEGLContextAttribsForOpenGLES.push_back(EGL_NONE);

fEGLContext = eglCreateContext(fDisplay, surfaceConfig, nullptr,
                               kEGLContextAttribsForOpenGLES.data());
```

### 窗口 Surface 创建

```cpp
const EGLint surfaceAttribs[] = {
    fDisplayParams->createProtectedNativeBackend() ? EGL_PROTECTED_CONTENT_EXT : EGL_NONE,
    fDisplayParams->createProtectedNativeBackend() ? EGL_TRUE : EGL_NONE,
    EGL_NONE
};

fSurfaceAndroid = eglCreateWindowSurface(fDisplay, surfaceConfig,
                                         fNativeWindow, surfaceAttribs);
```

### 上下文激活与初始化

```cpp
SkAssertResult(eglMakeCurrent(fDisplay, fSurfaceAndroid, fSurfaceAndroid, fEGLContext));

glClearStencil(0);
glClearColor(0, 0, 0, 0);
glStencilMask(0xffffffff);
glClear(GL_STENCIL_BUFFER_BIT | GL_COLOR_BUFFER_BIT);
```

### 配置查询

```cpp
eglGetConfigAttrib(fDisplay, surfaceConfig, EGL_STENCIL_SIZE, &fStencilBits);
eglGetConfigAttrib(fDisplay, surfaceConfig, EGL_SAMPLES, &fSampleCount);
fSampleCount = std::max(fSampleCount, 1);

eglSwapInterval(fDisplay, fDisplayParams->disableVsync() ? 0 : 1);
```

### 缓冲区交换

```cpp
void GLWindowContext_android::onSwapBuffers() {
    if (fDisplay && fEGLContext && fSurfaceAndroid) {
        eglSwapBuffers(fDisplay, fSurfaceAndroid);
    }
}
```

### 资源清理

```cpp
void GLWindowContext_android::onDestroyContext() {
    if (!fDisplay || !fEGLContext || !fSurfaceAndroid) {
        return;
    }
    eglMakeCurrent(fDisplay, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    SkAssertResult(eglDestroySurface(fDisplay, fSurfaceAndroid));
    SkAssertResult(eglDestroyContext(fDisplay, fEGLContext));
    fEGLContext = EGL_NO_CONTEXT;
    fSurfaceAndroid = EGL_NO_SURFACE;
}
```

## 依赖关系

**直接依赖**:
- `<EGL/egl.h>`: EGL 核心 API
- `<GLES/gl.h>`: OpenGL ES 头文件
- `include/gpu/ganesh/gl/GrGLInterface.h`: Skia OpenGL 接口封装
- `tools/window/DisplayParams.h`: 显示参数配置
- `tools/window/GLWindowContext.h`: OpenGL 窗口上下文基类
- `tools/window/android/WindowContextFactory_android.h`: Android 工厂

**间接依赖**:
- Android NDK: `ANativeWindow` 和 EGL 实现
- OpenGL ES 驱动: GPU 厂商提供
- `src/gpu/ganesh/`: Ganesh 渲染引擎

**依赖图**:
```
Android App
    ↓
MakeGLForAndroid
    ↓
GLWindowContext_android
    ↓
EGL (eglGetDisplay, eglCreateContext)
    ↓
OpenGL ES 驱动
    ↓
GPU 硬件
```

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `MakeGLForAndroid` 封装复杂的 EGL 初始化
2. **模板方法模式**: 重写基类的 `onInitializeContext`、`onDestroyContext`、`onSwapBuffers`
3. **RAII 模式**: 构造时初始化，析构时清理

### 设计决策

**1. EGL 作为中间层**:
- 使用 EGL 而非直接操作 OpenGL，提供标准化的上下文管理
- 支持跨平台（Android、嵌入式系统）

**2. 保护内容支持**:
- 通过 `EGL_EXT_protected_content` 扩展支持 DRM 内容
- 运行时检查并优雅降级

**3. 灵活的 MSAA 配置**:
```cpp
EGLint eglSampleCnt = fDisplayParams->msaaSampleCount() > 1 ?
                      fDisplayParams->msaaSampleCount() > 1 : 0;
```

**4. VSync 控制**:
```cpp
eglSwapInterval(fDisplay, fDisplayParams->disableVsync() ? 0 : 1);
```

**5. 窗口引用保存**:
- 保存 `fNativeWindow` 用于 `setDisplayParams` 和 `resize` 调用

**6. 完整的状态初始化**:
- 清除颜色和模板缓冲区
- 设置模板掩码
- 确保干净的初始状态

### 错误处理

- 使用 `SkAssertResult` 验证 EGL 调用
- 使用 `SkASSERT` 进行断言检查
- 使用 `SkDebugf` 打印调试信息（注释掉的代码）

## 性能考量

### 优化策略

1. **VSync 可配置**: 允许禁用垂直同步以获得更高帧率
2. **延迟状态查询**: 仅在初始化时查询 EGL 配置属性
3. **最小化状态切换**: 保持上下文激活状态
4. **智能 MSAA**: 根据配置动态启用 MSAA

### 性能特征

- **初始化时间**: 中等（需要创建 EGL 显示和上下文）
- **缓冲区交换**: 取决于 VSync 设置
- **内存占用**: 低（仅 EGL 句柄和窗口指针）
- **兼容性**: 极佳（几乎所有 Android 设备支持）

### MSAA 性能影响

```cpp
EGL_SAMPLE_BUFFERS, eglSampleCnt ? 1 : 0,
EGL_SAMPLES, eglSampleCnt,
```

MSAA 会增加内存和填充率开销，但在现代移动 GPU 上影响较小。

### 保护内容性能

保护内容模式可能禁用某些优化路径，但对大多数应用影响不大。

## 相关文件

### 同目录文件
- `tools/window/android/VulkanWindowContext_android.cpp`: Ganesh Vulkan 实现
- `tools/window/android/GraphiteVulkanWindowContext_android.cpp`: Graphite Vulkan 实现
- `tools/window/android/GraphiteDawnWindowContext_android.cpp`: Graphite Dawn 实现
- `tools/window/android/RasterWindowContext_android.cpp`: 软件光栅化实现
- `tools/window/android/WindowContextFactory_android.h`: Android 窗口工厂

### 基类与工具
- `tools/window/GLWindowContext.h`: OpenGL 窗口上下文基类
- `tools/window/DisplayParams.h`: 显示参数配置
- `tools/window/WindowContext.h`: 窗口上下文接口
- `include/gpu/ganesh/gl/GrGLInterface.h`: OpenGL 接口封装

### 其他平台 GL 实现
- `tools/window/mac/GLWindowContext_mac.mm`: macOS 实现
- `tools/window/win/GLWindowContext_win.cpp`: Windows 实现
- `tools/window/unix/GLWindowContext_unix.cpp`: Linux 实现
- `tools/window/ios/GLWindowContext_ios.mm`: iOS 实现

### EGL 相关
- Android NDK EGL 头文件和库
- `<EGL/egl.h>`, `<EGL/eglext.h>`
