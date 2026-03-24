# bazel_clean_step_test - Bazel 缓存清理的单元测试

> 源文件: `infra/bots/task_drivers/common/bazel_clean_step_test.go`

## 概述

本文件测试 `BazelCleanIfLowDiskSpace` 函数的两种行为:磁盘空间充足时保留缓存,空间不足时执行 `bazel clean`。

## 架构位置

Bazel 缓存管理的测试层。

## 公共 API 函数

- **`TestBazelCleanIfLowDiskSpace_EnoughDiskSpace_BazelCachePreserved`**: 20GB 可用时不执行清理
- **`TestBazelCleanIfLowDiskSpace_LowDiskSpace_BazelCacheDeleted`**: 0 字节可用时执行 `bazel clean`

## 内部实现细节

- 通过上下文注入 mock 函数模拟分区信息和磁盘空间
- 验证正确识别最长前缀挂载点(`/home/chrome-bot` 而非 `/home` 或 `/`)
- 使用 `exec_testutils.AssertCommandsMatch` 验证 clean 命令
- 验证 clean 命令的工作目录为 checkout 路径

## 依赖关系

- `go.skia.org/infra/go/exec/testutils` - 命令验证
- `go.skia.org/skia/infra/bots/task_drivers/testutils` - 步骤名称验证

## 设计模式与设计决策

- **Mock 注入**: 完全控制磁盘查询结果,无需真实磁盘操作

## 性能考量

纯内存操作,执行迅速。

## 相关文件

- `bazel_clean_step.go` - 被测试的主程序
