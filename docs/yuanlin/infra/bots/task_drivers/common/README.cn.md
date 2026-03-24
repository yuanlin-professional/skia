# common - 任务驱动共享库

## 概述

提供任务驱动程序之间共享的工具函数和通用逻辑。这不是独立的任务驱动，而是一个被其他驱动引用的共享 Go 包。

## 目录结构

```
common/
├── bazel_clean_step.go        # Bazel 清理步骤
├── bazel_clean_step_test.go   # Bazel 清理测试
├── bazel_flags.go             # Bazel 命令行标志
├── bazel_utils.go             # Bazel 工具函数
├── bazel_utils_test.go        # Bazel 工具测试
├── perf_steps.go              # 性能评测步骤
├── perf_steps_test.go         # 性能步骤测试
└── BUILD.bazel                # Bazel 构建文件
```

## 关键文件

- `bazel_utils.go` - Bazel 构建和测试的通用操作封装
- `bazel_flags.go` - Bazel 命令行标志定义
- `perf_steps.go` - 性能评测数据收集和上传步骤

## 依赖关系

- 被 `bazel_build/`、`cpu_tests/` 等多个任务驱动引用

## 相关文档与参考

- 父目录 `task_drivers/` 说明
