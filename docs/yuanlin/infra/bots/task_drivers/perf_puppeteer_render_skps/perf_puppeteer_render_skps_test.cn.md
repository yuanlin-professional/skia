# perf_puppeteer_render_skps_test - SKP 渲染性能测试的单元测试

> 源文件: `infra/bots/task_drivers/perf_puppeteer_render_skps/perf_puppeteer_render_skps_test.go`

## 概述

本文件包含 `perf_puppeteer_render_skps` 任务驱动的单元测试,验证通过 Puppeteer 在 CanvasKit 中渲染 SKP 文件的性能基准测试流程。测试覆盖了环境设置、CPU/GPU 配置差异、SKP 跳过列表、WebGL 版本选择以及性能数据聚合与输出格式化。

## 架构位置

属于 Skia 基础设施的测试层,用于验证 `perf_puppeteer_render_skps` 任务驱动的正确性。

## 主要类与结构体

- **常量**: `someGitHash`, `someTaskID`, `someMachineID` - 测试用固定值
- **`firstSKP` / `secondSKP`**: 模拟的 SKP 渲染输出 JSON 数据

## 公共 API 函数

- **`TestSetup_NPMInitializedChromeStoppedBenchmarkOutCreated`**: 验证 setup 函数正确执行 npm ci 和 killall chrome
- **`TestBenchSKPs_CPUHasNoUseGPUFlag`**: 验证 CPU 模式不附加 `--use_gpu` 标志
- **`TestBenchSKPs_SkiplistIsUsed`**: 验证跳过列表正确过滤已知问题 SKP
- **`TestBenchSKPs_GPUHasFlag`**: 验证 GPU 模式附加 `--use_gpu` 标志
- **`TestBenchSKPs_WebGL1`**: 验证 WebGL1 模式附加 `--query_params webgl1`
- **`TestProcessSkottieFramesData_GPUTwoInputsGetSummarizedAndCombined`**: 验证多个 SKP 的性能数据被正确聚合

## 内部实现细节

- 使用 `exec.CommandCollector` 模拟命令执行,捕获实际调用的命令和参数
- 使用 `td.RunTestSteps` 在测试上下文中运行任务驱动步骤
- 通过临时目录模拟 SKP 文件输入和性能结果输出
- 验证输出 JSON 的完整结构,包括 key 映射、统计指标(avg、median、stddev)

## 依赖关系

- `github.com/stretchr/testify` - 断言库
- `go.skia.org/infra/go/exec` - 命令模拟
- `go.skia.org/infra/task_driver/go/td` - 测试步骤运行器

## 设计模式与设计决策

- **命令收集模式**: 通过 CommandCollector 拦截所有外部命令调用,实现无副作用测试
- **黄金文件验证**: 将完整 JSON 输出与预期字符串逐字符比较,确保输出格式稳定

## 性能考量

测试使用模拟数据和内存操作,执行速度快。临时文件在 defer 中清理。

## 相关文件

- `infra/bots/task_drivers/perf_puppeteer_render_skps/perf_puppeteer_render_skps.go` - 被测试的主程序
