# GNI 导出器

> 源文件: `bazel/exporter/gni_exporter.go`

## 概述

此文件实现了 `GNIExporter`，将 Bazel 工作区中的构建规则导出为 GN 的 `.gni` 文件格式。这是 Skia 双构建系统共存的核心组件，确保 GN 构建系统中的文件列表与 Bazel 中的定义保持同步。

## 架构位置

位于 `bazel/exporter/` 包中，实现 `interfaces.Exporter` 接口。是 GNI 格式的具体导出器实现。

## 主要类与结构体

### `GNIExporter`
- `workspaceDir string` - Bazel 工作区路径
- `fs interfaces.FileSystem` - 文件系统抽象
- `exportGNIDescs []GNIExportDesc` - 导出描述配置

### `GNIExportDesc`
- `GNI string` - 目标 `.gni` 文件路径
- `Vars []GNIFileListExportDesc` - 变量定义列表

### `GNIFileListExportDesc`
- `Var string` - GNI 变量名
- `Rules []string` - 对应的 Bazel 规则名

### `gniFileContents`
- 跟踪文件中使用的顶级目录（src/include/modules/rust/experimental）
- `bazelFiles map[string]bool` - 来源的 Bazel BUILD 文件集合
- `data []byte` - 文件内容数据

## 公共 API 函数

- `NewGNIExporter(params, filesystem)` - 创建 GNI 导出器
- `Export(qcmd)` - 执行导出：读取 Bazel 查询结果，生成所有 `.gni` 文件

## 内部实现细节

- 路径变量替换：`src/` -> `$_src/`, `include/` -> `$_include/`, `modules/` -> `$_modules/` 等
- 文件头包含来源 BUILD 文件的注释和路径变量定义
- 特定 `.gni` 文件有页脚（footerMap）：codec.gni、ports.gni、rust.gni、sksl_tests.gni、skshaper.gni
- 文件列表自动去重排序
- `getPathToTopDir` 计算从 GNI 文件位置到工作区根目录的相对路径
- `gniVariableDefReg` 正则匹配 GNI 变量定义格式

## 依赖关系

- `bazel/exporter/build_proto/build` - Bazel QueryResult protobuf
- `bazel/exporter/interfaces` - FileSystem 和 Exporter 接口
- `google.golang.org/protobuf/proto` - protobuf 序列化

## 设计模式与设计决策

- **内存缓冲**：先在内存中构建所有文件内容，再一次性写入，以便生成正确的头部变量声明
- **合并模式**：多个规则的文件可以合并到同一个 GNI 变量中
- **变量路径**：使用 GNI 变量（`$_src` 等）而非硬编码路径，保持构建系统的灵活性

## 性能考量

文件列表排序和去重使用标准排序，复杂度 O(n log n)。所有内容先缓冲再写入，减少 I/O 次数。

## 相关文件

- `bazel/exporter_tool/main.go` - 使用者和配置定义
- `bazel/exporter/gni_exporter_test.go` - 测试
- `gn/*.gni` - 生成的目标文件
