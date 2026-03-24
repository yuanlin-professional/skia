# GNI 导出器测试

> 源文件: `bazel/exporter/gni_exporter_test.go`

## 概述

此文件全面测试 GNI 导出器的功能，包括完整的导出流程、路径转换、变量替换、文件分类、去重排序等。使用手工构建的 protobuf 数据和预期的 GNI 文件内容进行黄金文件比较。

## 架构位置

位于 `bazel/exporter/` 包的测试层，是最全面的 GNI 导出器测试套件。

## 主要类与结构体

定义了 `publicSrcsExpectedGNI` 常量作为期望输出，以及 `exportDescs` 和 `testExporterParams` 测试配置。

## 公共 API 函数

核心测试函数：
- `TestGNIExporterExport_ValidInput_Success` - 完整导出流程测试
- `TestMakeRelativeFilePathForGNI_*` - 路径变量替换
- `TestIsHeaderFile_*` - 头文件检测
- `TestFileListContainsOnlyCppHeaderFiles_*` - 纯头文件列表检测
- `TestWorkspaceToAbsPath_*` / `TestAbsToWorkspacePath_*` - 路径转换
- `TestGetGNILineVariable_*` - GNI 变量提取
- `TestExtractTopLevelFolder_*` - 顶级目录提取
- `TestAddGNIVariablesToWorkspacePaths_*` - 批量路径变量替换
- `TestConvertTargetsToFilePaths_*` - 目标到文件路径转换
- `TestRemoveDuplicate_*` - 去重排序
- `TestGetPathToTopDir_*` - 相对路径计算

## 内部实现细节

- `createCoreSourcesQueryResult` 手动构建 QueryResult protobuf，不依赖 Bazel
- 使用 mock 文件系统验证输出路径正确性
- 测试覆盖各种边界情况：空输入、无效路径、Unicode 字符等

## 依赖关系

- `github.com/stretchr/testify` - 断言和 mock
- `google.golang.org/protobuf/proto` - protobuf 序列化

## 设计模式与设计决策

- **表驱动测试**：大量使用子测试和表驱动方式
- **构建测试数据**：手工构建 protobuf 对象，而非从文件加载

## 性能考量

无特殊考量。

## 相关文件

- `bazel/exporter/gni_exporter.go` - 被测代码
