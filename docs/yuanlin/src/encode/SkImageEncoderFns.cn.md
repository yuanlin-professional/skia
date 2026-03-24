# SkImageEncoderFns

> 源文件: src/encode/SkImageEncoderFns.h

## 概述

`SkImageEncoderFns` 提供图像编码的通用辅助函数,包括像素格式转换、颜色空间变换和数据预处理。

## 架构位置

作为所有编码器的共享工具库,简化格式特定编码器的实现。

## 主要功能

### 像素转换

- RGBA 到编码器特定格式的转换
- 预乘 alpha 处理
- 字节序调整

### 颜色空间变换

- sRGB 到线性空间转换
- Gamma 校正
- 颜色空间转换

## 设计决策

提供模板化的转换函数,支持多种像素格式。优化常见转换路径,提高编码性能。

## 相关文件

- `src/encode/SkPngEncoderImpl.cpp`: PNG 编码器使用
- `src/encode/SkJpegEncoderImpl.cpp`: JPEG 编码器使用
- `src/encode/SkWebpEncoderImpl.cpp`: WebP 编码器使用
