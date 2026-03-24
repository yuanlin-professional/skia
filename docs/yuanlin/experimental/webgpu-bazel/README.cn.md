# webgpu-bazel - WebGPU Bazel 构建实验

## 概述

`experimental/webgpu-bazel/` 是一个使用 Bazel 构建系统将 Skia 编译为
WebAssembly 并通过 WebGPU API 进行 GPU 加速渲染的实验项目。它展示了如何
利用 Dawn WebGPU 后端在浏览器中运行 Skia 的 GPU 渲染管线。

## 目录结构

```
webgpu-bazel/
├── Makefile             # 顶层构建脚本
├── example/             # 示例页面
│   └── index.html       # WebGPU 演示页面
└── src/                 # 源码
    ├── BUILD.bazel      # Bazel 构建规则
    └── bindings.cpp     # WebGPU C++ 绑定
```

## 关键文件

- **Makefile**: 提供 `release`、`debug`、`serve` 三个目标
  - `make release` - 优化模式编译 WASM
  - `make debug` - 调试模式编译 WASM
  - `make serve` - 启动本地 Web 服务器

- **src/bindings.cpp**: WebGPU 绑定的 C++ 实现
- **example/index.html**: 加载 WASM 并初始化 WebGPU 的演示页面

## 构建方式

```bash
# 编译 release 版本
bazelisk build //experimental/webgpu-bazel/src:hello-world-wasm \
    --compilation_mode opt --gpu_backend=dawn_backend

# 启动本地服务器
python3 tools/serve_wasm.py
```

## 依赖关系

- Bazel / Bazelisk 构建系统
- Dawn WebGPU 后端
- Emscripten（WebAssembly 编译）
- Skia 核心库 + GPU 后端

## 相关文档与参考

- Dawn WebGPU: `third_party/dawn/`
- WebGPU 标准: https://www.w3.org/TR/webgpu/
- CanvasKit: `modules/canvaskit/`（另一种 WASM 方案）
