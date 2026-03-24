# rust/png - Rust PNG 编解码器

## 概述

`rust/png/` 包含将 Rust `png` crate 暴露给 Skia C++ 代码的 FFI 封装，
为 `SkPngRustCodec`（解码器）和 `SkPngRustEncoderImpl`（编码器）提供
底层的 PNG 处理功能。相比 C 语言的 libpng，Rust 版本提供了内存安全保障
和对 APNG、CICP 等新特性的支持。

## 目录结构

```
png/
├── BUILD.bazel      # Bazel 构建配置
├── FFI.h            # C++ FFI 头文件
├── FFI.rs           # Rust CXX 桥接定义
└── README.md        # 原始文档
```

## 与传统实现的区别

### SkPngRustCodec vs SkPngCodec
- 支持 APNG（动画 PNG）
- 支持 CICP 色彩元数据

### SkPngRustEncoder vs SkPngEncoder
- 使用 Rust `png` crate 替代 libpng

## 构建指南

### Bazel
```bash
$ bazelisk build //src/codec:rust_png_decoder //src/encode:rust_png_encoder rust/png/...
```

### GN / Ninja
```bash
$ gn args out/RustPng
# 设置: skia_use_rust_png_decode = true 和 skia_use_rust_png_encode = true
$ gn gen out/RustPng
$ autoninja -C out/RustPng dm
```

## 测试

```bash
$ out/RustPng/dm --src tests --nogpu \
    --match RustPngCodec RustEncodePng
```

## 依赖关系

- **cxx**: FFI 桥接
- **png** crate: Rust PNG 编解码库
- **rust/common**: 共享 FFI 工具
- **rust/icc**: ICC 配置文件解析

## 相关文档与参考

- Skia 编解码器: `src/codec/`
- PNG 编码器: `src/encode/`
- Rust BMP 解码器: `experimental/rust_bmp/`
