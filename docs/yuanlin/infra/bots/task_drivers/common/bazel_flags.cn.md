# bazel_flags - Bazel 公共标志定义

> 源文件: `infra/bots/task_drivers/common/bazel_flags.go`

## 概述

`bazel_flags` 定义了 Skia 任务驱动中通用的 Bazel 命令行标志,包括标签、配置、设备特定配置、额外参数和缓存目录。提供标志声明和验证功能,被所有使用 Bazel 的任务驱动共享。

## 架构位置

属于任务驱动公共工具层(`common` 包),是 Bazel 任务驱动的基础组件。

## 主要类与结构体

- **`BazelFlags`**: 持有所有 Bazel 标志指针和必需性标记
- **`MakeBazelFlagsOpts`**: 控制哪些标志被声明的选项

## 公共 API 函数

- **`MakeBazelFlags(opts)`**: 根据选项声明命令行标志并返回 BazelFlags 实例
- **`BazelFlags.Validate(ctx)`**: 验证必需标志已提供,设备配置在已知列表中

## 内部实现细节

- `--bazel_label`: Bazel 目标标签(如 `//tests:foo`)
- `--bazel_config`: 自定义配置(定义在 `//bazel/buildrc`)
- `--device_specific_bazel_config`: 设备特定配置(定义在 `//bazel/devicesrc`)
- `--bazel_arg`: 额外参数(多值标志)
- `--bazel_cache_dir`: 缓存目录(必需)

## 依赖关系

- `go.skia.org/skia/bazel/device_specific_configs` - 设备配置验证
- `go.skia.org/infra/go/common` - 多值标志

## 设计模式与设计决策

- **可选声明**: 通过 `MakeBazelFlagsOpts` 控制哪些标志被声明,避免不需要的标志
- **严格验证**: 设备配置必须在预定义列表中,防止拼写错误

## 性能考量

标志解析和验证开销可忽略。

## 相关文件

- `bazel_clean_step.go` - 使用 CacheDir 的缓存清理
