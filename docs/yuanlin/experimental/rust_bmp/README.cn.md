# rust_bmp - Rust 实现的 BMP 图像解码器

## 概述

`experimental/rust_bmp/` 包含一个完全用 Rust 编写的 BMP 图像解码器（`SkBmpRustCodec`），
通过 CXX 桥接与 Skia 的 C++ 代码集成。相比传统的 C++ 实现 `SkBmpCodec`，Rust 版本
提供了内存安全、全面的溢出保护和更强的格式兼容性。

## 目录结构

```
rust_bmp/
├── README.md                # 项目文档
├── decoder/                 # C++ 集成层
│   ├── BUILD.bazel          # Bazel 构建配置
│   ├── SkBmpRustDecoder.h   # Skia SkCodec 工厂头文件
│   ├── SkBmpRustDecoder.cpp # 工厂实现
│   └── impl/
│       ├── SkBmpRustCodec.h   # 核心编解码器头文件
│       └── SkBmpRustCodec.cpp # 核心编解码器实现
└── ffi/                     # Rust FFI 核心
    ├── BUILD.bazel          # Bazel 构建配置
    ├── FFI.rs               # C++ 接口桥接
    ├── lib.rs               # Crate 根
    ├── bmp_decoder.rs       # BMP 解码主逻辑
    ├── bmp_header.rs        # BMP 头部解析与验证
    ├── bmp_constants.rs     # 格式常量定义
    ├── bmp_types.rs         # 类型定义
    ├── bmp_icc.rs           # ICC 配置文件支持
    ├── bmp_jpeg_decoder.rs  # 嵌入式 JPEG 处理
    └── bmp_png_decoder.rs   # 嵌入式 PNG 处理
```

## 功能特性

### 完整格式支持
- **位深度**: 1位、4位、8位、16位、24位、32位
- **压缩**: 未压缩(BI_RGB)、RLE4、RLE8、位域(BI_BITFIELDS)
- **高级**: OS/2 位图变体
- **色彩空间**: sRGB、嵌入式 ICC 配置文件

### 安全性与健壮性
- 使用 u64 算术的完整溢出保护
- 全面的头部和流验证
- 高级损坏文件检测
- 100% bmptestsuite-0.9 标准符合性

## 构建指南

### Bazel
```bash
$ bazelisk build //src/codec:rust_bmp_decoder //experimental/rust_bmp/...
$ bazelisk test //experimental/rust_bmp/ffi:test_bmp_ffi
```

### GN / Ninja
```bash
$ gn args out/RustBmp  # 设置 skia_use_rust_bmp_decode = true
$ gn gen out/RustBmp
$ autoninja -C out/RustBmp dm
```

## 依赖关系

- Rust 工具链
- **cxx**: Rust-C++ FFI 桥接
- **moxcms**: ICC 配置文件解析
- **zune-jpeg**: 嵌入式 JPEG 解码
- **png** crate: 嵌入式 PNG 解码
- `rust/common`: 共享 FFI 工具
- `rust/icc`: ICC 配置文件解析封装

## 相关文档与参考

- Skia 编解码器: `src/codec/`
- Rust PNG 解码器: `rust/png/`
- Rust ICC 解析器: `rust/icc/`
