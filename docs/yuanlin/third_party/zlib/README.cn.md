# third_party/zlib - 数据压缩库

## 概述

`third_party/zlib/` 包含 zlib 数据压缩库的 Skia 构建配置。zlib 是最广泛使用的
数据压缩库之一，实现了 DEFLATE 压缩算法。Skia 在 PNG 编解码、PDF 生成、
字体处理等多个场景中依赖 zlib。

## 目录结构

```
zlib/
├── BUILD.gn             # GN 构建配置
└── zlib.gni             # GN 导入配置
```

## 关键文件

- **BUILD.gn**: zlib 的 Skia 构建配置
- **zlib.gni**: 可导入的 GN 配置变量

## 依赖关系

- zlib 源码（通过 DEPS 拉取或使用系统提供版本）

## 相关文档与参考

- zlib: https://www.zlib.net/
- Skia PNG 编解码: `src/codec/SkPngCodec.cpp`
- Skia PDF: `src/pdf/`
