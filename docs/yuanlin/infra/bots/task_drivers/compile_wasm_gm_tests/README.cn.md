# compile_wasm_gm_tests - WASM GM 测试编译驱动

## 概述

编译 WebAssembly 版本的 GM（Golden Master）测试。将 Skia 的 GM 测试编译为 WASM 模块，以便在浏览器环境中运行。

## 目录结构

```
compile_wasm_gm_tests/
├── compile_wasm_gm_tests.go   # 主程序
└── BUILD.bazel                # Bazel 构建文件
```

## 依赖关系

- Emscripten SDK（EMSDK）
- CanvasKit 构建基础设施

## 相关文档与参考

- `run_wasm_gm_tests/` - 运行编译后的 WASM GM 测试
