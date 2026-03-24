# third_party/libpng - PNG 图像库

## 概述

`third_party/libpng/` 包含 libpng 库的 Skia 构建配置。libpng 是 PNG
（Portable Network Graphics）图像格式的官方参考实现，Skia 使用它进行
PNG 图像的编码和解码。

## 目录结构

```
libpng/
├── BUILD.gn             # GN 构建配置
├── png.imp              # 导入库定义
└── pnglibconf.h         # libpng 配置头文件
```

## 关键文件

- **BUILD.gn**: 配置 libpng 的编译选项和源文件列表
- **pnglibconf.h**: Skia 定制的 libpng 配置，启用/禁用特定功能

## 依赖关系

- libpng 源码（通过 DEPS 拉取）
- zlib（PNG 使用 DEFLATE 压缩）

## 相关文档与参考

- libpng 官网: http://www.libpng.org/
- Rust PNG 替代: `rust/png/`
- Skia PNG 编解码: `src/codec/SkPngCodec.cpp`
