# third_party/libjpeg-turbo - JPEG 编解码库

## 概述

`third_party/libjpeg-turbo/` 包含 libjpeg-turbo 库的 Skia 构建配置。
libjpeg-turbo 是 libjpeg 的高性能分支，使用 SIMD 指令（SSE2、AVX2、NEON）
大幅提升 JPEG 编解码速度。Skia 使用它作为默认的 JPEG 处理库。

## 目录结构

```
libjpeg-turbo/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 libjpeg-turbo 的编译选项和 SIMD 支持

## 依赖关系

- libjpeg-turbo 源码（通过 DEPS 拉取）

## 相关文档与参考

- libjpeg-turbo: https://libjpeg-turbo.org/
- Skia JPEG 编解码: `src/codec/SkJpegCodec.cpp`
- Skia JPEG 编码: `src/encode/SkJPEGWriteUtility.cpp`
