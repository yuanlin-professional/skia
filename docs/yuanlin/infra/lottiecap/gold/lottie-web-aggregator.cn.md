# lottie-web-aggregator - Lottie Web Gold 数据聚合服务

> 源文件: `infra/lottiecap/gold/lottie-web-aggregator.go`

## 概述

`lottie-web-aggregator` 是一个 HTTP 服务器,与 `lottiecap.js` 并行运行,接收 Lottie 测试用例通过 POST 请求报告的 Gold 输出数据。它将 base64 编码的 PNG 图像解码后写入磁盘,收集所有测试结果,最终输出兼容 `upload_dm_results.py` 的 `dm.json` 文件。

## 架构位置

属于 Lottie 动画渲染质量测试子系统,连接浏览器端的 Lottie 渲染和 Gold 图像比较服务。

## 主要类与结构体

- **`reportBody`**: 从 JS 端接收的测试报告(Data: base64 PNG, TestName: 测试名)

## 公共 API 函数

- **HTTP `/report_gold_data`**: 接收单个测试的图像数据
- **HTTP `/dump_json`**: 将所有收集的结果写入 dm.json
- **`writeBase64EncodedPNG()`**: 解码 base64 PNG、计算像素 MD5 哈希、写入磁盘

## 内部实现细节

- 图像哈希使用 MD5 计算像素数据(非 PNG 字节),与 DM 工具的行为一致
- 支持 NRGBA、RGBA 和 RGBA64 三种图像格式
- 默认 key 包含 browser、renderer(lottie-web)、source_type(lottie) 等
- 支持 tryjob 模式(issue/patchset/buildbucket_build_id)

## 依赖关系

- `go.skia.org/infra/golden/go/jsonio` - Gold JSON 格式
- `go.skia.org/infra/golden/go/types` - Gold 类型定义

## 设计模式与设计决策

- **像素哈希**: MD5 对像素数据而非文件数据取哈希,确保与 C++ DM 工具的输出可比较
- **文件名即哈希**: PNG 文件以 MD5 哈希命名,支持去重

## 性能考量

单线程处理请求。结果数组无互斥保护(假设顺序调用)。

## 相关文件

- `infra/wasm-common/gold/wasm_gold_aggregator.go` - 类似的 WASM Gold 聚合器
