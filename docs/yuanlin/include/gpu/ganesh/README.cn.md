# include/gpu/ganesh - Ganesh 渲染引擎公共 API

## 概述

`include/gpu/ganesh` 是 Skia 中 Ganesh GPU 渲染引擎的公共 API 目录。Ganesh 是 Skia 的传统
GPU 加速后端，支持 OpenGL、OpenGL ES、Vulkan、Metal 和 Direct3D 12 等多种图形 API。它通过
`GrDirectContext` 提供 GPU 上下文管理，通过 `GrBackendTexture` 和 `GrBackendRenderTarget`
提供后端纹理和渲染目标的抽象封装。

Ganesh 的架构围绕 `GrDirectContext` 展开。`GrDirectContext` 继承自 `GrRecordingContext`，
后者又继承自 `GrImageContext`。这种继承层次使得在不需要直接 GPU 操作的场景下（如延迟显示列表
DDL 的录制），可以使用更轻量的上下文类型。`GrContextThreadSafeProxy` 提供了线程安全的上下文
代理，允许在不直接访问 3D API 的情况下执行某些操作。

`GrContextOptions` 提供了丰富的选项来控制 GPU 上下文的行为，包括持久缓存、着色器错误处理、
性能调优参数和驱动程序问题规避措施。`GrTypes.h` 定义了 `GrBackendApi` 枚举（OpenGL、Vulkan、
Metal、Direct3D、Mock）和各种刷新/提交选项。

该目录还包含将 GPU 纹理与 Skia 的 `SkImage` 和 `SkSurface` 集成的API。`SkImageGanesh.h`
提供了从 GPU 纹理创建 `SkImage` 的工厂方法，`SkSurfaceGanesh.h` 提供了在 GPU 上创建
`SkSurface` 的工厂方法。`GrYUVABackendTextures.h` 特别支持 YUV 平面纹理的管理。

Ganesh 虽然是较为成熟的渲染引擎，但 Skia 团队正在积极开发其继任者 Graphite。目前两者并行存在，
Ganesh 继续维护对现有平台和 API 的支持。

## 架构图

```
include/gpu/ganesh/
    |
    +-- GrTypes.h                   <-- 后端 API 枚举、刷新/提交选项
    +-- GrContextOptions.h          <-- GPU 上下文选项（缓存、调优等）
    +-- GrDriverBugWorkarounds.h    <-- GPU 驱动问题规避
    |
    +-- GrRecordingContext.h        <-- 录制上下文（基类）
    |       ^
    |       |
    +-- GrDirectContext.h           <-- 直接 GPU 上下文（核心）
    |
    +-- GrContextThreadSafeProxy.h  <-- 线程安全上下文代理
    |
    +-- GrBackendSurface.h          <-- 后端纹理/渲染目标抽象
    +-- GrBackendSemaphore.h        <-- 后端信号量抽象
    +-- GrYUVABackendTextures.h     <-- YUV 平面纹理集合
    +-- GrExternalTextureGenerator.h <-- 外部纹理生成器
    |
    +-- SkImageGanesh.h             <-- GPU SkImage 工厂方法
    +-- SkSurfaceGanesh.h           <-- GPU SkSurface 工厂方法
    +-- SkMeshGanesh.h              <-- GPU SkMesh 支持
    |
    +-- gl/                         <-- OpenGL 后端
    +-- vk/                         <-- Vulkan 后端
    +-- mtl/                        <-- Metal 后端
    +-- d3d/                        <-- Direct3D 12 后端
    +-- mock/                       <-- Mock 测试后端
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrTypes.h` | `GrBackendApi` 枚举、`GrFlushInfo`、`GrSemaphoresSubmitted` 等核心类型 |
| `GrContextOptions.h` | GPU 上下文选项：缓存策略、着色器处理、性能参数等 |
| `GrDirectContext.h` | 核心 GPU 上下文类，管理 GPU 资源和渲染操作 |
| `GrRecordingContext.h` | 录制上下文基类，支持 DDL 和多线程录制 |
| `GrContextThreadSafeProxy.h` | 线程安全的上下文代理 |
| `GrBackendSurface.h` | `GrBackendFormat`、`GrBackendTexture`、`GrBackendRenderTarget` |
| `GrBackendSemaphore.h` | 后端信号量封装 |
| `GrYUVABackendTextures.h` | YUV 平面纹理的信息和资源管理 |
| `GrExternalTextureGenerator.h` | 外部纹理生成器接口 |
| `GrDriverBugWorkarounds.h` | GPU 驱动问题规避标志 |
| `GrDriverBugWorkaroundsAutogen.h` | 自动生成的驱动问题列表 |
| `SkImageGanesh.h` | Ganesh GPU 上的 SkImage 创建工厂方法 |
| `SkSurfaceGanesh.h` | Ganesh GPU 上的 SkSurface 创建工厂方法 |
| `SkMeshGanesh.h` | Ganesh GPU 上的 SkMesh 支持 |

## 关键类与函数

### `GrDirectContext` 类 (GrDirectContext.h)

Ganesh 的核心类，管理 GPU 资源和渲染：

```cpp
class GrDirectContext : public GrRecordingContext {
    // 工厂方法（各后端在各自子目录中提供）
    static sk_sp<GrDirectContext> MakeMock(const GrMockOptions*);

    void resetContext(uint32_t state = kAll_GrBackendState);
    void abandonContext();
    void releaseResourcesAndAbandonContext();
    void freeGpuResources();

    // 纹理创建
    GrBackendTexture createBackendTexture(...);
    void deleteBackendTexture(const GrBackendTexture&);

    // 刷新和提交
    GrSemaphoresSubmitted flush(const GrFlushInfo&);
    bool submit(GrSyncCpu = GrSyncCpu::kNo);

    // 资源缓存管理
    void setResourceCacheLimit(size_t maxResourceBytes);
    void getResourceCacheUsage(int* resourceCount, size_t* resourceBytes) const;
    void purgeUnlockedResources(GrPurgeResourceOptions);
};
```

### `GrRecordingContext` 类 (GrRecordingContext.h)

```cpp
class GrRecordingContext : public GrImageContext {
    bool abandoned();
    bool colorTypeSupportedAsSurface(SkColorType) const;
    int maxTextureSize() const;
    int maxRenderTargetSize() const;
    bool supportsProtectedContent() const;
    int maxSurfaceSampleCountForColorType(SkColorType) const;
};
```

### `GrBackendApi` 枚举 (GrTypes.h)

```cpp
enum class GrBackendApi : unsigned {
    kOpenGL,     // OpenGL / OpenGL ES / WebGL
    kVulkan,     // Vulkan
    kMetal,      // Apple Metal
    kDirect3D,   // Direct3D 12
    kMock,       // 测试用 Mock 后端
    kUnsupported,
};
```

### `GrFlushInfo` 结构体 (GrTypes.h)

```cpp
struct GrFlushInfo {
    size_t fNumSemaphores = 0;
    GrBackendSemaphore* fSignalSemaphores = nullptr;
    GrGpuFinishedProc fFinishedProc = nullptr;
    GrGpuSubmittedProc fSubmittedProc = nullptr;
    // ...
};
```

### `GrBackendTexture` / `GrBackendRenderTarget` 类 (GrBackendSurface.h)

后端无关的 GPU 纹理和渲染目标封装，通过内部多态子类型化支持各后端。

### `GrContextOptions::PersistentCache` (GrContextOptions.h)

```cpp
class PersistentCache {
    virtual sk_sp<SkData> load(const SkData& key) = 0;
    virtual void store(const SkData& key, const SkData& data, const SkString& description);
};
```

### SkImage / SkSurface 工厂方法

```cpp
// SkImageGanesh.h
namespace SkImages {
    sk_sp<SkImage> AdoptTextureFrom(GrRecordingContext*, const GrBackendTexture&, ...);
    sk_sp<SkImage> BorrowTextureFrom(GrRecordingContext*, const GrBackendTexture&, ...);
    sk_sp<SkImage> TextureFromYUVATextures(GrRecordingContext*, const GrYUVABackendTextures&, ...);
}

// SkSurfaceGanesh.h
namespace SkSurfaces {
    sk_sp<SkSurface> RenderTarget(GrRecordingContext*, skgpu::Budgeted, const SkImageInfo&, ...);
    sk_sp<SkSurface> WrapBackendTexture(GrRecordingContext*, const GrBackendTexture&, ...);
    sk_sp<SkSurface> WrapBackendRenderTarget(GrRecordingContext*, const GrBackendRenderTarget&, ...);
}
```

## 依赖关系

- **上游依赖**: `include/gpu/GpuTypes.h`, `include/gpu/ShaderErrorHandler.h`
- **上游依赖**: `include/core/SkImage.h`, `include/core/SkSurface.h`, `include/core/SkRefCnt.h`
- **私有依赖**: `include/private/gpu/ganesh/` (内部类型)
- **下游子目录**: `gl/`, `vk/`, `mtl/`, `d3d/`, `mock/` (各后端实现)
- **实现代码**: `src/gpu/ganesh/`

## 相关文档与参考

- `include/gpu/ganesh/gl/` - OpenGL 后端 API
- `include/gpu/ganesh/vk/` - Vulkan 后端 API
- `include/gpu/ganesh/mtl/` - Metal 后端 API
- `include/gpu/ganesh/d3d/` - Direct3D 12 后端 API
- `include/gpu/ganesh/mock/` - Mock 测试后端
- `include/gpu/graphite/` - Graphite 渲染引擎（Ganesh 的继任者）
- Skia GPU 文档: https://skia.org/docs/user/api/skcanvas_creation/
