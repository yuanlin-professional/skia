# Bazel 查询命令

> 源文件: `bazel/exporter/bazel_query_command.go`

## 概述

此文件实现了 `BazelQueryCommand` 结构体，封装了对 Bazel 可执行文件的 `query` 和 `cquery` 命令调用。它是导出工具与 Bazel 构建系统之间的桥梁，负责执行规则查询并返回二进制 protobuf 格式的结果。

## 架构位置

位于 `bazel/exporter/` 包中，实现 `interfaces.QueryCommand` 接口，被 GNI 和 CMake 导出器使用。

## 主要类与结构体

### `BazelQueryCommand`
- `ruleNames []string` - 要查询的 Bazel 规则名列表
- `workspace string` - Bazel 工作区路径
- `queryType string` - 查询类型：`"query"` 或 `"cquery"`

## 公共 API 函数

- `NewBazelCMakeQueryCommand(ruleNames, workspace)` - 创建 cquery 命令（用于 CMake）
- `NewBazelGNIQueryCommand(ruleNames, workspace)` - 创建 query 命令（用于 GNI）
- `Read() ([]byte, error)` - 执行查询并返回 protobuf 结果

## 内部实现细节

- cquery 前会调用 `shutdownBazelServer()` 以解决已知的非确定性输出问题
- 查询表达式格式：`kind("rule", deps(rule1) + deps(rule2) + ...)`
- cquery 附加 Skia 特定标志（如 `--ck_enable_fonts`、`--ck_enable_skottie` 等）以启用所有源文件
- 使用 `bazelisk` 而非直接调用 `bazel`，确保使用正确的 Bazel 版本

## 依赖关系

- `go.skia.org/skia/bazel/exporter/interfaces` - QueryCommand 接口
- `go.skia.org/infra/go/skerr` - 错误处理

## 设计模式与设计决策

- **接口实现**：通过 `var _ interfaces.QueryCommand = (*BazelQueryCommand)(nil)` 编译时验证接口满足
- **cquery vs query**：CMake 需要配置解析（cquery），GNI 只需规则结构（query）

## 性能考量

cquery 需要先关闭 Bazel 服务器，增加了额外延迟，但这是解决非确定性输出的必要代价。

## 相关文件

- `bazel/exporter/interfaces/query_command.go`
- `bazel/exporter/cmake_exporter.go`
- `bazel/exporter/gni_exporter.go`
