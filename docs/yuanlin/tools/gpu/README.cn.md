# tools/gpu/ - GPU 测试辅助工具

## 概述

`tools/gpu/` 目录提供了一套全面的 GPU 测试辅助工具，服务于 Skia 的 GPU 渲染后端（Ganesh 和 Graphite）的单元测试、集成测试和性能测试。该目录中的代码位于 `sk_gpu_test` 命名空间下，提供了后端纹理和 Surface 的工厂方法、托管纹理的生命周期管理、GPU 上下文类型枚举、刷新完成追踪和 YUV 图像处理工具等功能。

这些工具的核心设计目标是简化 GPU 测试代码的编写。在 Skia 的测试中，频繁需要创建 GPU 后端纹理、将其包装为 SkSurface 或 SkImage、等待 GPU 操作完成以及正确清理资源。`tools/gpu/` 中的辅助类封装了这些繁琐的操作，提供了简洁的 API。

特别值得关注的是 `ManagedBackendTexture` 和 `ManagedGraphiteTexture` 类。它们通过引用计数自动管理 GPU 纹理的生命周期，解决了 GPU 资源释放时序的复杂性问题——纹理必须在所有使用它的 GPU 操作完成后才能安全销毁。这些类提供了 `ReleaseProc` 回调，可以与 SkImage 和 SkSurface 的释放机制集成。

`ContextType` 枚举定义了 Skia 支持的所有 GPU 上下文类型，包括 OpenGL、OpenGL ES、ANGLE（多种 D3D/GL/Metal 后端）、Vulkan、Metal、Direct3D、Dawn（多种后端）和 Mock。该枚举在测试框架中广泛用于参数化测试，确保每种 GPU 后端都得到充分测试。

`vk/` 子目录专门提供 Vulkan 相关的测试工具，包括 Vulkan 后端上下文的创建、测试用内存分配器和 YCbCr 采样器辅助器。

## 架构图

```
+------------------------------------------------------------------+
|                    tools/gpu/ GPU 测试工具                         |
|                                                                   |
|  +----------------------------+  +-----------------------------+  |
|  |  BackendSurfaceFactory     |  |  BackendTextureImageFactory |  |
|  |  创建 GPU 后端 Surface      |  |  创建 GPU 后端纹理 Image     |  |
|  |                            |  |                             |  |
|  |  Ganesh:                   |  |  Ganesh + Graphite          |  |
|  |  - MakeBackendTextureSurf  |  |                             |  |
|  |  - MakeBackendRTSurface    |  |                             |  |
|  |  Graphite:                 |  |                             |  |
|  |  - MakeBackendTextureSurf  |  |                             |  |
|  +----------------------------+  +-----------------------------+  |
|                                                                   |
|  +----------------------------+  +-----------------------------+  |
|  |  ManagedBackendTexture     |  |  ManagedGraphiteTexture     |  |
|  |  (Ganesh)                  |  |  (Graphite)                 |  |
|  |                            |  |                             |  |
|  |  引用计数管理 GPU 纹理      |  |  引用计数管理 GPU 纹理       |  |
|  |  - MakeWithData()          |  |  - MakeUnInit()             |  |
|  |  - MakeWithoutData()       |  |  - MakeFromPixmap()         |  |
|  |  - MakeFromInfo()          |  |  - MakeMipmappedFromPixmaps |  |
|  |  - MakeFromBitmap()        |  |  - MakeFromCompressedData() |  |
|  |  - ReleaseProc()           |  |  - ReleaseProc/FinishedProc |  |
|  +----------------------------+  +-----------------------------+  |
|                                                                   |
|  +----------------------------+  +-----------------------------+  |
|  |  ContextType               |  |  FlushFinishTracker         |  |
|  |  GPU 上下文类型枚举          |  |  GPU 刷新完成追踪            |  |
|  |                            |  |                             |  |
|  |  kGL, kGLES,              |  |  - FlushFinished() 回调      |  |
|  |  kANGLE_D3D9_ES2, ...    |  |  - setFinished()             |  |
|  |  kVulkan, kMetal,         |  |  - waitTillFinished()        |  |
|  |  kDirect3D,               |  |                             |  |
|  |  kDawn_D3D11/12/Metal/Vk  |  |  支持 Ganesh 和 Graphite     |  |
|  |  kMock                    |  |                             |  |
|  +----------------------------+  +-----------------------------+  |
|                                                                   |
|  +----------------------------+  +-----------------------------+  |
|  |  YUVUtils                  |  |  CompressedTexture          |  |
|  |  YUV 图像处理工具           |  |  压缩纹理工具               |  |
|  |                            |  |                             |  |
|  |  - MakeYUVAPlanesAsA8()   |  |  处理 ETC1/BC1 等           |  |
|  |  - LazyYUVImage 类         |  |  压缩纹理格式               |  |
|  +----------------------------+  +-----------------------------+  |
|                                                                   |
|  +----------------------------+                                   |
|  |  vk/ (Vulkan 专用工具)      |                                   |
|  |  - VkTestHelper            |  Vulkan 测试环境管理              |
|  |  - VkTestUtils             |  后端上下文创建                   |
|  |  - VkTestMemoryAllocator   |  测试用内存分配器                 |
|  |  - VkYcbcrSamplerHelper    |  YCbCr 采样器管理                |
|  |  - VulkanDefines.h         |  Vulkan 头文件定义                |
|  +----------------------------+                                   |
+------------------------------------------------------------------+
```

## 目录结构

```
tools/gpu/
|-- BUILD.bazel                      # Bazel 构建定义
|
|-- # 工厂方法
|-- BackendSurfaceFactory.h/cpp      # 后端 Surface 工厂 (Ganesh + Graphite)
|-- BackendTextureImageFactory.h/cpp # 后端纹理图像工厂
|
|-- # 托管纹理
|-- ManagedBackendTexture.h/cpp      # 托管后端纹理 (Ganesh + Graphite)
|
|-- # 上下文类型
|-- ContextType.h/cpp                # GPU 上下文类型枚举及查询函数
|
|-- # 追踪与同步
|-- FlushFinishTracker.h/cpp         # GPU 刷新完成追踪器
|
|-- # 纹理工具
|-- CompressedTexture.h/cpp          # 压缩纹理创建与管理
|-- YUVUtils.h/cpp                   # YUV 图像处理 (LazyYUVImage)
|
|-- # 受保护内容
|-- ProtectedUtils.h                 # 受保护 GPU 内容工具
|
+-- vk/                             # Vulkan 专用测试工具
    |-- BUILD.bazel                  # Vulkan 子目录构建定义
    |-- VulkanDefines.h              # Vulkan 平台头文件引入
    |-- VkTestHelper.h/cpp           # Vulkan 测试辅助器
    |-- VkTestUtils.h/cpp            # Vulkan 后端上下文创建
    |-- VkTestMemoryAllocator.h/cpp  # 测试用 Vulkan 内存分配器
    +-- VkYcbcrSamplerHelper.h/cpp   # Vulkan YCbCr 采样器辅助器
```

## 关键类与函数

### ContextType 枚举

```cpp
// tools/gpu/ContextType.h
namespace skgpu {
enum class ContextType {
    kGL,                    // OpenGL
    kGLES,                  // OpenGL ES
    kANGLE_D3D9_ES2,       // ANGLE on Direct3D 9
    kANGLE_D3D11_ES2,      // ANGLE on Direct3D 11 (ES2)
    kANGLE_D3D11_ES3,      // ANGLE on Direct3D 11 (ES3)
    kANGLE_GL_ES2,         // ANGLE on OpenGL (ES2)
    kANGLE_GL_ES3,         // ANGLE on OpenGL (ES3)
    kANGLE_Metal_ES2,      // ANGLE on Metal (ES2)
    kANGLE_Metal_ES3,      // ANGLE on Metal (ES3)
    kVulkan,                // Vulkan
    kMetal,                 // Metal
    kDirect3D,              // Direct3D 12
    kDawn_D3D11,            // Dawn on D3D11
    kDawn_D3D12,            // Dawn on D3D12
    kDawn_Metal,            // Dawn on Metal
    kDawn_Vulkan,           // Dawn on Vulkan
    kDawn_OpenGL,           // Dawn on OpenGL
    kDawn_OpenGLES,         // Dawn on OpenGL ES
    kMock,                  // Mock（不渲染）
};

// 辅助查询函数
const char* ContextTypeName(ContextType type);
bool IsNativeBackend(ContextType type);      // 是否为原生后端
bool IsDawnBackend(ContextType type);        // 是否为 Dawn 后端
bool IsRenderingContext(ContextType type);   // 是否会实际渲染
}
```

### BackendSurfaceFactory

```cpp
// tools/gpu/BackendSurfaceFactory.h
namespace sk_gpu_test {
// Ganesh 版本
sk_sp<SkSurface> MakeBackendTextureSurface(GrDirectContext*,
                                           const SkImageInfo&,
                                           GrSurfaceOrigin, int sampleCnt,
                                           skgpu::Mipmapped, GrProtected,
                                           const SkSurfaceProps*);

sk_sp<SkSurface> MakeBackendRenderTargetSurface(GrDirectContext*,
                                                const SkImageInfo&,
                                                GrSurfaceOrigin, int sampleCnt,
                                                GrProtected,
                                                const SkSurfaceProps*);

// Graphite 版本
sk_sp<SkSurface> MakeBackendTextureSurface(graphite::Recorder*,
                                           const SkImageInfo&,
                                           skgpu::Mipmapped, skgpu::Protected,
                                           const SkSurfaceProps*);
}
```

### ManagedBackendTexture (Ganesh)

```cpp
// tools/gpu/ManagedBackendTexture.h
namespace sk_gpu_test {
class ManagedBackendTexture : public SkNVRefCnt<ManagedBackendTexture> {
public:
    // 带初始数据的创建
    template <typename... Args>
    static sk_sp<ManagedBackendTexture> MakeWithData(GrDirectContext*, Args&&...);

    // 无初始数据的创建
    template <typename... Args>
    static sk_sp<ManagedBackendTexture> MakeWithoutData(GrDirectContext*, Args&&...);

    // 从 SkImageInfo 创建
    static sk_sp<ManagedBackendTexture> MakeFromInfo(GrDirectContext*, const SkImageInfo&, ...);

    // 从位图/像素图创建
    static sk_sp<ManagedBackendTexture> MakeFromBitmap(GrDirectContext*, const SkBitmap&, ...);
    static sk_sp<ManagedBackendTexture> MakeFromPixmap(GrDirectContext*, const SkPixmap&, ...);

    // 释放回调（与 SkImage/SkSurface 集成）
    static void ReleaseProc(void* context);
    void* releaseContext(...) const;

    // 访问底层纹理
    const GrBackendTexture& texture();

    // YUVA 纹理组释放上下文
    static void* MakeYUVAReleaseContext(const sk_sp<ManagedBackendTexture>[kMaxPlanes]);
};
}
```

### FlushFinishTracker

```cpp
// tools/gpu/FlushFinishTracker.h
namespace sk_gpu_test {
class FlushFinishTracker : public SkRefCnt {
public:
    // 回调函数，可直接传递给 GPU 刷新 API
    static void FlushFinished(void* finishedContext);
    static void FlushFinishedResult(void* finishedContext, skgpu::CallbackResult);

    // 构造（接受 Ganesh 或 Graphite 上下文）
    explicit FlushFinishTracker(GrDirectContext* context);
    explicit FlushFinishTracker(graphite::Context* context);

    void setFinished();                           // 标记完成
    void waitTillFinished(std::function<void()>); // 阻塞等待完成
};
}
```

### LazyYUVImage (YUV 图像工具)

```cpp
// tools/gpu/YUVUtils.h
namespace sk_gpu_test {
class LazyYUVImage {
public:
    static std::unique_ptr<LazyYUVImage> Make(sk_sp<SkData>, skgpu::Mipmapped, sk_sp<SkColorSpace>);
    static std::unique_ptr<LazyYUVImage> Make(SkYUVAPixmaps, skgpu::Mipmapped, sk_sp<SkColorSpace>);

    enum class Type { kFromPixmaps, kFromGenerator, kFromTextures, kFromImages };

    SkISize dimensions() const;
    sk_sp<SkImage> refImage(GrRecordingContext*, Type);
    sk_sp<SkImage> refImage(graphite::Recorder*, Type);
};
}
```

## 依赖关系

```
sk_gpu_test (tools/gpu/)
    |
    +---> Skia Core
    |       +---> SkSurface, SkImage, SkBitmap, SkPixmap
    |       +---> SkYUVAPixmaps, SkYUVAInfo
    |       +---> SkRefCnt, SkNVRefCnt
    |
    +---> Ganesh (SK_GANESH)
    |       +---> GrDirectContext
    |       +---> GrBackendSurface, GrBackendTexture
    |       +---> GrContextOptions, GrSurfaceOrigin
    |       +---> GrProtected, skgpu::Mipmapped
    |
    +---> Graphite (SK_GRAPHITE)
    |       +---> graphite::Context, graphite::Recorder
    |       +---> graphite::BackendTexture
    |
    +---> Vulkan (vk/ 子目录)
    |       +---> Vulkan SDK (VkInstance, VkDevice, VkImage, ...)
    |       +---> VulkanMemoryAllocator (VMA)
    |       +---> skgpu::VulkanBackendContext, VulkanExtensions
    |
    +---> 被以下模块使用:
            +---> tests/ (单元测试和 GPU 测试)
            +---> tools/window/ (VulkanWindowContext)
            +---> tools/viewer/ (Viewer GPU 功能)
            +---> dm/ (Skia 测试运行器)
```

## 设计模式分析

### 1. 工厂方法模式 (Factory Method)

`BackendSurfaceFactory` 和 `BackendTextureImageFactory` 提供了丰富的重载工厂函数，根据输入参数（SkImageInfo、SkISize、SkColorType 等）和 GPU 后端类型（Ganesh/Graphite）创建不同的 Surface 和 Image。

### 2. RAII + 引用计数

`ManagedBackendTexture` 结合了 RAII 和引用计数两种资源管理模式。通过 `SkNVRefCnt` 基类提供引用计数，`ReleaseProc` 回调机制确保纹理在所有消费者（SkImage、SkSurface、GPU 操作）释放引用后才被销毁。

### 3. 惰性初始化 (Lazy Initialization)

`LazyYUVImage` 延迟 GPU 纹理的创建直到实际需要时。它在构造时只解码 YUV 数据到 CPU 像素，在 `refImage()` 调用时才上传到 GPU。如果 GPU 上下文发生变化（如 Viewer 切换后端），它会自动重新创建纹理。

### 4. 类型安全枚举 (Type-Safe Enum)

`ContextType` 使用 C++ enum class 提供类型安全的 GPU 上下文类型标识，配合辅助查询函数（`IsNativeBackend`、`IsDawnBackend`、`IsRenderingContext`）实现了类型特征查询的模式。

### 5. 变参模板转发 (Variadic Template Forwarding)

`ManagedBackendTexture::MakeWithData` 和 `MakeWithoutData` 使用变参模板和完美转发，将任意参数直接传递给 `GrDirectContext::createBackendTexture()`，在不丢失类型信息的前提下增加了资源管理层。

## 相关文档与参考

- **Vulkan 测试工具**: `tools/gpu/vk/README.md`
- **Ganesh GPU 后端**: `include/gpu/ganesh/` 头文件
- **Graphite GPU 后端**: `include/gpu/graphite/` 头文件
- **Skia 测试框架**: `tests/` 目录
- **DM 测试运行器**: `dm/` 目录
- **YUV 图像处理**: `include/core/SkYUVAInfo.h`, `include/core/SkYUVAPixmaps.h`
