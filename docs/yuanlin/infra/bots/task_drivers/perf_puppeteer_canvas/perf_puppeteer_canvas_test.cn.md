# perf_puppeteer_canvas_test - Canvas 性能基准测试的单元测试

> 源文件: `infra/bots/task_drivers/perf_puppeteer_canvas/perf_puppeteer_canvas_test.go`

## 概述

本文件包含 `perf_puppeteer_canvas` 任务驱动的单元测试,验证 Canvas 性能基准测试的设置、CPU/GPU 模式切换以及帧数据处理与 JSON 输出的正确性。测试使用模拟数据验证统计计算(含百分位数)和最终 JSON 格式。

## 架构位置

CanvasKit Canvas 性能测试的测试层,确保基准测试流程和数据处理的正确性。

## 主要类与结构体

- **`sampleData`**: 模拟的 Canvas 基准测试输出数据,包含两个测试用例(`canvas_drawColor` 和 `canvas_drawHugeGradient`),各含 26 个帧时间样本

## 公共 API 函数

- **`TestSetup_NPMInitializedBenchmarkOutCreated`**: 验证 setup 只执行 npm ci(不 killall chrome)
- **`TestBenchCanvas_CPUHasNoUseGPUFlag`**: 验证 CPU 模式的命令行参数
- **`TestBenchCanvas_GPUHasFlag`**: 验证 GPU 模式附加 `--use_gpu`
- **`TestProcessFramesData_GPUTwoInputsGetSummarizedAndCombined`**: 完整验证数据处理管线

## 内部实现细节

- 使用 `exec.CommandCollector` 捕获命令调用
- 最终测试验证完整的 JSON 输出字符串,包括 90/95/99 百分位帧时间
- `writeFilesToDisk` 辅助函数创建测试所需的模拟文件

## 依赖关系

- `github.com/stretchr/testify` (assert, require)
- `go.skia.org/infra/go/exec`, `go.skia.org/infra/task_driver/go/td`

## 设计模式与设计决策

- **黄金字符串比较**: 使用完整 JSON 字符串比较确保输出格式的绝对稳定性
- **与 SKP 测试的差异**: setup 测试验证 Canvas 版本不执行 `killall chrome`

## 性能考量

纯内存操作,执行迅速。临时目录在 defer 中清理。

## 相关文件

- `perf_puppeteer_canvas.go` - 被测试的主程序
