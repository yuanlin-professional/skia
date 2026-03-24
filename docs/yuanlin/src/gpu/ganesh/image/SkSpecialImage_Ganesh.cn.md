# SkSpecialImage_Ganesh - Ganesh GPU 特殊图像

> 源文件: `src/gpu/ganesh/image/SkSpecialImage_Ganesh.h`, `src/gpu/ganesh/image/SkSpecialImage_Ganesh.cpp`

## 概述

`SkSpecialImages` 命名空间（Ganesh 部分）提供了在 Ganesh GPU 后端创建和操作 `SkSpecialImage` 的工具函数。`SkSpecialImage` 是 Skia 内部用于图像滤镜管线的特殊图像类型，它表示一个更大纹理中的子区域。该头文件提供了从 GPU 纹理代理视图创建特殊图像以及从特殊图像提取代理视图的功能。

## 架构位置

```
SkImageFilter 管线
    |
SkSpecialImage (抽象基类)
    |
SkSpecialImages (本命名空间 - Ganesh 工厂函数)
    |
GrSurfaceProxyView (GPU 纹理代理)
```

特殊图像主要在 Skia 的图像滤镜管线中使用，用于表示滤镜输入和输出。

## 主要类与结构体

该头文件不定义类，仅提供命名空间级别的自由函数。

## 公共 API 函数

### `MakeFromTextureImage()`

```cpp
sk_sp<SkSpecialImage> MakeFromTextureImage(GrRecordingContext* rContext,
                                            const SkIRect& subset,
                                            sk_sp<SkImage> image,
                                            const SkSurfaceProps& props);
```

从 `SkImage` 创建特殊图像，提取其 GPU 纹理代理视图。

### `MakeDeferredFromGpu()`

```cpp
sk_sp<SkSpecialImage> MakeDeferredFromGpu(GrRecordingContext*,
                                           const SkIRect& subset,
                                           uint32_t uniqueID,
                                           GrSurfaceProxyView,
                                           const GrColorInfo&,
                                           const SkSurfaceProps&);
```

直接从 `GrSurfaceProxyView` 创建延迟特殊图像。这是最常用的创建方式，被 `Device::snapSpecial` 使用。

### `AsView()`

```cpp
GrSurfaceProxyView AsView(GrRecordingContext*, const SkSpecialImage*);
```

从特殊图像提取完整的后备纹理代理视图。注意返回的视图表示整个后备图像，纹理坐标需要从内容矩形映射到代理空间。

## 内部实现细节

特殊图像的 `subset` 参数定义了后备纹理中的有效区域。使用者必须根据 `subset().topLeft()` 偏移纹理坐标。

## 依赖关系

- **上游依赖**: `SkSpecialImage`（基类）、`GrSurfaceProxyView`、`GrColorInfo`。
- **被依赖**: `skgpu::ganesh::Device`、图像滤镜后端。

## 设计模式与设计决策

1. **工厂函数模式**: 通过命名空间函数而非类方法创建特殊图像，解耦创建逻辑。
2. **子区域语义**: 特殊图像始终是更大纹理的子区域，减少纹理拷贝。

## 性能考量

- `MakeDeferredFromGpu` 不触发纹理拷贝，仅创建轻量级包装。
- `AsView` 是零拷贝的视图提取操作。

## 相关文件

- `src/core/SkSpecialImage.h` - 特殊图像基类
- `src/gpu/ganesh/GrSurfaceProxyView.h` - 纹理代理视图
- `src/gpu/ganesh/Device.h` - Device 的 `snapSpecial` 使用此功能
