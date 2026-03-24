# rust_bmp/ffi - BMP 解码器 Rust FFI 核心

## 概述

`ffi/` 目录包含 BMP 解码器的 Rust 核心实现代码，以及通过 CXX 桥接暴露给
C++ 层的 FFI（外部函数接口）代码。这里是实际的 BMP 解析和解码逻辑所在。

## 目录结构

```
ffi/
├── BUILD.bazel          # Bazel 构建配置
├── FFI.rs               # CXX 桥接接口定义
├── lib.rs               # Rust crate 根文件
├── bmp_decoder.rs       # BMP 解码主逻辑
├── bmp_header.rs        # 文件头和信息头解析
├── bmp_constants.rs     # BMP 格式常量
├── bmp_types.rs         # 数据类型定义
├── bmp_icc.rs           # ICC 色彩配置文件支持
├── bmp_jpeg_decoder.rs  # BMP 中嵌入的 JPEG 数据处理
└── bmp_png_decoder.rs   # BMP 中嵌入的 PNG 数据处理
```

## 关键文件

- **FFI.rs**: CXX 桥接定义，声明 Rust 和 C++ 之间的函数和类型映射
- **bmp_decoder.rs**: 核心解码逻辑，处理像素数据的读取和转换
- **bmp_header.rs**: BMP 文件头解析，包含全面的验证逻辑

## 依赖关系

- **cxx** crate: Rust-C++ 安全桥接
- **moxcms**: ICC 配置文件解析
- **zune-jpeg**: JPEG 解码（用于 BMP 中嵌入的 JPEG）
- **png** crate: PNG 解码（用于 BMP 中嵌入的 PNG）

## 相关文档与参考

- C++ 集成层: `experimental/rust_bmp/decoder/`
- CXX 桥接文档: https://cxx.rs/
