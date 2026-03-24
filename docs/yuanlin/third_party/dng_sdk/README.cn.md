# third_party/dng_sdk - Adobe DNG SDK

## 概述

`third_party/dng_sdk/` 包含 Adobe 数字负片（DNG）SDK 的 Skia 构建配置。
DNG 是一种用于存储相机原始图像数据的开放格式，该 SDK 提供了 DNG 文件的
读取和处理功能。

## 目录结构

```
dng_sdk/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 DNG SDK 的编译选项，实际源码在 `third_party/externals/` 中

## 依赖关系

- DNG SDK 源码（通过 DEPS 拉取）
- zlib（数据压缩）

## 相关文档与参考

- Adobe DNG 规范: https://helpx.adobe.com/camera-raw/digital-negative.html
- Skia 图像编解码: `src/codec/`
