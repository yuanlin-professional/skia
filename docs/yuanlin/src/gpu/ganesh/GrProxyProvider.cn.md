# GrProxyProvider

> 源文件
> - src/gpu/ganesh/GrProxyProvider.h
> - src/gpu/ganesh/GrProxyProvider.cpp

## 概述

`GrProxyProvider` 是 Ganesh GPU 后端中创建和管理 `GrSurfaceProxy` 派生对象的工厂类。它是延迟实例化系统的核心组件,负责代理的创建、唯一键管理、以及从各种数据源(位图、后端纹理、压缩数据等)创建代理。

主要职责包括:
- 创建各种类型的表面代理(纹理、渲染目标、纹理渲染目标)
- 管理唯一键(UniqueKey)和代理的映射关系
- 包装外部 GPU 资源(后端纹理、渲染目标)
- 从位图和压缩数据创建纹理代理
- 支持懒实例化(lazy instantiation)和 Promise 纹理
- 管理 DDL(延迟显示列表)场景下的代理生命周期

在 DDL 模式下,代理在记录线程创建,在渲染线程实例化。在直接渲染模式下,代理通常立即实例化。

## 架构位置

`GrProxyProvider` 在 Ganesh 上下文架构中的位置:

```
GrImageContext
    └── GrProxyProvider (代理工厂)
        ├── 创建 GrTextureProxy
        ├── 创建 GrRenderTargetProxy
        └── 创建 GrTextureRenderTargetProxy
            ↓
        延迟实例化
            ↓
        GrResourceProvider (实际创建 GPU 资源)
            ↓
        GrTexture / GrRenderTarget (GPU 资源)
```

它是高层 API 和底层资源管理的中间层。

## 主要类与结构体

### GrProxyProvider 类

**继承关系**:
- 无继承关系,独立的工厂类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fUniquelyKeyedProxies | UniquelyKeyedProxyHash | 唯一键代理哈希表 |
| fImageContext | GrImageContext* | 所属的图像上下文 |

### UniquelyKeyedProxyHashTraits 结构体

哈希表特性定义:

```cpp
struct UniquelyKeyedProxyHashTraits {
    static const skgpu::UniqueKey& GetKey(const GrTextureProxy& p);
    static uint32_t Hash(const skgpu::UniqueKey& key);
};
```

### TextureInfo 结构体

懒实例化纹理信息:

```cpp
struct TextureInfo {
    skgpu::Mipmapped fMipmapped;
    GrTextureType fTextureType;
};
```

## 公共 API 函数

### 构造和析构

```cpp
explicit GrProxyProvider(GrImageContext*);
~GrProxyProvider();
```

### 唯一键管理

```cpp
bool assignUniqueKeyToProxy(const skgpu::UniqueKey&, GrTextureProxy*);
void adoptUniqueKeyFromSurface(GrTextureProxy* proxy, const GrSurface*);
void removeUniqueKeyFromProxy(GrTextureProxy*);
sk_sp<GrTextureProxy> findProxyByUniqueKey(const skgpu::UniqueKey&);
sk_sp<GrTextureProxy> findOrCreateProxyByUniqueKey(const skgpu::UniqueKey&,
                                                   UseAllocator = UseAllocator::kYes);
GrSurfaceProxyView findCachedProxyWithColorTypeFallback(const skgpu::UniqueKey&,
                                                        GrSurfaceOrigin,
                                                        GrColorType,
                                                        int sampleCnt);
```

管理代理的唯一标识,支持缓存查找和复用。

### 从位图创建

```cpp
sk_sp<GrTextureProxy> createProxyFromBitmap(const GrMippedBitmap&,
                                           skgpu::Mipmapped,
                                           SkBackingFit,
                                           skgpu::Budgeted);
```

从位图数据创建纹理代理,可选生成 mipmap。

### 创建空代理

```cpp
sk_sp<GrTextureProxy> createProxy(const GrBackendFormat&,
                                  SkISize dimensions,
                                  GrRenderable,
                                  int renderTargetSampleCnt,
                                  skgpu::Mipmapped,
                                  SkBackingFit,
                                  skgpu::Budgeted,
                                  GrProtected,
                                  std::string_view label,
                                  GrInternalSurfaceFlags = GrInternalSurfaceFlags::kNone,
                                  UseAllocator useAllocator = UseAllocator::kYes);
```

创建未初始化的纹理代理。

### 创建压缩纹理

```cpp
sk_sp<GrTextureProxy> createCompressedTextureProxy(SkISize dimensions,
                                                   skgpu::Budgeted,
                                                   skgpu::Mipmapped,
                                                   GrProtected,
                                                   SkTextureCompressionType,
                                                   sk_sp<SkData> data);
```

从压缩数据创建纹理代理。

### 包装后端纹理

```cpp
sk_sp<GrTextureProxy> wrapBackendTexture(const GrBackendTexture&,
                                         GrWrapOwnership,
                                         GrWrapCacheable,
                                         GrIOType,
                                         sk_sp<skgpu::RefCntedCallback> = nullptr);

sk_sp<GrTextureProxy> wrapCompressedBackendTexture(const GrBackendTexture&,
                                                   GrWrapOwnership,
                                                   GrWrapCacheable,
                                                   sk_sp<skgpu::RefCntedCallback>);

sk_sp<GrTextureProxy> wrapRenderableBackendTexture(const GrBackendTexture&,
                                                   int sampleCnt,
                                                   GrWrapOwnership,
                                                   GrWrapCacheable,
                                                   sk_sp<skgpu::RefCntedCallback> releaseHelper);
```

包装外部创建的后端纹理。

### 包装后端渲染目标

```cpp
sk_sp<GrSurfaceProxy> wrapBackendRenderTarget(const GrBackendRenderTarget&,
                                              sk_sp<skgpu::RefCntedCallback> releaseHelper);
```

### 懒实例化

```cpp
sk_sp<GrTextureProxy> createLazyProxy(LazyInstantiateCallback&&,
                                      const GrBackendFormat&,
                                      SkISize dimensions,
                                      skgpu::Mipmapped,
                                      GrMipmapStatus,
                                      GrInternalSurfaceFlags,
                                      SkBackingFit,
                                      skgpu::Budgeted,
                                      GrProtected,
                                      UseAllocator,
                                      std::string_view label);

sk_sp<GrRenderTargetProxy> createLazyRenderTargetProxy(LazyInstantiateCallback&&,
                                                       const GrBackendFormat&,
                                                       SkISize dimensions,
                                                       int renderTargetSampleCnt,
                                                       GrInternalSurfaceFlags,
                                                       const TextureInfo*,
                                                       GrMipmapStatus,
                                                       SkBackingFit,
                                                       skgpu::Budgeted,
                                                       GrProtected,
                                                       bool wrapsVkSecondaryCB,
                                                       UseAllocator useAllocator);
```

创建懒代理,在 flush 时通过回调实例化。

### Promise 纹理

```cpp
static sk_sp<GrTextureProxy> CreatePromiseProxy(GrContextThreadSafeProxy*,
                                                LazyInstantiateCallback&&,
                                                const GrBackendFormat&,
                                                SkISize dimensions,
                                                skgpu::Mipmapped);
```

创建 Promise 纹理代理,用于跨线程纹理共享。

### 完全懒代理

```cpp
static sk_sp<GrTextureProxy> MakeFullyLazyProxy(LazyInstantiateCallback&&,
                                                const GrBackendFormat&,
                                                GrRenderable,
                                                int renderTargetSampleCnt,
                                                GrProtected,
                                                const GrCaps&,
                                                UseAllocator);
```

创建尺寸未知的完全懒代理(用于动态大小的图集等)。

### 无效键处理

```cpp
void processInvalidUniqueKey(const skgpu::UniqueKey&, GrTextureProxy*,
                            InvalidateGPUResource);
```

处理无效的唯一键,清理代理和 GPU 资源。

### 上下文信息

```cpp
GrDDLProvider isDDLProvider() const;
uint32_t contextID() const;
const GrCaps* caps() const;
sk_sp<const GrCaps> refCaps() const;
GrResourceProvider* resourceProvider() const;
bool renderingDirectly() const;
bool isAbandoned() const;
```

### DDL 生命周期管理

```cpp
void orphanAllUniqueKeys();  // 孤立所有唯一键(DDL 结束时)
void removeAllUniqueKeys();  // 移除所有唯一键(上下文释放时)
```

## 内部实现细节

### 唯一键分配

```cpp
bool GrProxyProvider::assignUniqueKeyToProxy(const skgpu::UniqueKey& key,
                                             GrTextureProxy* proxy) {
    SkASSERT(key.isValid());
    if (this->isAbandoned() || !proxy) {
        return false;
    }

    // 检查资源缓存中是否已存在
    #ifdef SK_DEBUG
    if (auto direct = fImageContext->asDirectContext()) {
        GrResourceCache* resourceCache = direct->priv().getResourceCache();
        SkASSERT(!resourceCache->findAndRefUniqueResource(key));
    }
    #endif

    SkASSERT(!fUniquelyKeyedProxies.find(key));  // 防止重复
    proxy->cacheAccess().setUniqueKey(this, key);
    fUniquelyKeyedProxies.add(proxy);
    return true;
}
```

### 从位图创建代理

```cpp
sk_sp<GrTextureProxy> GrProxyProvider::createProxyFromBitmap(
        const GrMippedBitmap& bm,
        skgpu::Mipmapped mipmapped,
        SkBackingFit fit,
        skgpu::Budgeted budgeted) {

    SkBitmap bitmap = bm.bitmap();

    // DDL 模式下,如果位图可变,必须拷贝
    SkBitmap copyBitmap = bitmap;
    sk_sp<const SkMipmap> mips = bm.mips();
    if (!this->renderingDirectly() && !bitmap.isImmutable()) {
        copyBitmap.allocPixels();
        if (!bitmap.readPixels(copyBitmap.pixmap())) {
            return nullptr;
        }
        // 拷贝 mipmap
        if (mipmapped == skgpu::Mipmapped::kYes && bm.mips()) {
            mips.reset(SkMipmap::Build(copyBitmap.pixmap(), nullptr, false));
            // ... 拷贝 mipmap 层级
        }
        copyBitmap.setImmutable();
    }

    // 创建懒代理
    sk_sp<GrTextureProxy> proxy;
    if (mipmapped == skgpu::Mipmapped::kNo || !SkMipmap::ComputeLevelCount(...)) {
        proxy = this->createNonMippedProxyFromBitmap(...);
    } else {
        proxy = this->createMippedProxyFromBitmap(...);
    }

    // 直接模式下立即实例化
    if (auto direct = fImageContext->asDirectContext()) {
        GrResourceProvider* resourceProvider = direct->priv().resourceProvider();
        if (!proxy->priv().doLazyInstantiation(resourceProvider)) {
            return nullptr;
        }
    }
    return proxy;
}
```

### 包装后端纹理

```cpp
sk_sp<GrTextureProxy> GrProxyProvider::wrapBackendTexture(
        const GrBackendTexture& backendTex,
        GrWrapOwnership ownership,
        GrWrapCacheable cacheable,
        GrIOType ioType,
        sk_sp<skgpu::RefCntedCallback> releaseHelper) {

    SkASSERT(ioType != kWrite_GrIOType);

    // 仅直接上下文支持
    auto direct = fImageContext->asDirectContext();
    if (!direct) {
        return nullptr;
    }

    GrResourceProvider* resourceProvider = direct->priv().resourceProvider();
    sk_sp<GrTexture> tex = resourceProvider->wrapBackendTexture(
        backendTex, ownership, cacheable, ioType);
    if (!tex) {
        return nullptr;
    }

    if (releaseHelper) {
        tex->setRelease(std::move(releaseHelper));
    }

    // 创建包装代理
    return sk_sp<GrTextureProxy>(new GrTextureProxy(
        std::move(tex), UseAllocator::kNo, this->isDDLProvider()));
}
```

### 懒代理创建

```cpp
sk_sp<GrTextureProxy> GrProxyProvider::createLazyProxy(
        LazyInstantiateCallback&& callback,
        const GrBackendFormat& format,
        SkISize dimensions,
        skgpu::Mipmapped mipmapped,
        GrMipmapStatus mipmapStatus,
        GrInternalSurfaceFlags surfaceFlags,
        SkBackingFit fit,
        skgpu::Budgeted budgeted,
        GrProtected isProtected,
        UseAllocator useAllocator,
        std::string_view label) {

    SkASSERT((dimensions.fWidth <= 0 && dimensions.fHeight <= 0) ||
             (dimensions.fWidth > 0 && dimensions.fHeight > 0));

    // 验证格式和尺寸
    if (!format.isValid() || format.backend() != fImageContext->backend()) {
        return nullptr;
    }
    if (dimensions.fWidth > this->caps()->maxTextureSize() ||
        dimensions.fHeight > this->caps()->maxTextureSize()) {
        return nullptr;
    }

    return sk_sp<GrTextureProxy>(new GrTextureProxy(
        std::move(callback), format, dimensions, mipmapped,
        mipmapStatus, fit, budgeted, isProtected, surfaceFlags,
        useAllocator, this->isDDLProvider(), label));
}
```

### 无效键处理

```cpp
void GrProxyProvider::processInvalidUniqueKeyImpl(
        const skgpu::UniqueKey& key,
        GrTextureProxy* proxy,
        InvalidateGPUResource invalidateGPUResource,
        RemoveTableEntry removeTableEntry) {

    if (!proxy) {
        proxy = fUniquelyKeyedProxies.find(key);
    }

    // 查找对应的 GPU 资源
    sk_sp<GrGpuResource> invalidGpuResource;
    if (InvalidateGPUResource::kYes == invalidateGPUResource) {
        if (auto direct = fImageContext->asDirectContext()) {
            GrResourceProvider* resourceProvider = direct->priv().resourceProvider();
            invalidGpuResource = resourceProvider->findByUniqueKey<GrGpuResource>(key);
        }
    }

    // 清理代理键
    if (proxy) {
        if (removeTableEntry == RemoveTableEntry::kYes) {
            fUniquelyKeyedProxies.remove(key);
        }
        proxy->cacheAccess().clearUniqueKey();
    }

    // 清理 GPU 资源键
    if (invalidGpuResource) {
        invalidGpuResource->resourcePriv().removeUniqueKey();
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| GrImageContext | 所属上下文 |
| GrResourceProvider | 创建实际 GPU 资源 |
| GrCaps | GPU 能力查询 |
| GrSurfaceProxy 家族 | 创建的代理类型 |
| GrResourceCache | 查找已缓存的资源 |
| skgpu::UniqueKey | 唯一键类型 |
| SkBitmap/SkMipmap | 位图和 mipmap 数据 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| GrRecordingContextPriv | 通过 priv 访问 ProxyProvider |
| GrDrawingManager | 使用代理创建绘制任务 |
| SkImage_Gpu | 创建 GPU 图像的代理 |
| SkSurface_Gpu | 创建 GPU 表面的代理 |
| GrTextureGenerator | 生成纹理代理 |

## 设计模式与设计决策

### 工厂模式

`GrProxyProvider` 是代理对象的工厂,封装复杂的创建逻辑。

### 单例模式(每个上下文)

每个 `GrImageContext` 拥有一个 `GrProxyProvider` 实例。

### 懒初始化

代理创建时不立即分配 GPU 资源,支持:
- 优化资源使用
- DDL 模式
- 资源合并和重用

### 唯一键缓存

使用哈希表管理唯一键代理,支持快速查找和去重。

### 回调模式

懒代理使用回调延迟实例化,解耦创建和实例化逻辑。

### 构建器模式

Promise 纹理使用复杂的回调构建实例化逻辑。

## 性能考量

### 代理复用

通过唯一键查找已存在的代理,避免重复创建。

### 延迟实例化

仅在需要时分配 GPU 资源,减少内存占用和创建开销。

### 位图拷贝优化

直接模式下避免位图拷贝,DDL 模式下仅在必要时拷贝。

### 哈希表性能

`SkTDynamicHash` 提供 O(1) 查找性能。

### 内存池化

懒代理的回调可以捕获大对象,但回调本身使用 `std::function`,有一定开销。

### 批量实例化

DDL 模式下代理批量实例化,减少上下文切换。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrSurfaceProxy.h/cpp | 产品 | 表面代理基类 |
| src/gpu/ganesh/GrTextureProxy.h/cpp | 产品 | 纹理代理 |
| src/gpu/ganesh/GrRenderTargetProxy.h/cpp | 产品 | 渲染目标代理 |
| src/gpu/ganesh/GrTextureRenderTargetProxy.h | 产品 | 纹理+渲染目标代理 |
| src/gpu/ganesh/GrResourceProvider.h/cpp | 依赖 | 资源创建 |
| src/gpu/ganesh/GrResourceCache.h/cpp | 依赖 | 资源缓存 |
| include/private/gpu/ganesh/GrImageContext.h | 所有者 | 图像上下文 |
| src/gpu/ganesh/GrCaps.h | 依赖 | GPU 能力 |
| src/gpu/ResourceKey.h | 依赖 | 唯一键定义 |
| src/gpu/ganesh/image/GrMippedBitmap.h | 依赖 | 位图包装 |
