# perf_puppeteer_skottie_frames

> 源文件: infra/bots/task_drivers/perf_puppeteer_skottie_frames/perf_puppeteer_skottie_frames.go

## 概述

`perf_puppeteer_skottie_frames` 是一个通用的 Puppeteer 性能测试任务驱动程序，专门用于测量 Skottie（Skia 的 Lottie 渲染引擎）动画帧的渲染性能。该程序使用 Puppeteer 自动化工具在 Chromium 浏览器中运行 CanvasKit/Skottie 基准测试，收集详细的帧渲染时间数据（包括有/无 flush、总帧时间等），并将结果格式化为 Skia Perf 系统可接受的 JSON 格式。支持 CPU 和 GPU 两种渲染模式，以及 WebGL 1/2 配置。

## 架构位置

该文件位于 Skia 性能测试基础设施的任务驱动层：

```
skia/
├── infra/
│   └── bots/
│       └── task_drivers/
│           └── perf_puppeteer_skottie_frames/
│               ├── perf_puppeteer_skottie_frames.go       # 主程序
│               ├── perf_puppeteer_skottie_frames_test.go  # 单元测试
│               └── make_lotties_with_assets/              # Lottie 文件准备工具
```

该程序与性能测试流水线深度集成，处理从测试执行到结果上传的完整流程。

## 主要类与结构体

### 常量定义

```go
const perfKeyWebGLVersion = "webgl_version"
const perfKeyCpuOrGPU = "cpu_or_gpu"
```

用于性能数据键值对的常量标识符。

### 核心数据结构

#### perfJSONFormat

```go
type perfJSONFormat struct {
    GitHash           string            `json:"gitHash"`
    SwarmingTaskID    string            `json:"swarming_task_id"`
    SwarmingMachineID string            `json:"swarming_machine_id"`
    Key               map[string]string `json:"key"`
    Results           map[string]map[string]perfResult `json:"results"`
}
```

Skia Perf 系统的顶层 JSON 格式，包含：
- Git 哈希和任务元数据
- 平台/配置键值对
- 嵌套的测试结果（测试名 → 配置 → 指标）

#### perfResult

```go
type perfResult map[string]float32
```

单个测试的性能指标映射，键为指标名（如 "avg_render_frame_ms"），值为测量值。

#### skottieFramesJSONFormat

```go
type skottieFramesJSONFormat struct {
    WithoutFlushMS []float32 `json:"without_flush_ms"`
    WithFlushMS    []float32 `json:"with_flush_ms"`
    TotalFrameMS   []float32 `json:"total_frame_ms"`
    JSONLoadMS     float32   `json:"json_load_ms"`
}
```

Puppeteer 基准测试的原始输出格式，包含三组时间序列数据和 JSON 加载时间。

### 命令行标志

程序定义了丰富的命令行参数：

**必需参数**:
- `project_id`: Google Cloud 项目 ID
- `task_name`: 任务名称
- `benchmark_path`: 基准测试文件位置
- `output_path`: 性能输出目录
- `git_hash`: Git 提交哈希
- `task_id`: 任务 ID
- `node_bin_path`: Node.js 二进制文件目录

**性能追踪键**:
- `os_trace`: 操作系统
- `model_trace`: 主机描述
- `cpu_or_gpu_trace`: CPU 或 GPU 配置
- `cpu_or_gpu_value_trace`: 具体硬件型号
- `webgl_version`: WebGL 主版本号（1 或 2）

**可选配置**:
- `canvaskit_bin_path`: CanvasKit 二进制文件位置
- `lotties_path`: Lottie 文件路径

## 公共 API 函数

### main()

```go
func main()
```

主入口函数，协调整个性能测试流程：
1. 解析命令行参数
2. 构建性能元数据对象
3. 设置 Node.js 环境
4. 执行 Skottie 帧基准测试
5. 处理和聚合测试数据
6. 写入 Perf JSON 文件

### makePerfObj()

```go
func makePerfObj(gitHash, taskID, machineID string, keys map[string]string) (perfJSONFormat, error)
```

创建性能数据对象的工厂函数。

**填充的键值对**:
- `arch`: "wasm"
- `browser`: "Chromium"
- `configuration`: "Release"
- `extra_config`: "SkottieFrames"
- `binary`: "CanvasKit"

### setup()

```go
func setup(ctx context.Context, benchmarkPath, nodeBinPath string) error
```

初始化测试环境：
- 运行 `npm ci` 安装依赖
- 创建输出目录 `out/`

### benchSkottieFrames()

```go
func benchSkottieFrames(ctx context.Context, perf perfJSONFormat, benchmarkPath, canvaskitBinPath, lottiesPath, nodeBinPath string) error
```

核心基准测试函数，负责：
1. 遍历 Lottie 文件夹
2. 为每个动画运行 `perf-canvaskit-with-puppeteer`
3. 根据 CPU/GPU 配置添加相应参数
4. 处理跳过列表（超时的动画）
5. 生成单独的 JSON 输出文件

### processSkottieFramesData()

```go
func processSkottieFramesData(ctx context.Context, perf perfJSONFormat, benchmarkPath, outputFilePath string) error
```

处理基准测试原始输出：
1. 扫描输出目录中的 JSON 文件
2. 解析每个文件的性能数据
3. 调用 `parseSkottieFramesMetrics` 计算统计指标
4. 将所有结果合并到单个 Perf JSON
5. 写入磁盘

### parseSkottieFramesMetrics()

```go
func parseSkottieFramesMetrics(b []byte) (map[string]float32, error)
```

解析和计算统计指标：
- 平均值、中位数、标准差
- 前 5 帧的详细指标
- 90th、95th、99th 百分位数

### summarize()

```go
func summarize(input []float32) (float32, float32, float32, float32, float32, float32)
```

统计辅助函数，返回：
1. 平均值
2. 中位数
3. 标准差
4. 90th 百分位数
5. 95th 百分位数
6. 99th 百分位数

## 内部实现细节

### Lottie 文件夹结构

程序期望的目录结构：
```
lottiesPath/
├── first-animation/
│   ├── data.json        # Lottie 动画数据
│   └── images/          # 资源文件夹
│       ├── img001.png
│       ├── img002.png
│       └── my-font.ttf
├── second-animation/
│   └── ...
```

使用 `filepath.Walk` 识别顶层文件夹，每个文件夹作为一个测试用例。

### 跳过列表机制

```go
var cpuSkiplist = []string{
    "Curly_Hair",     // 约 200 帧后超时
    "Day_Night",      // 约 400 帧后超时
    // ...
}
var gpuSkiplist = []string{}
```

CPU 模式下跳过已知会超时的动画，GPU 模式下跳过列表为空。这避免了长时间等待和任务失败。

### Puppeteer 命令构建

```go
args := []string{filepath.Join(nodeBinPath, "node"),
    "perf-canvaskit-with-puppeteer",
    "--bench_html", "skottie-frames.html",
    "--canvaskit_js", filepath.Join(canvaskitBinPath, "canvaskit.js"),
    "--canvaskit_wasm", filepath.Join(canvaskitBinPath, "canvaskit.wasm"),
    "--input_lottie", filepath.Join(lottie, "data.json"),
    "--assets", filepath.Join(lottie, "images"),
    "--output", filepath.Join(benchmarkPath, "out", name+".json"),
}
```

**条件参数**:
- GPU 模式: 添加 `--use_gpu`
- WebGL 1: 添加 `--query_params webgl1`
- CPU 模式: 添加 `--timeout=90`

### 统计计算细节

```go
func summarize(input []float32) (...) {
    sorted := make([]float32, len(input))
    copy(sorted, input)
    sort.Slice(sorted, func(i, j int) bool {
        return sorted[i] < sorted[j]
    })

    // 平均值和方差
    avg := computeAverage(sorted)
    variance := float32(0)
    for i := 0; i < len(sorted); i++ {
        variance += (sorted[i] - avg) * (sorted[i] - avg)
    }
    stddev := float32(math.Sqrt(float64(variance / float32(len(sorted)))))

    // 百分位数
    medIdx := (len(sorted) * 50) / 100
    p90Idx := (len(sorted) * 90) / 100
    // ...
}
```

先排序，然后计算各种统计量。标准差使用总体标准差公式。

### 输出指标详解

生成 20 个性能指标：

**JSON 加载**:
- `json_load_ms`: Lottie JSON 解析时间

**渲染时间（无 flush）**:
- `avg_render_without_flush_ms`
- `median_render_without_flush_ms`
- `stddev_render_without_flush_ms`

**渲染时间（有 flush）**:
- `avg_render_with_flush_ms`
- `median_render_with_flush_ms`
- `stddev_render_with_flush_ms`

**总帧时间**:
- `avg_render_frame_ms`
- `median_render_frame_ms`
- `stddev_render_frame_ms`

**详细帧分析**:
- `1st_frame_ms` 到 `5th_frame_ms`: 前 5 帧的时间
- `avg_first_five_frames_ms`: 前 5 帧平均
- `90th_percentile_frame_ms`
- `95th_percentile_frame_ms`
- `99th_percentile_frame_ms`

## 依赖关系

### 外部库依赖

```go
import (
    "go.skia.org/infra/go/exec"          // 命令执行
    "go.skia.org/infra/go/skerr"         // 错误包装
    "go.skia.org/infra/go/sklog"         // 日志记录
    "go.skia.org/infra/go/util"          // 工具函数
    "go.skia.org/infra/task_driver/go/lib/os_steps"  // 文件操作
    "go.skia.org/infra/task_driver/go/td"            // 任务驱动框架
)
```

### 系统依赖

- **Node.js**: 运行 Puppeteer 脚本
- **npm**: 安装依赖包
- **Chromium**: Puppeteer 控制的浏览器
- **CanvasKit**: Skia 的 WASM 编译版本
- **Lottie 文件**: 测试输入

### 工具依赖

- **tools/perf-puppeteer/**: 包含 Puppeteer 基准测试脚本
  - `perf-canvaskit-with-puppeteer`: 主测试脚本
  - `skottie-frames.html`: 测试页面
  - `package.json`: Node.js 依赖定义

### 数据流

```
命令行参数 → makePerfObj()
    ↓
setup() → npm ci, 创建目录
    ↓
benchSkottieFrames():
    遍历 Lottie 文件夹
    ↓
    为每个动画:
        运行 perf-canvaskit-with-puppeteer
        ↓
        生成 JSON (out/animation_name.json)
    ↓
processSkottieFramesData():
    扫描 out/ 目录
    ↓
    为每个 JSON:
        parseSkottieFramesMetrics()
        ↓
        计算统计指标
        ↓
        添加到 Results
    ↓
    写入 perf-{taskID}.json
```

## 设计模式与设计决策

### 任务驱动模式

使用 `td.Do` 创建嵌套的步骤结构：
```go
err := td.Do(ctx, td.Props("Benchmark "+name), func(ctx context.Context) error {
    // 基准测试逻辑
})
```

这提供了层次化的日志和错误追踪。

### 容错设计

```go
for _, lottie := range lottieFolders {
    err = td.Do(ctx, td.Props("Benchmark "+name), func(ctx context.Context) error {
        // 测试逻辑
    })
    if err != nil {
        lastErr = td.FailStep(ctx, skerr.Wrap(err))
        // 不返回 - 继续测试其他输入
    }
}
return lastErr
```

单个测试失败不会中断整个任务，确保尽可能收集更多数据。

### 两阶段处理

1. **执行阶段**: `benchSkottieFrames` 运行所有测试，生成原始 JSON
2. **聚合阶段**: `processSkottieFramesData` 处理和汇总结果

这种分离允许：
- 并行执行测试（未来优化）
- 独立调试每个阶段
- 保留原始数据用于后续分析

### 配置驱动行为

通过 `ExtraConfig` 部分的任务名选择逻辑：
- CPU vs GPU 模式
- WebGL 版本选择
- 超时设置

这使得单个程序可以处理多种测试配置。

### 唯一输出文件名

```go
outputFile := filepath.Join(outputAbsPath, fmt.Sprintf("perf-%s.json", *taskID))
```

使用任务 ID 作为文件名的一部分，避免上传到 GCS 时的文件名冲突。

## 性能考量

### 超时保护

```go
if perf.Key[perfKeyCpuOrGPU] != "CPU" {
    args = append(args, "--use_gpu")
} else {
    args = append(args, "--timeout=90")
}
```

CPU 模式下设置 90 秒超时，防止慢速动画无限期运行。

### 跳过列表优化

预先跳过已知会超时的动画：
```go
if util.In(name, skiplist) {
    sklog.Infof("Skipping lottie %s", name)
    continue
}
```

节省大量 CI 时间和资源。

### 增量统计计算

```go
for i := 0; i < len(sorted); i++ {
    variance += (sorted[i] - avg) * (sorted[i] - avg)
}
```

单次遍历计算方差，避免多次迭代。

### 内存管理

```go
sorted := make([]float32, len(input))
copy(sorted, input)
```

复制数据而非原地排序，避免修改原始数据。对于帧数据（通常几百个浮点数），内存开销可接受。

### npm ci vs npm install

```go
exec.RunCwd(ctx, benchmarkPath, filepath.Join(nodeBinPath, "npm"), "ci")
```

使用 `npm ci`（clean install）而非 `npm install`：
- 更快（跳过依赖解析）
- 更可靠（严格遵循 package-lock.json）
- 适合 CI 环境

## 相关文件

### Skia 基础设施

- **tools/perf-puppeteer/**: Puppeteer 测试脚本
  - `perf-canvaskit-with-puppeteer.js`: 主测试运行器
  - `skottie-frames.html`: 测试页面模板
  - `package.json`: Node 依赖配置

### 相关任务驱动

- **perf_puppeteer_skottie_frames_test.go**: 单元测试
- **make_lotties_with_assets**: Lottie 文件转换工具
- **upload_perf_results**: 上传性能数据到 Skia Perf

### Lottie 资源

- **skia/internal/lotties_with_assets**: CIPD 包，包含测试用 Lottie
- **lottiefiles.com**: Lottie 动画来源

### CanvasKit 相关

- **modules/canvaskit/**: CanvasKit 源代码
- **modules/skottie/**: Skottie 渲染引擎

### 性能系统

- **Skia Perf**: https://perf.skia.org
- **upload_nano_results.py**: 上传脚本（处理 dm.json 格式）

### 测试流水线

```
编译 CanvasKit WASM
    ↓
准备 Lottie 文件 (make_lotties_with_assets)
    ↓
perf_puppeteer_skottie_frames (本程序)
    ↓
上传到 Skia Perf
    ↓
可视化和分析
```

该程序是 Skottie 性能监控流水线的核心组件，确保每次提交的性能变化都能被捕获和分析。
