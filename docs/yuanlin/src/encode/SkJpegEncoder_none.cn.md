# SkJpegEncoder_none

> 源文件: src/encode/SkJpegEncoder_none.cpp

## 概述

`SkJpegEncoder_none` 是当系统未配置 JPEG 编码支持时的空实现。提供编译时的占位符,确保 API 完整性但功能返回失败。

## 架构位置

作为条件编译的一部分,在禁用 JPEG 支持时提供空操作实现。

## 主要功能

所有编码函数返回 `nullptr` 或 `false`,表示不支持 JPEG 编码。

## 设计决策

保持 API 兼容性,允许代码在没有 JPEG 库的环境下编译。运行时返回明确的失败状态。

## 相关文件

- `src/encode/SkJpegEncoderImpl.cpp`: 实际的 JPEG 编码器实现
- `src/encode/SkPngEncoder_none.cpp`: PNG 的类似实现
- `src/encode/SkWebpEncoder_none.cpp`: WebP 的类似实现
