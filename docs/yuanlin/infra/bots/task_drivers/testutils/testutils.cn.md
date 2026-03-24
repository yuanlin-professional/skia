# testutils - 任务驱动测试工具包

> 源文件: `infra/bots/task_drivers/testutils/testutils.go`

## 概述

`testutils` 提供 Skia 任务驱动单元测试中常用的辅助函数,包括步骤名称断言、ZIP 文件创建、目录填充和临时目录 mock 工厂。

## 架构位置

任务驱动测试的公共工具层,被 `common` 包和各任务驱动的测试文件共享使用。

## 公共 API 函数

- **`AssertStepNames()`**: 展平步骤报告树并验证步骤名称序列(跳过根步骤)
- **`MakeZIP()`**: 从 map[string]string 创建确定性 ZIP 文件(按文件名排序)
- **`PopulateDir()`**: 将 map[string]string 写入指定目录
- **`MakeTempDirMockFn()`**: 返回可用于 mock os_steps.TempDir 的函数(按调用次序返回预设路径)

## 内部实现细节

- `AssertStepNames` 使用 `StepReport.Recurse` 递归遍历步骤树
- `MakeZIP` 对文件排序确保 ZIP 内容确定性
- `MakeTempDirMockFn` 通过闭包计数器追踪调用次数,超出预设数量时测试失败

## 依赖关系

- `archive/zip` - ZIP 操作
- `go.skia.org/infra/task_driver/go/td` - 步骤报告

## 设计模式与设计决策

- **确定性输出**: ZIP 文件排序确保相同输入产生相同输出
- **调用计数保护**: TempDir mock 防止意外的额外调用

## 性能考量

所有操作使用内存缓冲区,性能优秀。

## 相关文件

- 被 `common/` 目录下多个测试文件使用
