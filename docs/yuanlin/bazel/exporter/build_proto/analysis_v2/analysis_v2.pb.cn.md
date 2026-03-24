# Analysis V2 Protobuf 定义

> 源文件: `bazel/exporter/build_proto/analysis_v2/analysis_v2.pb.go`

## 概述

此文件是由 protobuf 编译器自动生成的 Go 代码，定义了 Bazel cquery 输出的 `CqueryResult` 消息类型。它是导出器解析 Bazel 配置查询结果的数据模型基础。

## 架构位置

位于 `bazel/exporter/build_proto/analysis_v2/` 包中，作为 Bazel cquery protobuf 输出的 Go 绑定，被 CMake 导出器使用。

## 主要类与结构体

### `CqueryResult`
- 包含 cquery 查询结果的顶层消息
- 持有 `ConfiguredTarget` 的结果列表

### `ConfiguredTarget`
- 表示配置后的构建目标
- 包含 `Target` 和配置信息

## 公共 API 函数

由 protobuf 编译器自动生成的标准访问器方法（Get/Set 等）。

## 内部实现细节

- 自动生成代码，不应手动修改
- 使用 `google.golang.org/protobuf` 运行时库
- 反射信息用于序列化/反序列化

## 依赖关系

- `google.golang.org/protobuf` - protobuf Go 运行时
- `bazel/exporter/build_proto/build` - 引用 build.proto 中的 Target 类型

## 设计模式与设计决策

**代码生成**：由 `.proto` 文件自动生成，确保与 Bazel 的 protobuf 输出格式完全一致。

## 性能考量

protobuf 的二进制序列化格式比 JSON/文本格式更紧凑高效。

## 相关文件

- `bazel/exporter/build_proto/build/build.pb.go` - 关联的 build protobuf
- `bazel/exporter/cmake_exporter.go` - 使用者
