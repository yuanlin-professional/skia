# rust_cxx - Rust-C++ CXX 桥接实验

## 概述

`experimental/rust_cxx/` 是一个 Rust 与 C++ 互操作的实验项目，使用 CXX 库在
Rust 和 C++ 之间建立安全的函数调用桥接。该目录探索了将 Rust 代码集成到 Skia
C++ 代码库的最佳实践。

## 目录结构

```
rust_cxx/
├── BUILD.bazel          # Bazel 构建配置
├── hello-world.rs       # Rust 侧 Hello World 示例
├── hype-bridge.rs       # Rust-C++ 桥接示例
└── main.cpp             # C++ 侧入口程序
```

## 关键文件

- **hello-world.rs**: 展示基本的 Rust 函数暴露给 C++ 的方式
- **hype-bridge.rs**: 更复杂的 CXX 桥接示例，演示类型映射
- **main.cpp**: C++ 侧调用 Rust 函数的示例代码

## 依赖关系

- Rust 工具链
- **cxx** crate: Rust-C++ 安全桥接框架
- Bazel 构建系统

## 相关文档与参考

- CXX 官方文档: https://cxx.rs/
- Rust BMP 解码器: `experimental/rust_bmp/`（实际应用案例）
- Rust 集成: `rust/` 目录
