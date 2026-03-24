# CMake 规则

> 源文件: `bazel/exporter/cmake_rule.go`

## 概述

此文件定义了 `cmakeRule` 结构体，表示 Bazel 规则到 CMake 的等价转换。每个 cmakeRule 持有其内容（CMake 文件片段）、依赖关系和对原始 Bazel 规则的引用。

## 架构位置

位于 `bazel/exporter/` 包中，是 CMake 导出器的核心数据模型。被 `cmakeWorkspace` 管理，被 `CMakeExporter` 创建和填充。

## 主要类与结构体

### `cmakeRule`
- `contents []byte` - 要写入 CMake 文件的数据
- `deps []string` - 直接依赖的 Bazel 目标名列表
- `rule *build.Rule` - 对应的 Bazel 规则（指针，因为 Rule 含 Mutex）

## 公共 API 函数

- `newCMakeRule(r)` - 创建新的 cmakeRule
- `getName()` - 返回规则名
- `hasSrcs()` - 检查是否有源文件
- `hasDependency(ruleName)` - 检查是否有指定依赖
- `addDependency(ruleName)` - 添加规则依赖（去重，禁止自依赖）
- `setContents(contents)` - 设置 CMake 内容
- `write(writer)` - 写出内容

## 内部实现细节

- 依赖去重使用线性搜索（`util.In`），适合小规模依赖列表
- 防御性编程：`addDependency` 检查空名和自依赖
- 信任 Bazel 已解决循环依赖问题

## 依赖关系

- `go.skia.org/infra/go/util` - 集合操作工具
- `bazel/exporter/build_proto/build` - Bazel 构建 protobuf

## 设计模式与设计决策

**数据传输对象**：cmakeRule 作为 Bazel 规则到 CMake 的中间表示，解耦了解析和输出。

## 性能考量

依赖列表使用切片存储，查找为 O(n)，但实际依赖数通常很少。

## 相关文件

- `bazel/exporter/cmake_workspace.go` - 工作区管理
- `bazel/exporter/cmake_exporter.go` - 创建和填充规则
