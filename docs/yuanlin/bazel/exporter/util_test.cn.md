# 导出器测试工具函数

> 源文件: `bazel/exporter/util_test.go`

## 概述

此文件提供测试辅助函数，用于在其他测试文件中创建 protobuf 测试数据。包含将 textproto 转换为二进制 protobuf 的函数和创建测试用 build.Rule 的工厂函数。

## 架构位置

位于 `bazel/exporter/` 包的测试支持层，被多个测试文件共享使用。

## 主要类与结构体

无独立结构体。

## 公共 API 函数

- `textProtoToProtobuf(textProto)` - 将 textproto 字符串转换为二进制 protobuf 数据
- `createTestBuildRule(name, ruleClass, loc, srcs)` - 创建带有指定属性的测试 build.Rule 对象

## 内部实现细节

- `textProtoToProtobuf` 先反序列化为 `CqueryResult`，再序列化为二进制格式
- `createTestBuildRule` 手动构建 Rule 的 `srcs` 属性，设置为 `STRING_LIST` 类型

## 依赖关系

- `google.golang.org/protobuf` - protobuf 序列化
- `bazel/exporter/build_proto/` - 生成的 protobuf 类型

## 设计模式与设计决策

**测试工厂模式**：提供复用的测试数据构建函数，减少测试代码重复。

## 性能考量

无特殊考量。

## 相关文件

- `bazel/exporter/gni_exporter_test.go` - 使用 createTestBuildRule
- `bazel/exporter/cmake_exporter_test.go` - 使用 textProtoToProtobuf
