# android/ - Android 平台 OpenGL ES 接口

## 概述

`android/` 目录提供 Android 平台上的 OpenGL ES 接口加载实现。该目录的实现非常简洁 -- 它直接复用了 `egl/` 目录的实现，因为 Android 原生使用 EGL 作为其 GL 上下文管理机制。

Android 是 OpenGL ES 的主要平台之一，支持 ES 2.0（Android 2.2+）和 ES 3.0/3.1/3.2（Android 4.3+/5.0+/7.0+）。Skia 在 Android 上通过 EGL 接口加载 GL ES 函数指针。

## 文件分类索引

### 1. Android GL 接口 — Platform Interface

| 文件 | 说明 |
|------|------|
| GrGLMakeNativeInterface_android.cpp | Android GL ES 接口入口（通过 #include 复用 EGL 实现） |

## 关键实现

### 源码内容

```cpp
// 直接包含EGL目录的实现文件
#include "src/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.cpp"
#include "src/gpu/ganesh/gl/egl/GrGLMakeNativeInterface_egl.cpp"
```

**设计决策：**
Android 使用 `#include` 直接包含 `egl/` 目录中的两个源文件，完全复用 EGL 的函数加载逻辑。这是因为：
1. Android 原生支持 EGL 作为 GL 上下文管理层
2. Android NDK 提供了完整的 EGL 和 GLES 头文件及库
3. 函数加载策略完全相同（编译时链接核心函数 + `eglGetProcAddress` 加载扩展）

**最终效果：**
调用 `GrGLInterfaces::MakeEGL()` 或旧版 `GrGLMakeNativeInterface()` 来创建 Android 上的 GL ES 接口。

## Android 特有考虑

虽然本目录的代码简单复用了 EGL 实现，但 Skia 在 Android 上有一些特有的 GL 相关处理：

1. **AHardwareBuffer 互操作：** 父目录中的 `AHardwareBufferGL.cpp` 实现了 Android HardwareBuffer 与 GL 纹理之间的互操作，用于零拷贝纹理共享
2. **Gralloc 缓冲：** Android 的图形内存分配器与 GL 的交互
3. **SurfaceTexture：** Android 的外部纹理（`GL_TEXTURE_EXTERNAL_OES`）支持
4. **驱动兼容性：** `GrGLCaps.cpp` 中有大量针对 Qualcomm Adreno、ARM Mali、Imagination PowerVR 等移动 GPU 的兼容性修正

## 依赖关系

- **上游：** 由 Android 应用或 Skia 的 Android 集成层调用
- **下游：** 完全依赖 `egl/` 目录的实现
- **系统依赖：** Android NDK 中的 EGL 和 GLES 库

## 适用平台

- Android 手机和平板（所有 CPU 架构：ARM, ARM64, x86, x86_64）
- Android TV
- Android Automotive
- ChromeOS 的 Android 容器
