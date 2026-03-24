# bazel_build - Bazel 构建任务驱动

## 概述

执行 Skia 的 Bazel 构建任务。此驱动程序在 CI 中使用 Bazel 构建系统编译 Skia 及其组件。

## 目录结构

```
bazel_build/
├── bazel_build.go   # 主程序
└── BUILD.bazel      # Bazel 构建文件
```

## 关键文件

### bazel_build.go
Bazel 构建的主逻辑，包括环境准备、Bazel 命令调用和结果收集。

## 依赖关系

- `common/` - 共享的 Bazel 工具函数
- Bazelisk 资源

## 相关文档与参考

- `infra/bots/assets/bazel/` - Bazel 工具资源
