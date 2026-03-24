# SkJpegGainmapEncoder

> 源文件: src/encode/SkJpegGainmapEncoder.cpp

## 概述

`SkJpegGainmapEncoder` 实现支持 Gainmap 的 JPEG 编码,用于 HDR 图像。Gainmap 是一种在 JPEG 中嵌入 HDR 信息的技术,通过辅助图像存储动态范围扩展数据。

## 架构位置

扩展标准 JPEG 编码器,支持 HDR/Gainmap 元数据和多图像嵌入。

## 主要功能

### Gainmap 编码

- 主图像编码(SDR 基准)
- Gainmap 图像编码(HDR 扩展)
- ISO 21496-1 元数据生成

### 多图像打包

将主图像和 gainmap 打包到单个 JPEG 文件中。

### 元数据管理

嵌入 XMP 和 EXIF 元数据,描述 HDR 参数。

## 设计决策

兼容现有 JPEG 解码器(显示 SDR 图像),支持 HDR 的解码器可提取 gainmap。使用标准的 JPEG APP 标记存储额外数据。

## 相关文件

- `src/encode/SkJpegEncoderImpl.cpp`: 基础 JPEG 编码
- `include/core/SkGainmapInfo.h`: Gainmap 元数据
- `src/codec/SkJpegGainmapDecoder.cpp`: Gainmap 解码
