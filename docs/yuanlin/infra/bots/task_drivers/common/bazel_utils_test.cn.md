# bazel_utils_test - Bazel 工具函数的单元测试

> 源文件: `infra/bots/task_drivers/common/bazel_utils_test.go`

## 概述

本文件测试 `common` 包中 Bazel 相关工具函数,主要验证 Bazel 标签验证和输出 ZIP 路径生成(`ValidateLabelAndReturnOutputsZipPath`)以及 ZIP 文件提取(`ExtractOutputsZip`)的正确性。

## 架构位置

属于公共 Bazel 工具的测试层。

## 主要类与结构体

无新定义。使用 `testutils.MakeZIP` 和 `testutils.MakeTempDirMockFn` 辅助函数。

## 公共 API 函数

- **`TestValidateLabelAndReturnOutputZipPath_ValidLabel_Success`**: 验证有效标签的路径生成(`//:foo`, `//foo:bar` 等)
- **`TestValidateLabelAndReturnOutputZipPath_InvalidLabel_Error`**: 验证 20+ 种无效标签格式
- **`TestExtractOutputsZip_Success`**: 验证 ZIP 提取(仅提取根目录的 PNG 和 JSON 文件)

## 内部实现细节

- 标签验证覆盖正则 `//:<target>` 和 `//<path>:<target>` 格式
- ZIP 提取测试验证:根目录 PNG/JSON 被提取,TXT 被忽略,子目录文件被跳过
- 使用 `testutils.AssertStepNames` 验证任务驱动步骤序列

## 依赖关系

- `go.skia.org/skia/infra/bots/task_drivers/testutils` - 测试工具

## 设计模式与设计决策

- **详尽的负面测试**: 无效标签测试覆盖了各种可能的格式错误
- **步骤名称验证**: 确保任务驱动步骤的可观测性

## 性能考量

使用内存中的 ZIP 文件和临时目录,执行速度快。

## 相关文件

- `bazel_utils.go` - 被测试的工具函数
