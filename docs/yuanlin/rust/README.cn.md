# rust/ - Skia Rust 集成模块

## 概述

`rust/` 目录包含 Skia 的 Rust 语言集成代码，提供辅助工具、简化封装和 FFI
（外部函数接口）桥接，使 Skia 的 C/C++ 代码能够调用 Rust crate 的功能。
这是 Skia 逐步引入 Rust 内存安全代码的核心基础设施。

## 目录结构

```
rust/
├── README.md            # 项目说明
├── common/              # 共享 FFI 工具
│   ├── BUILD.bazel      # Bazel 构建配置
│   ├── io_traits_ffi.rs # I/O 特征 FFI 适配
│   ├── SkStreamAdapter.cpp  # C++ 流适配器
│   ├── SkStreamAdapter.h    # 流适配器头文件
│   └── SpanUtils.h      # Span 工具类
├── icc/                 # ICC 配置文件解析器
│   ├── BUILD.bazel      # Bazel 构建配置
│   ├── FFI.cpp          # C++ 侧 FFI 实现
│   ├── FFI.h            # FFI 头文件
│   ├── FFI.rs           # Rust 侧 FFI 定义
│   └── README.md        # ICC 解析器文档
└── png/                 # PNG 编解码器
    ├── BUILD.bazel      # Bazel 构建配置
    ├── FFI.h            # FFI 头文件
    ├── FFI.rs           # Rust 侧 FFI 定义
    └── README.md        # PNG 编解码器文档
```

## 关键文件

- **common/SkStreamAdapter**: 将 Skia 的 `SkStream` 适配为 Rust 的 `Read` trait
- **icc/FFI.rs**: ICC 配置文件解析的 CXX 桥接定义
- **png/FFI.rs**: PNG 编解码的 CXX 桥接定义

## 依赖关系

- Rust 工具链
- **cxx** crate: Rust-C++ 安全桥接
- **moxcms**: ICC 配置文件解析
- **png** crate: PNG 编解码
- Skia 核心库

## 相关文档与参考

- Rust BMP 解码器: `experimental/rust_bmp/`
- Rust CXX 实验: `experimental/rust_cxx/`
- CXX 文档: https://cxx.rs/
