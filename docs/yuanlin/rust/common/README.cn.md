# rust/common - Rust FFI 共享工具

## 概述

`rust/common/` 包含 Skia 所有 Rust 集成模块共享的 FFI 基础工具，主要解决
C++ 流（SkStream）与 Rust I/O trait 之间的适配问题。

## 目录结构

```
common/
├── BUILD.bazel          # Bazel 构建配置
├── io_traits_ffi.rs     # Rust I/O trait FFI 适配
├── SkStreamAdapter.cpp  # C++ 流适配器实现
├── SkStreamAdapter.h    # 流适配器头文件声明
└── SpanUtils.h          # Span 工具类
```

## 关键文件

- **SkStreamAdapter**: 将 Skia 的 `SkStream` C++ 类适配为 Rust `std::io::Read`
  trait，使 Rust 解码器可以透明地从 Skia 数据流中读取数据
- **io_traits_ffi.rs**: Rust 侧的 I/O trait 实现，通过 FFI 回调 C++ 流操作
- **SpanUtils.h**: 用于在 C++ 和 Rust 之间安全传递连续内存块的工具

## 依赖关系

- Skia `SkStream` 基础类
- CXX 桥接框架

## 相关文档与参考

- ICC 解析模块: `rust/icc/`
- PNG 编解码模块: `rust/png/`
- Skia 流 API: `include/core/SkStream.h`
