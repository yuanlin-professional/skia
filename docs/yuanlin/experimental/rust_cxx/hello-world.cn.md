# Hello World - Rust 最小示例

> 源文件: `experimental/rust_cxx/hello-world.rs`

## 概述

`hello-world.rs` 是一个最小化的 Rust 程序，用于验证 Skia 的 GN 构建系统能够正确编译和链接 Rust 源文件。它仅打印两行消息并退出。

## 架构位置

位于 `experimental/rust_cxx/` 目录，作为 Skia Rust 集成的最基础验证用例。

## 主要类与结构体

无。

## 公共 API 函数

- `main()`: 程序入口，打印 "Hello Rust!" 和 "Run from GN"

## 内部实现细节

仅包含两个 `println!` 宏调用。

## 依赖关系

- Rust 标准库

## 设计模式与设计决策

- 最小化实现，专注于验证构建系统集成

## 性能考量

无。

## 相关文件

- `experimental/rust_cxx/hype-bridge.rs`: 更复杂的 Rust/C++ 互操作示例
- `experimental/rust_cxx/main.cpp`: C++ 端的配合程序
