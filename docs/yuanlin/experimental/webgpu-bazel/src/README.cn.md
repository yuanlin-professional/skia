# webgpu-bazel/src - WebGPU 绑定源码

## 概述

`src/` 包含 WebGPU WASM 应用的核心源码和 Bazel 构建配置。

## 目录结构

```
src/
├── BUILD.bazel      # Bazel 构建规则（定义 hello-world-wasm 目标）
└── bindings.cpp     # WebGPU C++ 绑定实现
```

## 关键文件

- **BUILD.bazel**: 定义 `hello-world-wasm` 构建目标，配置 Dawn 后端
  和 Emscripten 编译选项
- **bindings.cpp**: Skia 与 WebGPU 的绑定代码，初始化 GPU 上下文并执行渲染

## 依赖关系

- Skia 核心库
- Dawn WebGPU 实现
- Emscripten SDK

## 相关文档与参考

- 示例页面: `../example/`
- Dawn 构建: `third_party/dawn/`
