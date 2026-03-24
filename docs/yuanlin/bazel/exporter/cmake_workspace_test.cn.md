# CMake 工作区测试

> 源文件: `bazel/exporter/cmake_workspace_test.go`

## 概述

此文件测试 `cmakeWorkspace` 的核心功能：规则查找、规则创建和写入状态跟踪。通过先执行完整的 CMake 导出流程创建工作区，再验证其内部状态。

## 架构位置

位于 `bazel/exporter/` 包的测试层。

## 主要类与结构体

定义 `workspaceTestTextProto` 常量和辅助函数 `getTestWorkspace` 用于创建测试工作区。

## 公共 API 函数

- `TestIsGetRule_ValidName_ReturnsRule` - 查找存在的规则
- `TestIsGetRule_InvalidName_ReturnsNil` - 查找不存在的规则
- `TestCreateRule_ValidBazelRule_NotNil` - 创建新规则
- `TestIsRuleWritten_NotWritten_ReturnsFalse` - 未写入状态检查
- `TestIsRuleWritten_Written_ReturnsTrue` - 已写入状态检查

## 内部实现细节

- `getTestWorkspace` 通过完整的 Export 流程创建真实的工作区状态
- 使用 mock 文件系统和查询命令隔离外部依赖
- 验证跨工作区的规则复制正确性

## 依赖关系

- `github.com/stretchr/testify` - 断言和 mock
- `bazel/exporter/interfaces/mocks` - mock 对象

## 设计模式与设计决策

**集成式测试**：不直接构建工作区状态，而是通过 Export 流程间接创建，更接近实际使用场景。

## 性能考量

无特殊考量。

## 相关文件

- `bazel/exporter/cmake_workspace.go` - 被测代码
