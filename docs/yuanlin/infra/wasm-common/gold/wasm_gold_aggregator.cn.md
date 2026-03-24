# wasm_gold_aggregator - WASM Gold 数据聚合服务

> 源文件: `infra/wasm-common/gold/wasm_gold_aggregator.go`

## 概述

`wasm_gold_aggregator` 是一个与 Karma 测试并行运行的 HTTP 服务器,接收 WASM 测试用例(PathKit/CanvasKit)报告的 Gold 图像输出。与 Lottie 版本类似但增加了线程安全的结果收集和更多配置选项(编译语言、source_type 等)。

## 架构位置

属于 WASM (PathKit/CanvasKit) 图像质量测试子系统。

## 主要类与结构体

- **`reportBody`**: 测试报告(OutputType: 如"canvas"/"svg", Data: base64 PNG, TestName)

## 公共 API 函数

- **HTTP `/report_gold_data`**: 接收测试图像(线程安全)
- **HTTP `/dump_json`**: 输出 dm.json
- **`writeBase64EncodedPNG()`**: base64 解码、MD5 哈希、写盘

## 内部实现细节

- 使用 `sync.Mutex` 保护 results 切片(多个 Karma 测试可能并发报告)
- 根据 builder 名称自动检测 CPU/GPU 配置
- 结果包含 `config` 字段(来自 OutputType)
- tryjob 信息仅在 patchset > 0 时写入

## 依赖关系

- `go.skia.org/infra/go/util` - Close 等工具
- `go.skia.org/infra/golden/go/jsonio` - Gold JSON 格式

## 设计模式与设计决策

- **线程安全**: 使用 mutex 保护并发写入(Karma 可能并行报告)
- **自动配置检测**: 从 builder 名称中检测 GPU 关键字

## 性能考量

Mutex 锁开销对于测试报告频率可忽略。

## 相关文件

- `infra/lottiecap/gold/lottie-web-aggregator.go` - Lottie 版本
- `infra/wasm-common/perf/wasm_perf_aggregator.go` - Perf 数据聚合器
