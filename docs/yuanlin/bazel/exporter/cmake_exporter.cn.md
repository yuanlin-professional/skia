# CMake 导出器

> 源文件: `bazel/exporter/cmake_exporter.go`

## 概述

此文件实现了 `CMakeExporter`，将 Bazel cquery 结果转换为 CMake 项目文件。它处理 `cc_binary`、`cc_library` 和 `filegroup` 三种规则类型，生成包含源文件列表、编译标志、链接标志、宏定义和包含目录的完整 CMakeLists.txt。

## 架构位置

位于 `bazel/exporter/` 包中，实现 `interfaces.Exporter` 接口。是 CMake 格式的具体导出器实现。

## 主要类与结构体

### `CMakeExporter`
- `projName` - CMake 项目名
- `workspace` - cmakeWorkspace 实例
- `workspaceDir` - 工作区绝对路径
- `cmakeFile` - 输出 CMake 文件路径
- `fs` - 文件系统接口

## 公共 API 函数

- `NewCMakeExporter(projName, workspaceDir, cmakeFile, fs)` - 创建导出器
- `Export(qcmd)` - 执行导出：解析 cquery 结果，转换规则，写出 CMake 文件

## 内部实现细节

- 平台编译标志：macOS 使用 `--target=arm64-apple-macos11`，Linux 使用 `-Wno-attributes`
- 跳过外部仓库规则（`@` 前缀）
- `convertCCBinaryRule` 生成 `add_executable` + `target_sources`
- `convertCCLibraryRule` 生成 `add_library` + `target_sources`
- `convertFilegroupRule` 生成 `list(APPEND ...)`
- 递归收集依赖的 includes 和 defines
- 路径转换：绝对路径 -> `${CMAKE_SOURCE_DIR}/...` 相对路径

## 依赖关系

- `bazel/exporter/build_proto/analysis_v2` - CqueryResult protobuf
- `bazel/exporter/build_proto/build` - Rule protobuf
- `bazel/exporter/interfaces` - Exporter 接口

## 设计模式与设计决策

- **递归属性收集**：`getRuleIncludes` 和 `getRuleDefines` 递归遍历依赖树收集属性
- **工作区管理**：通过 cmakeWorkspace 实现拓扑排序输出
- **跨平台支持**：生成的 CMake 包含 macOS 和 Linux 的条件编译标志

## 性能考量

递归遍历依赖树可能在大型项目中产生开销，但 Skia 的依赖深度有限。

## 相关文件

- `bazel/exporter/cmake_workspace.go`
- `bazel/exporter/cmake_rule.go`
- `bazel/exporter/bazel_util.go`
