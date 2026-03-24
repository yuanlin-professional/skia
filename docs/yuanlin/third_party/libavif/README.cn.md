# third_party/libavif - AVIF 图像编解码

## 概述

`third_party/libavif/` 包含 libavif 库的 Skia 构建配置。libavif 提供
AVIF（AV1 Image File Format）图像格式的编码和解码支持。AVIF 是一种基于
AV1 视频编码的现代图像格式，提供卓越的压缩效率。

## 目录结构

```
libavif/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 libavif 的编译选项

## 依赖关系

- libavif 源码（通过 DEPS 拉取）
- libgav1（AV1 解码器后端）

## 相关文档与参考

- libavif: https://github.com/AOMediaCodec/libavif
- AVIF 格式: https://aomediacodec.github.io/av1-avif/
- Skia AVIF 编解码: `src/codec/SkAvifCodec.cpp`
