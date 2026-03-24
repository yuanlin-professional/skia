# Build Protobuf 定义

> 源文件: `bazel/exporter/build_proto/build/build.pb.go`

## 概述

此文件是由 protobuf 编译器自动生成的 Go 代码，定义了 Bazel 构建系统的核心数据结构，包括 `QueryResult`、`Target`、`Rule`、`Attribute` 等。它是 Bazel query 输出格式的 Go 语言绑定，被 GNI 导出器用于解析查询结果。

## 架构位置

位于 `bazel/exporter/build_proto/build/` 包中，是 Bazel query protobuf 输出的 Go 绑定。

## 主要类与结构体

### `QueryResult`
- Bazel query 命令的结果容器
- 包含 `Target` 列表

### `Target`
- 表示一个构建目标，包含 `Rule` 和目标类型

### `Rule`
- 构建规则定义，包含名称、规则类（cc_library 等）、位置、属性列表

### `Attribute`
- 规则属性（如 srcs、hdrs、deps、copts 等）
- 支持多种类型：STRING、STRING_LIST、LABEL_LIST 等

## 公共 API 函数

由 protobuf 编译器自动生成的标准方法：`GetName()`, `GetRuleClass()`, `GetAttribute()` 等。

## 内部实现细节

- 大型自动生成文件（3493 行），定义了 Bazel 构建系统的完整数据模型
- 属性类型枚举 (`Attribute_Discriminator`) 区分不同的属性值类型

## 依赖关系

- `google.golang.org/protobuf` - protobuf Go 运行时

## 设计模式与设计决策

**Protocol Buffers**：使用 Google 的 protobuf 规范实现跨语言数据交换。

## 性能考量

protobuf 的二进制格式在大型查询结果上比文本格式有显著性能优势。

## 相关文件

- `bazel/exporter/gni_exporter.go` - 使用 QueryResult
- `bazel/exporter/bazel_util.go` - 使用 Rule 和 Attribute
