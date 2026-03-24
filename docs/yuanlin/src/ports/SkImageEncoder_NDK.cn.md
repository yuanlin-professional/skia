# SkImageEncoder_NDK

> 源文件: [src/ports/SkImageEncoder_NDK.cpp](../../../../src/ports/SkImageEncoder_NDK.cpp)

## 概述

本文件实现了基于 Android NDK (`AndroidBitmap_compress`) 的图像编码器后端，为 `SkPngEncoder`、`SkJpegEncoder` 和 `SkWebpEncoder` 三个命名空间提供了 `Encode()` 函数的实现。这是 Skia 在 Android 平台上的专用图像编码路径，利用 Android 系统内置的图像编码能力，避免了在 APK 中额外打包 libpng、libjpeg 或 libwebp 库。

## 架构位置

```
图像编码接口
  ├── include/encode/SkPngEncoder.h
  ├── include/encode/SkJpegEncoder.h
  └── include/encode/SkWebpEncoder.h
        │
        ├── 标准编码器 (libpng/libjpeg/libwebp)
        └── NDK 编码器 (本文件: Android 专用)
              └── AndroidBitmap_compress (Android 系统 API)
```

## 主要类与结构体

本文件不定义公共类，仅包含辅助函数。

## 公共 API 函数

### SkPngEncoder 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `unique_ptr<SkEncoder> Make(SkWStream*, const SkPixmap&, const Options&)` | **不支持**，返回 nullptr |
| `bool Encode(SkWStream* dst, const SkPixmap& src, const Options&)` | 编码 PNG (质量固定 100) |
| `sk_sp<SkData> Encode(const SkPixmap& src, const Options&)` | 编码 PNG 到内存 |
| `sk_sp<SkData> Encode(GrDirectContext*, const SkImage*, const Options&)` | 从 GPU 图像编码 PNG |

### SkJpegEncoder 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `bool Encode(SkWStream* dst, const SkPixmap& src, const Options&)` | 编码 JPEG (使用 options.fQuality) |
| `sk_sp<SkData> Encode(const SkPixmap& src, const Options&)` | 编码 JPEG 到内存 |
| `bool Encode(SkWStream*, const SkYUVAPixmaps&, const SkColorSpace*, const Options&)` | **不支持** YUVA 编码 |
| `sk_sp<SkData> Encode(GrDirectContext*, const SkImage*, const Options&)` | 从 GPU 图像编码 JPEG |
| `unique_ptr<SkEncoder> Make(...)` | **不支持**，两个重载均返回 nullptr |

### SkWebpEncoder 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `bool Encode(SkWStream* dst, const SkPixmap& src, const Options&)` | 编码 WebP (有损/无损由 options 决定) |
| `sk_sp<SkData> Encode(const SkPixmap& src, const Options&)` | 编码 WebP 到内存 |
| `sk_sp<SkData> Encode(GrDirectContext*, const SkImage*, const Options&)` | 从 GPU 图像编码 WebP |
| `bool EncodeAnimated(SkWStream*, SkSpan<const SkEncoder::Frame>, const Options&)` | **不支持**动画 WebP |

## 内部实现细节

### info_for_pixmap - 像素图信息转换

将 `SkPixmap` 的属性转换为 Android 的 `AndroidBitmapInfo`:
- `width`, `height`, `stride` — 使用 `SkTFitsIn<uint32_t>` 安全转换
- `format` — 通过 `SkNDKConversions::toAndroidBitmapFormat()` 转换颜色类型
- `flags` — 通过 `SkNDKConversions::toAndroidBitmapAlphaFlags()` 转换 Alpha 类型
- 任何无效值设为 0，会被 `AndroidBitmap_compress` 拒绝

### write_image_to_stream - 核心编码函数

```cpp
static bool write_image_to_stream(SkWStream* stream,
                                  const SkPixmap& pmap,
                                  AndroidBitmapCompressFormat androidFormat,
                                  int quality)
```

使用 lambda 作为写入回调:
```cpp
auto write_to_stream = [](void* userContext, const void* data, size_t size) {
    return reinterpret_cast<SkWStream*>(userContext)->write(data, size);
};
```

调用 `AndroidBitmap_compress()` 并传入:
- 像素图信息和数据指针
- 通过 `SkNDKConversions::toDataSpace()` 转换的色彩空间
- 格式 (PNG/JPEG/WEBP_LOSSY/WEBP_LOSSLESS)
- 质量参数
- 流写入回调

### GPU 图像处理

带 `GrDirectContext` 参数的重载:
1. 使用 `as_IB(img)->getROPixels(ctx, &bm)` 将 GPU 图像读回 CPU
2. 获取 pixmap 后委托给基本的 Encode 函数

### 不支持的功能

以下功能在 NDK 路径下不可用（调用会触发 `SkDEBUGFAIL`）:
- `SkEncoder::Make()` — 增量编码器创建
- YUVA 格式的 JPEG 编码
- 动画 WebP 编码

### WebP 编码

根据 `options.fCompression` 选择:
- `Compression::kLossless` -> `ANDROID_BITMAP_COMPRESS_FORMAT_WEBP_LOSSLESS`
- 其他 -> `ANDROID_BITMAP_COMPRESS_FORMAT_WEBP_LOSSY`

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkBitmap.h` | GPU 图像读回 |
| `include/core/SkPixmap.h` | 像素图数据 |
| `include/core/SkStream.h` | 输出流 |
| `include/encode/SkJpegEncoder.h` | JPEG 编码接口 |
| `include/encode/SkPngEncoder.h` | PNG 编码接口 |
| `include/encode/SkWebpEncoder.h` | WebP 编码接口 |
| `include/private/base/SkTFitsIn.h` | 安全类型转换 |
| `src/encode/SkImageEncoderPriv.h` | 编码器私有工具 |
| `src/image/SkImage_Base.h` | as_IB() 辅助 |
| `src/ports/SkNDKConversions.h` | Skia-NDK 类型转换 |
| Android NDK | AndroidBitmap_compress 等 API |

## 设计模式与设计决策

1. **平台委托**: 将编码工作委托给 Android 系统，减少 APK 大小
2. **统一接口**: 实现与标准编码器相同的 API 签名，上层代码无需关心后端差异
3. **回调写入**: 使用 lambda 回调桥接 Android 的写入回调和 Skia 的 SkWStream
4. **优雅降级**: 不支持的功能使用 `SkDEBUGFAIL` 提醒开发者，Release 模式返回 false/nullptr
5. **GPU 到 CPU 回退**: 带 GPU 上下文的重载自动处理 GPU-CPU 数据传输

## 性能考量

- 利用 Android 系统已加载的编码库，避免重复加载和链接
- NDK 编码器可能使用硬件加速（取决于设备和 Android 版本）
- GPU 图像编码需要先读回 CPU (`getROPixels`)，这是一个同步且可能昂贵的操作
- PNG 编码质量固定为 100，不支持压缩级别调节
- `SkDynamicMemoryWStream` 用于内存编码，可能在大图像上产生多次内存分配
- 回调函数中的 `reinterpret_cast` 仅用于类型恢复，无实际开销
- `info_for_pixmap` 中的 `SkTFitsIn` 检查确保不会发生整数溢出

## 功能限制

使用 NDK 编码路径时，以下功能**不**可用:

| 不支持的功能 | 涉及的命名空间 | 原因 |
|-------------|:---:|------|
| 增量编码 (`Make()`) | PNG / JPEG | NDK 仅支持一次性编码 |
| YUVA 编码 | JPEG | NDK 不支持 YUV 输入格式 |
| 动画 WebP | WebP | NDK 不支持多帧编码 |
| PNG 压缩级别 | PNG | 质量固定为 100 |

## 相关文件

- `src/ports/SkNDKConversions.h` / `.cpp` — Skia 与 Android NDK 类型转换
- `include/encode/SkPngEncoder.h` — PNG 编码接口
- `include/encode/SkJpegEncoder.h` — JPEG 编码接口
- `include/encode/SkWebpEncoder.h` — WebP 编码接口
- `src/encode/SkImageEncoderPriv.h` — 编码器内部工具
