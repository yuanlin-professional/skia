# SkBitmap

> 源文件: include/core/SkBitmap.h, src/core/SkBitmap.cpp

## 概述

`SkBitmap` 是 Skia 中描述二维光栅像素数组的核心类。它基于 `SkImageInfo` 构建,包含宽度、高度、颜色类型、透明度类型和颜色空间等信息,并通过 `SkPixelRef` 引用实际的像素内存。`SkBitmap` 提供灵活的像素容器能力,支持多种分配策略、像素操作、子集提取和图像转换等功能,是 Skia 光栅图形处理的基础数据结构。

## 架构位置

```
include/core/
  ├── SkBitmap.h         # 位图类公共接口
  ├── SkPixmap.h         # 像素映射(只读视图)
  ├── SkImageInfo.h      # 图像信息描述
  └── SkPixelRef.h       # 像素引用计数

src/core/
  └── SkBitmap.cpp       # 位图实现
```

本模块位于 Skia 图像抽象层,作为可修改的像素容器,与只读的 `SkImage` 和无所有权的 `SkPixmap` 形成互补。

## 主要类与结构体

### SkBitmap

| **属性** | **说明** |
|---------|---------|
| **继承关系** | 独立类,无继承 |
| **作用** | 可修改的二维像素数组容器 |
| **线程安全** | 否,每个线程需要独立副本(像素数据可共享) |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPixelRef` | `sk_sp<SkPixelRef>` | 像素数据引用(共享所有权) |
| `fPixmap` | `SkPixmap` | 像素映射(地址+行字节+ImageInfo) |

### SkBitmap::Allocator

**抽象分配器基类:**

```cpp
class Allocator : public SkRefCnt {
public:
    virtual bool allocPixelRef(SkBitmap* bitmap) = 0;
};
```

### SkBitmap::HeapAllocator

**默认堆分配器:**

| **属性** | **说明** |
|---------|---------|
| **继承关系** | `HeapAllocator` → `Allocator` → `SkRefCnt` |
| **作用** | 使用系统堆分配像素内存 |

## 公共 API 函数

### 构造与析构

```cpp
SkBitmap();  // 空位图
SkBitmap(const SkBitmap& src);  // 共享像素引用
SkBitmap(SkBitmap&& src);  // 移动语义
~SkBitmap();
```

### 基本属性访问

```cpp
const SkImageInfo& info() const;
int width() const;
int height() const;
SkColorType colorType() const;
SkAlphaType alphaType() const;
SkColorSpace* colorSpace() const;
size_t rowBytes() const;
bool empty() const;  // 宽高为零
bool isNull() const;  // 无 PixelRef
bool drawsNothing() const;  // empty() || isNull()
```

### 配置与重置

```cpp
bool setInfo(const SkImageInfo& imageInfo, size_t rowBytes = 0);
bool setAlphaType(SkAlphaType alphaType);
void setColorSpace(sk_sp<SkColorSpace> colorSpace);
void reset();  // 重置为空状态
```

### 内存分配

```cpp
// 尝试分配(返回成功与否)
[[nodiscard]] bool tryAllocPixels(const SkImageInfo& info, size_t rowBytes = 0);
[[nodiscard]] bool tryAllocPixels(Allocator* allocator = nullptr);
[[nodiscard]] bool tryAllocN32Pixels(int width, int height, bool isOpaque = false);

// 强制分配(失败则 abort)
void allocPixels(const SkImageInfo& info, size_t rowBytes = 0);
void allocPixels(Allocator* allocator = nullptr);
void allocN32Pixels(int width, int height, bool isOpaque = false);
```

### 像素安装

```cpp
bool installPixels(const SkImageInfo& info, void* pixels, size_t rowBytes,
                   void (*releaseProc)(void*, void*) = nullptr, void* context = nullptr);
bool installPixels(const SkPixmap& pixmap);
void setPixels(void* pixels);  // 简化版,无释放回调
```

### PixelRef 管理

```cpp
SkPixelRef* pixelRef() const;
SkIPoint pixelRefOrigin() const;
void setPixelRef(sk_sp<SkPixelRef> pr, int dx, int dy);
uint32_t getGenerationID() const;
void notifyPixelsChanged() const;
```

### 像素访问

```cpp
void* getPixels() const;
void* getAddr(int x, int y) const;
uint32_t* getAddr32(int x, int y) const;
uint16_t* getAddr16(int x, int y) const;
uint8_t* getAddr8(int x, int y) const;

SkColor getColor(int x, int y) const;
SkColor4f getColor4f(int x, int y) const;
float getAlphaf(int x, int y) const;
```

### 像素操作

```cpp
void eraseColor(SkColor4f c) const;
void eraseColor(SkColor c) const;
void erase(SkColor4f c, const SkIRect& area) const;

bool readPixels(const SkImageInfo& dstInfo, void* dstPixels, size_t dstRowBytes,
                int srcX, int srcY) const;
bool readPixels(const SkPixmap& dst, int srcX = 0, int srcY = 0) const;

bool writePixels(const SkPixmap& src, int dstX = 0, int dstY = 0);
```

### 子集与变换

```cpp
bool extractSubset(SkBitmap* dst, const SkIRect& subset) const;
bool extractAlpha(SkBitmap* dst, const SkPaint* paint = nullptr,
                  Allocator* allocator = nullptr, SkIPoint* offset = nullptr) const;
```

### 图像转换

```cpp
sk_sp<SkImage> asImage() const;
sk_sp<SkShader> makeShader(SkTileMode tmx, SkTileMode tmy,
                           const SkSamplingOptions& sampling,
                           const SkMatrix* localMatrix = nullptr) const;
bool peekPixels(SkPixmap* pixmap) const;
```

### 不可变性

```cpp
bool isImmutable() const;
void setImmutable();  // 标记为不可变,不可逆
```

### 不透明性检测

```cpp
bool isOpaque() const;
static bool ComputeIsOpaque(const SkBitmap& bm);
```

## 内部实现细节

### 内存布局

```
SkBitmap
  ├── fPixelRef (sk_sp<SkPixelRef>)
  │   └── 共享的像素内存块
  └── fPixmap (SkPixmap)
      ├── fInfo (SkImageInfo): 宽高、颜色类型、透明度、色彩空间
      ├── fPixels (void*): 指向 fPixelRef 中的某个偏移
      └── fRowBytes (size_t): 行字节数
```

### PixelRef 偏移计算

```cpp
SkIPoint SkBitmap::pixelRefOrigin() const {
    const char* addr = (const char*)fPixmap.addr();
    const char* pix = (const char*)(fPixelRef ? fPixelRef->pixels() : nullptr);
    size_t rb = this->rowBytes();
    size_t off = addr - pix;
    return {SkToS32((off % rb) >> this->shiftPerPixel()), SkToS32(off / rb)};
}
```

**用途:** 支持多个 `SkBitmap` 共享同一 `SkPixelRef` 的不同区域。

### 子集提取机制

```cpp
bool SkBitmap::extractSubset(SkBitmap* result, const SkIRect& subset) const {
    SkIRect srcRect, r;
    srcRect.setWH(this->width(), this->height());
    if (!r.intersect(srcRect, subset)) return false;

    SkBitmap dst;
    dst.setInfo(this->info().makeDimensions(r.size()), this->rowBytes());

    if (fPixelRef) {
        SkIPoint origin = this->pixelRefOrigin();
        dst.setPixelRef(fPixelRef, origin.x() + r.fLeft, origin.y() + r.fTop);
    }
    result->swap(dst);
    return true;
}
```

**优势:** 零拷贝,仅调整偏移量。

### Alpha 提取流程

```cpp
bool SkBitmap::extractAlpha(SkBitmap* dst, const SkPaint* paint,
                            Allocator* allocator, SkIPoint* offset) const {
    SkMaskBuilder srcM, dstM;
    srcM.bounds().setWH(this->width(), this->height());
    srcM.format() = SkMask::kA8_Format;

    SkMaskFilter* filter = paint ? paint->getMaskFilter() : nullptr;
    if (filter) {
        // 应用 MaskFilter 扩展边界
        if (!as_MFB(filter)->filterMask(&dstM, srcM, identity, nullptr)) {
            goto NO_FILTER_CASE;
        }
    }

    // 转换为 A8 格式
    GetBitmapAlpha(*this, tmpBitmap.getAddr8(0, 0), srcM.fRowBytes);
    tmpBitmap.swap(*dst);
    return true;
}
```

**应用:** 生成阴影、发光等效果的 Alpha 蒙版。

### 不可变性实现

```cpp
void SkBitmap::setImmutable() {
    if (fPixelRef) {
        fPixelRef->setImmutable();
    }
}

void SkBitmap::notifyPixelsChanged() const {
    SkASSERT(!this->isImmutable());
    if (fPixelRef) {
        fPixelRef->notifyPixelsChanged();
    }
}
```

**设计:** 不可变性由 `SkPixelRef` 强制,所有共享同一 `PixelRef` 的位图受影响。

### 像素格式验证

```cpp
bool SkBitmap::setAlphaType(SkAlphaType newAlphaType) {
    if (!SkColorTypeValidateAlphaType(this->colorType(), newAlphaType, &newAlphaType)) {
        return false;
    }
    if (this->alphaType() != newAlphaType) {
        fPixmap.reset(fPixmap.info().makeAlphaType(newAlphaType),
                     fPixmap.addr(), fPixmap.rowBytes());
    }
    return true;
}
```

**规则:**
- `kRGB_565`, `kGray_8`: 强制 `kOpaque`
- `kAlpha_8`: 不允许 `kUnpremul`,自动转为 `kPremul`

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPixelRef` | 像素内存管理 |
| `SkPixmap` | 像素只读视图 |
| `SkImageInfo` | 图像格式描述 |
| `SkMallocPixelRef` | 默认堆分配实现 |
| `SkMask` | Alpha 提取 |
| `SkImage_Raster` | 转换为 Image |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkCanvas` | 绘制目标 |
| `SkImageShader` | 位图着色器 |
| `SkBitmapDevice` | 渲染后端 |
| `SkCodec` | 图像解码输出 |
| `SkSurface` | 表面像素访问 |

## 设计模式与设计决策

### 1. 写时复制 (Copy-on-Write)

共享 `SkPixelRef` 直到修改时才复制,节省内存。

### 2. 句柄-主体模式 (Handle-Body)

`SkBitmap` 是轻量级句柄,`SkPixelRef` 是重量级主体。

### 3. 策略模式

通过 `Allocator` 接口支持自定义内存分配策略。

### 4. 不可变对象

`setImmutable()` 后,像素变为只读,优化缓存和线程安全。

### 5. 空对象模式

空位图 (`isNull()`) 可正常操作,无需空指针检查。

## 性能考量

### 内存共享

```cpp
SkBitmap bm1, bm2;
bm1.allocN32Pixels(100, 100);
bm2 = bm1;  // 共享像素,无拷贝
```

### 子集零拷贝

```cpp
bm2.extractSubset(&bm1, SkIRect::MakeXYWH(10, 10, 50, 50));  // 仅调整偏移
```

### 像素格式优化

优先使用原生格式 `kN32_SkColorType` (=`kBGRA_8888` 或 `kRGBA_8888`),避免转换。

### 行字节对齐

```cpp
size_t rowBytes = info.minRowBytes();
rowBytes = SkAlign4(rowBytes);  // 4 字节对齐,提升缓存性能
```

### 不可变性优化

不可变位图可:
- 安全地跨线程共享
- 作为缓存键
- 触发 GPU 纹理上传

### 延迟分配

```cpp
bm.setInfo(info);  // 仅设置格式
// ... 稍后再 allocPixels()
```

允许先配置,后分配,节省不需要的内存。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkImageInfo.h` | 图像格式描述 |
| `include/core/SkPixelRef.h` | 像素引用接口 |
| `include/core/SkPixmap.h` | 只读像素视图 |
| `include/core/SkMallocPixelRef.h` | 堆分配实现 |
| `include/core/SkImage.h` | 不可变图像 |
| `src/core/SkConvertPixels.cpp` | 像素格式转换 |
| `src/image/SkImage_Raster.h` | 光栅图像实现 |
| `src/core/SkMask.h` | Alpha 蒙版 |
