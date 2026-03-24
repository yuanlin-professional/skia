# encode - 图像编码 API

## 概述

`include/encode` 目录定义了 Skia 图像编码框架的公共 API。该框架提供了将内存中的
像素数据（SkPixmap）编码为各种标准图像格式的能力。当前支持的编码格式包括 JPEG、
PNG 和 WebP 三种主流格式。

编码框架的设计遵循简洁实用的原则。每种格式都以命名空间（如 `SkJpegEncoder`、
`SkPngEncoder`、`SkWebpEncoder`）的形式组织，提供三类核心函数：`Encode()` 函数
将像素数据编码并写入输出流或直接返回编码后的 `SkData`；`Make()` 函数创建一个
`SkEncoder` 实例用于增量编码。每种格式还定义了各自的 `Options` 结构体，允许精细
控制编码参数，如 JPEG 的质量和下采样、PNG 的滤镜选择和压缩级别、WebP 的有损/无损
模式等。

该模块还提供了 ICC 颜色配置文件的写入功能（`SkICC.h`），支持从传输函数和 XYZ 矩阵
或从完整的 ICC 配置文件创建 ICC 数据。此外，PNG 编码器支持嵌入 Gainmap（HDR 增益图）
数据和 HDR 元数据，WebP 编码器还支持动画帧编码。

编码框架特别值得注意的是其对 GPU 纹理图像的支持。通过提供 `GrDirectContext`，
可以直接从 GPU 纹理支持的 `SkImage` 进行编码，Skia 会自动处理像素的回读。

## 架构图

```
+------------------------------------------------------------------+
|                        应用层                                      |
|  SkPixmap / SkImage / SkBitmap --> 编码为文件/流/内存               |
+------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+------------------+  +------------------+  +------------------+
| SkJpegEncoder    |  | SkPngEncoder     |  | SkWebpEncoder    |
| JPEG 编码器       |  | PNG 编码器        |  | WebP 编码器       |
+------------------+  +------------------+  +------------------+
| Options:         |  | Options:         |  | Options:         |
|  - fQuality      |  |  - fFilterFlags  |  |  - fCompression  |
|  - fDownsample   |  |  - fZLibLevel    |  |  - fQuality      |
|  - fAlphaOption  |  |  - fComments     |  +------------------+
|  - xmpMetadata   |  |  - fHdrMetadata  |  | Encode()         |
|  - fOrigin       |  |  - fGainmap      |  | EncodeAnimated() |
+------------------+  +------------------+  +------------------+
| Encode()         |  | Encode()         |
| Make()           |  | Make()           |
+------------------+  +------------------+
         |                    |                    |
         v                    v                    v
+------------------------------------------------------------------+
|                     SkEncoder (基类)                               |
|  encodeRows() - 增量编码接口                                       |
|  Frame { pixmap, duration } - 动画帧结构                           |
+------------------------------------------------------------------+
         |
         v
+------------------------------------------------------------------+
|  SkICC - ICC 颜色配置文件写入工具                                   |
|  SkWriteICCProfile() - 从传输函数或 ICC 配置文件创建数据             |
+------------------------------------------------------------------+
```

## 目录结构

```
include/encode/
  BUILD.bazel             # Bazel 构建配置
  SkEncoder.h             # 编码器基类，定义增量编码接口和动画帧结构
  SkICC.h                 # ICC 颜色配置文件写入工具
  SkJpegEncoder.h         # JPEG 编码器（质量、下采样、Alpha 处理）
  SkPngEncoder.h          # PNG 编码器（滤镜、压缩、HDR 元数据、Gainmap）
  SkPngRustEncoder.h      # PNG 编码器（Rust 实现）
  SkWebpEncoder.h         # WebP 编码器（有损/无损、动画帧编码）
```

## 关键类与函数

### SkEncoder - 编码器基类

所有编码器的公共基类：
- `encodeRows(int numRows)` - 编码指定行数的像素数据
- `Frame` 结构体 - 动画帧，包含 `pixmap`（像素数据）和 `duration`（持续时间毫秒）

### SkJpegEncoder - JPEG 编码

- `Encode(SkWStream*, const SkPixmap&, const Options&)` - 编码到流
- `Encode(const SkPixmap&, const Options&)` - 编码为 SkData
- `Encode(GrDirectContext*, const SkImage*, const Options&)` - 从 GPU 图像编码
- `Make()` - 创建增量编码器
- 支持 YUV 数据编码（`SkYUVAPixmaps`）
- `Options`:
  - `fQuality` - 质量（0-100）
  - `fDownsample` - 色度下采样（k420/k422/k444）
  - `fAlphaOption` - Alpha 处理（忽略/混合到黑色背景）
  - `xmpMetadata` - XMP 元数据
  - `fOrigin` - EXIF 方向

### SkPngEncoder - PNG 编码

- `Encode()` - 编码到流或 SkData
- `Make()` - 创建增量编码器
- `Options`:
  - `fFilterFlags` - PNG 行滤镜（None/Sub/Up/Avg/Paeth 或其组合）
  - `fZLibLevel` - zlib 压缩级别（0-9）
  - `fComments` - tEXt 块注释
  - `fHdrMetadata` - HDR 元数据
  - `fGainmap` / `fGainmapInfo` - Gainmap 增益图数据

### SkWebpEncoder - WebP 编码

- `Encode()` - 编码到流或 SkData
- `EncodeAnimated()` - 编码动画帧序列
- `Options`:
  - `fCompression` - 压缩模式（kLossy/kLossless）
  - `fQuality` - 质量（0.0-100.0）

### SkICC - ICC 配置文件

- `SkWriteICCProfile(const skcms_TransferFunction&, const skcms_Matrix3x3&)` - 从传输函数创建
- `SkWriteICCProfile(const skcms_ICCProfile*, const char*)` - 从配置文件创建
- `SkICCFloatXYZD50ToGrid16Lab()` - XYZD50 到 Lab 网格转换
- `SkICCFloatToTable16()` - 浮点到 16 位表格转换

## 依赖关系

- **内部依赖**：`include/core`（SkPixmap、SkData、SkWStream、SkImage 等）
- **内部依赖**：`include/codec`（SkEncodedOrigin）
- **外部依赖**：libjpeg-turbo、libpng（或 Rust PNG）、libwebp、skcms
- **被依赖**：`include/docs`（PDF 和 SVG 文档输出中的图像编码）

## 相关文档与参考

- JPEG 编码标准及 libjpeg-turbo
- PNG 规范：https://www.w3.org/TR/png/
- WebP 格式：https://developers.google.com/speed/webp
- ICC 颜色配置文件规范
- Gainmap 提案：https://github.com/w3c/png/issues/380
- 源码实现位于 `src/encode/` 目录
