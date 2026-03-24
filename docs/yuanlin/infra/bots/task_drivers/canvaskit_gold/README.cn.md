# canvaskit_gold - CanvasKit Gold 测试驱动

## 概述

执行 CanvasKit 的 Gold 视觉回归测试。将 CanvasKit（WebAssembly 版 Skia）的渲染结果与 Gold 基准进行比较。

## 目录结构

```
canvaskit_gold/
├── canvaskit_gold.go   # 主程序
└── BUILD.bazel         # Bazel 构建文件
```

## 依赖关系

- Skia Gold 服务
- CanvasKit WASM 构建产物
- Node.js 运行时

## 相关文档与参考

- [Skia Gold](https://gold.skia.org/)
- `infra/canvaskit/` - CanvasKit 构建脚本
