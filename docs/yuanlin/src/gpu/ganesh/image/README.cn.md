# image - Ganesh GPU 图像处理模块

## 概述

`src/gpu/ganesh/image/` 目录是 Skia Ganesh GPU 渲染后端中负责图像管理的核心模块。该模块实现了 `SkImage` 基类在 GPU 上下文下的各种具体子类，涵盖了从纹理支持的图像、YUVA 多平面图像、延迟加载纹理到可固定（pinnable）的光栅图像等多种 GPU 图像类型。每种类型都针对特定的使用场景进行了优化。

在 Skia 的图像架构中，`SkImage` 是不可变的图像抽象，而 GPU 图像的具体实现需要管理纹理代理（Texture Proxy）、表面代理视图（SurfaceProxyView）以及与 GPU 上下文的生命周期关系。本模块中的类层次结构以 `SkImage_GaneshBase` 为中间基类，统一了 GPU 图像的通用行为，如纹理验证、像素读取、mipmap 管理和颜色空间转换。

该模块还包含关键的工具函数层（`GrImageUtils` 和 `SkSpecialImage_Ganesh`），为上层绘制操作提供图像到纹理代理视图的转换、片段处理器（Fragment Processor）的创建以及图像滤镜后端的支持。这些工具函数是 Ganesh 渲染管线中图像采样和合成操作的基础设施。

`GrMippedBitmap` 类则提供了带 mipmap 支持的不可变位图封装，专门用于 Ganesh 的纹理上传管线，确保位图数据在上传到 GPU 时能携带预计算的 mipmap 层级。

模块的线程安全设计也值得注意。`SkImage_Ganesh` 使用内部的 `ProxyChooser` 类，通过自旋锁（`SkSpinlock`）实现了在 volatile 代理和 stable 代理之间的线程安全切换，这对于支持 SkSurface 快照的写时复制（Copy-on-Write）语义至关重要。

## 架构图

```
+-------------------------------------------------------------------+
|                        SkImage (公共 API)                          |
+-------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                     SkImage_Base (内部基类)                        |
+-------------------------------------------------------------------+
          |                                    |
          v                                    v
+------------------------+           +---------------------+
| SkImage_GaneshBase     |           | SkImage_Lazy        |
| (GPU图像通用基类)      |           | (延迟图像基类)      |
|  - getROPixels()       |           +---------------------+
|  - ValidateBackend()   |                     |
|  - MakePromiseImage()  |                     v
+------------------------+           +---------------------+
    |          |         |           | SkImage_LazyTexture |
    |          |         |           | (延迟纹理图像)      |
    v          v         |           +---------------------+
+--------+ +--------+   |
| SkImage| | SkImage|   |    +------------------------+
| _Ganesh| | _Ganesh|   |    | SkImage_Raster         |
|        | | YUVA   |   |    +------------------------+
+--------+ +--------+   |               |
                         |               v
                         |    +------------------------+
                         |    | SkImage_RasterPinnable |
                         |    | (可固定光栅图像)       |
                         |    +------------------------+
                         |
                         v
             +-------------------------+
             | SkSpecialImage_Ganesh   |
             | (滤镜专用图像)          |
             +-------------------------+

+-------------------------------------------------------------------+
|                       工具层                                       |
+-------------------------------------------------------------------+
| GrImageUtils (skgpu::ganesh 命名空间)                              |
|  - AsView()              将 SkImage 转为 GrSurfaceProxyView       |
|  - AsFragmentProcessor() 将 SkImage 转为 GrFragmentProcessor      |
|  - LockTextureProxyView()锁定延迟图像的纹理代理                   |
|  - CopyView()            创建纹理视图副本                          |
|  - FindOrMakeCachedMipmappedView() 获取或创建 mipmap 缓存         |
|                                                                     |
| GrMippedBitmap                                                      |
|  - 带 mipmap 的不可变位图封装                                      |
+-------------------------------------------------------------------+
```

## 文件分类索引

### 1. 图像工具 — Image Utilities

| 文件 | 说明 |
|------|------|
| GrImageUtils.h / GrImageUtils.cpp | GPU 图像工具函数集 |
| GrTextureGenerator.cpp | 纹理生成器的 GPU 实现 |

### 2. Mipmap — Mipped Bitmap

| 文件 | 说明 |
|------|------|
| GrMippedBitmap.h / GrMippedBitmap.cpp | 带 mipmap 的位图封装 |

### 3. SkImage 实现 — GPU Image Types

| 文件 | 说明 |
|------|------|
| SkImage_GaneshBase.h / SkImage_GaneshBase.cpp | GPU 图像通用基类 |
| SkImage_Ganesh.h / SkImage_Ganesh.cpp | 纹理支持的 GPU 图像 |
| SkImage_GaneshFactories.cpp | GPU 图像工厂函数 |
| SkImage_GaneshFactories_Android.cpp | Android 平台专用工厂 |

### 4. YUVA 图像 — Multi-plane YUV Image

| 文件 | 说明 |
|------|------|
| SkImage_GaneshYUVA.h / SkImage_GaneshYUVA.cpp | YUVA 多平面 GPU 图像 |

### 5. 延迟加载 — Lazy Texture

| 文件 | 说明 |
|------|------|
| SkImage_LazyTexture.h / SkImage_LazyTexture.cpp | 延迟加载的纹理图像 |

### 6. 栅格图像 — Raster Pinnable

| 文件 | 说明 |
|------|------|
| SkImage_RasterPinnable.h / SkImage_RasterPinnable.cpp | 可固定到 GPU 的光栅图像 |

### 7. 特殊图像 — Special Image (Filter)

| 文件 | 说明 |
|------|------|
| SkSpecialImage_Ganesh.h / SkSpecialImage_Ganesh.cpp | 图像滤镜专用 GPU 图像 |

## 关键类与函数

### SkImage_GaneshBase - GPU 图像基类

所有 Ganesh GPU 图像的共同基类，提供 GPU 图像的通用功能：

```cpp
class SkImage_GaneshBase : public SkImage_Base {
public:
    bool isValid(SkRecorder*) const final;
    GrImageContext* context() const final;
    bool getROPixels(GrDirectContext*, SkBitmap*, CachingHint) const final;

    // 纹理验证
    static bool ValidateBackendTexture(const GrCaps*, const GrBackendTexture&,
                                       GrColorType, SkColorType, SkAlphaType,
                                       sk_sp<SkColorSpace>);

    // Promise Image 的懒代理创建
    static sk_sp<GrTextureProxy> MakePromiseImageLazyProxy(...);

    // 子类必须实现的纯虚函数
    virtual std::tuple<GrSurfaceProxyView, GrColorType> asView(...) const = 0;
    virtual std::unique_ptr<GrFragmentProcessor> asFragmentProcessor(...) const = 0;
    virtual GrSurfaceOrigin origin() const = 0;
};
```

### SkImage_Ganesh - 标准纹理图像

最常见的 GPU 图像类型，由单个纹理代理支持。核心特性包括：

```cpp
class SkImage_Ganesh final : public SkImage_GaneshBase {
public:
    // 从 volatile 源创建（用于 SkSurface 快照）
    static sk_sp<SkImage> MakeWithVolatileSrc(sk_sp<GrRecordingContext>,
                                               GrSurfaceProxyView volatileSrc,
                                               SkColorInfo);

    // 检查是否需要写时复制
    bool surfaceMustCopyOnWrite(GrSurfaceProxy* surfaceProxy) const;

    // 异步像素读取
    void onAsyncRescaleAndReadPixels(...) const override;
    void onAsyncRescaleAndReadPixelsYUV420(...) const override;

private:
    // 线程安全的代理选择器
    class ProxyChooser {
        sk_sp<GrSurfaceProxy> chooseProxy(GrRecordingContext*, GrRenderTargetProxy*);
        sk_sp<GrSurfaceProxy> switchToStableProxy();
        sk_sp<GrSurfaceProxy> makeVolatileProxyStable();
    };
};
```

`ProxyChooser` 内部类是 `SkImage_Ganesh` 的核心设计。它维护了一个 volatile 代理（可能被 SkSurface 覆写）和一个 stable 副本。当检测到 volatile 代理被修改时，自动切换到 stable 副本，实现写时复制语义。

### SkImage_GaneshYUVA - YUVA 多平面图像

封装 1-4 个 YUVA 平面纹理，支持 YUV 色彩空间的 GPU 图像：

```cpp
class SkImage_GaneshYUVA final : public SkImage_GaneshBase {
public:
    static constexpr auto kAssumedColorType = kRGBA_8888_SkColorType;

    // 初始渲染通过将单独平面传递给着色器完成
    // 一旦需要扁平化图像（如 readPixels），则生成 RGB 代理并缓存
    std::unique_ptr<GrFragmentProcessor> asFragmentProcessor(...) const override;
    bool setupMipmapsForPlanes(GrRecordingContext*) const;

private:
    mutable GrYUVATextureProxies fYUVAProxies;
    const sk_sp<SkColorSpace> fFromColorSpace;
};
```

### SkImage_LazyTexture - 延迟纹理图像

推迟纹理创建到实际绘制时，适用于 Android `AHardwareBuffer` 等平台对象：

```cpp
class SkImage_LazyTexture final : public SkImage_Lazy {
public:
    // 纹理生成器（GrTextureGenerator）在需要时导入纹理
    explicit SkImage_LazyTexture(SkImage_Lazy::Validator* validator);
    bool readPixelsProxy(GrDirectContext*, const SkPixmap&) const override;
};
```

### SkImage_RasterPinnable - 可固定光栅图像

允许光栅图像被"固定"到 GPU 纹理，避免重复上传：

```cpp
class SkImage_RasterPinnable final : public SkImage_Raster {
public:
    std::tuple<GrSurfaceProxyView, GrColorType> asView(GrRecordingContext*,
                                                        skgpu::Mipmapped,
                                                        GrImageTexGenPolicy) const;
    std::unique_ptr<PinnedData> fPinnedData;
};

struct PinnedData {
    GrSurfaceProxyView fPinnedView;
    int32_t fPinnedCount;
    uint32_t fPinnedUniqueID;
    uint32_t fPinnedContextID;
    GrColorType fPinnedColorType;
};
```

### GrImageUtils - 图像工具函数

`skgpu::ganesh` 命名空间下的核心工具函数集：

```cpp
namespace skgpu::ganesh {
    // 将任意 SkImage 转换为 GPU 纹理视图
    std::tuple<GrSurfaceProxyView, GrColorType> AsView(
        GrRecordingContext*, const SkImage*, skgpu::Mipmapped,
        GrRenderTargetProxy* targetSurface,
        GrImageTexGenPolicy = GrImageTexGenPolicy::kDraw);

    // 将图像转换为片段处理器（用于着色器采样）
    std::unique_ptr<GrFragmentProcessor> AsFragmentProcessor(
        SurfaceDrawContext*, const SkImage*, SkSamplingOptions,
        const SkTileMode[2], const SkMatrix&, const SkRect*, const SkRect*);

    // 获取或创建带 mipmap 的缓存视图
    GrSurfaceProxyView FindOrMakeCachedMipmappedView(
        GrRecordingContext*, GrSurfaceProxyView, uint32_t imageUniqueID);

    // 查询支持的 YUVA 纹理格式
    SkYUVAPixmapInfo::SupportedDataTypes SupportedTextureFormats(const GrImageContext&);
}
```

### GrMippedBitmap - Mipmap 位图封装

```cpp
class GrMippedBitmap {
public:
    explicit GrMippedBitmap(SkBitmap b);
    explicit GrMippedBitmap(SkBitmap b, sk_sp<const SkMipmap> mipmaps);

    SkBitmap bitmap() const;
    sk_sp<const SkMipmap> mips() const;

    static std::optional<GrMippedBitmap> Make(
        SkImageInfo, const void* pixels, size_t rowBytes, ReleaseProc, void* context);
};
```

## 依赖关系

### 向上依赖（本模块依赖的组件）

- `include/core/SkImage.h` / `src/image/SkImage_Base.h` - 图像基类定义
- `src/gpu/ganesh/GrSurfaceProxyView.h` - 纹理代理视图
- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
- `src/gpu/ganesh/GrRecordingContext.h` - GPU 录制上下文
- `src/gpu/ganesh/GrYUVATextureProxies.h` - YUVA 纹理代理集
- `src/gpu/ganesh/GrColorInfo.h` - 颜色信息
- `src/gpu/ganesh/GrColorSpaceXform.h` - 颜色空间变换
- `src/gpu/ganesh/SkGr.h` - Skia/Ganesh 桥接工具

### 向下依赖（依赖本模块的组件）

- `src/gpu/ganesh/surface/` - Surface 快照时创建 `SkImage_Ganesh`
- `src/gpu/ganesh/SurfaceDrawContext.h` - 图像绘制操作
- `src/gpu/ganesh/ops/` - 使用 `AsView()` / `AsFragmentProcessor()` 的绘制操作
- `src/gpu/ganesh/effects/GrTextureEffect.h` - 纹理采样效果

### 平台特定依赖

- `SkImage_GaneshFactories_Android.cpp` 依赖 Android NDK 的 `AHardwareBuffer` API
- `GrTextureGenerator.cpp` 依赖平台特定的纹理导入机制

## 设计模式分析

### 继承层次与模板方法模式

图像类层次使用了清晰的模板方法模式。`SkImage_GaneshBase` 定义了 `asView()` 和 `asFragmentProcessor()` 等纯虚接口，各子类按自身纹理管理方式实现：

- `SkImage_Ganesh`：直接返回内部代理视图
- `SkImage_GaneshYUVA`：按需扁平化 YUVA 平面
- `SkImage_LazyTexture`：按需触发纹理生成

### 写时复制 (Copy-on-Write)

`SkImage_Ganesh::ProxyChooser` 实现了精巧的 COW 机制。当 SkSurface 创建快照时，图像最初共享 surface 的 volatile 代理。只有当 surface 被修改时，才切换到 stable 副本。如果 surface 在图像生命周期内从未修改，则复制被完全避免（`makeVolatileProxyStable()`）。

### 工厂方法模式

`SkImage_GaneshFactories.cpp` 和 `SkImage_GaneshFactories_Android.cpp` 集中了所有 GPU 图像的创建逻辑，提供了多种工厂方法以适配不同的输入源（后端纹理、像素数据、硬件缓冲区等）。

### 代理模式

整个 GPU 图像系统大量使用代理模式。`GrSurfaceProxy` 延迟了实际 GPU 资源的分配，`SkImage_LazyTexture` 则进一步将纹理生成推迟到绘制时。这种多级延迟策略最大化了资源利用效率。

## 数据流

```
创建阶段:
  SkImage::MakeFromTexture()
  SkImage::MakeFromEncoded()           SkSurface::makeImageSnapshot()
  SkImage::MakeFromAHardwareBuffer()              |
            |                                      v
            v                           +---------------------+
  +-------------------+                 | SkImage_Ganesh      |
  | SkImage_Lazy      |                 |  (ProxyChooser:     |
  | Texture           |                 |   volatile+stable)  |
  +-------------------+                 +---------------------+

绘制阶段:
  Canvas.drawImage(image, ...)
            |
            v
  +-------------------+     +-------------------------+
  | SurfaceDrawContext|---->| skgpu::ganesh::AsView() |
  | drawImageQuad()   |     +-------------------------+
  +-------------------+              |
            |                        v
            |             +---------------------------+
            |             | GrSurfaceProxyView        |
            |             | (纹理代理 + origin +      |
            |             |  swizzle)                  |
            |             +---------------------------+
            |                        |
            v                        v
  +-------------------+     +-------------------------+
  | AsFragment        |---->| GrTextureEffect /       |
  | Processor()       |     | YUV FP Chain            |
  +-------------------+     +-------------------------+
                                     |
                                     v
                            +-------------------------+
                            | GPU 管线执行            |
                            | (顶点着色 -> 片段着色)  |
                            +-------------------------+

像素读取:
  SkImage::readPixels()
            |
            v
  +-------------------+
  | getROPixels()     |  --> GPU 回读到 SkBitmap
  | onReadPixels()    |
  | asyncRescale...() |  --> 异步缩放+读取
  +-------------------+
```

## 相关文档与参考

- `src/image/SkImage_Base.h` - SkImage 内部基类定义
- `src/image/SkImage_Lazy.h` - 延迟图像基类
- `src/image/SkImage_Raster.h` - 光栅图像基类
- `src/gpu/ganesh/GrSurfaceProxyView.h` - 纹理代理视图
- `src/gpu/ganesh/GrYUVATextureProxies.h` - YUVA 纹理代理集
- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
- `include/gpu/ganesh/GrDirectContext.h` - GPU 直接上下文
- `src/gpu/ganesh/surface/` - Surface 模块（创建 GPU 图像的主要来源）
- `src/gpu/ganesh/effects/GrTextureEffect.h` - 纹理采样效果处理器
- `include/android/GrAHardwareBufferUtils.h` - Android 硬件缓冲区工具
- Skia GPU 架构概览：https://skia.org/docs/dev/design/
