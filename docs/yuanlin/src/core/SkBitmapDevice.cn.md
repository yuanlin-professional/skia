# SkBitmapDevice

> 源文件: src/core/SkBitmapDevice.h, src/core/SkBitmapDevice.cpp

## 概述

`SkBitmapDevice` 是 Skia 光栅渲染后端的核心设备类,实现了基于 CPU 的位图绘制能力。作为 `SkDevice` 的具体实现,它提供完整的 2D 图形绘制操作,包括形状、文本、图像等的光栅化。该设备支持大尺寸位图的分块绘制、抗锯齿裁剪、特殊图像处理等高级特性。

## 架构位置

```
src/core/
  ├── SkBitmapDevice.cpp       # 位图设备实现
  ├── SkBitmapDevice.h         # 设备类定义
  ├── SkDevice.h               # 抽象设备基类
  ├── SkDraw.cpp               # 绘制核心逻辑
  └── SkRasterClipStack.h      # 光栅裁剪栈
```

本模块位于 Skia 设备抽象层,是 CPU 渲染的主要实现,与 GPU 设备(如 GaneshDevice)并列。

## 主要类与结构体

### SkBitmapDevice

| **属性** | **说明** |
|---------|---------|
| **继承关系** | `SkBitmapDevice` → `SkDevice` → `SkRefCnt` |
| **作用** | 基于位图的光栅渲染设备 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBitmap` | `SkBitmap` | 后端像素缓冲区 |
| `fRCStack` | `SkRasterClipStack` | 光栅裁剪栈 |
| `fGlyphPainter` | `skcpu::GlyphRunListPainter` | 文本渲染器 |
| `fRasterHandle` | `void*` | 外部光栅句柄 |
| `fRecorder` | `skcpu::RecorderImpl*` | CPU 记录器 |

### SkDrawTiler

**内部辅助类,处理大尺寸位图分块:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDevice` | `SkBitmapDevice*` | 目标设备 |
| `fRootPixmap` | `SkPixmap` | 完整像素映射 |
| `fDraw` | `skcpu::Draw` | 当前绘制上下文 |
| `fNeedsTiling` | `bool` | 是否需要分块 |
| `kMaxDim` | 常量 | 最大维度 8191 |

## 公共 API 函数

### 构造与创建

```cpp
explicit SkBitmapDevice(const SkBitmap& bitmap);
SkBitmapDevice(const SkBitmap& bitmap, const SkSurfaceProps& surfaceProps,
               void* externalHandle = nullptr);

static sk_sp<SkBitmapDevice> Create(const SkImageInfo& info,
                                     const SkSurfaceProps& props,
                                     SkRasterHandleAllocator* allocator = nullptr);
```

**功能:** 创建位图设备,支持自定义分配器和表面属性。

### 绘制操作

```cpp
void drawPaint(const SkPaint& paint) override;
void drawPoints(SkCanvas::PointMode mode, SkSpan<const SkPoint> pts, const SkPaint&) override;
void drawRect(const SkRect& r, const SkPaint& paint) override;
void drawOval(const SkRect& oval, const SkPaint& paint) override;
void drawRRect(const SkRRect& rr, const SkPaint& paint) override;
void drawPath(const SkPath& path, const SkPaint& paint) override;
void drawImageRect(const SkImage* img, const SkRect* src, const SkRect& dst,
                   const SkSamplingOptions& sampling, const SkPaint& paint,
                   SkCanvas::SrcRectConstraint constraint) override;
```

**功能:** 实现各种图形元素的光栅化绘制。

### 裁剪操作

```cpp
void pushClipStack() override;
void popClipStack() override;
void clipRect(const SkRect& rect, SkClipOp op, bool aa) override;
void clipRRect(const SkRRect& rrect, SkClipOp op, bool aa) override;
void clipPath(const SkPath& path, SkClipOp op, bool aa) override;
void clipRegion(const SkRegion& deviceRgn, SkClipOp op) override;
void replaceClip(const SkIRect& rect) override;
```

**功能:** 管理裁剪区域,支持抗锯齿裁剪。

### 像素访问

```cpp
bool onReadPixels(const SkPixmap& pm, int x, int y) override;
bool onWritePixels(const SkPixmap& pm, int x, int y) override;
bool onPeekPixels(SkPixmap* pmap) override;
bool onAccessPixels(SkPixmap* pmap) override;
```

**功能:** 直接读写设备像素数据。

## 内部实现细节

### 大尺寸位图分块机制

```cpp
class SkDrawTiler {
    static constexpr int kMaxDim = 8192 - 1;  // 避免 SkFixed 溢出

    bool NeedsTiling(SkBitmapDevice* dev) {
        return dev->width() > kMaxDim || dev->height() > kMaxDim;
    }

    void stepAndSetupTileDraw() {
        // 8K × 8K 分块遍历
        if (fOrigin.fX >= fSrcBounds.fRight - kMaxDim) {
            fOrigin.fX = fSrcBounds.fLeft;
            fOrigin.fY += kMaxDim;
        } else {
            fOrigin.fX += kMaxDim;
        }

        // 提取子像素映射
        SkIRect bounds = SkIRect::MakeXYWH(fOrigin.x(), fOrigin.y(), kMaxDim, kMaxDim);
        fRootPixmap.extractSubset(&fDraw.fDst, bounds);

        // 调整变换矩阵和裁剪
        fTileMatrix = fDevice->localToDevice();
        fTileMatrix->postTranslate(-fOrigin.x(), -fOrigin.y());
        fDevice->fRCStack.rc().translate(-fOrigin.x(), -fOrigin.y(), &fTileRC);
    }
};
```

**设计目的:** `SkFixed` 使用 16.16 定点数,超过 8K 会溢出,分块确保精度。

### 绘制宏 LOOP_TILER

```cpp
#define LOOP_TILER(code, boundsPtr) \
    SkDrawTiler priv_tiler(this, boundsPtr); \
    while (const skcpu::Draw* priv_draw = priv_tiler.next()) { \
        priv_draw->code; \
    }

// 使用示例
void SkBitmapDevice::drawRect(const SkRect& r, const SkPaint& paint) {
    LOOP_TILER(drawRect(r, paint), Bounder(r, paint))
}
```

**优势:** 自动处理分块逻辑,统一绘制接口。

### 图像绘制优化

```cpp
void SkBitmapDevice::drawImageRect(...) {
    // 1. 快速路径判断
    if (CanApplyDstMatrixAsCTM(matrix, paint)) {
        this->drawBitmap(bitmap, matrix, &dst, sampling, paint, mips);
        return;
    }

    // 2. 回退到着色器路径
    auto shader = img->makeShaderForPaint(paint, SkTileMode::kClamp,
                                          SkTileMode::kClamp, sampling, &matrix);
    SkPaint paintWithShader(paint);
    paintWithShader.setShader(std::move(shader));
    this->drawRect(dst, paintWithShader);
}
```

**条件:** 无 MaskFilter 或仅平移变换时,直接位图绘制更高效。

### 裁剪栈管理

```cpp
void SkBitmapDevice::clipRect(const SkRect& rect, SkClipOp op, bool aa) {
    fRCStack.clipRect(this->localToDevice(), rect, op, aa);
}

bool SkBitmapDevice::isClipWideOpen() const {
    const SkRasterClip& rc = fRCStack.rc();
    return rc.isBW() && rc.bwRgn().isRect() &&
           rc.bwRgn().getBounds() == SkIRect{0, 0, this->width(), this->height()};
}
```

**光栅裁剪栈特性:**
- 支持 BW(黑白)和 AA(抗锯齿)两种模式
- 自动优化全屏裁剪为空操作

### 特殊图像处理

```cpp
void SkBitmapDevice::drawSpecial(SkSpecialImage* src, const SkMatrix& localToDevice,
                                 const SkSamplingOptions& sampling, const SkPaint& paint,
                                 SkCanvas::SrcRectConstraint) {
    SkBitmap resultBM;
    if (SkSpecialImages::AsBitmap(src, &resultBM)) {
        skcpu::Draw draw;
        draw.fDst = &fPixmap;
        draw.fCTM = &localToDevice;
        draw.fRC = &fRCStack.rc();
        draw.drawBitmap(resultBM, SkMatrix::I(), nullptr, sampling, paint, nullptr);
    }
}
```

**用途:** 处理图像滤镜的输出,绕过通用管线。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBitmap` | 像素存储 |
| `SkRasterClipStack` | 裁剪管理 |
| `skcpu::Draw` | 核心绘制逻辑 |
| `skcpu::GlyphRunListPainter` | 文本渲染 |
| `SkSpecialImage` | 特殊图像处理 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkSurface_Raster` | 创建光栅表面 |
| `SkCanvas` | 设备绘制目标 |
| `SkPictureRecorder` | 记录绘制命令 |

## 设计模式与设计决策

### 1. 模板方法模式

`SkDevice` 定义绘制接口,`SkBitmapDevice` 实现具体算法。

### 2. 迭代器模式

`SkDrawTiler` 提供分块迭代:
```cpp
while (const skcpu::Draw* draw = tiler.next()) {
    draw->drawRect(r, paint);
}
```

### 3. 桥接模式

通过 `SkRasterClipStack` 隔离裁剪实现,支持不同裁剪策略。

### 4. 享元模式

共享 `fBitmap` 的像素引用,多个设备可引用同一内存。

### 5. 策略模式

根据 `SkPaint` 的 `MaskFilter` 选择不同的渲染路径。

## 性能考量

### 分块绘制

**单块:** 直接操作完整位图,无额外开销
**多块:** 8K × 8K 分块,避免固定点溢出,内存访问友好

### 快速路径检测

```cpp
bool CanApplyDstMatrixAsCTM(const SkMatrix& m, const SkPaint& paint) {
    if (!paint.getMaskFilter()) return true;
    return m.getType() <= SkMatrix::kTranslate_Mask;
}
```

跳过着色器构建,直接位图拷贝。

### 裁剪优化

```cpp
if (isClipWideOpen()) {
    // 无裁剪,跳过边界检查
}
if (isClipEmpty()) {
    // 空裁剪,跳过所有绘制
}
```

### 内存对齐

使用 `SkPixmap` 确保行字节对齐,提升缓存命中率。

### 像素格式转换

优先使用原生格式 `kN32_SkColorType`,减少转换开销。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkDevice.h` | 抽象设备基类 |
| `src/core/SkDraw.cpp` | 核心绘制实现 |
| `src/core/SkRasterClip.h` | 光栅裁剪 |
| `src/core/SkRasterClipStack.h` | 裁剪栈 |
| `include/core/SkBitmap.h` | 位图类 |
| `src/core/SkGlyphRunPainter.h` | 文本渲染 |
| `src/core/SkSpecialImage.h` | 特殊图像 |
| `include/core/SkSurface.h` | 绘图表面 |
