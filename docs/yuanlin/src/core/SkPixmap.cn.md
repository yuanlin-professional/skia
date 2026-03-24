# SkPixmap

> 源文件
> - include/core/SkPixmap.h
> - src/core/SkPixmap.cpp

## 概述

`SkPixmap` 是 Skia 中用于配对像素数据和图像信息（`SkImageInfo`）的实用工具类。它是一个轻量级、非所有权的像素视图，提供便捷的像素访问、读写、颜色查询和像素操作功能。`SkPixmap` 不管理像素内存的生命周期，仅持有指针引用。

与 `SkBitmap` 不同，`SkPixmap` 不能直接绘制到 Canvas 上，也不提供绘制目标。它专注于像素级别的数据访问和处理，常用于像素格式转换、颜色查询、像素擦除等底层操作。

## 架构位置

`SkPixmap` 位于 Skia 核心图形层的像素处理层：

- 被 `SkBitmap` 使用来暴露像素访问接口
- 与 `SkImageInfo` 紧密配合描述像素格式
- 使用 `SkConvertPixels` 进行格式转换
- 提供 `SkSurface` 和 `SkBitmap` 的底层像素操作

## 主要类与结构体

### SkPixmap

像素映射类。

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fPixels | const void* | 像素数据指针 |
| fRowBytes | size_t | 行字节数 |
| fInfo | SkImageInfo | 图像信息（宽高、颜色类型等） |

## 公共 API 函数

### 构造与重置

```cpp
// 默认构造（空 Pixmap）
SkPixmap();

// 构造函数
SkPixmap(const SkImageInfo& info, const void* addr, size_t rowBytes);

// 重置为空
void reset();

// 重置为新数据
void reset(const SkImageInfo& info, const void* addr, size_t rowBytes);

// 从掩码重置（已废弃）
[[nodiscard]] bool reset(const SkMask& mask);

// 修改颜色空间
void setColorSpace(sk_sp<SkColorSpace> colorSpace);
```

### 信息访问

```cpp
const SkImageInfo& info() const;    // 图像信息
size_t rowBytes() const;            // 行字节数
const void* addr() const;           // 像素基址
int width() const;                  // 宽度
int height() const;                 // 高度
SkISize dimensions() const;         // 尺寸
SkColorType colorType() const;      // 颜色类型
SkAlphaType alphaType() const;      // Alpha类型
SkColorSpace* colorSpace() const;   // 颜色空间
sk_sp<SkColorSpace> refColorSpace() const;
bool isOpaque() const;              // 是否不透明
SkIRect bounds() const;             // 边界矩形
```

### 子集提取

```cpp
// 提取子矩形的 Pixmap
[[nodiscard]] bool extractSubset(SkPixmap* subset, const SkIRect& area) const;
```

### 像素地址访问

```cpp
// 通用访问（需要类型转换）
const void* addr(int x, int y) const;
void* writable_addr() const;
void* writable_addr(int x, int y) const;

// 类型化访问（8位）
const uint8_t* addr8() const;
const uint8_t* addr8(int x, int y) const;
uint8_t* writable_addr8(int x, int y) const;

// 类型化访问（16位）
const uint16_t* addr16() const;
const uint16_t* addr16(int x, int y) const;
uint16_t* writable_addr16(int x, int y) const;

// 类型化访问（32位）
const uint32_t* addr32() const;
const uint32_t* addr32(int x, int y) const;
uint32_t* writable_addr32(int x, int y) const;

// 类型化访问（64位）
const uint64_t* addr64() const;
const uint64_t* addr64(int x, int y) const;
uint64_t* writable_addr64(int x, int y) const;

// F16访问
const uint16_t* addrF16() const;
const uint16_t* addrF16(int x, int y) const;
uint16_t* writable_addrF16(int x, int y) const;
```

### 颜色查询

```cpp
// 获取单个像素的颜色
SkColor getColor(int x, int y) const;
SkColor4f getColor4f(int x, int y) const;

// 获取Alpha值
float getAlphaf(int x, int y) const;
```

### 像素读取

```cpp
// 读取像素到目标
bool readPixels(const SkImageInfo& dstInfo,
                void* dstPixels,
                size_t dstRowBytes) const;

bool readPixels(const SkImageInfo& dstInfo,
                void* dstPixels,
                size_t dstRowBytes,
                int srcX, int srcY) const;

bool readPixels(const SkPixmap& dst, int srcX, int srcY) const;
bool readPixels(const SkPixmap& dst) const;
```

### 像素缩放

```cpp
// 缩放像素到目标
bool scalePixels(const SkPixmap& dst,
                 const SkSamplingOptions& sampling) const;
```

### 像素擦除

```cpp
// 擦除指定颜色
bool erase(SkColor color, const SkIRect& subset) const;
bool erase(SkColor color) const;
bool erase(const SkColor4f& color, const SkIRect* subset = nullptr) const;
```

### 不透明度计算

```cpp
// 计算所有像素是否不透明
bool computeIsOpaque() const;
```

### 辅助函数

```cpp
// 行像素数
int rowBytesAsPixels() const;

// 每像素位移量
int shiftPerPixel() const;

// 计算字节大小
size_t computeByteSize() const;
```

## 内部实现细节

### 颜色查询实现

`getColor()` 根据颜色类型解析像素：

```cpp
SkColor SkPixmap::getColor(int x, int y) const {
    SkASSERT(this->addr());
    SkASSERT((unsigned)x < (unsigned)this->width());
    SkASSERT((unsigned)y < (unsigned)this->height());

    const bool needsUnpremul = (kPremul_SkAlphaType == fInfo.alphaType());

    switch (this->colorType()) {
        case kGray_8_SkColorType: {
            uint8_t value = *this->addr8(x, y);
            return SkColorSetRGB(value, value, value);
        }
        case kAlpha_8_SkColorType: {
            return SkColorSetA(0, *this->addr8(x, y));
        }
        case kRGB_565_SkColorType: {
            return SkPixel16ToColor(*this->addr16(x, y));
        }
        case kRGBA_8888_SkColorType: {
            uint32_t value = *this->addr32(x, y);
            SkPMColor c = SkSwizzle_RGBA_to_PMColor(value);
            return needsUnpremul ? SkUnPreMultiply::PMColorToColor(c) : c;
        }
        case kRGBA_F16_SkColorType: {
            const uint64_t* addr = (const uint64_t*)fPixels +
                                   y * (fRowBytes >> 3) + x;
            skvx::float4 p4 = from_half(skvx::half4::Load(addr));
            if (p4[3] && needsUnpremul) {
                float inva = 1 / p4[3];
                p4 = p4 * skvx::float4(inva, inva, inva, 1);
            }
            return Sk4f_toL32(swizzle_rb(p4));
        }
        // ... 其他颜色类型
    }
    return SkColorSetARGB(0, 0, 0, 0);
}
```

支持20+种颜色格式，包括8位、16位、32位、64位、浮点等。

### Alpha查询优化

`getAlphaf()` 直接读取 Alpha 通道：

```cpp
float SkPixmap::getAlphaf(int x, int y) const {
    const void* srcPtr = fast_getaddr(*this, x, y);

    switch (this->colorType()) {
        case kAlpha_8_SkColorType:
            return static_cast<const uint8_t*>(srcPtr)[0] * (1.0f/255);
        case kA16_unorm_SkColorType:
            return static_cast<const uint16_t*>(srcPtr)[0] * (1.0f/65535);
        case kRGBA_8888_SkColorType:
        case kBGRA_8888_SkColorType:
            return static_cast<const uint8_t*>(srcPtr)[3] * (1.0f/255);
        case kRGBA_F16_SkColorType:
            return from_half(skvx::half4::Load(srcPtr))[3];
        // ... 其他类型
        default:
            return 1.0f;  // 不透明类型
    }
}
```

比 `getColor()` 更高效，避免解析整个颜色。

### 像素读取

```cpp
bool SkPixmap::readPixels(const SkImageInfo& dstInfo,
                          void* dstPixels,
                          size_t dstRB,
                          int x, int y) const
{
    // 验证转换可行性
    if (!SkImageInfoValidConversion(dstInfo, fInfo)) {
        return false;
    }

    // 裁剪到有效区域
    SkReadPixelsRec rec(dstInfo, dstPixels, dstRB, x, y);
    if (!rec.trim(fInfo.width(), fInfo.height())) {
        return false;
    }

    // 计算源像素地址
    const void* srcPixels = this->addr(rec.fX, rec.fY);
    const SkImageInfo srcInfo = fInfo.makeDimensions(rec.fInfo.dimensions());

    // 执行格式转换
    return SkConvertPixels(rec.fInfo, rec.fPixels, rec.fRowBytes,
                           srcInfo, srcPixels, this->rowBytes());
}
```

支持任意颜色格式之间的转换。

### 不透明度计算

`computeIsOpaque()` 逐像素检查：

```cpp
bool SkPixmap::computeIsOpaque() const {
    const int height = this->height();
    const int width = this->width();

    switch (this->colorType()) {
        case kAlpha_8_SkColorType: {
            unsigned a = 0xFF;
            for (int y = 0; y < height; ++y) {
                const uint8_t* row = this->addr8(0, y);
                for (int x = 0; x < width; ++x) {
                    a &= row[x];
                }
                if (0xFF != a) {
                    return false;
                }
            }
            return true;
        }
        case kRGB_565_SkColorType:
        case kGray_8_SkColorType:
            return true;  // 没有Alpha通道
        case kRGBA_8888_SkColorType: {
            SkPMColor c = (SkPMColor)~0;
            for (int y = 0; y < height; ++y) {
                const SkPMColor* row = this->addr32(0, y);
                for (int x = 0; x < width; ++x) {
                    c &= row[x];
                }
                if (0xFF != SkGetPackedA32(c)) {
                    return false;
                }
            }
            return true;
        }
        // ... 其他类型
    }
    return false;
}
```

针对不同格式优化检查逻辑。

### 像素擦除

```cpp
bool SkPixmap::erase(const SkColor4f& color, const SkIRect* subset) const {
    if (this->colorType() == kUnknown_SkColorType) {
        return false;
    }

    // 裁剪到边界
    SkIRect clip = this->bounds();
    if (subset && !clip.intersect(*subset)) {
        return false;
    }

    // 预乘颜色（模拟 kSrc 混合模式）
    const auto c = color.premul();

    // 转换为目标颜色格式
    const auto dst = SkImageInfo::Make(1, 1, this->colorType(),
                                       this->alphaType(),
                                       sk_ref_sp(this->colorSpace()));
    const auto src = SkImageInfo::Make(1, 1, kRGBA_F32_SkColorType,
                                       kPremul_SkAlphaType, nullptr);

    uint64_t dstPixel[2] = {};
    if (!SkConvertPixels(dst, dstPixel, sizeof(dstPixel),
                         src, &c, sizeof(c))) {
        return false;
    }

    // 按行填充
    if (this->colorType() == kRGBA_F32_SkColorType) {
        SkColor4f dstColor;
        memcpy(&dstColor, dstPixel, sizeof(dstColor));
        for (int y = clip.fTop; y < clip.fBottom; ++y) {
            SkColor4f* addr = (SkColor4f*)this->writable_addr(clip.fLeft, y);
            SK_OPTS_NS::memsetT(addr, dstColor, clip.width());
        }
    } else {
        // 使用优化的 memset
        unsigned shift = SkColorTypeShiftPerPixel(this->colorType());
        MemSet proc = procs[shift];
        for (int y = clip.fTop; y < clip.fBottom; ++y) {
            proc(this->writable_addr(clip.fLeft, y),
                 dstPixel[0], clip.width());
        }
    }
    return true;
}
```

使用 SIMD 优化的 `memsetT` 提高性能。

### 子集提取

```cpp
bool SkPixmap::extractSubset(SkPixmap* result, const SkIRect& subset) const {
    SkIRect srcRect, r;
    srcRect.setWH(this->width(), this->height());
    if (!r.intersect(srcRect, subset)) {
        return false;  // 无交集
    }

    // 计算子集像素地址
    const void* pixels = nullptr;
    if (fPixels) {
        const size_t bpp = fInfo.bytesPerPixel();
        pixels = (const uint8_t*)fPixels + r.fTop * fRowBytes + r.fLeft * bpp;
    }

    // 创建子集 Pixmap（共享行字节数）
    result->reset(fInfo.makeDimensions(r.size()), pixels, fRowBytes);
    return true;
}
```

子集与原始 Pixmap 共享行字节数，仅调整起始地址。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkImageInfo | 描述像素格式和尺寸 |
| SkColor | 颜色类型定义 |
| SkColorSpace | 颜色空间管理 |
| SkConvertPixels | 像素格式转换 |
| SkReadPixelsRec | 像素读取辅助 |
| SkSwizzlePriv | 颜色通道交换 |
| SkVx | SIMD向量操作 |
| SkMemset_opts | 优化的内存设置 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| SkBitmap | 使用 Pixmap 暴露像素访问 |
| SkSurface | 使用 Pixmap 读写像素 |
| SkImage | 使用 Pixmap 读取像素 |
| SkCanvas | 间接通过 Bitmap/Surface 使用 |

## 设计模式与设计决策

### 轻量级视图

`SkPixmap` 是非所有权视图：
- 不管理内存生命周期
- 可以廉价复制
- 适合作为函数参数

### 类型安全访问

提供类型化地址访问方法：
- `addr8()`, `addr16()`, `addr32()` 等
- 编译时类型检查
- 运行时断言保护

### 格式抽象

支持20+种颜色格式：
- 统一的接口
- 格式特定的优化
- 自动格式转换

### 常量正确性

区分只读和可写访问：
- `addr()` 返回 `const void*`
- `writable_addr()` 返回 `void*`
- 明确意图，防止误用

## 性能考量

### 直接内存访问

提供直接指针访问：
- 避免虚函数开销
- 支持批量操作
- 内联优化

### SIMD优化

使用向量化操作：
- `skvx::float4` 处理浮点颜色
- `SK_OPTS_NS::memsetT` 快速填充
- 平台特定优化

### 避免分支

使用查表和模板特化：
- 减少运行时分支
- 提高预测命中率
- 编译时优化

### 缓存友好

连续内存访问：
- 按行遍历像素
- 预取优化
- 局部性原理

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| include/core/SkImageInfo.h | 图像信息定义 |
| include/core/SkColor.h | 颜色类型定义 |
| include/core/SkBitmap.h | 使用 Pixmap 的位图类 |
| src/core/SkConvertPixels.h/cpp | 像素格式转换 |
| src/core/SkReadPixelsRec.h | 像素读取辅助 |
| src/base/SkVx.h | SIMD 向量类型 |
| src/opts/SkMemset_opts.h | 优化内存操作 |
| src/core/SkSwizzlePriv.h | 颜色通道交换 |
