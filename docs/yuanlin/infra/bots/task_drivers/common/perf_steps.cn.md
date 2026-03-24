# perf_steps - Perf 数据上传公共步骤

> 源文件: `infra/bots/task_drivers/common/perf_steps.go`

## 概述

`perf_steps` 提供 Skia CI 任务驱动中向 perf.skia.org 上传基准测试结果的公共功能。它处理从 Bazel 测试输出(ZIP 文件或目录)中提取 `results.json`、计算 GCS 路径并上传到 Perf 的 GCS 桶。

## 架构位置

属于任务驱动公共工具层,为所有需要上传 Perf 数据的任务驱动提供统一接口。

## 主要类与结构体

- **`BenchmarkInfo`**: 基准测试元信息(GitCommit, TaskName, TaskID, ChangelistID, PatchsetOrder)
- **常量**: `PerfGCSBucketName = "skia-perf"`, `resultsJSON = "results.json"`

## 公共 API 函数

- **`ComputeBenchmarkTestRunnerCLIFlags()`**: 生成基准测试运行器的命令行参数(--gitHash, --issue, --patchset, --links)
- **`UploadToPerf()`**: 从 ZIP/目录提取 results.json 并上传到 GCS

## 内部实现细节

- GCS 路径格式: `nano-json-v1/YYYY/MM/DD/HH/<commit>/<taskName>/results_<taskID>.json`
- 支持 ZIP 文件和目录两种输入格式
- ZIP 文件先通过 `ExtractOutputsZip` 提取,处理后清理临时目录
- 链接参数包含任务调度器和 Gerrit CL 的 URL

## 依赖关系

- `go.skia.org/infra/go/gcs` - GCS 操作
- `go.skia.org/infra/go/now` - 时间工具(UTC)

## 设计模式与设计决策

- **双模式输入**: 支持 ZIP 文件(Bazel 输出)和目录(本地测试),提高灵活性
- **时间前缀路径**: GCS 路径按时间组织便于清理和查找

## 性能考量

单文件上传,性能瓶颈在网络传输。

## 相关文件

- `perf_steps_test.go` - 单元测试
- `bazel_utils.go` - ZIP 提取功能
