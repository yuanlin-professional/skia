# SkImage_Raster

> 源文件：src/image/SkImage_Raster.h, src/image/SkImage_Raster.cpp

## 概述

`SkImage_Raster` 是 Skia 中基于 CPU 内存的栅格图像实现。它通过 `SkBitmap` 存储像素数据，提供快速的像素访问能力，无需延迟解码或 GPU 纹理上传。该类是最基础的图像实现，支持多种功能包括像素直接访问（`peekPixels`）、Mipmap 管理、子集创建、颜色空间转换等。

与 `SkImage_Lazy` 不同，`SkImage_Raster` 的像素数据已经解码完成并驻留在内存中，可以立即访问。它还支持通过 `SkCopyPixelsMode` 控制像素拷贝行为，以及与 `SkBitmap` 的高效互操作。

## 架构位置

`SkImage_Raster` 在 Skia 图像架构中的位置：

- **继承关系**：继承自 `SkImage_Base`（所有图像实现的基类）
- **类型标识**：`SkImage_Base::Type::kRaster`
- **所属模块**：`src/image/` 图像实现模块
- **数据存储**：基于 `SkBitmap` 和 `SkPixelRef`
- **Mipmap 支持**：可选的 `SkMipmap` 对象

在图像类型层次中，`SkImage_Raster` 是最基础的 CPU 栅格图像，其他类型（如 `SkImage_Lazy`、`SkImage_Picture`）在需要时会转换为栅格图像。

## 主要类与结构体

### SkImage_Raster

基于 CPU 内存的栅格图像类。

**成员变量**：
- `fBitmap`：`SkBitmap` - 存储像素数据
- `fMips`：`sk_sp<SkMipmap>` - 可选的 Mipmap 金字塔

**构造函数**：
- 从 `SkData` 构造（用于工厂函数）
- 从 `SkBitmap` 构造（可控制是否可变）
- 从 `SkImageInfo` 和 `SkData` 构造（主构造函数）

**核心方法**：
- `onReadPixels()`：读取像素到缓冲区
- `onPeekPixels()`：提供零拷贝像素访问
- `getROPixels()`：获取只读位图
- `onMakeSubset()`：创建子集图像
- `MakeFromBitmap()`：静态工厂函数，从位图创建图像
- `onMakeWithMipmaps()`：创建带 Mipmap 的新图像

### SkCopyPixelsMode 枚举

```cpp
enum class SkCopyPixelsMode {
    kIfMutable,   // 仅当可变时拷贝
    kAlways,      // 总是拷贝
    kNever,       // 永不拷贝
};
```

控制从 `SkBitmap` 创建图像时的像素拷贝行为。

## 公共 API 函数

### MakeFromBitmap

```cpp
static sk_sp<SkImage_Raster> MakeFromBitmap(const SkBitmap& bm,
                                            SkCopyPixelsMode cpm,
                                            sk_sp<SkMipmap> mips = nullptr)
```

从位图创建栅格图像，根据拷贝模式决定是共享还是拷贝像素。

**参数**：
- `bm`：源位图
- `cpm`：拷贝模式
- `mips`：可选的 Mipmap

**返回值**：成功返回图像指针，失败返回 `nullptr`

**拷贝策略**：
- `kAlways`：总是拷贝像素
- `kIfMutable`：位图可变时拷贝，不可变时共享
- `kNever`：总是共享（调用方需确保位图生命周期）

### isValid

```cpp
bool isValid(SkRecorder* recorder) const override
```

检查图像是否在给定 Recorder 中有效，对于栅格图像要求 Recorder 支持 CPU 绘制。

### onReadPixels

```cpp
bool onReadPixels(GrDirectContext*, const SkImageInfo& dstInfo,
                  void* dstPixels, size_t dstRowBytes,
                  int srcX, int srcY, CachingHint) const override
```

读取像素到目标缓冲区，支持格式转换和子矩形读取。

### onPeekPixels

```cpp
bool onPeekPixels(SkPixmap* pm) const override
```

提供零拷贝的像素访问，返回指向内部位图的 `SkPixmap`。

### getROPixels

```cpp
bool getROPixels(GrDirectContext*, SkBitmap* dst, CachingHint) const override
```

获取只读位图，直接返回内部位图的副本（浅拷贝，共享像素）。

### onMakeSubset

```cpp
sk_sp<SkImage> onMakeSubset(SkRecorder*, const SkIRect& subset,
                            RequiredProperties requiredProperties) const override
```

创建子集图像，支持 Mipmap 处理。

### makeShaderForPaint

```cpp
sk_sp<SkShader> makeShaderForPaint(const SkPaint& paint,
                                   SkTileMode tmx, SkTileMode tmy,
                                   const SkSamplingOptions& sampling,
                                   const SkMatrix* localMatrix)
```

创建图像着色器，处理 Alpha-only 图像与 Paint 着色器的组合。

## 内部实现细节

### 构造函数实现

**从 SkData 构造**（主构造函数）：
```cpp
SkImage_Raster::SkImage_Raster(const SkImageInfo& info,
                               sk_sp<SkData> data,
                               size_t rowBytes,
                               sk_sp<SkMipmap> mips,
                               uint32_t id)
    : SkImage_Base(info, id), fMips(mips) {
    void* addr = const_cast<void*>(data->data());
    // 使用自定义释放函数，确保 SkData 生命周期
    fBitmap.installPixels(info, addr, rowBytes, release_data, data.release());
    fBitmap.setImmutable();
}
```

**释放回调**：
```cpp
static void release_data(void* addr, void* context) {
    SkData* data = static_cast<SkData*>(context);
    data->unref();
}
```

通过 `installPixels()` 将 `SkData` 的生命周期绑定到 `SkPixelRef`，当位图销毁时自动释放数据。

**从 SkBitmap 构造**：
```cpp
SkImage_Raster::SkImage_Raster(const SkBitmap& bm, sk_sp<SkMipmap> mips, bool bitmapMayBeMutable)
    : SkImage_Base(bm.info(),
                   is_not_subset(bm) ? bm.getGenerationID()
                                     : (uint32_t)kNeedNewImageUniqueID)
    , fBitmap(bm)
    , fMips(mips) {
    SkASSERT(bitmapMayBeMutable || fBitmap.isImmutable());
}
```

**唯一 ID 处理**：
- 如果位图是完整的（非子集），共享生成 ID
- 如果是子集，分配新的唯一 ID

### 像素访问实现

**直接访问（零拷贝）**：
```cpp
bool SkImage_Raster::onPeekPixels(SkPixmap* pm) const {
    return fBitmap.peekPixels(pm);
}
```

**读取访问（可能格式转换）**：
```cpp
bool SkImage_Raster::onReadPixels(...) const {
    SkBitmap shallowCopy(fBitmap);
    return shallowCopy.readPixels(dstInfo, dstPixels, dstRowBytes, srcX, srcY);
}
```

使用浅拷贝确保位图生命周期正确，实际像素读取由 `SkBitmap::readPixels()` 处理格式转换。

**获取只读位图**：
```cpp
bool SkImage_Raster::getROPixels(...) const {
    *dst = fBitmap;  // 浅拷贝，共享像素
    return true;
}
```

### 子集创建

**无 Mipmap 路径**（简单拷贝）：
```cpp
static SkBitmap copy_bitmap_subset(const SkBitmap& orig, const SkIRect& subset) {
    SkImageInfo info = orig.info().makeDimensions(subset.size());
    SkBitmap bitmap;
    if (!bitmap.tryAllocPixels(info)) {
        return {};
    }

    void* dst = bitmap.getPixels();
    void* src = orig.getAddr(subset.x(), subset.y());

    // 逐行拷贝
    SkRectMemcpy(dst, bitmap.rowBytes(), src, orig.rowBytes(),
                 bitmap.rowBytes(), subset.height());

    bitmap.setImmutable();
    return bitmap;
}
```

**有 Mipmap 路径**（复杂处理）：
```cpp
sk_sp<SkImage> SkImage_Raster::onMakeSubset(...) const {
    if (requiredProperties.fMipmapped) {
        bool fullCopy = subset == SkIRect::MakeSize(fBitmap.dimensions());
        sk_sp<SkMipmap> mips = fullCopy ? copy_mipmaps(fBitmap, fMips.get()) : nullptr;

        SkBitmap tmpSubset;
        fBitmap.extractSubset(&tmpSubset, subset);  // 浅拷贝

        sk_sp<SkImage> tmp(new SkImage_Raster(tmpSubset, nullptr, true));
        return tmp->withMipmaps(std::move(mips));  // withMipmaps 会强制深拷贝
    } else {
        return SkImages::RasterFromBitmap(copy_bitmap_subset(fBitmap, subset));
    }
}
```

**策略**：
- 需要 Mipmap 时：先浅拷贝位图，再调用 `withMipmaps()` 触发深拷贝和 Mipmap 生成
- 不需要 Mipmap 时：直接深拷贝像素

### Mipmap 拷贝

```cpp
static sk_sp<SkMipmap> copy_mipmaps(const SkBitmap& src, SkMipmap* srcMips) {
    if (!srcMips) return nullptr;

    // 构建 Mipmap 结构但不计算内容
    sk_sp<SkMipmap> dst;
    dst.reset(SkMipmap::Build(src.pixmap(), nullptr, false));
    if (!dst) return nullptr;

    // 逐级拷贝
    for (int i = 0; i < dst->countLevels(); ++i) {
        SkMipmap::Level srcLevel, dstLevel;
        srcMips->getLevel(i, &srcLevel);
        dst->getLevel(i, &dstLevel);
        srcLevel.fPixmap.readPixels(dstLevel.fPixmap);
    }

    return dst;
}
```

**注意**：只有完整图像才拷贝 Mipmap，子集会重新生成 Mipmap。

### Mipmap 管理

**添加 Mipmap**：
```cpp
sk_sp<SkImage> SkImage_Raster::onMakeWithMipmaps(sk_sp<SkMipmap> mips) const {
    if (!mips) {
        mips.reset(SkMipmap::Build(fBitmap.pixmap(), nullptr));
    }
    // 总是深拷贝以避免 PixelRef 共享问题
    return SkImage_Raster::MakeFromBitmap(fBitmap, SkCopyPixelsMode::kAlways, std::move(mips));
}
```

**原因**：共享 `SkPixelRef` 但 Mipmap 不同会导致缓存问题（缓存以 PixelRef 生成 ID 为键）。

### 颜色空间处理

**转换颜色类型和颜色空间**：
```cpp
sk_sp<SkImage> SkImage_Raster::makeColorTypeAndColorSpace(...) const {
    SkPixmap src;
    fBitmap.peekPixels(&src);

    SkBitmap dst;
    if (!dst.tryAllocPixels(fBitmap.info().makeColorType(targetColorType)
                                          .makeColorSpace(targetColorSpace))) {
        return nullptr;
    }

    dst.writePixels(src);  // 执行颜色转换
    dst.setImmutable();
    return SkImages::RasterFromBitmap(dst);
}
```

**重解释颜色空间**（无像素转换）：
```cpp
sk_sp<SkImage> SkImage_Raster::onReinterpretColorSpace(sk_sp<SkColorSpace> newCS) const {
    SkPixmap pixmap = fBitmap.pixmap();
    pixmap.setColorSpace(std::move(newCS));
    return SkImages::RasterFromPixmapCopy(pixmap);
}
```

注释说明理想情况是共享 PixelRef，但由于生成 ID 的限制，只能拷贝。

### Alpha-only 图像着色器

```cpp
sk_sp<SkShader> SkImage_Raster::makeShaderForPaint(const SkPaint& paint, ...) {
    auto s = SkImageShader::Make(sk_ref_sp<SkImage>(this), tmx, tmy, sampling, localMatrix);

    if (SkColorTypeIsAlphaOnly(this->colorType()) && paint.getShader()) {
        // Alpha 图像：组合图像着色器和 Paint 着色器
        // 使用 DstIn 混合模式：d*sa（目标颜色 × 源 Alpha）
        s = SkShaders::Blend(SkBlendMode::kDstIn, paint.refShader(), std::move(s));
    }
    return s;
}
```

**逻辑**：
- 普通图像：直接使用图像着色器，忽略 Paint 着色器
- Alpha 图像：组合两个着色器，用图像 Alpha 调制 Paint 颜色

### 缓存通知

```cpp
void notifyAddedToRasterCache() const override {
    // 不调用 INHERITED::notifyAddedToRasterCache
    // 直接通知 PixelRef
    fBitmap.pixelRef()->notifyAddedToCache();
}
```

**设计决策**：栅格图像的缓存生命周期绑定到 `PixelRef` 而非图像对象本身，允许多个图像共享同一 PixelRef 时共享缓存。

### 遗留位图转换

```cpp
bool SkImage_Raster::onAsLegacyBitmap(GrDirectContext*, SkBitmap* bitmap) const {
    if (fBitmap.isImmutable()) {
        // 共享 PixelRef
        bitmap->setInfo(fBitmap.info(), fBitmap.rowBytes());
        bitmap->setPixelRef(sk_ref_sp(fBitmap.pixelRef()),
                           fBitmap.pixelRefOrigin().x(),
                           fBitmap.pixelRefOrigin().y());
        return true;
    }
    // 否则使用基类实现（会拷贝）
    return this->SkImage_Base::onAsLegacyBitmap(nullptr, bitmap);
}
```

仅当位图不可变时才共享 PixelRef，避免调用方修改共享数据。

## 依赖关系

### 核心依赖

| 依赖项 | 用途 |
|--------|------|
| `SkImage_Base` | 基类，图像实现框架 |
| `SkBitmap` | 像素数据存储 |
| `SkPixelRef` | 像素内存管理 |
| `SkData` | 不可变数据块 |
| `SkMipmap` | Mipmap 金字塔 |

### 次要依赖

| 依赖项 | 用途 |
|--------|------|
| `SkPixmap` | 像素数据访问 |
| `SkImageInfo` | 图像格式描述 |
| `SkColorSpace` | 颜色空间管理 |
| `SkImageShader` | 着色器创建 |
| `SkRecorder` | 绘制记录器 |

### 反向依赖

| 依赖方 | 用途 |
|--------|------|
| `SkImages::RasterFromBitmap()` | 工厂函数 |
| `SkImages::RasterFromPixmap()` | 工厂函数 |
| `SkImage_Lazy` | 延迟加载后转为栅格图像 |
| `SkSurface_Raster` | 表面快照 |

## 设计模式与设计决策

### 决策 1：基于 SkBitmap 而非直接管理像素

- **原因**：复用 `SkBitmap` 的像素管理、格式转换、子集访问等功能
- **优势**：代码简洁，与位图 API 无缝互操作
- **权衡**：增加了一层间接性，但开销可忽略

### 决策 2：SkCopyPixelsMode 控制拷贝行为

- **原因**：不同场景对性能和安全性需求不同
- **kIfMutable**：平衡性能和安全性（默认策略）
- **kAlways**：安全优先（确保图像不受原位图影响）
- **kNever**：性能优先（要求调用方保证生命周期）

### 决策 3：子集创建总是拷贝像素

```cpp
SkBitmap copy = copy_bitmap_subset(fBitmap, subset);
```

- **原因**：子集图像需要独立生命周期
- **权衡**：性能开销（O(W×H)），但保证正确性
- **替代方案**：`SkBitmap::extractSubset()` 可以浅拷贝，但增加生命周期管理复杂度

### 决策 4：Mipmap 与 PixelRef 分离

```cpp
sk_sp<SkMipmap> fMips;  // 独立管理
```

- **原因**：并非所有图像都需要 Mipmap
- **优势**：节省内存，按需分配
- **权衡**：增加了 `onMakeWithMipmaps()` 的复杂性

### 决策 5：onMakeWithMipmaps 总是深拷贝

```cpp
return SkImage_Raster::MakeFromBitmap(fBitmap, SkCopyPixelsMode::kAlways, std::move(mips));
```

- **原因**：避免多个图像共享 PixelRef 但 Mipmap 不同导致的缓存问题
- **权衡**：内存和性能开销，但确保缓存一致性

### 决策 6：notifyAddedToRasterCache 不调用基类

```cpp
// 显式不调用 INHERITED::notifyAddedToRasterCache
fBitmap.pixelRef()->notifyAddedToCache();
```

- **原因**：栅格图像的缓存应绑定到 PixelRef 生命周期而非图像对象
- **优势**：多个图像共享 PixelRef 时共享缓存
- **注释说明**：这是有意的设计决策

### 决策 7：Alpha-only 图像特殊着色器处理

```cpp
if (SkColorTypeIsAlphaOnly(this->colorType()) && paint.getShader()) {
    s = SkShaders::Blend(SkBlendMode::kDstIn, paint.refShader(), std::move(s));
}
```

- **原因**：Alpha 图像在绘制时应该调制 Paint 颜色而非替换
- **符合规范**：与 `drawImage()` 和 `drawBitmap()` 的行为一致

## 性能考量

### 像素访问性能

**零拷贝访问（最快）**：
```cpp
SkPixmap pm;
if (image->peekPixels(&pm)) {
    // 直接访问像素，无拷贝
}
```

**读取访问（可能有拷贝）**：
```cpp
image->readPixels(dstInfo, dstPixels, dstRowBytes, 0, 0);
// 如果格式匹配：memcpy
// 如果格式不同：格式转换（较慢）
```

### 子集创建开销

**像素拷贝**：
```cpp
// O(W×H) - 线性时间
SkRectMemcpy(dst, ..., subset.height());
```

对于 1000×1000 子集，需要拷贝约 4MB 数据（RGBA32）。

**Mipmap 子集**：
```cpp
// 需要生成新的 Mipmap，开销更大
return tmp->withMipmaps(nullptr);  // 触发 SkMipmap::Build
```

### Mipmap 生成开销

```cpp
SkMipmap::Build(pixmap, nullptr);
```

生成完整 Mipmap 金字塔需要约 33% 的额外内存（1 + 1/4 + 1/16 + ...），以及过滤计算时间。

### 颜色空间转换开销

**格式转换**：
```cpp
dst.writePixels(src);  // 可能触发颜色空间转换
```

每像素需要进行颜色空间矩阵乘法和伽马校正，对大图像开销显著。

**重解释**（快但有限制）：
```cpp
pixmap.setColorSpace(newCS);  // 只改元数据，无像素转换
```

适用于已知像素数据在新颜色空间中正确的场景。

### 内存占用

**基本内存**：
```cpp
W × H × BytesPerPixel + sizeof(SkImage_Raster) + sizeof(SkBitmap) + sizeof(SkPixelRef)
```

**Mipmap 额外内存**：
```cpp
基本内存 × 1.33  // Mipmap 金字塔
```

### 优化建议

1. **使用 peekPixels**：只读访问时避免 `readPixels()`
2. **避免频繁子集**：子集操作需要像素拷贝
3. **按需 Mipmap**：仅在需要时调用 `withMipmaps()`
4. **共享 PixelRef**：使用 `kNever` 模式复用像素数据（注意生命周期）
5. **批量格式转换**：避免重复的颜色空间转换

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/image/SkImage_Base.h` | 基类 | 图像实现基类 |
| `include/core/SkBitmap.h` | 核心依赖 | 像素数据存储 |
| `include/core/SkPixelRef.h` | 像素管理 | 像素内存管理 |
| `src/core/SkMipmap.h` | Mipmap | Mipmap 金字塔 |
| `include/core/SkPixmap.h` | 像素访问 | 像素数据视图 |
| `src/shaders/SkImageShader.h` | 着色器 | 图像着色器 |
| `src/image/SkImage_RasterFactories.cpp` | 工厂函数 | 栅格图像创建函数 |
| `include/core/SkSurface.h` | 表面 | 栅格表面使用此类作为快照 |
