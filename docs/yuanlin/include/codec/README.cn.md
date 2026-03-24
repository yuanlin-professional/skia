# codec - 图像编解码 API

## 概述

`include/codec` 目录定义了 Skia 图像编解码框架的公共 API。该框架提供了一套统一的接口，
用于将各种编码格式的图像数据（如 PNG、JPEG、WebP、GIF 等）解码为 Skia 内部可以直接
使用的像素数据（SkPixmap/SkBitmap）。

Skia 的编解码框架采用了可插拔的解码器架构。核心类 `SkCodec` 作为所有解码器的抽象基类，
为各种格式提供统一的解码接口，包括全量解码、增量解码和扫描行解码三种模式。每种具体
格式（PNG、JPEG、WebP 等）通过 `SkCodecs::Decoder` 注册机制进行动态注册，使得应用
可以根据需要选择性地链接解码器，从而减小二进制体积。

该模块还提供了 `SkAndroidCodec` 类，它是专门为 Android 平台优化的解码接口，支持
采样（下采样）和子集解码，使得移动端可以高效地处理大尺寸图像。此外，模块还包含
动画图像支持（如 GIF、APNG），通过 `SkCodecAnimation` 定义帧混合和处理方式，
以及 EXIF 方向信息处理（`SkEncodedOrigin`）等辅助功能。

编解码框架支持的格式非常广泛，涵盖了 BMP、GIF、ICO、JPEG、PNG（包括 Rust 实现的
解码器）、WebP、WBMP、AVIF、JPEG XL 和 RAW 等主流图像格式。每种格式都有独立的
头文件定义其特有的解码器创建函数。

## 架构图

```
+------------------------------------------------------------------+
|                         应用层                                     |
|  (调用 SkCodec::MakeFromStream / MakeFromData)                    |
+------------------------------------------------------------------+
         |                                    |
         v                                    v
+-------------------+             +------------------------+
|     SkCodec       |             |   SkAndroidCodec       |
|  (解码核心基类)    |<------------|  (Android 优化包装)     |
|                   |             |  - 采样解码             |
|  - getPixels()    |             |  - 子集解码             |
|  - getImage()     |             |  - Gainmap 支持         |
|  - 增量解码       |             +------------------------+
|  - 扫描行解码     |
|  - YUV 解码       |
|  - 动画帧管理     |
+-------------------+
         |
         v  (SkCodecs::Decoder 注册机制)
+-------------------+-------------------+-------------------+
| SkPngDecoder      | SkJpegDecoder     | SkWebpDecoder     |
| SkPngRustDecoder  | SkGifDecoder      | SkAvifDecoder     |
| SkBmpDecoder      | SkIcoDecoder      | SkJpegxlDecoder   |
| SkWbmpDecoder     | SkRawDecoder      |                   |
+-------------------+-------------------+-------------------+
         |
         v
+-------------------+     +-------------------+
| SkCodecAnimation  |     | SkEncodedOrigin   |
| (动画帧混合方式)   |     | (EXIF 方向信息)    |
+-------------------+     +-------------------+
```

## 目录结构

```
include/codec/
  BUILD.bazel               # Bazel 构建配置
  SkCodec.h                 # 核心解码器基类，定义所有解码功能
  SkAndroidCodec.h          # Android 平台专用解码器，支持采样和子集解码
  SkCodecAnimation.h        # 动画帧的混合与处理方式枚举
  SkEncodedImageFormat.h    # 编码图像格式枚举（BMP/GIF/JPEG/PNG/WebP 等）
  SkEncodedOrigin.h         # EXIF 方向信息枚举及变换矩阵工具
  SkPixmapUtils.h           # Pixmap 方向变换工具函数
  SkPngChunkReader.h        # PNG 未知块读取器回调接口
  SkAvifDecoder.h           # AVIF 格式解码器
  SkBmpDecoder.h            # BMP 格式解码器
  SkGifDecoder.h            # GIF 格式解码器
  SkIcoDecoder.h            # ICO 格式解码器
  SkJpegDecoder.h           # JPEG 格式解码器
  SkJpegxlDecoder.h         # JPEG XL 格式解码器
  SkPngDecoder.h            # PNG 格式解码器 (libpng)
  SkPngRustDecoder.h        # PNG 格式解码器 (Rust 实现)
  SkRawDecoder.h            # RAW 格式解码器
  SkWbmpDecoder.h           # WBMP 格式解码器
  SkWebpDecoder.h           # WebP 格式解码器
```

## 关键类与函数

### SkCodec - 核心解码器基类

`SkCodec` 是整个编解码框架的核心类，定义了三种主要的解码模式：

- **全量解码** (`getPixels`)：一次性解码整幅图像
- **增量解码** (`startIncrementalDecode` / `incrementalDecode`)：逐步解码，支持流式数据
- **扫描行解码** (`startScanlineDecode` / `getScanlines`)：按行解码，支持跳行

关键方法：
- `MakeFromStream()` / `MakeFromData()` - 从数据流或数据块创建解码器
- `getInfo()` - 获取图像信息（尺寸、颜色类型等）
- `getPixels()` - 将编码数据解码为像素
- `getImage()` - 直接返回一个 `SkImage` 对象
- `queryYUVAInfo()` / `getYUVAPlanes()` - YUV 平面解码
- `getFrameCount()` / `getFrameInfo()` - 动画帧信息查询
- `getRepetitionCount()` - 动画循环次数
- `isAnimated()` - 判断是否为动画图像

### SkAndroidCodec - Android 平台解码器

为 Android 平台优化的解码器封装，提供额外的功能：
- `getSampledDimensions()` - 获取采样后的尺寸
- `getAndroidPixels()` - 带采样和子集选项的解码
- `computeOutputColorType()` - 自动计算合适的输出颜色类型
- `getGainmapAndroidCodec()` - 获取 Gainmap（HDR 增益图）解码器

### SkCodecAnimation - 动画帧处理

- `DisposalMethod` - 帧处置方式：kKeep（保留）、kRestoreBGColor（恢复背景色）、kRestorePrevious（恢复上一帧）
- `Blend` - 帧混合方式：kSrcOver（源覆盖）、kSrc（源替换）

### SkEncodedOrigin - EXIF 方向

定义了8种 EXIF 方向及其对应的变换矩阵：
- `SkEncodedOriginToMatrix()` - 根据方向生成变换矩阵
- `SkEncodedOriginSwapsWidthHeight()` - 判断该方向是否交换宽高

### SkCodecs::Decoder - 解码器注册

通过 `SkCodecs::Register()` 注册解码器，每个解码器包含：
- `id` - 格式标识符（如 "png"、"jpg"）
- `isFormat` - 格式检测回调
- `makeFromStream` - 解码器创建回调

## 依赖关系

- **内部依赖**：`include/core`（SkImageInfo、SkPixmap、SkData、SkStream 等）
- **外部依赖**：skcms（颜色管理）、各格式编解码库（libpng、libjpeg-turbo、libwebp 等）
- **被依赖**：`include/encode`（编码模块）、`include/docs`（文档模块，如 PDF 中的 JPEG 处理）

## 相关文档与参考

- Skia 官方文档：https://skia.org/docs/user/api/
- EXIF 方向标准：http://www.exif.org/Exif2-2.PDF
- GIF 89a 规范（动画帧处理）
- PNG 规范（块读取器）
- 源码实现位于 `src/codec/` 目录
