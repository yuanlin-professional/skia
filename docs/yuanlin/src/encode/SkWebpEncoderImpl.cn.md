# SkWebpEncoderImpl

> 源文件: src/encode/SkWebpEncoderImpl.cpp

## 概述

`SkWebpEncoderImpl` 实现 WebP 图像格式的编码,使用 libwebp 库将 Skia 位图转换为 WebP 格式。支持有损和无损压缩,以及动画 WebP。

## 架构位置

作为 `SkWebpEncoder` 的后端实现,调用 libwebp API。

## 主要功能

- 静态 WebP 图像编码
- 有损/无损压缩模式
- 质量控制
- 动画 WebP 支持(多帧)
- ICC 配置文件嵌入

## 设计决策

包装 libwebp 的 C API,提供 C++ 接口。支持流式输出,减少内存占用。处理各种像素格式的转换。

## 相关文件

- `include/encode/SkWebpEncoder.h`: 公共 API
- `src/encode/SkWebpEncoder_none.cpp`: 空实现
- libwebp 库
