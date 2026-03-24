# SkSurface_Raster

> 源文件：src/image/SkSurface_Raster.h, src/image/SkSurface_Raster.cpp

## 概述

`SkSurface_Raster` 是 Skia 中基于 CPU 内存的栅格绘制表面实现。它提供了一个可绘制的 2D 画布，像素数据直接存储在系统内存中。该类通过 `SkBitmap` 管理像素缓冲区，支持直接像素包装（`WrapPixels`）和自动分配（`Raster`）两种创建方式。作为最基础的表面实现，它支持写时复制（Copy-on-Write, COW）机制，以优化表面快照（`makeImageSnapshot`）的性能。

与 GPU 表面不同，栅格表面的所有绘制操作都在 CPU 上执行，适用于离屏渲染、图像处理、无 GPU 环境等场景。

## 架构位置

`SkSurface_Raster` 在 Skia 架构中的位置：

- **继承关系**：继承自 `SkSurface_Base`（所有表面实现的基类）
- **类型标识**：`SkSurface_Base::Type::kRaster`
- **所属模块**：`src/image/` 图像和表面模块
- **数据存储**：基于 `SkBitmap` 和 `SkPixelRef`
- **绘制设备**：使用 `SkBitmapDevice` 提供 CPU 栅格化

在表面类型层次中，`SkSurface_Raster` 与 Ganesh 表面、Graphite 表面平级，是三种主要表面类型之一。

## 主要类与结构体

### SkSurface_Raster

基于 CPU 内存的栅格表面类。

**成员变量**：
- `fRecorder`：`skcpu::RecorderImpl*` - CPU 录制器实现指针
- `fBitmap`：`SkBitmap` - 像素数据存储
- `fWeOwnThePixels`：`bool` - 是否拥有像素内存（区分 Direct 和 Allocated 模式）

**构造函数**（4 个重载）：
1. 从外部像素创建（带释放回调）
2. 从 `SkPixelRef` 创建
3. 从 Recorder + 外部像素创建
4. 从 Recorder + `SkPixelRef` 创建

**核心方法**：
- `onNewCanvas()`：创建 Canvas
- `onNewImageSnapshot()`：创建快照图像
- `onCopyOnWrite()`：写时复制处理
- `onRestoreBackingMutability()`：恢复像素可变性
- `onWritePixels()`：写入像素
- `onDraw()`：在另一个 Canvas 上绘制此表面

## 公共 API 函数

### SkSurfaces::WrapPixels

```cpp
sk_sp<SkSurface> WrapPixels(const SkImageInfo& info,
                            void* pixels,
                            size_t rowBytes,
                            PixelsReleaseProc releaseProc,
                            void* context,
                            const SkSurfaceProps* props)
```

包装外部像素缓冲区为表面，不拷贝像素。

**参数**：
- `info`：图像信息
- `pixels`：像素缓冲区指针
- `rowBytes`：行字节数
- `releaseProc`：可选的释放回调
- `context`：释放回调上下文
- `props`：表面属性

**返回值**：成功返回表面指针，失败返回 `nullptr`

### SkSurfaces::Raster

```cpp
sk_sp<SkSurface> Raster(const SkImageInfo& info,
                        size_t rowBytes,
                        const SkSurfaceProps* props)
```

分配新的像素缓冲区并创建表面。

### skcpu::Recorder::makeBitmapSurface

```cpp
sk_sp<SkSurface> makeBitmapSurface(const SkImageInfo& imageInfo,
                                   size_t rowBytes,
                                   const SkSurfaceProps* surfaceProps)
```

通过 Recorder 创建栅格表面，支持捕获和记录。

## 内部实现细节

### 构造函数实现

**Direct 模式**（包装外部像素）：
```cpp
SkSurface_Raster::SkSurface_Raster(skcpu::RecorderImpl* recorder,
                                   const SkImageInfo& info,
                                   void* pixels, size_t rowBytes,
                                   void (*releaseProc)(void*, void*),
                                   void* context,
                                   const SkSurfaceProps* props)
    : SkSurface_Base(info, props), fRecorder(recorder) {
    fBitmap.installPixels(info, pixels, rowBytes, releaseProc, context);
    fWeOwnThePixels = false;  // 不拥有像素
}
```

**Allocated 模式**（自行分配像素）：
```cpp
SkSurface_Raster::SkSurface_Raster(skcpu::RecorderImpl* recorder,
                                   const SkImageInfo& info,
                                   sk_sp<SkPixelRef> pr,
                                   const SkSurfaceProps* props)
    : SkSurface_Base(pr->width(), pr->height(), props), fRecorder(recorder) {
    fBitmap.setInfo(info, pr->rowBytes());
    fBitmap.setPixelRef(std::move(pr), 0, 0);
    fWeOwnThePixels = true;  // 拥有像素
}
```

**区别**：`fWeOwnThePixels` 标志控制写时复制行为和快照策略。

### 参数验证

```cpp
bool SkSurfaceValidateRasterInfo(const SkImageInfo& info, size_t rowBytes) {
    if (!SkImageInfoIsValid(info)) return false;
    if (kIgnoreRowBytesValue == rowBytes) return true;
    if (!info.validRowBytes(rowBytes)) return false;

    uint64_t size = sk_64_mul(info.height(), rowBytes);
    static const size_t kMaxTotalSize = SK_MaxS32;
    if (size > kMaxTotalSize) return false;  // 防止溢出

    return true;
}
```

验证图像信息和行字节数的有效性，防止整数溢出和无效参数。

### Canvas 创建

```cpp
SkCanvas* SkSurface_Raster::onNewCanvas() {
    SkASSERT(fRecorder);
    return new SkCanvas(sk_make_sp<SkBitmapDevice>(fRecorder, fBitmap, this->props()));
}
```

创建基于 `SkBitmapDevice` 的 Canvas，将绘制操作直接应用到 `fBitmap`。

### 快照创建

**完整快照**（最常见）：
```cpp
sk_sp<SkImage> SkSurface_Raster::onNewImageSnapshot(const SkIRect* subset) {
    if (!subset) {
        SkCopyPixelsMode cpm = SkCopyPixelsMode::kIfMutable;
        if (fWeOwnThePixels) {
            // 标记为临时不可变以支持 COW
            if (SkPixelRef* pr = fBitmap.pixelRef()) {
                pr->setTemporarilyImmutable();
            }
        } else {
            // Direct 模式总是拷贝（外部可能修改）
            cpm = SkCopyPixelsMode::kAlways;
        }
        return SkImage_Raster::MakeFromBitmap(fBitmap, cpm);
    }
    // 子集快照逻辑...
}
```

**关键策略**：
- **Allocated 模式**：标记 PixelRef 为临时不可变，启用 COW
- **Direct 模式**：总是拷贝像素，因为外部可能修改缓冲区

**子集快照**：
```cpp
if (subset) {
    SkBitmap dst;
    dst.allocPixels(fBitmap.info().makeDimensions(subset->size()));
    SkAssertResult(fBitmap.readPixels(dst.pixmap(), subset->left(), subset->top()));
    dst.setImmutable();
    return dst.asImage();
}
```

子集快照总是拷贝像素。

### 写时复制（COW）

```cpp
bool SkSurface_Raster::onCopyOnWrite(ContentChangeMode mode) {
    sk_sp<SkImage> cached(this->refCachedImage());
    SkASSERT(cached);

    // 检查是否与快照共享 PixelRef
    if (static_cast<SkImage_Raster*>(cached.get())->getPixelRef() == fBitmap.pixelRef()) {
        SkASSERT(fWeOwnThePixels);

        if (kDiscard_ContentChangeMode == mode) {
            // 丢弃模式：直接分配新缓冲区
            if (!fBitmap.tryAllocPixels()) {
                return false;
            }
        } else {
            // 保留模式：拷贝像素到新缓冲区
            SkBitmap prev(fBitmap);
            if (!fBitmap.tryAllocPixels()) {
                return false;
            }
            memcpy(fBitmap.getPixels(), prev.getPixels(), fBitmap.computeByteSize());
        }

        // 更新 Canvas 的后端位图
        SkBitmapDevice* bmDev = static_cast<SkBitmapDevice*>(
            this->getCachedCanvas()->rootDevice());
        bmDev->replaceBitmapBackendForRasterSurface(fBitmap);
    }
    return true;
}
```

**COW 触发条件**：
1. 存在外部持有的快照图像（`!cached->unique()`）
2. 快照与表面共享同一 PixelRef

**COW 操作**：
1. 分配新的像素缓冲区
2. 可选地拷贝旧像素（取决于 `ContentChangeMode`）
3. 更新 Canvas 设备的后端位图

### 可变性恢复

```cpp
void SkSurface_Raster::onRestoreBackingMutability() {
    SkASSERT(!this->hasCachedImage());  // 确保没有快照
    if (SkPixelRef* pr = fBitmap.pixelRef()) {
        pr->restoreMutability();
    }
}
```

当快照被释放且不需要 COW 时，恢复 PixelRef 的可变性标记。

### 像素写入

```cpp
void SkSurface_Raster::onWritePixels(const SkPixmap& src, int x, int y) {
    fBitmap.writePixels(src, x, y);
}
```

直接委托给 `SkBitmap::writePixels()`，支持格式转换。

### 绘制到 Canvas

```cpp
void SkSurface_Raster::onDraw(SkCanvas* canvas, SkScalar x, SkScalar y,
                              const SkSamplingOptions& sampling, const SkPaint* paint) {
    canvas->drawImage(fBitmap.asImage().get(), x, y, sampling, paint);
}
```

将表面内容作为图像绘制到目标 Canvas。

## 依赖关系

### 核心依赖

| 依赖项 | 用途 |
|--------|------|
| `SkSurface_Base` | 基类，表面实现框架 |
| `SkBitmap` | 像素数据存储 |
| `SkBitmapDevice` | CPU 绘制设备 |
| `SkPixelRef` | 像素内存管理 |
| `SkImage_Raster` | 快照图像类型 |

### 次要依赖

| 依赖项 | 用途 |
|--------|------|
| `SkCanvas` | 绘制接口 |
| `SkImageInfo` | 图像格式描述 |
| `SkMallocPixelRef` | 堆分配像素 |
| `skcpu::RecorderImpl` | CPU 录制器实现 |

### 反向依赖

| 依赖方 | 用途 |
|--------|------|
| `SkSurfaces::WrapPixels()` | 工厂函数 |
| `SkSurfaces::Raster()` | 工厂函数 |
| `skcpu::Recorder::makeBitmapSurface()` | 创建表面 |

## 设计模式与设计决策

### 决策 1：区分 Direct 和 Allocated 模式

- **Direct 模式**（`fWeOwnThePixels = false`）：
  - 包装外部像素，不负责释放
  - 快照总是拷贝像素（外部可能修改）
  - 不支持 COW

- **Allocated 模式**（`fWeOwnThePixels = true`）：
  - 自行分配和管理像素
  - 快照使用 COW 优化
  - 支持临时不可变标记

### 决策 2：临时不可变标记启用 COW

```cpp
pr->setTemporarilyImmutable();
```

- **原因**：`SkImage_Raster` 要求像素不可变，但表面需要可绘制
- **机制**：快照时标记不可变，绘制前检查是否需要 COW
- **恢复**：快照释放后调用 `restoreMutability()`

### 决策 3：子集快照总是拷贝

- **原因**：子集需要独立的像素缓冲区
- **权衡**：性能开销，但简化实现

### 决策 4：Direct 模式总是拷贝快照

```cpp
cpm = SkCopyPixelsMode::kAlways;
```

- **原因**：无法控制外部缓冲区的生命周期
- **权衡**：牺牲性能换取安全性

### 决策 5：COW 时更新 Canvas 设备

```cpp
bmDev->replaceBitmapBackendForRasterSurface(fBitmap);
```

- **原因**：Canvas 持有对旧位图的引用
- **必要性**：确保后续绘制应用到新缓冲区

### 决策 6：参数验证防止整数溢出

```cpp
uint64_t size = sk_64_mul(info.height(), rowBytes);
if (size > kMaxTotalSize) return false;
```

- **原因**：大尺寸图像可能导致整数溢出
- **安全性**：使用 64 位乘法检测溢出

## 性能考量

### 快照性能

**COW 优化**（Allocated 模式）：
```cpp
// 第一次快照：O(1)
sk_sp<SkImage> img1 = surface->makeImageSnapshot();
// 不修改表面时，额外快照也是 O(1)
sk_sp<SkImage> img2 = surface->makeImageSnapshot();
```

**拷贝路径**（Direct 模式或 COW 触发）：
```cpp
// O(W×H) - 拷贝所有像素
memcpy(fBitmap.getPixels(), prev.getPixels(), fBitmap.computeByteSize());
```

### COW 触发成本

第一次绘制触发 COW 时：
1. 分配新缓冲区：O(W×H) 内存分配
2. 拷贝像素：O(W×H) memcpy
3. 更新 Canvas 设备：O(1)

对于大表面（如 4K 图像），这可能是显著开销。

### 内存占用

**基本内存**：
```cpp
W × H × BytesPerPixel + sizeof(SkSurface_Raster) + sizeof(SkBitmap)
```

**COW 后内存**：
```cpp
2 × (W × H × BytesPerPixel)  // 表面 + 快照各占一份
```

### 优化建议

1. **使用 Allocated 模式**：充分利用 COW 优化
2. **避免频繁快照**：每次快照后绘制都会触发 COW
3. **考虑快照生命周期**：及时释放快照以恢复可变性
4. **丢弃模式**：如果不需要保留内容，使用 `kDiscard_ContentChangeMode`

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/image/SkSurface_Base.h` | 基类 | 表面实现基类 |
| `include/core/SkBitmap.h` | 核心依赖 | 像素数据存储 |
| `src/core/SkBitmapDevice.h` | 绘制设备 | CPU 栅格化设备 |
| `src/image/SkImage_Raster.h` | 快照类型 | 栅格图像实现 |
| `include/core/SkPixelRef.h` | 像素管理 | 像素内存管理 |
| `include/core/SkSurface.h` | 公共接口 | 表面公共 API |
| `src/core/SkCPURecorderImpl.h` | 录制器 | CPU 录制器实现 |
