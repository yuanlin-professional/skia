# wasm_perf_aggregator - WASM Perf 数据聚合服务

> 源文件: `infra/wasm-common/perf/wasm_perf_aggregator.go`

## 概述

`wasm_perf_aggregator` 是与 Karma 性能测试并行运行的 HTTP 服务器,接收 WASM 基准测试(PathKit/CanvasKit)的性能数据。它允许同一基准测试的多次报告,在输出时自动计算平均值。结果以唯一命名的 JSON 文件输出,兼容 `upload_nano_results` 上传脚本。

## 架构位置

属于 WASM 性能测试子系统,与 Gold 聚合器并行,负责 Perf 数据收集。

## 主要类与结构体

- **`reportBody`**: 基准测试报告(BenchName, TimeMicroSeconds)
- **`BenchData`**: Perf JSON 输出格式(Hash, Issue, PatchSet, Key, Results, Swarming 信息)

## 公共 API 函数

- **HTTP `/report_perf_data`**: 接收单次基准测试结果(线程安全)
- **HTTP `/dump_json`**: 计算平均值并输出 JSON

## 内部实现细节

- 文件名包含 UUID 避免 GCS 上传时的命名冲突
- 同名基准测试的多次报告存储在切片中,dump 时计算平均值
- 输出包含所有样本值(`samples`)和计算的平均值(`average_us`)
- 使用 `sync.Mutex` 保护并发访问

## 依赖关系

- `github.com/google/uuid` - 唯一文件名生成
- `go.skia.org/infra/perf/go/ingest/format` - Perf 数据格式

## 设计模式与设计决策

- **多次采样平均**: 允许同一基准测试多次运行以获得更稳定的结果
- **UUID 文件名**: 解决基于时间的 GCS 目录中的文件名冲突
- **原始样本保留**: 输出同时包含平均值和原始样本,支持后续分析

## 性能考量

内存中积累所有结果,dump 时一次性计算和写入。

## 相关文件

- `infra/wasm-common/gold/wasm_gold_aggregator.go` - Gold 数据聚合器
