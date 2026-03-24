# CMake 工作区

> 源文件: `bazel/exporter/cmake_workspace.go`

## 概述

此文件定义了 `cmakeWorkspace`，管理整个 CMake 项目的状态。它负责创建、存储和按正确顺序写出所有 CMake 规则，确保依赖在被引用之前已被定义。

## 架构位置

位于 `bazel/exporter/` 包中，是 CMake 导出管线的输出组织层。

## 主要类与结构体

### `cmakeWorkspace`
- `rules map[string]*cmakeRule` - 规则名到 cmakeRule 的映射

### `writeState`
- `writtenRules []string` - 已写出的规则列表，防止重复写入

## 公共 API 函数

- `newCMakeWorkspace()` - 创建空工作区
- `getRule(name)` - 按名称查找规则
- `createRule(rule)` - 创建或获取已有规则
- `write(writer)` - 按拓扑排序写出所有规则
- `writeRule(writer, r, state)` - 递归写出规则及其依赖

## 内部实现细节

- `write` 先对规则名排序保证输出确定性
- `writeRule` 递归写入依赖规则，实现拓扑排序（CMake 不支持前向引用）
- `writeState` 跟踪已写入的规则，防止重复输出
- 跳过没有源文件的规则（`hasSrcs()` 为 false）

## 依赖关系

- `go.skia.org/infra/go/skerr` - 错误处理
- `go.skia.org/infra/go/util` - 集合操作

## 设计模式与设计决策

- **拓扑排序输出**：通过递归先写依赖再写当前规则，保证 CMake 中定义顺序正确
- **惰性创建**：`createRule` 在规则不存在时才创建新实例

## 性能考量

规则名排序为 O(n log n)，递归写入最坏为 O(n^2)（线性搜索已写入列表），但规则数量有限。

## 相关文件

- `bazel/exporter/cmake_rule.go`
- `bazel/exporter/cmake_exporter.go`
