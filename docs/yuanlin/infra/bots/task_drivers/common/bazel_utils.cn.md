# bazel_utils - Bazel 工具函数

> 源文件: `infra/bots/task_drivers/common/bazel_utils.go`

## 概述

`bazel_utils` 提供 Bazel 相关的公共工具函数,包括 Bazel 标签验证、测试输出 ZIP 路径计算和 ZIP 文件提取功能。这些功能被多个任务驱动共享使用。

## 架构位置

属于任务驱动公共工具层(`common` 包)。

## 主要类与结构体

- **`validBazelLabelRegexps`**: 有效 Bazel 标签的正则表达式列表

## 公共 API 函数

- **`ValidateLabelAndReturnOutputsZipPath()`**: 验证标签格式并返回 `bazel-testlogs` 下的 `outputs.zip` 路径
- **`ExtractOutputsZip()`**: 将 ZIP 文件中的 PNG 和 JSON 文件提取到临时目录

## 内部实现细节

- 标签验证支持 `//:foo` 和 `//path/to:target` 两种格式
- 路径转换: `//foo/bar:baz` -> `bazel-testlogs/foo/bar/baz/test.outputs/outputs.zip`
- ZIP 提取仅处理根目录的 `.png` 和 `.json` 文件(大小写不敏感)
- 跳过子目录中的文件和非 PNG/JSON 文件

## 依赖关系

- `archive/zip` - ZIP 处理
- `go.skia.org/infra/task_driver/go/lib/os_steps` - 临时目录

## 设计模式与设计决策

- **安全提取**: 只提取预期类型的文件,避免 ZIP 炸弹或路径穿越
- **步骤可见性**: 每个提取/跳过操作都创建任务驱动步骤用于调试

## 性能考量

ZIP 提取为单线程顺序操作。文件内容完全读入内存后写入磁盘。

## 相关文件

- `bazel_utils_test.go` - 单元测试
