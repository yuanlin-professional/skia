# src/image - 图像实现模块

## 概述

`src/image` 目录是 Skia 图形库中图像子系统的核心实现层。该目录包含了 `SkImage` 和 `SkSurface` 两大核心公共 API 的底层实现，是 Skia 2D 渲染管线中最关键的模块之一。所有与图像创建、像素读取、颜色空间转换、缩放以及绘图表面管理相关的逻辑均汇聚于此。

从架构角度来看，该目录采用经典的基类-派生类多态设计。`SkImage_Base` 作为所有图像实现的内部基类，定义了统一的虚函数接口；而 `SkImage_Raster`、`SkImage_Lazy`、`SkImage_Picture` 等子类则针对不同的像素数据来源（内存位图、延迟生成器、录制的绘图命令）提供差异化的实现。同样，`SkSurface_Base` 是绘图表面的内部基类，`SkSurface_Raster` 和 `SkNullSurface` 分别提供了 CPU 光栅化和空操作的实现。

该模块与 Skia 的其他子系统有广泛的交互。向上，它通过 `include/core/SkImage.h` 和 `include/core/SkSurface.h` 暴露公共 API；向下，它依赖 `src/core` 中的位图缓存（`SkBitmapCache`）、像素转换（`SkConvertPixels`）、mipmap 生成（`SkMipmap`）等基础设施；横向，它与 GPU 后端（Ganesh/Graphite）通过类型枚举和虚函数进行解耦交互。

值得注意的是，该目录还包含了工厂函数文件（如 `SkImage_RasterFactories.cpp`、`SkImage_LazyFactories.cpp`），这些文件实现了 `SkImages` 命名空间中的各种图像创建方法，是用户最常调用的入口点。此外，`SkRescaleAndReadPixels` 提供了多步缩放-读取像素的通用算法，被图像和表面共同使用。

## 架构图

```
                           +------------------+
                           |   SkImage (公共)   |
                           | include/core/    |
                           +--------+---------+
                                    |
                           +--------+---------+
                           |  SkImage_Base    |
                           | (内部基类)        |
                           +--------+---------+
                                    |
              +---------------------+---------------------+
              |                     |                     |
     +--------+--------+  +--------+--------+  +---------+---------+
     | SkImage_Raster   |  | SkImage_Lazy    |  | SkImage_Picture   |
     | (内存位图图像)    |  | (延迟生成图像)  |  | (Picture图像)     |
     +------------------+  +-----------------+  +-------------------+
                                    |
                           继承 SkImage_Lazy

   +------------------+
   | SkSurface (公共)  |
   | include/core/    |
   +--------+---------+
            |
   +--------+---------+
   | SkSurface_Base   |
   | (内部基类)        |
   +--------+---------+
            |
   +--------+-----------+-----------------+
   |                    |                 |
   | SkSurface_Raster   | SkNullSurface   |
   | (CPU光栅化表面)     | (空操作表面)     |
   +--------------------+-----------------+

   辅助模块:
   +------------------------+  +---------------------------+
   | SkRescaleAndReadPixels |  | SkPictureImageGenerator   |
   | (多步缩放读取)         |  | (Picture->像素 生成器)     |
   +------------------------+  +---------------------------+
   +------------------------+  +---------------------------+
   | SkTiledImageUtils      |  | SkImageGeneratorPriv      |
   | (分块图像绘制工具)      |  | (图像生成器私有接口)       |
   +------------------------+  +---------------------------+
```

## 目录结构

```
src/image/
├── BUILD.bazel                    # Bazel 构建规则定义
├── SkImage.cpp                    # SkImage 公共 API 实现（readPixels, makeShader, makeScaled 等）
├── SkImage_Base.h                 # SkImage 内部基类头文件，定义虚函数接口和 Type 枚举
├── SkImage_Base.cpp               # SkImage_Base 默认实现（异步读取、遗留位图转换等）
├── SkImage_Raster.h               # 栅格图像头文件（基于 SkBitmap 的不可变图像）
├── SkImage_Raster.cpp             # 栅格图像实现（像素读写、子集创建、mipmap 支持）
├── SkImage_RasterFactories.cpp    # SkImages:: 命名空间中的栅格图像工厂方法
├── SkImage_Lazy.h                 # 延迟图像头文件（基于 SkImageGenerator 的懒加载图像）
├── SkImage_Lazy.cpp               # 延迟图像实现（带缓存的像素生成、YUV 平面获取）
├── SkImage_LazyFactories.cpp      # DeferredFromPicture/DeferredFromGenerator 工厂方法
├── SkImage_Picture.h              # Picture 图像头文件（SkPicture 转图像的延迟实现）
├── SkImage_Picture.cpp            # Picture 图像实现（replay 绘制、键值生成）
├── SkImage_AndroidFactories.cpp   # Android 平台特有的图像工厂方法
├── SkImageGeneratorPriv.h         # 图像生成器私有接口（MakeFromPicture, MakeFromEncoded）
├── SkPictureImageGenerator.h      # Picture 图像生成器头文件
├── SkPictureImageGenerator.cpp    # Picture 图像生成器实现（将 SkPicture 光栅化为像素）
├── SkRescaleAndReadPixels.h       # 多步缩放读取接口
├── SkRescaleAndReadPixels.cpp     # 多步缩放读取实现（支持线性/三次缩放模式）
├── SkSurface.cpp                  # SkSurface 公共 API 实现（getCanvas, makeImageSnapshot 等）
├── SkSurface_Base.h               # SkSurface 内部基类（含 Copy-on-Write 机制）
├── SkSurface_Base.cpp             # SkSurface_Base 实现
├── SkSurface_Raster.h             # CPU 栅格化表面头文件
├── SkSurface_Raster.cpp           # CPU 栅格化表面实现（含 SkSurfaces::Raster 工厂）
├── SkSurface_Null.cpp             # 空操作表面实现（SkSurfaces::Null 工厂）
└── SkTiledImageUtils.cpp          # 分块图像绘制工具实现
```

## 关键类与函数

### SkImage_Base（内部基类）

`SkImage_Base` 继承自公共的 `SkImage`，是所有具体图像实现的内部抽象基类。

```cpp
class SkImage_Base : public SkImage {
public:
    // 图像类型枚举，区分不同的后端实现
    enum class Type {
        kRaster,          // 内存位图
        kRasterPinnable,  // 可固定的位图（Android 特有）
        kLazy,            // 延迟生成（基于 SkImageGenerator）
        kLazyPicture,     // 延迟生成（基于 SkPicture）
        kLazyTexture,     // 延迟生成（GPU 纹理）
        kGanesh,          // Ganesh GPU 后端
        kGaneshYUVA,      // Ganesh YUVA 格式
        kGraphite,        // Graphite GPU 后端
        kGraphiteYUVA,    // Graphite YUVA 格式
    };

    virtual Type type() const = 0;
    virtual bool onReadPixels(...) const = 0;      // 纯虚：读取像素
    virtual bool getROPixels(...) const = 0;        // 纯虚：获取只读像素
    virtual sk_sp<SkImage> onMakeSubset(...) const = 0; // 纯虚：创建子集图像
};
```

关键辅助函数 `as_IB()` 用于将公共 `SkImage*` 安全地向下转型为 `SkImage_Base*`：

```cpp
static inline SkImage_Base* as_IB(SkImage* image) {
    return static_cast<SkImage_Base*>(image);
}
```

### SkImage_Raster（栅格图像）

存储实际像素数据的不可变图像，通过 `SkBitmap` 管理底层内存。

```cpp
class SkImage_Raster : public SkImage_Base {
    SkBitmap fBitmap;           // 底层位图数据
    sk_sp<SkMipmap> fMips;     // 可选的 mipmap 层级

    bool onPeekPixels(SkPixmap*) const override;    // 零拷贝访问像素
    bool getROPixels(...) const override;            // 直接返回内部位图
    static sk_sp<SkImage_Raster> MakeFromBitmap(const SkBitmap&, SkCopyPixelsMode, ...);
};
```

### SkImage_Lazy（延迟图像）

通过 `SharedGenerator`（对 `SkImageGenerator` 的线程安全包装）按需生成像素。

```cpp
class SkImage_Lazy : public SkImage_Base {
    sk_sp<SharedGenerator> fSharedGenerator;   // 共享的图像生成器

    bool getROPixels(...) const override;      // 带缓存的像素生成
    sk_sp<SkCachedData> getPlanes(...) const;  // 获取 YUV 平面数据
};
```

`ScopedGenerator` 内部类提供了对 `SharedGenerator` 的 RAII 互斥锁管理。

### SkImage_Picture（Picture 图像）

继承自 `SkImage_Lazy`，将 `SkPicture` 记录的绘图命令作为像素数据源。

```cpp
class SkImage_Picture : public SkImage_Lazy {
    void replay(SkCanvas*) const;  // 在画布上回放 Picture
    bool getImageKeyValues(uint32_t keyValues[]) const;  // 生成缓存键值
};
```

### SkSurface_Base / SkSurface_Raster（绘图表面）

`SkSurface_Base` 实现了 Copy-on-Write（写时复制）机制，确保快照图像与活动表面之间的数据一致性。

```cpp
class SkSurface_Base : public SkSurface {
    sk_sp<SkImage> fCachedImage;        // 缓存的快照图像
    virtual bool onCopyOnWrite(ContentChangeMode) = 0;  // 写时复制回调
    sk_sp<SkImage> refCachedImage();    // 获取或创建缓存的快照
};
```

### SkRescaleAndReadPixels（多步缩放读取）

实现了渐进式缩放算法，通过多个中间步骤逐步调整图像尺寸以获得更高质量的结果：

```cpp
void SkRescaleAndReadPixels(SkBitmap bmp,
                            const SkImageInfo& resultInfo,
                            const SkIRect& srcRect,
                            SkImage::RescaleGamma rescaleGamma,
                            SkImage::RescaleMode rescaleMode,
                            SkImage::ReadPixelsCallback callback,
                            SkImage::ReadPixelsContext context);
```

### 工厂函数（SkImages 命名空间）

```cpp
namespace SkImages {
    sk_sp<SkImage> RasterFromBitmap(const SkBitmap&);           // 从位图创建
    sk_sp<SkImage> RasterFromPixmapCopy(const SkPixmap&);       // 从像素图复制创建
    sk_sp<SkImage> RasterFromData(const SkImageInfo&, sk_sp<SkData>, size_t); // 从数据创建
    sk_sp<SkImage> DeferredFromGenerator(unique_ptr<SkImageGenerator>);       // 延迟创建
    sk_sp<SkImage> DeferredFromPicture(sk_sp<SkPicture>, ...);                // 从 Picture 延迟创建
}
```

## 依赖关系

### 上游依赖（本模块依赖的组件）

| 依赖模块 | 文件/类 | 用途 |
|---------|---------|------|
| `include/core/` | `SkImage.h`, `SkSurface.h` | 公共 API 基类定义 |
| `src/core/` | `SkBitmapCache` | 延迟图像的位图缓存 |
| `src/core/` | `SkMipmap` | mipmap 生成与管理 |
| `src/core/` | `SkNextID` | 唯一 ID 生成 |
| `src/core/` | `SkConvertPixels` | 像素格式转换 |
| `src/core/` | `SkYUVPlanesCache` | YUV 平面数据缓存 |
| `src/core/` | `SkResourceCache` | 通用资源缓存 |
| `src/core/` | `SkBitmapDevice` | CPU 光栅化设备 |
| `src/shaders/` | `SkImageShader` | 图像着色器（makeShader 方法） |
| `include/core/` | `SkImageGenerator` | 图像数据生成器接口 |
| `include/core/` | `SkPicture` | 绘图命令记录 |

### 下游被依赖（使用本模块的组件）

| 依赖方 | 用途 |
|--------|------|
| `src/gpu/ganesh/` | Ganesh GPU 后端的图像/表面实现 |
| `src/gpu/graphite/` | Graphite GPU 后端的图像/表面实现 |
| `src/encode/` | 编码器通过 `getROPixels` 获取像素数据 |
| `src/core/SkCanvas` | 画布绘制图像和管理表面 |
| `src/core/SkPictureRecorder` | 录制包含图像绘制的命令 |

## 设计模式分析

### 1. 模板方法模式（Template Method）

`SkImage_Base` 和 `SkSurface_Base` 大量使用模板方法模式。公共方法（如 `SkImage::readPixels()`）在基类中执行参数校验和通用逻辑，然后委托给子类的虚函数（如 `onReadPixels()`）处理具体实现。所有 `on*` 前缀的虚函数均遵循此模式。

### 2. 工厂方法模式（Factory Method）

图像创建通过 `SkImages` 命名空间中的静态工厂函数实现，隐藏了具体子类的构造细节。例如 `SkImages::RasterFromBitmap()` 内部创建 `SkImage_Raster`，而 `SkImages::DeferredFromGenerator()` 内部创建 `SkImage_Lazy`。

### 3. 写时复制模式（Copy-on-Write）

`SkSurface_Raster` 与 `SkImage_Raster` 之间通过 `SkPixelRef` 的 `setTemporarilyImmutable()` 和 `restoreMutability()` 机制实现写时复制。当表面创建快照后，底层像素被标记为临时不可变；当表面需要修改时，通过 `onCopyOnWrite` 触发深拷贝。

### 4. 代理模式（Proxy）

`SharedGenerator` 类作为 `SkImageGenerator` 的线程安全代理，提供引用计数和互斥锁保护。`ScopedGenerator` 则是一个 RAII 风格的作用域锁代理，确保生成器在使用时被正确锁定。

### 5. 观察者模式（Observer）

`SkImage_Lazy` 通过 `SkIDChangeListener::List` 维护一个监听器列表。当图像的唯一 ID 失效时（如对象被销毁），所有注册的监听器都会收到通知，用于清理 GPU 纹理缓存等依赖资源。

## 数据流

### 图像创建与像素读取流程

```
用户调用 SkImages::RasterFromBitmap(bitmap)
    |
    v
SkImage_Raster::MakeFromBitmap(bitmap, SkCopyPixelsMode::kIfMutable)
    |
    +--> 检查 bitmap 是否不可变
    +--> 若可变，则深拷贝像素数据 (SkData::MakeWithCopy)
    +--> 创建 SkImage_Raster 实例
    |
    v
用户调用 image->readPixels(dstInfo, dstPixels, ...)
    |
    v
SkImage::readPixels() --委托--> SkImage_Base::onReadPixels()
    |
    v
SkImage_Raster::onReadPixels()
    +--> 通过 SkBitmap::readPixels 执行像素转换和拷贝
```

### 延迟图像的像素生成流程

```
用户调用 SkImages::DeferredFromGenerator(generator)
    |
    v
SharedGenerator::Make(generator) --> 包装为线程安全的共享生成器
    |
    v
SkImage_Lazy::Validator 验证生成器信息
    |
    v
创建 SkImage_Lazy 实例（此时不生成像素）
    |
    ... 用户绘制或读取像素 ...
    |
    v
SkImage_Lazy::getROPixels()
    +--> SkBitmapCache::Find() 查找缓存
    |     命中 --> 返回缓存位图
    |     未命中:
    +--> SkBitmapCache::Alloc() 分配缓存空间
    +--> ScopedGenerator(fSharedGenerator)->getPixels(pmap) 生成像素
    +--> SkBitmapCache::Add() 存入缓存
    +--> notifyAddedToRasterCache() 通知缓存系统
```

### Surface 快照与写时复制流程

```
用户调用 surface->makeImageSnapshot()
    |
    v
SkSurface_Base::refCachedImage()
    +--> 若有缓存 --> 返回 fCachedImage
    +--> 否则 --> onNewImageSnapshot()
              |
              v
         SkSurface_Raster::onNewImageSnapshot()
              +--> SkPixelRef::setTemporarilyImmutable()
              +--> SkImage_Raster::MakeFromBitmap(fBitmap, kIfMutable)
              |     (因为临时不可变，不会发生拷贝)
              v
         返回共享像素的 SkImage_Raster

用户继续在 surface 上绘制
    |
    v
SkSurface_Base::aboutToDraw()
    +--> SkSurface_Raster::onCopyOnWrite()
         +--> 检测到共享 PixelRef
         +--> fBitmap.tryAllocPixels() 分配新内存
         +--> memcpy 拷贝像素到新位图
         +--> 更新 canvas 的后备设备
```

## 相关文档与参考

| 资源 | 说明 |
|------|------|
| `include/core/SkImage.h` | SkImage 公共 API 头文件，定义所有用户可见的方法 |
| `include/core/SkSurface.h` | SkSurface 公共 API 头文件 |
| `include/core/SkImageGenerator.h` | 图像生成器接口，用于延迟图像 |
| `include/core/SkPicture.h` | SkPicture 绘图命令记录接口 |
| `include/core/SkBitmap.h` | 位图类，管理可变的像素数据 |
| `include/core/SkPixmap.h` | 像素图类，提供对像素数据的只读视图 |
| `src/core/SkBitmapCache.h` | 位图缓存，为延迟图像提供像素缓存 |
| `src/core/SkMipmap.h` | Mipmap 层级生成和管理 |
| `src/gpu/ganesh/image/` | Ganesh GPU 后端的图像实现 |
| `src/gpu/graphite/Image_Graphite.h` | Graphite GPU 后端的图像实现 |
| Skia 官方文档: Image 概念 | https://skia.org/docs/user/api/skimage_overview/ |
| Skia 官方文档: Surface 概念 | https://skia.org/docs/user/api/sksurface_overview/ |
