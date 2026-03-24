# CMake 导出器测试

> 源文件: `bazel/exporter/cmake_exporter_test.go`

## 概述

此文件测试 `CMakeExporter` 的核心导出功能，包括错误处理、protobuf 解析和 CMake 文件生成。通过精心构建的 textproto 测试数据验证完整的导出管线。

## 架构位置

位于 `bazel/exporter/` 包的测试层。

## 主要类与结构体

定义 `textProto` 常量，包含两个测试规则（cc_library `sum` 和 cc_binary `hello`），用于验证导出器行为。

## 公共 API 函数

- `TestExport_QueryReadError_ReturnsError` - 查询读取失败时返回错误
- `TestExport_InvalidProtobuf_ReturnsError` - 无效 protobuf 数据时返回错误
- `TestExport_ValidProtobuf_Success` - 正常情况下生成正确的 CMake 文件
- `TestGetRuleCopts_CoptsExists_Success` - 编译选项提取测试

## 内部实现细节

- 使用 mock FileSystem 和 QueryCommand 隔离测试
- `TestExport_ValidProtobuf_Success` 手动构造完整的期望输出并逐字符比较
- 验证生成的 CMake 包含正确的 `cmake_minimum_required`、`project`、`add_executable`/`add_library`、`target_sources`、编译标志等

## 依赖关系

- `github.com/stretchr/testify` - 断言和 mock
- `bazel/exporter/interfaces/mocks` - 自动生成的 mock 对象

## 设计模式与设计决策

**黄金文件测试**：通过精确匹配整个输出内容验证正确性，而非仅检查部分属性。

## 性能考量

无特殊考量。

## 相关文件

- `bazel/exporter/cmake_exporter.go` - 被测代码
