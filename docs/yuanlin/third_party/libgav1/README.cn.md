# third_party/libgav1 - AV1 视频解码器

## 概述

`third_party/libgav1/` 包含 Google libgav1 AV1 视频解码器的 Skia 构建配置。
libgav1 用于解码 AVIF 图像中的 AV1 编码数据，是 Skia AVIF 图像支持的
底层依赖之一。

## 目录结构

```
libgav1/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 libgav1 的编译选项

## 依赖关系

- libgav1 源码（通过 DEPS 拉取）
- libavif（AVIF 容器格式支持）

## 相关文档与参考

- libgav1: https://chromium.googlesource.com/codecs/libgav1/
- AVIF 支持: `third_party/libavif/`
- AV1 规范: https://aomediacodec.github.io/av1-spec/
