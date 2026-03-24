# cpu_tests - CPU 测试 Bazel 任务驱动

> 源文件: `infra/bots/task_drivers/cpu_tests/cpu_tests.go`

## 概述

`cpu_tests` 是一个简洁的任务驱动,用于在 CI 环境中通过 Bazel 运行 Skia 的 CPU 测试。它处理 Bazel 环境设置(缓存路径、RC 文件),执行 `bazelisk test` 命令,并在完成后检查磁盘空间以决定是否清理 Bazel 缓存。

## 架构位置

属于 Skia Bazel 测试执行子系统,是 CI 中 CPU 测试任务的标准入口。

## 主要类与结构体

无自定义结构体。使用 `common.BazelFlags` 管理标志。

## 公共 API 函数

- **`main()`**: 解析标志、配置 Bazel、运行测试、清理缓存
- **`bazelTest()`**: 执行 `bazelisk test <label> --config=<config> --test_output=errors`

## 内部实现细节

- 使用 `bazel.EnsureBazelRCFile` 配置 Bazel RC 文件(主要是缓存路径)
- 测试输出模式为 `errors`(只显示失败的测试输出)
- 非本地模式下执行磁盘空间检查和可能的缓存清理

## 依赖关系

- Bazelisk - Bazel 版本管理
- `go.skia.org/skia/infra/bots/task_drivers/common` - Bazel 公共工具
- `go.skia.org/infra/task_driver/go/lib/bazel` - Bazel 配置

## 设计模式与设计决策

- **最小化驱动**: 专注于单一职责(运行 Bazel 测试)
- **缓存管理**: 自动检测和清理以防止磁盘空间警告

## 性能考量

Bazel 缓存可显著加速增量测试。缓存路径应位于大容量磁盘上。

## 相关文件

- `infra/bots/task_drivers/common/bazel_flags.go` - Bazel 标志
- `infra/bots/task_drivers/common/bazel_clean_step.go` - 缓存清理
