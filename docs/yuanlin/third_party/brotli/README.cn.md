# third_party/brotli - Brotli 压缩库

## 概述

`third_party/brotli/` 包含 Google Brotli 压缩库的 Skia 构建配置。Brotli
是一种通用的无损压缩算法，在 Web 字体（WOFF2 格式）中广泛使用。Skia 使用
Brotli 来解压 WOFF2 字体数据。

## 目录结构

```
brotli/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 Brotli 的编译选项

## 依赖关系

- Brotli 源码（通过 DEPS 拉取）

## 相关文档与参考

- Brotli: https://github.com/google/brotli
- WOFF2 格式: https://www.w3.org/TR/WOFF2/
- Skia 字体处理: `src/ports/`
