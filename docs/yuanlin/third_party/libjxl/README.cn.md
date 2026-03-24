# third_party/libjxl - JPEG XL 编解码库

## 概述

`third_party/libjxl/` 包含 JPEG XL 图像格式编解码库的 Skia 构建配置。
JPEG XL 是一种新一代的图像压缩格式，提供比 JPEG 更好的压缩率和图像质量，
同时支持无损压缩、渐进解码、HDR 和动画。

## 目录结构

```
libjxl/
├── BUILD.gn             # GN 构建配置
└── jxl/                 # 自定义头文件
    └── jxl_export.h     # 导出宏定义
```

## 关键文件

- **BUILD.gn**: libjxl 的 Skia 构建配置
- **jxl/jxl_export.h**: 自定义的符号导出宏

## 依赖关系

- libjxl 源码（通过 DEPS 拉取）
- highway（SIMD 加速）
- brotli（压缩支持）

## 相关文档与参考

- JPEG XL: https://jpeg.org/jpegxl/
- libjxl: https://github.com/libjxl/libjxl
- Skia JXL 编解码: `src/codec/SkJpegxlCodec.cpp`
