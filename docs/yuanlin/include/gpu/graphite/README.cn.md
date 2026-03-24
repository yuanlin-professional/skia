# include/gpu/graphite - Graphite 渲染引擎公共 API

## 概述

`include/gpu/graphite` 是 Skia 中 Graphite GPU 渲染引擎的公共 API 目录。Graphite 是 Skia
团队开发的新一代 GPU 加速后端，旨在取代 Ganesh。Graphite 采用了更现代的架构设计，
以"录制-回放"（Record-Replay）模型为核心，更好地适配 Vulkan、Metal 和 Dawn/WebGPU 等
现代低级图形 API 的特性。

Graphite 的核心架构围绕 `Context`、`Recorder` 和 `Recording` 三个类展开。`Context` 是
全局资源管理器，拥有 GPU 设备连接，负责管线缓存和资源预算。`Recorder` 是绘制命令的录制器，
可以在独立线程上创建和使用。`Recording` 是录制完成的命令包，提交给 `Context` 执行。
这种设计允许多个 `Recorder` 并行工作，极大提升了多线程渲染的效率。

`ContextOptions` 提供了丰富的配置选项，包括 MSAA 采样数、字形缓存大小、路径图集大小、
管线缓存回调、有序录制要求等。`TextureInfo` 和 `BackendTexture` 提供了后端无关的纹理
抽象，通过内部多态子类型化支持各后端的特有属性。

Graphite 还引入了管线预编译（Precompile）机制，允许客户端提前创建渲染管线，避免绘制时的
即时编译开销。`PrecompileContext` 可以移动到后台线程进行预编译工作。

`ImageProvider` 提供了集中化的图像缓存机制，当 Graphite 遇到非 GPU 支持的 `SkImage` 时，
会调用 `ImageProvider::findOrCreate` 来获取 GPU 版本。

## 架构图

```
include/gpu/graphite/
    |
    +-- GraphiteTypes.h            <-- 基础类型（InsertStatus、回调类型等）
    +-- ContextOptions.h           <-- 上下文配置选项
    |
    +-- Context.h                  <-- 全局 GPU 上下文（资源管理、命令提交）
    |       |
    |       +-- makeRecorder()     --> Recorder
    |       +-- insertRecording()  <-- Recording
    |       +-- submit()
    |
    +-- Recorder.h                 <-- 绘制命令录制器（可多线程使用）
    |       |
    |       +-- snap()             --> Recording
    |
    +-- Recording.h                <-- 录制完成的命令包
    |
    +-- TextureInfo.h              <-- 后端无关的纹理信息
    +-- BackendTexture.h           <-- 后端无关的纹理封装
    +-- BackendSemaphore.h         <-- 后端无关的信号量
    +-- YUVABackendTextures.h      <-- YUV 平面纹理集合
    |
    +-- Surface.h                  <-- GPU SkSurface 工厂方法
    +-- Image.h                    <-- GPU SkImage 工厂方法
    +-- ImageProvider.h            <-- 图像缓存提供者接口
    |
    +-- PrecompileContext.h        <-- 预编译上下文（可后台线程使用）
    +-- PersistentPipelineStorage.h <-- 持久管线存储
    |
    +-- dawn/                      <-- Dawn/WebGPU 后端
    +-- vk/                        <-- Vulkan 后端
    +-- mtl/                       <-- Metal 后端
    +-- precompile/                <-- 管线预编译框架
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `Context.h` | `skgpu::graphite::Context` - 全局上下文，管理资源和命令提交 |
| `Recorder.h` | `skgpu::graphite::Recorder` - 命令录制器，支持多线程 |
| `Recording.h` | `skgpu::graphite::Recording` - 录制完成的命令包 |
| `GraphiteTypes.h` | 基础类型：`InsertStatus`、`GpuFinishedProc`、`DepthStencilFlags` 等 |
| `ContextOptions.h` | 上下文选项：MSAA、缓存大小、管线回调、有序录制等 |
| `TextureInfo.h` | `TextureInfo` - 后端无关的纹理属性描述 |
| `BackendTexture.h` | `BackendTexture` - 后端无关的纹理封装 |
| `BackendSemaphore.h` | `BackendSemaphore` - 后端无关的信号量 |
| `YUVABackendTextures.h` | YUV 平面纹理的管理 |
| `Surface.h` | `SkSurfaces::RenderTarget()`, `WrapBackendTexture()` |
| `Image.h` | `SkImages::WrapTexture()`, `PromiseTextureFrom()` 等 |
| `ImageProvider.h` | `ImageProvider` - 图像缓存与转换的抽象接口 |
| `PrecompileContext.h` | `PrecompileContext` - 线程安全的预编译上下文 |
| `PersistentPipelineStorage.h` | 跨 Context 生命周期的管线数据存储 |

## 关键类与函数

### `skgpu::graphite::Context` 类

```cpp
class Context final {
    BackendApi backend() const;
    std::unique_ptr<Recorder> makeRecorder(const RecorderOptions& = {});
    std::unique_ptr<PrecompileContext> makePrecompileContext();
    InsertStatus insertRecording(const InsertRecordingInfo&);
    bool submit(SyncToCpu = SyncToCpu::kNo);
    void asyncRescaleAndReadPixels(...);
    bool hasUnfinishedGpuWork() const;
    size_t currentBudgetedBytes() const;
};
```

### `skgpu::graphite::Recorder` 类

```cpp
class Recorder {
    BackendApi backend() const;
    std::unique_ptr<Recording> snap();
    BackendTexture createBackendTexture(SkISize, const TextureInfo&);
    void deleteBackendTexture(const BackendTexture&);
};
```

### `skgpu::graphite::Recording` 类

```cpp
class Recording final {
    // 主要由 Context 内部使用
    RecordingPriv priv();
};
```

### `InsertStatus` 状态类 (GraphiteTypes.h)

```cpp
class InsertStatus {
    enum V {
        kSuccess,
        kInvalidRecording,
        kPromiseImageInstantiationFailed,
        kAddCommandsFailed,
        kAsyncShaderCompilesFailed,
        kOutOfOrderRecording,
    };
};
```

### `TextureInfo` 类

后端无关的纹理属性描述，通过内部子类型化支持各后端特有属性：

```cpp
class TextureInfo {
    bool isValid() const;
    BackendApi backend() const;
    Protected isProtected() const;
    SampleCount sampleCount() const;
    Mipmapped mipmapped() const;
    bool canBeFulfilledBy(const TextureInfo&) const;
};
```

### Surface 和 Image 工厂方法

```cpp
// Surface.h
namespace SkSurfaces {
    sk_sp<SkSurface> RenderTarget(Recorder*, const SkImageInfo&, Mipmapped, ...);
    sk_sp<SkSurface> WrapBackendTexture(Recorder*, const BackendTexture&, ...);
    sk_sp<SkImage> AsImage(sk_sp<const SkSurface>);
    sk_sp<SkImage> AsImageCopy(sk_sp<const SkSurface>, ...);
}

// Image.h
namespace SkImages {
    sk_sp<SkImage> WrapTexture(Recorder*, const BackendTexture&, ...);
    sk_sp<SkImage> PromiseTextureFrom(Recorder*, ...);
    sk_sp<SkImage> TextureFromYUVATextures(Recorder*, ...);
}
```

### `ImageProvider` 抽象类

```cpp
class ImageProvider : public SkRefCnt {
    virtual sk_sp<SkImage> findOrCreate(Recorder*, const SkImage*, SkImage::RequiredProperties) = 0;
};
```

### `ContextOptions` 关键字段

```cpp
struct ContextOptions {
    skgpu::ShaderErrorHandler* fShaderErrorHandler;
    SampleCount fInternalMultisampleCount = SampleCount::k4;
    size_t fGlyphCacheTextureMaximumBytes;
    bool fRequireOrderedRecordings = false;
    size_t fGpuBudgetInBytes = 256MB;
    PipelineCachingCallback fPipelineCachingCallback;
    SkExecutor* fExecutor;  // 多线程管线编译
    PersistentPipelineStorage* fPersistentPipelineStorage;
};
```

## 依赖关系

- **上游依赖**: `include/gpu/GpuTypes.h`, `include/gpu/ShaderErrorHandler.h`
- **上游依赖**: `include/core/SkImage.h`, `include/core/SkSurface.h`, `include/core/SkRefCnt.h`
- **下游子目录**: `dawn/`, `vk/`, `mtl/`, `precompile/` (各后端和预编译)
- **实现代码**: `src/gpu/graphite/`

## 相关文档与参考

- `include/gpu/graphite/dawn/` - Dawn/WebGPU 后端
- `include/gpu/graphite/vk/` - Vulkan 后端
- `include/gpu/graphite/mtl/` - Metal 后端
- `include/gpu/graphite/precompile/` - 管线预编译框架
- `include/gpu/ganesh/` - Ganesh 渲染引擎（Graphite 的前身）
- Skia Graphite 设计文档: https://skia.org/docs/dev/design/graphite/
