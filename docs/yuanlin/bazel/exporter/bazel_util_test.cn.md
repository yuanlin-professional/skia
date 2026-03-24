# Bazel 工具函数测试

> 源文件: `bazel/exporter/bazel_util_test.go`

## 概述

此文件包含 `bazel_util.go` 中各工具函数的单元测试，覆盖规则名解析、位置解析、规则查找、文件目标判断等核心功能。测试使用表驱动方式组织，涵盖正常输入和异常输入场景。

## 架构位置

位于 `bazel/exporter/` 包的测试层，使用 Go 标准测试框架和 testify 断言库。

## 主要类与结构体

无独立结构体定义。使用 `analysis_v2.CqueryResult` 和 `build.Rule` 等 protobuf 类型。

## 公共 API 函数

测试函数包括：
- `TestMakeCanonicalRuleName_*` - 规范化规则名
- `TestParseRule_*` - 解析规则为仓库/路径/目标
- `TestParseLocation_*` - 解析 BUILD 文件位置
- `TestGetRuleSimpleName_*` - 生成 CMake 兼容的简单名称
- `TestIsExternalRule_*` / `TestIsFileRule_*` - 规则类型判断
- `TestFindRule_*` - protobuf 结果中查找规则
- `TestGetFilePathFromFileTarget_*` - 目标转文件路径
- `TestAppendUnique_*` - 去重追加

## 内部实现细节

- 使用 textproto 格式的测试数据模拟 Bazel cquery 输出
- 表驱动测试模式：每个测试用例通过闭包传入名称和参数
- 覆盖边界情况：空字符串、无效规则名、不存在的规则等

## 依赖关系

- `github.com/stretchr/testify` - 断言库
- `google.golang.org/protobuf/encoding/prototext` - protobuf 文本格式解析

## 设计模式与设计决策

- **表驱动测试**：每组测试用内嵌 `test` 函数封装，清晰分离测试用例
- **子测试**：使用 `t.Run(name, ...)` 支持单独运行和报告

## 性能考量

单元测试，无需关注性能。

## 相关文件

- `bazel/exporter/bazel_util.go` - 被测代码
- `bazel/exporter/cmake_exporter_test.go` - 共享 textProto 测试数据
