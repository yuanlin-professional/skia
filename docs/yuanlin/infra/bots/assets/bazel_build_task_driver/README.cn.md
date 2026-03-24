# bazel_build_task_driver - Bazel 构建任务驱动二进制

## 概述

预编译的 Bazel 构建任务驱动程序二进制资源。该程序在 CI 中执行 Bazel 构建任务。

## 目录结构

```
bazel_build_task_driver/
├── create.py   # 自动化创建脚本（编译并打包）
└── VERSION     # 当前版本号
```

## 依赖关系

- 来源于 `infra/bots/task_drivers/bazel_build/` 的编译输出
- 被 Bazel 构建 CI 任务使用

## 相关文档与参考

- `infra/bots/task_drivers/bazel_build/` - 源代码
