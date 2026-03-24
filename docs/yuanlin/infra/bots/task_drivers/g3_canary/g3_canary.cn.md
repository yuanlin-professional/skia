# g3_canary - Google3 金丝雀测试任务驱动

> 源文件: `infra/bots/task_drivers/g3_canary/g3_canary.go`

## 概述

`g3_canary` 是 Skia 的 Google3 (G3) 金丝雀测试任务驱动。当作为 tryjob 运行时,它会触发一次 G3 TAP(Test Anything Protocol)编译测试,验证 Skia 的变更是否与 Google 内部代码库兼容。通过 GCS 文件协调触发和轮询机制管理异步测试流程。

## 架构位置

属于 Skia 的 CQ(Commit Queue)集成层,是确保 Skia 变更不会破坏 Google 内部依赖的关键守门任务。

## 主要类与结构体

- **`CanaryStatusType`**: 金丝雀状态枚举(exception/missing_approval/merge_conflict/failure/success)
- **`G3CanaryTask`**: GCS 任务文件结构(Issue, Patchset, Status, Result, Error, CL)

## 公共 API 函数

- **`main()`**: 解析标志、检查现有任务、触发新任务、等待完成
- **`triggerCanaryRoll()`**: 创建 GCS 任务文件触发金丝雀构建
- **`waitForCanaryRoll()`**: 轮询 GCS 文件等待结果

## 内部实现细节

- 通过 GCS 桶 `g3-compile-tasks` 与 G3 构建系统通信
- 任务文件名格式: `<issue>-<patchset>.json`
- 轮询间隔: 30 秒
- 结果处理: 区分基础设施故障、缺少审批、合并冲突、测试失败等不同错误
- 使用 Pushgateway 上报 `g3_canary_infra_failure` 指标

## 依赖关系

- `cloud.google.com/go/storage` - GCS 操作
- `go.skia.org/infra/go/gcs` - GCS 客户端
- `go.skia.org/infra/promk/go/pushgateway` - Prometheus 指标
- `go.skia.org/infra/task_driver/go/lib/checkout` - 代码库状态

## 设计模式与设计决策

- **GCS 协调**: 使用 GCS 文件作为任务队列,避免直接调用 G3 API
- **幂等触发**: 检查任务文件是否已存在,避免重复触发
- **清理机制**: defer 中删除 GCS 任务文件,确保不污染后续运行

## 性能考量

G3 TAP 测试可能耗时较长,30 秒轮询间隔平衡了响应性和 GCS API 开销。

## 相关文件

- `infra/bots/task_drivers/common/` - 公共任务驱动工具
