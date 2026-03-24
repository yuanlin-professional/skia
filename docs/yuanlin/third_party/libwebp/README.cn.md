# third_party/libwebp - WebP 图像编解码

## 概述

`third_party/libwebp/` 包含 Google WebP 图像格式库的 Skia 构建配置。
WebP 是一种现代图像格式，同时支持有损和无损压缩，通常比 JPEG 和 PNG
提供更好的压缩率。Skia 使用 libwebp 进行 WebP 图像的编码和解码。

## 目录结构

```
libwebp/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 libwebp 的编译选项和 SIMD 支持

## 依赖关系

- libwebp 源码（通过 DEPS 拉取）

## 相关文档与参考

- WebP: https://developers.google.com/speed/webp/
- libwebp: https://chromium.googlesource.com/webm/libwebp
- Skia WebP 编解码: `src/codec/SkWebpCodec.cpp`
