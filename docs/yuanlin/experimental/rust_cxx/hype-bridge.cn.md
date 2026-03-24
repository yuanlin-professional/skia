# Hype Bridge - Rust/C++ CXX 桥接示例

> 源文件: `experimental/rust_cxx/hype-bridge.rs`

## 概述

`hype-bridge.rs` 是一个使用 `cxx` crate 实现的 Rust/C++ 互操作示例。它定义了一个简单的 `hypeify` 函数，将输入字符串转换为大写并追加指定数量的感叹号，通过 CXX 桥接暴露给 C++ 调用。

## 架构位置

位于 `experimental/rust_cxx/` 目录，属于 Skia 实验性 Rust 集成的概念验证（POC）。探索了在 Skia 构建系统中使用 Rust 编写组件并从 C++ 调用的可行性。

## 主要类与结构体

- **`HypeOutput`**: CXX 桥接结构体
  - `output: String`: 处理后的字符串
  - `new_len: usize`: 结果字符串长度

## 公共 API 函数

- **`hypeify(input: String, num_exclamations: i32) -> HypeOutput`**: 将字符串转为大写并追加感叹号
  - 通过 `#[cxx::bridge]` 宏暴露给 C++
  - 位于 `hype_train` 命名空间

## 内部实现细节

1. `cxx::bridge` 宏定义 FFI 接口，指定 C++ 命名空间为 `hype_train`
2. `ffi` 模块声明跨语言接口：共享结构体 `HypeOutput` 和 Rust 导出函数 `hypeify`
3. 函数实现使用 Rust 标准库的 `to_uppercase()` 方法和字符串拼接

## 依赖关系

- Rust `cxx` crate: 提供安全的 C++/Rust 互操作
- 生成的 C++ 头文件: `gen/hype-bridge.rs.h`

## 设计模式与设计决策

- 使用 CXX 而非 FFI 手动绑定，获得类型安全的跨语言调用
- 共享结构体 `HypeOutput` 可以在两种语言间零拷贝传递（CXX 管理内存布局）
- 命名空间 `hype_train` 避免与其他 C++ 符号冲突

## 性能考量

无特殊性能考量，此为概念验证代码。

## 相关文件

- `experimental/rust_cxx/main.cpp`: C++ 端调用此 Rust 函数
- `experimental/rust_cxx/hello-world.rs`: 更简单的 Rust 示例
