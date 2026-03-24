# FilterFuzz - 滤镜模糊测试骨架

> 源文件: `experimental/filterfuzz/filterfuzz.cpp`

## 概述

`filterfuzz.cpp` 是一个极简的 Skia 应用程序骨架，作为滤镜模糊测试（fuzz testing）的入口点。它初始化 Skia 图形引擎并解析命令行参数，目前只定义了一个简单的选项检查。

## 架构位置

位于 `experimental/filterfuzz/` 目录，属于 Skia 的实验性测试工具。该文件依赖 Skia 核心库和命令行标志工具。

## 主要类与结构体

无自定义类或结构体。使用了 Skia 的 `CommandLineFlags` 宏 `DEFINE_int_2` 定义命令行选项。

## 公共 API 函数

- `main(int argc, char** argv)`: 应用程序入口
- `exitf(const char* format, ...)`: 格式化错误输出并退出的辅助函数

## 内部实现细节

1. `CommandLineFlags::Parse` 解析命令行参数
2. 检查 `FLAGS_option` 标志值，若非零则退出并报告无效选项
3. 调用 `SkGraphics::Init()` 初始化 Skia 图形子系统
4. `exitf` 函数使用 `SK_PRINTF_LIKE` 属性进行编译器格式字符串检查

## 依赖关系

- `include/core/SkGraphics.h`: Skia 图形初始化
- `tools/flags/CommandLineFlags.h`: Skia 命令行参数解析框架

## 设计模式与设计决策

- 最小化的应用框架，作为模糊测试工具的基础结构
- 使用 Skia 内置的命令行标志系统，保持与其他 Skia 工具一致的接口风格
- `exitf` 前向声明使用 `SK_PRINTF_LIKE` 属性以启用编译期格式字符串安全检查

## 性能考量

无特殊性能考量。该程序主要用于测试目的。

## 相关文件

- `tools/flags/CommandLineFlags.h`: 命令行参数解析工具
- `fuzz/`: Skia 主要的模糊测试目录
