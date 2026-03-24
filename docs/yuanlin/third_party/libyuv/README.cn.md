# third_party/libyuv - YUV 格式转换库

## 概述

`third_party/libyuv/` 包含 Google libyuv 库的 Skia 构建配置。libyuv 提供
高效的 YUV 色彩空间转换和图像缩放功能，在视频处理和某些图像编解码场景中使用。

## 目录结构

```
libyuv/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 libyuv 的编译选项

## 依赖关系

- libyuv 源码（通过 DEPS 拉取）

## 相关文档与参考

- libyuv: https://chromium.googlesource.com/libyuv/libyuv/
- Skia 图像编解码: `src/codec/`
