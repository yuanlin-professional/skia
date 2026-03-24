# third_party/perfetto - Perfetto 性能跟踪

## 概述

`third_party/perfetto/` 包含 Google Perfetto 系统级跟踪框架的 Skia 构建配置。
Perfetto 用于收集和分析性能跟踪数据，帮助开发者诊断 Skia 的性能问题。

## 目录结构

```
perfetto/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 Perfetto SDK 的编译和链接选项

## 依赖关系

- Perfetto SDK 源码（通过 DEPS 拉取）

## 相关文档与参考

- Perfetto 官方文档: https://perfetto.dev/
- Skia 性能跟踪: `tools/trace/`
