# Rust CXX Main - C++ 端 Rust 互操作示例

> 源文件: `experimental/rust_cxx/main.cpp`

## 概述

`main.cpp` 是 Rust/C++ CXX 互操作实验的 C++ 端入口程序。它通过 CXX 自动生成的头文件调用 Rust 实现的 `hypeify` 函数，演示了从 C++ 调用 Rust 代码的完整流程。

## 架构位置

位于 `experimental/rust_cxx/` 目录，与 `hype-bridge.rs` 配对使用，共同构成 Skia Rust 集成的概念验证。

## 主要类与结构体

使用由 CXX 生成的 `hype_train::HypeOutput` 结构体（定义在 Rust 侧）。

## 公共 API 函数

- `main(int argc, char** argv)`: 程序入口，调用 Rust 函数并打印结果

## 内部实现细节

1. 包含 CXX 自动生成的头文件 `experimental/rust_cxx/gen/hype-bridge.rs.h`
2. 调用 `hype_train::hypeify("it works", 3)` 传入字符串和感叹号数量
3. 输出转换后的字符串（"IT WORKS!!!"）和新长度

## 依赖关系

- 自动生成的 CXX 桥接头文件: `gen/hype-bridge.rs.h`
- C 标准库: `<stdio.h>`, `<string>`

## 设计模式与设计决策

- 通过 CXX 生成的头文件实现类型安全的跨语言调用
- 使用 C++ `std::string` 与 Rust `String` 之间的自动转换

## 性能考量

无特殊性能考量，此为概念验证代码。

## 相关文件

- `experimental/rust_cxx/hype-bridge.rs`: Rust 端的函数实现
- `experimental/rust_cxx/hello-world.rs`: 简单的 Rust 构建验证
