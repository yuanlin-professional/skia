# perf_puppeteer_canvas - CanvasKit Canvas 性能基准测试

> 源文件: `infra/bots/task_drivers/perf_puppeteer_canvas/perf_puppeteer_canvas.go`

## 概述

`perf_puppeteer_canvas` 是一个 Puppeteer 驱动的性能基准测试任务,用于测量 CanvasKit 的 Canvas API 性能。与 SKP 渲染测试不同,本驱动运行的是预定义的 Canvas 绘图基准测试(canvas_perf.html),收集帧时间数据,计算统计摘要并输出 Perf JSON 格式的结果。

## 架构位置

属于 CanvasKit 性能基准测试子系统,与 `perf_puppeteer_render_skps` 并行的另一个性能测量维度。输出数据上传至 perf.skia.org。

## 主要类与结构体

- **`perfJSONFormat`**: Perf 输出格式(gitHash、key、results 映射)
- **`perfResult`**: `map[string]float32` 性能指标
- **`oneTestResult`**: 单个测试的帧时间数据(withoutFlush/withFlush/totalFrame)

## 公共 API 函数

- **`main()`**: 解析标志、初始化环境、运行基准测试、处理输出
- **`setup()`**: npm ci 安装、创建 out 目录
- **`benchCanvas()`**: 运行 canvas_perf.html 基准测试
- **`processFramesData()`**: 读取 perf.json、计算统计指标、写入最终输出
- **`calculatePerfFromTest()`**: 从单个测试结果计算详细统计(含百分位数)

## 内部实现细节

- **额外统计**: 相比 SKP 渲染测试,增加了 90/95/99 百分位帧时间
- **`summarize()` 函数**: 返回 6 个统计值(avg/median/stddev/p90/p95/p99)
- **单文件输出**: 所有 Canvas 基准测试结果输出到同一个 perf.json
- **超时**: 设置 300 秒(5 分钟)超时

## 依赖关系

- Node.js + Puppeteer
- CanvasKit WASM
- `go.skia.org/infra/go/exec`, `go.skia.org/infra/go/skerr`

## 设计模式与设计决策

- **集中式输出**: 所有 Canvas 测试结果合并为单个 JSON,与 SKP 的逐文件输出不同
- **extra_config 标识**: 使用 "CanvasPerf" 区分于 "RenderSKP"
- **百分位数统计**: 提供更丰富的性能分布信息用于尾延迟分析

## 性能考量

- 5 分钟超时适配复杂 Canvas 基准测试
- GPU 模式和 WebGL1/2 可配置
- 统计使用排序数组实现高效百分位数计算

## 相关文件

- `perf_puppeteer_canvas_test.go` - 单元测试
- `perf_puppeteer_render_skps/` - SKP 渲染性能测试(姊妹项目)
