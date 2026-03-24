# rust_bmp/decoder - BMP Rust 解码器 C++ 集成层

## 概述

`decoder/` 目录包含将 Rust BMP 解码器集成到 Skia C++ 编解码框架的适配代码。
它实现了标准的 `SkCodec` 接口，使 Rust 解码器可以无缝融入 Skia 现有的图像
处理管线。

## 目录结构

```
decoder/
├── BUILD.bazel              # Bazel 构建配置
├── SkBmpRustDecoder.h       # 公共工厂函数声明
├── SkBmpRustDecoder.cpp     # 工厂函数实现
└── impl/
    ├── SkBmpRustCodec.h     # 核心编解码器类声明
    └── SkBmpRustCodec.cpp   # 核心编解码器类实现
```

## 关键文件

- **SkBmpRustDecoder.h/.cpp**: 提供 SkCodec 工厂方法，用于从数据流创建
  BMP Rust 解码器实例
- **impl/SkBmpRustCodec.h/.cpp**: `SkBmpRustCodec` 类的完整实现，继承自
  `SkCodec`，封装 Rust FFI 调用

## 依赖关系

- Skia `SkCodec` 框架（`src/codec/`）
- Rust FFI 层（`../ffi/`）
- CXX 生成的 C++ 头文件

## 相关文档与参考

- Rust FFI 层: `experimental/rust_bmp/ffi/`
- Skia 编解码器架构: `src/codec/`
