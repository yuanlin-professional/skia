# third_party/cpu-features - CPU 特性检测

## 概述

`third_party/cpu-features/` 包含 Google cpu_features 库的 Skia 构建配置。
该库提供运行时 CPU 特性检测功能，可以查询处理器支持的指令集扩展（如 SSE、
AVX、NEON 等），帮助 Skia 在运行时选择最优的代码路径。

## 目录结构

```
cpu-features/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 cpu_features 的编译选项

## 依赖关系

- cpu_features 源码（通过 DEPS 拉取）

## 相关文档与参考

- cpu_features: https://github.com/google/cpu_features
- Skia SIMD 优化: `src/opts/`
