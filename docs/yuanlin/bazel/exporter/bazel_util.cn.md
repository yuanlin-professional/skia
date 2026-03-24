# Bazel 工具函数

> 源文件: `bazel/exporter/bazel_util.go`

## 概述

此文件提供 Bazel 规则解析和操作的核心工具函数，包括规则名解析、文件位置解析、规则查找、属性提取和名称转换等。是 GNI 和 CMake 导出器共用的基础设施层。

## 架构位置

位于 `bazel/exporter/` 包中，是导出器的公共工具层，被 `gni_exporter.go` 和 `cmake_exporter.go` 广泛使用。

## 主要类与结构体

无独立结构体。定义了三个正则表达式用于解析：
- `ruleOnlyRepoPattern` - 纯仓库名（如 `@libpng`）
- `rulePattern` - 完整规则名（如 `//foo/bar:wiz`）
- `locationPattern` - 文件位置（如 `/path/file:12:5`）

## 公共 API 函数

- `isExternalRule(name)` - 判断是否为外部仓库规则
- `findRule(qr, name)` - 在 CqueryResult 中查找规则
- `parseRule(rule)` - 解析规则为 repo/path/target 三部分
- `parseLocation(location)` - 解析文件位置为 path/line/pos
- `getLocationDir(location)` - 获取位置的目录部分
- `makeCanonicalRuleName(name)` - 生成规范化规则名
- `isFileTarget(target)` - 判断目标是否指向文件
- `getRuleSimpleName(name)` - 生成适合导出项目文件的简单名称
- `appendUnique(slice, elems...)` - 去重追加
- `getRuleStringArrayAttribute(r, name)` - 提取规则的字符串列表属性
- `getFilePathFromFileTarget(target)` - 目标名转工作区相对路径

## 内部实现细节

- `getRuleSimpleName` 将 `//include/private/chromium:private_hdrs` 转换为 `include_private_chromium_private_hdrs`
- 默认目标规则：`//tools/flags` 等同于 `//tools/flags:flags`
- 纯仓库规则：`@libpng` 等同于 `@libpng//:libpng`
- `isFileTarget` 通过检查目标名是否包含 `.` 来判断

## 依赖关系

- `go.skia.org/infra/go/util` - 集合操作
- `bazel/exporter/build_proto/` - protobuf 类型

## 设计模式与设计决策

- **正则驱动解析**：使用预编译正则表达式解析 Bazel 规则语法
- **约定优于配置**：遵循 Bazel 的默认目标命名约定

## 性能考量

正则表达式预编译为包级变量，避免重复编译开销。

## 相关文件

- `bazel/exporter/bazel_util_test.go` - 测试
