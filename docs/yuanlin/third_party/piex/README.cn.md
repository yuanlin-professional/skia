# third_party/piex - 预览图像提取器

## 概述

`third_party/piex/` 包含 PIEX（Preview Image Extractor）库的 Skia 构建配置。
PIEX 用于从各种相机 RAW 格式文件中快速提取嵌入的预览图像，无需完整解码原始数据。

## 目录结构

```
piex/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 PIEX 的编译选项

## 依赖关系

- PIEX 源码（通过 DEPS 拉取）

## 相关文档与参考

- PIEX: https://github.com/nicknash/piex
- DNG SDK: `third_party/dng_sdk/`
- Skia RAW 编解码: `src/codec/SkRawCodec.cpp`
