# main_wasm - WebAssembly 平台应用程序入口

> 源文件: `tools/sk_app/wasm/main_wasm.cpp`

## 概述

main_wasm.cpp 是 Skia sk_app 框架在 WebAssembly 平台上的应用程序入口占位文件。目前仅输出 "Hello world"，尚未实现完整的 Canvas2D/WebGL/WebGPU 渲染功能。

## 架构位置

位于 `tools/sk_app/wasm/` 目录，属于 sk_app 框架的 WebAssembly 平台适配层。

## 主要类与结构体

无。

## 公共 API 函数

### `main(int argc, char** argv)`
标准 C 入口点，当前仅打印调试信息。

## 内部实现细节

文件内容极为简洁，仅包含一个 `printf` 调用和一个 TODO 注释，表明将来需要实现对 Canvas2D、WebGL Canvas 或 WebGPU Canvas 的绘制支持。

## 依赖关系

- `<iostream>` - 标准 I/O

## 设计模式与设计决策

- **占位实现**: 作为 WASM 平台支持的起点，预留了未来扩展的空间
- 计划支持 Canvas2D、WebGL 和 WebGPU 三种渲染后端

## 性能考量

无实质性功能，无性能考量。

## 相关文件

- `tools/sk_app/Application.h` - Application 基类接口
