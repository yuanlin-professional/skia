# bazel_clean_step - Bazel 缓存磁盘空间管理

> 源文件: `infra/bots/task_drivers/common/bazel_clean_step.go`

## 概述

`bazel_clean_step` 提供了 Bazel 缓存的磁盘空间管理功能。当 Bazel 缓存所在分区的可用空间低于阈值(15GB)时,自动执行 `bazel clean` 清理缓存。这解决了 Bazel 缓存无限增长导致 CI 机器磁盘空间告警的问题。

## 架构位置

属于任务驱动的公共工具层(`common` 包),被所有使用 Bazel 的任务驱动在完成后调用。

## 主要类与结构体

- **`BazelCleanIfLowDiskSpaceContextValue`**: 测试用上下文值,包含可替换的分区查找和空间查询函数
- **`BazelCleanIfLowDiskSpaceContextKey`**: 上下文键,用于注入测试 mock

## 公共 API 函数

- **`BazelCleanIfLowDiskSpace()`**: 核心函数,检查磁盘空间并在必要时清理
- **`WithEnoughSpaceOnBazelCachePartitionTestOnlyContext()`**: 测试辅助函数,返回模拟足够磁盘空间的上下文

## 内部实现细节

- 阈值: 15GB (`bazelCachePartitionMinRequiredFreeSpaceBytes`)
- 使用 `gopsutil/disk` 包获取分区信息和磁盘使用情况
- 通过最长路径前缀匹配找到缓存所在的分区挂载点
- 支持通过上下文注入 mock 函数用于测试
- 磁盘操作函数(`getPartitionMountpoints`, `freeBytesOnPartition`)可被替换

## 依赖关系

- `github.com/shirou/gopsutil/disk` - 跨平台磁盘信息
- Bazelisk/Bazel - 执行 clean 命令

## 设计模式与设计决策

- **上下文注入模式**: 通过 Go context.Value 注入测试替身,避免在测试中访问真实磁盘
- **最长前缀匹配**: 正确处理多分区场景(如 `/home` 和 `/home/chrome-bot`)
- **保守阈值**: 15GB 高于 Swarming 的 3GB 隔离阈值和 10GB 告警阈值

## 性能考量

`bazel clean` 本身很快,但清理缓存意味着后续构建需要重新缓存。

## 相关文件

- `bazel_clean_step_test.go` - 单元测试
- `bazel_flags.go` - Bazel 标志定义(包含 cache_dir)
