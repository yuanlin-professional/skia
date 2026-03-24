# run_wasm_gm_tests - WASM GM 测试运行驱动

## 概述

运行由 `compile_wasm_gm_tests` 编译的 WebAssembly GM 测试，在浏览器环境中执行并收集结果。

## 目录结构

```
run_wasm_gm_tests/
├── run_wasm_gm_tests.go   # 主程序
└── BUILD.bazel            # Bazel 构建文件
```

## 依赖关系

- `compile_wasm_gm_tests/` 的编译产出
- Chrome 浏览器环境

## 相关文档与参考

- `compile_wasm_gm_tests/` - WASM GM 测试编译驱动
