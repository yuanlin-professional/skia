# third_party/highway - Google Highway SIMD 库

## 概述

`third_party/highway/` 包含 Google Highway 库的 Skia 构建配置。Highway 是一个
跨平台的 SIMD（单指令多数据）抽象库，提供统一的 API 来编写可在 x86（SSE/AVX）、
ARM（NEON/SVE）等平台上高效运行的向量化代码。

## 目录结构

```
highway/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 Highway 库的编译选项

## 依赖关系

- Highway 源码（通过 DEPS 拉取）

## 相关文档与参考

- Highway: https://github.com/google/highway
- Skia SIMD 优化: `src/opts/`
- Skia 光栅管线: `src/core/SkRasterPipeline.h`
