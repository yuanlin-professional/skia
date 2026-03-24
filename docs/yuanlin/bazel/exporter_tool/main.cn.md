# Bazel 导出工具主程序

> 源文件: `bazel/exporter_tool/main.go`

## 概述

此文件是 Skia Bazel 构建规则导出工具的主入口点。它将 Bazel 工作区中定义的构建规则导出为 GNI（GN Include）或 CMake 格式的项目文件。该工具是 Skia 双构建系统（Bazel + GN）共存策略的关键组件，确保两个构建系统之间的文件列表保持同步。

## 架构位置

位于 Bazel 构建工具链 (`bazel/exporter_tool/`) 中，作为命令行工具运行。它是 `bazel/exporter/` 包中导出器实现的使用者和配置者。

## 主要类与结构体

### `fileSystem`
- 实现了 `interfaces.FileSystem` 接口
- `workspaceDir` - Bazel 工作区目录
- `outFormat` - 输出格式（"cmake" 或 "gni"）
- `openFiles` - 跟踪打开的文件以确保关闭

### `gniExportDescs`
- 类型 `[]exporter.GNIExportDesc` 的大型配置数组
- 定义了所有需要导出的 GNI 文件及其对应的 Bazel 规则映射
- 涵盖 codec、core、effects、graphite、pathops、ports、pdf、sksl、gpu 等所有主要模块

## 公共 API 函数

- `main()` - 解析命令行参数，创建查询命令和导出器，执行导出
- `createExporter()` - 根据输出格式创建 CMake 或 GNI 导出器
- `doExport()` - 执行实际的导出操作

### fileSystem 方法
- `OpenFile(path)` - 创建输出文件
- `ReadFile(filename)` - 读取文件内容
- `Shutdown()` - 关闭所有打开的文件

## 内部实现细节

- 支持两种查询模式：GNI 使用 `bazel query`（无需配置），CMake 使用 `bazel cquery`（需要配置解析）
- `gniExportDescs` 是核心配置表，精确映射了每个 GNI 变量到一个或多个 Bazel 规则
- 支持 CPU profiling（`--cpuprofile` 参数）用于性能分析
- 命令行参数包括：`--rule`（Bazel 规则）、`--output_format`（输出格式）、`--out`（CMake 输出文件）、`--proj_name`（项目名）
- 工作区目录通过 `os.Getwd()` 自动检测
- 涵盖了 Skia 的几乎所有模块：codec、core、effects、graphite、ganesh、pathops、ports、pdf、sksl、svg、skparagraph、skshaper、skunicode、skottie、skcms 等

## 依赖关系

- `go.skia.org/skia/bazel/exporter` - 导出器核心实现
- `go.skia.org/skia/bazel/exporter/interfaces` - 接口定义
- `go.skia.org/infra/go/common` - Skia 基础设施公共库
- `go.skia.org/infra/go/skerr` - 错误处理工具
- Go 标准库：`flag`, `fmt`, `os`, `runtime/pprof`

## 设计模式与设计决策

- **策略模式**：通过 `interfaces.Exporter` 接口支持多种输出格式，运行时选择 CMake 或 GNI 导出器
- **配置驱动**：所有 Bazel 到 GNI 的映射关系通过 `gniExportDescs` 数据表声明式定义
- **单一职责**：fileSystem 结构体封装所有文件系统操作，便于测试中使用 mock
- **Bazel 作为 Source of Truth**：GNI 文件由 Bazel 规则自动生成，保证两个构建系统的一致性

## 性能考量

- 内置 CPU profiling 支持，可分析导出过程的性能瓶颈
- GNI 导出使用 `bazel query`（而非 `cquery`）避免不必要的配置解析
- 文件在 Shutdown 时统一关闭，减少文件句柄管理开销

## 相关文件

- `bazel/exporter/gni_exporter.go` - GNI 导出器实现
- `bazel/exporter/cmake_exporter.go` - CMake 导出器实现
- `bazel/exporter/bazel_query_command.go` - Bazel 查询命令
- `bazel/exporter/interfaces/` - 接口定义
