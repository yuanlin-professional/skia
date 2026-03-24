# SkJpegEncoderImpl — JPEG 图像编码器

> 源文件：[src/encode/SkJpegEncoderImpl.h](../../src/encode/SkJpegEncoderImpl.h)、[src/encode/SkJpegEncoderImpl.cpp](../../src/encode/SkJpegEncoderImpl.cpp)

## 概述

`SkJpegEncoderImpl` 是 Skia 的 JPEG 图像编码器实现，继承自 `SkEncoder`。它封装 libjpeg-turbo 提供 RGB 和 YUV 两种输入模式的 JPEG 编码能力。

核心功能：
- RGB 像素数据编码（支持多种 SkColorType 输入）
- YUV 原始数据编码（Y_U_V 和 Y_UV 平面配置）
- 可配置的质量、色度子采样（420/422/444）
- JPEG 元数据支持（ICC Profile、XMP、EXIF 方向）
- 优化 Huffman 编码表
- Alpha 通道处理（混合到黑色背景或忽略）

## 架构位置

```
SkEncoder (基类)
    └── SkJpegEncoderImpl
            ├── SkJpegEncoderMgr (libjpeg-turbo 封装)
            │   ├── jpeg_compress_struct
            │   ├── skjpeg_error_mgr
            │   └── skjpeg_destination_mgr
            └── SkJpegMetadataEncoder (元数据段管理)
```

## 主要类与结构体

### `SkJpegEncoderImpl`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fEncoderMgr` | `unique_ptr<SkJpegEncoderMgr>` | libjpeg-turbo 管理器 |
| `fSrcYUVA` | `optional<SkYUVAPixmaps>` | YUV 源数据（YUV 模式时） |

### `SkJpegEncoderMgr`（内部类）

封装 `jpeg_compress_struct`、错误管理器和目标管理器。提供 RGB 和 YUV 初始化方法以及可选的颜色格式转换。

### `SkJpegMetadataEncoder`（命名空间）

| 函数 | 说明 |
|------|------|
| `AppendICC` | 添加 ICC Profile 段 |
| `AppendXMPStandard` | 添加标准 XMP 元数据段 |
| `AppendOrigin` | 添加 EXIF 方向信息段 |

## 公共 API 函数

- **`MakeRGB(dst, src, options, metadata)`**：从 RGB Pixmap 创建编码器。
- **`MakeYUV(dst, srcYUVA, colorSpace, options, metadata)`**：从 YUV 数据创建编码器。
- **`onEncodeRows(numRows)`**：编码指定行数。RGB 模式逐行扫描，YUV 模式通过 `yuva_copy_row` 组合平面数据。

## 内部实现细节

### 颜色类型映射

直接映射路径（无需转换）：`kRGB_888x` → `JCS_EXT_RGBX`、`kRGBA_8888` → `JCS_EXT_RGBA`、`kBGRA_8888` → `JCS_EXT_BGRA`。需要转换时使用 `SkConvertPixels` 处理。

### YUV 编码

通过 `yuva_copy_row()` 将分离的 YUV 平面数据按像素交织为 Y,Cb,Cr 三元组。支持 `kY_U_V` 和 `kY_UV` 平面配置，处理子采样因子。仅支持 `kJPEG_Full` YUV 色彩空间和 8 位数据。

### 优化编码

默认启用 `optimize_coding = TRUE`，让 libjpeg-turbo 计算最优 Huffman 表，提高压缩率但增加编码时间。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| libjpeg-turbo | JPEG 压缩引擎 |
| `SkJPEGWriteUtility` | libjpeg 目标管理器和错误处理 |
| `SkConvertPixels` | 颜色格式转换 |
| `SkImageEncoderFns` | 编码器通用函数 |

## 设计模式与设计决策

1. **RGB/YUV 双路径**：分别优化了 RGB 像素和 YUV 原始数据的输入路径。
2. **元数据段列表**：`SegmentList` 将 ICC、XMP、EXIF 统一为标记段列表，在 `jpeg_start_compress` 后通过 `jpeg_write_marker` 写入。
3. **延迟颜色转换**：仅在必要时启用 `fUseColorXform`，避免不必要的像素格式转换。

## 性能考量

- libjpeg-turbo 利用 SIMD 加速 DCT 和颜色空间转换。
- 优化 Huffman 编码增加约 5-10% 的编码时间，但提升 5-10% 的压缩率。
- YUV 直接输入避免了 RGB→YCbCr 的转换开销。

## 相关文件

- `src/encode/SkJPEGWriteUtility.h` — libjpeg 写入工具
- `include/encode/SkJpegEncoder.h` — 公共 API
- `src/codec/SkJpegConstants.h` — JPEG 标记常量
