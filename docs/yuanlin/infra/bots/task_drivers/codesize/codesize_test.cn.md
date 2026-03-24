# codesize_test - 代码体积分析的单元测试

> 源文件: `infra/bots/task_drivers/codesize/codesize_test.go`

## 概述

本文件包含 `codesize` 任务驱动的全面单元测试,覆盖 post-submit 和 tryjob 两种模式的完整执行流程。测试验证命令序列(cp/strip/ls/bloaty)、GCS 上传路径和内容、JSON 元数据格式,以及 Bloaty diff 输出解析。

## 架构位置

codesize 任务驱动的测试层,使用多种 mock 技术验证与 GCS、Gerrit、Gitiles 的集成。

## 主要类与结构体

无新定义结构体。使用 `mocks.GCSClient`、`gerrit_testutils.MockGerrit`、`gitiles_testutils.MockRepo` 等模拟对象。

## 公共 API 函数

- **`TestRunSteps_PostSubmit_Success`**: 验证 post-submit 模式的完整流程(8 条命令,3+1 个 GCS 上传)
- **`TestRunSteps_Tryjob_Success`**: 验证 tryjob 模式(相同命令序列,不同 GCS 路径)
- **`TestParseBloatyDiffOutput`**: 表驱动测试验证 Bloaty diff 输出解析

## 内部实现细节

- 使用 `exec.CommandCollector` + `SetDelegateRun` 模拟 Bloaty 输出
- 使用 `now.TimeTravelingContext` 固定时间确保 GCS 路径可预测
- 使用 `git_testutils.GitInit` 创建真实 Git 仓库获取确定性的 commit hash
- 创建模拟的 stripped 二进制文件验证体积计算(17 bytes vs 23 bytes)
- 过滤 Git 命令后验证恰好 8 条命令序列

## 依赖关系

- `go.skia.org/infra/go/gcs/mocks` - GCS 模拟
- `go.skia.org/infra/go/gerrit/testutils` - Gerrit 模拟
- `go.skia.org/infra/go/gitiles/testutils` - Gitiles 模拟
- `go.skia.org/infra/go/now` - 时间控制

## 设计模式与设计决策

- **完整端到端验证**: 验证从输入到 GCS 上传的完整数据流
- **确定性测试**: 固定时间、commit hash 和 mock 数据确保测试可重复
- **表驱动测试**: `TestParseBloatyDiffOutput` 使用表驱动风格测试多种输入

## 性能考量

测试创建真实 Git 仓库,略有 I/O 开销但确保了 commit hash 的真实性。

## 相关文件

- `codesize.go` - 被测试的主程序
