# perf_puppeteer_render_skps - CanvasKit SKP 渲染性能基准测试

> 源文件: `infra/bots/task_drivers/perf_puppeteer_render_skps/perf_puppeteer_render_skps.go`

## 概述

`perf_puppeteer_render_skps` 是一个通用的 Puppeteer 性能数据收集任务驱动,专门用于通过 CanvasKit 在浏览器中渲染 SKP 文件并收集性能指标。它遍历 SKP 文件目录,对每个 SKP 运行基于 Puppeteer 的渲染基准测试,然后聚合结果并输出符合 Skia Perf 服务格式的 JSON 文件。

## 架构位置

属于 Skia CI 的性能测试基础设施,是 Swarming 任务调度系统中 CanvasKit 性能测试的核心驱动。输出的数据最终被上传到 perf.skia.org 进行分析展示。

## 主要类与结构体

- **`perfJSONFormat`**: Perf JSON 输出格式,包含 gitHash、swarming 信息、key 映射和 results
- **`perfResult`**: `map[string]float32`,性能指标键值对
- **`skpPerfData`**: 单个 SKP 的原始性能数据(withoutFlush/withFlush/totalFrame 毫秒数组)

## 公共 API 函数

- **`main()`**: 入口函数,解析标志、设置环境、运行基准测试、处理结果
- **`setup()`**: 执行 npm ci 安装依赖,关闭已运行的 Chrome,创建输出目录
- **`benchSKPs()`**: 遍历 SKP 目录,对每个文件运行 Puppeteer 渲染基准测试
- **`processSKPData()`**: 读取基准测试输出 JSON,计算统计指标,写入最终 Perf JSON
- **`makePerfObj()`**: 构建 Perf JSON 对象的基础结构

## 内部实现细节

- **SKP 跳过列表**: 维护 `cpuSkiplist` 和 `gpuSkiplist`,排除已知超时的 SKP
- **统计计算**: `summarize()` 函数计算平均值、中位数和标准差
- **配置检测**: 根据 `cpu_or_gpu` 和 `webgl_version` 键动态设置 `--use_gpu` 和 WebGL 版本参数
- **超时控制**: 每个 SKP 设置 90 秒超时

## 依赖关系

- Node.js + Puppeteer(通过 npm ci 安装)
- CanvasKit WASM 二进制
- `go.skia.org/infra/go/exec` - 命令执行
- `go.skia.org/infra/go/util` - 工具函数

## 设计模式与设计决策

- **逐文件测试**: 每个 SKP 独立运行,隔离故障影响
- **配置驱动**: 通过 ExtraConfig 部分选择不同的基准测试逻辑
- **绝对路径**: 所有路径转为绝对路径以确保一致性

## 性能考量

- SKP 渲染可能非常耗时,设置了 90 秒超时
- 跳过列表过滤已知超时的 SKP,避免阻塞 CI
- 使用非锁定帧率(--disable-frame-rate-limit)确保测量准确

## 相关文件

- `perf_puppeteer_render_skps_test.go` - 对应的单元测试
- `tools/perf-puppeteer/` - Puppeteer 基准测试 HTML 和 JS 文件
