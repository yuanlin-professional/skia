# CMake 规则测试

> 源文件: `bazel/exporter/cmake_rule_test.go`

## 概述

此文件测试 `cmakeRule` 结构体及其方法，验证 CMake 规则的名称获取、源文件检查、依赖管理和内容写入功能。使用 protobuf textproto 格式的测试数据模拟 Bazel 查询结果。

## 架构位置

位于 `bazel/exporter/` 包的测试层。

## 主要类与结构体

定义了 `ruleTestTextProto` 常量作为测试输入数据，包含 `cc_library`（sum）和 `cc_binary`（hello）两个规则。

## 公共 API 函数

- `TestGetName_MatchingValue` - 验证规则名获取
- `TestHasSrcs_*` - 验证源文件检测
- `TestHasDependency_*` - 验证依赖关系管理
- `TestSetContents_*` - 验证内容写入

## 内部实现细节

- 通过 prototext 反序列化构建测试用的 CqueryResult 对象
- 测试 `addDependency` 的去重逻辑和 `hasDependency` 查询
- 验证 `setContents` + `write` 的字节数正确性

## 依赖关系

- `github.com/stretchr/testify` - 测试断言
- `bazel/exporter/build_proto/analysis_v2` - protobuf 类型

## 设计模式与设计决策

使用真实的 protobuf 数据结构进行测试，确保与实际 Bazel 输出兼容。

## 性能考量

无特殊性能考量。

## 相关文件

- `bazel/exporter/cmake_rule.go` - 被测代码
