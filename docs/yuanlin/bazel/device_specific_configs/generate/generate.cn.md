# Bazel 设备特定配置生成器

> 源文件: `bazel/device_specific_configs/generate/generate.go`

## 概述

此程序生成 Bazel 设备特定测试配置文件 (`devicesrc`)，为不同的硬件设备生成相应的 Bazel 测试标志和参数。生成的文件控制测试如何在特定设备上执行，特别是确保设备特定测试在本地运行而非远程执行。

## 架构位置

位于 Bazel 构建基础设施 (`bazel/device_specific_configs/generate/`) 中，是一个代码生成工具。通过 `go:generate` 指令与 Bazel 集成。

## 主要类与结构体

无自定义结构体。使用 `device_specific_configs.Configs` 映射表作为输入数据源。

## 公共 API 函数

- `main()` - 解析 `--output-file` 命令行标志并调用 `writeDeviceFlagsFile`
- `writeDeviceFlagsFile(outputFile)` - 生成设备配置文件的核心逻辑
- `writeFlag(sb, configName, flagName, flagValue)` - 写入 Bazel 标志行
- `writeTestArgFlag(sb, configName, testArgFlag)` - 写入测试参数行

## 内部实现细节

- 使用 `strings.Builder` 构建输出内容，对配置名排序以确保输出确定性
- 为每个设备配置添加 `--strategy=TestRunner=local`，强制测试在本地执行
- 通过 `config.TestRunnerArgs()` 获取每个设备的特定测试参数
- 输出格式符合 Bazel 的 `.bazelrc` 语法：`test:<config> --flag=value`
- 详细注释解释了 `--strategy` 和 `--spawn_strategy` 的关系及其工作原理

## 依赖关系

- `go.skia.org/skia/bazel/device_specific_configs` - 设备配置定义
- Go 标准库：`flag`, `fmt`, `os`, `sort`, `strings`

## 设计模式与设计决策

- **代码生成模式**：通过 Go 程序生成 Bazel 配置文件，而非手动维护
- **本地执行策略**：设备特定测试必须在有物理设备访问权限的本地机器上运行
- **确定性输出**：通过排序配置名确保每次生成的文件内容一致

## 性能考量

作为一次性生成工具，性能不是主要关注点。

## 相关文件

- `bazel/device_specific_configs/configs.go` - 设备配置定义
- `bazel/devicesrc` - 生成的输出文件
