# SkImage_RasterFactories

> 源文件：src/image/SkImage_RasterFactories.cpp

## 概述

`SkImage_RasterFactories.cpp` 实现了创建栅格图像的各种工厂函数。这些函数提供了从位图、Pixmap、编码数据、压缩纹理等不同数据源创建 `SkImage` 对象的方法。文件还包含参数验证逻辑，确保创建的图像符合 Skia 的内部约束。

## 主要函数

### 参数验证

```cpp
static bool valid_args(const SkImageInfo& info, size_t rowBytes, size_t* minSize) {
    const int maxDimension = SK_MaxS32 >> 2;
    // 检查尺寸、颜色类型、Alpha 类型、行字节数
    // 检查整数溢出
    size_t size = info.computeByteSize(rowBytes);
    if (SkImageInfo::ByteSizeOverflowed(size)) {
        return false;
    }
    return true;
}
```

### 工厂函数

**从位图创建**：
```cpp
sk_sp<SkImage> RasterFromBitmap(const SkBitmap& bm) {
    if (!bm.pixelRef()) return nullptr;
    return SkImage_Raster::MakeFromBitmap(bm, SkCopyPixelsMode::kIfMutable);
}
```

**从 Pixmap 拷贝**：
```cpp
sk_sp<SkImage> RasterFromPixmapCopy(const SkPixmap& pmap) {
    if (!valid_args(pmap.info(), pmap.rowBytes(), &size) || !pmap.addr()) {
        return nullptr;
    }
    sk_sp<SkData> data(SkData::MakeWithCopy(pmap.addr(), size));  // 拷贝像素
    return sk_make_sp<SkImage_Raster>(pmap.info(), std::move(data), pmap.rowBytes(), nullptr, kNeedNewImageUniqueID);
}
```

**从 SkData 创建**：
```cpp
sk_sp<SkImage> RasterFromData(const SkImageInfo& info, sk_sp<SkData> data, size_t rowBytes) {
    if (!valid_args(info, rowBytes, &size) || !data || data->size() < size) {
        return nullptr;
    }
    return sk_make_sp<SkImage_Raster>(info, std::move(data), rowBytes, nullptr, kNeedNewImageUniqueID);
}
```

**从 Pixmap 创建（带释放回调）**：
```cpp
sk_sp<SkImage> RasterFromPixmap(const SkPixmap& pmap, RasterReleaseProc proc, ReleaseContext ctx) {
    if (!valid_args(pmap.info(), pmap.rowBytes(), &size) || !pmap.addr()) {
        return nullptr;
    }
    sk_sp<SkData> data(SkData::MakeWithProc(pmap.addr(), size, proc, ctx));
    return sk_make_sp<SkImage_Raster>(pmap.info(), std::move(data), pmap.rowBytes(), nullptr, kNeedNewImageUniqueID);
}
```

**从压缩纹理创建**：
```cpp
sk_sp<SkImage> RasterFromCompressedTextureData(sk_sp<SkData> data, int width, int height,
                                               SkTextureCompressionType type) {
    // 验证数据大小
    size_t expectedSize = SkCompressedFormatDataSize(type, {width, height}, false);
    if (!data || data->size() < expectedSize) return nullptr;

    // 解压缩到位图
    SkBitmap bitmap;
    bitmap.tryAllocPixels(SkImageInfo::MakeN32(width, height, at));
    if (!SkDecompress(std::move(data), {width, height}, type, &bitmap)) {
        return nullptr;
    }

    bitmap.setImmutable();
    return RasterFromBitmap(bitmap);
}
```

**应用图像滤镜**：
```cpp
sk_sp<SkImage> MakeWithFilter(sk_sp<SkImage> src,
                              const SkImageFilter* filter,
                              const SkIRect& subset,
                              const SkIRect& clipBounds,
                              SkIRect* outSubset,
                              SkIPoint* offset) {
    if (!src || !filter) return nullptr;

    sk_sp<skif::Backend> backend = skif::MakeRasterBackend({}, src->colorType());
    return as_IFB(filter)->makeImageWithFilter(std::move(backend), std::move(src),
                                               subset, clipBounds, outSubset, offset);
}
```

## 设计模式与设计决策

### 工厂方法模式

每个函数都是创建 `SkImage_Raster` 的工厂方法。

### 决策 1：严格参数验证

- **原因**：防止整数溢出、内存错误
- **检查**：尺寸、颜色类型、行字节数、数据大小

### 决策 2：拷贝 vs 包装

- `RasterFromPixmapCopy()`：总是拷贝像素
- `RasterFromPixmap()`：包装外部像素，使用释放回调管理生命周期
- `RasterFromBitmap()`：根据可变性决定是否拷贝

### 决策 3：压缩纹理自动解压

- **原因**：Skia 栅格后端不直接支持压缩格式
- **策略**：解压为 N32 格式

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/image/SkImage_Raster.h` | 实现类 | 栅格图像实现 |
| `include/core/SkImage.h` | 公共 API | 图像接口声明 |
| `include/core/SkData.h` | 数据容器 | 不可变数据块 |
