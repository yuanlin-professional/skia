# perf_puppeteer_skottie_frames_test

> 源文件: infra/bots/task_drivers/perf_puppeteer_skottie_frames/perf_puppeteer_skottie_frames_test.go

## 概述

`perf_puppeteer_skottie_frames_test` 是 `perf_puppeteer_skottie_frames` 任务驱动程序的全面单元测试套件。该测试文件验证了 Skottie 性能测试流程的各个核心组件，包括环境设置、Puppeteer 测试执行、性能数据处理和 JSON 输出生成。测试覆盖了 CPU 和 GPU 两种渲染模式，以及数据聚合和统计计算的正确性。

## 架构位置

```
skia/
└── infra/
    └── bots/
        └── task_drivers/
            └── perf_puppeteer_skottie_frames/
                ├── perf_puppeteer_skottie_frames.go        # 主程序
                └── perf_puppeteer_skottie_frames_test.go   # 测试套件（本文件）
```

## 主要类与结构体

### 测试常量

```go
const (
    someGitHash   = "032631e490db494128e0610a19adce4cab9706d1"
    someTaskID    = "4bdd43ed7c906c11"
    someMachineID = "skia-e-gce-203"
)
```

用于测试的模拟 Git 哈希和机器标识符。

### 测试数据

#### skottieFramesSampleOne 和 skottieFramesSampleTwo

两个预定义的 JSON 测试样本，包含：
- `total_frame_ms`: 总帧时间数组（26 个数据点）
- `without_flush_ms`: 无 flush 渲染时间
- `with_flush_ms`: 有 flush 渲染时间
- `json_load_ms`: JSON 加载时间

这些样本数据模拟了真实的 Puppeteer 测试输出。

## 公共 API 函数

### TestSetup_NPMInitializedBenchmarkOutCreated()

```go
func TestSetup_NPMInitializedBenchmarkOutCreated(t *testing.T)
```

测试 `setup()` 函数的行为：

**验证点**:
1. `npm ci` 命令被正确调用
2. 使用了正确的 Node.js 二进制路径
3. `out/` 目录被成功创建
4. 目录权限正确设置

**测试策略**: 使用 `exec.CommandCollector` 模拟命令执行，验证命令参数。

### TestBenchSkottieFrames_CPUHasNoUseGPUFlag()

```go
func TestBenchSkottieFrames_CPUHasNoUseGPUFlag(t *testing.T)
```

测试 CPU 模式下的 Puppeteer 命令构建。

**验证点**:
1. 命令不包含 `--use_gpu` 标志
2. 包含 `--timeout=90` 参数
3. 所有必需参数（CanvasKit 路径、Lottie 文件、输出路径）都正确传递

**测试数据结构**:
```go
perfObj := perfJSONFormat{
    Key: map[string]string{
        perfKeyCpuOrGPU: "CPU",
    },
}
```

### TestBenchSkottieFrames_GPUHasFlag()

```go
func TestBenchSkottieFrames_GPUHasFlag(t *testing.T)
```

测试 GPU 模式下的命令构建。

**验证点**:
1. 命令包含 `--use_gpu` 标志
2. 不包含超时参数（GPU 通常更快）
3. 其他参数配置正确

### TestProcessSkottieFramesData_CPUTwoInputsGetSummarizedAndCombined()

```go
func TestProcessSkottieFramesData_CPUTwoInputsGetSummarizedAndCombined(t *testing.T)
```

测试 CPU 模式下的数据处理和聚合流程。

**测试流程**:
1. 在临时目录创建两个 JSON 测试文件
2. 调用 `processSkottieFramesData()`
3. 验证输出 JSON 的结构和值

**验证的数据结构**:
```json
{
  "gitHash": "...",
  "swarming_task_id": "...",
  "swarming_machine_id": "...",
  "key": {
    "arch": "wasm",
    "binary": "CanvasKit",
    "browser": "Chromium",
    "configuration": "Release",
    "cpu_or_gpu": "CPU",
    ...
  },
  "results": {
    "first_animation": {
      "software": {
        "1st_frame_ms": 31.555,
        "avg_render_frame_ms": 5.662692,
        ...
      }
    },
    "second_animation": { ... }
  }
}
```

**关键验证点**:
- 20 个性能指标都正确计算
- 统计值（平均值、中位数、标准差、百分位数）精度正确
- 配置键为 "software"（CPU 渲染）

### TestProcessSkottieFramesData_GPUTwoInputsGetSummarizedAndCombined()

```go
func TestProcessSkottieFramesData_GPUTwoInputsGetSummarizedAndCombined(t *testing.T)
```

测试 GPU 模式下的数据处理。

**与 CPU 测试的差异**:
1. `cpu_or_gpu` 键设置为 "GPU"
2. `cpu_or_gpu_value` 为 "QuadroP400"（真实 GPU 型号）
3. 配置键为 "webgl2"（默认 GPU 配置）

**测试数据结构**:
```go
keys := map[string]string{
    "os":               "Ubuntu18",
    "model":            "Golo",
    perfKeyCpuOrGPU:    "GPU",
    "cpu_or_gpu_value": "QuadroP400",
}
```

### writeFilesToDisk()

```go
func writeFilesToDisk(path string, fileNamesToContent map[string]string) error
```

辅助函数，用于创建测试文件。

**功能**:
- 创建目录（如不存在）
- 将映射中的每个键值对写入文件
- 设置适当的权限

## 内部实现细节

### 测试框架集成

所有测试使用 Skia 的任务驱动测试框架：

```go
res := td.RunTestSteps(t, false, func(ctx context.Context) error {
    mock := exec.CommandCollector{}
    ctx = td.WithExecRunFn(ctx, mock.Run)
    // 测试逻辑
    return nil
})
require.Empty(t, res.Errors)
require.Empty(t, res.Exceptions)
```

这提供了：
- 步骤追踪和日志记录
- 命令执行模拟
- 错误收集和报告

### 命令模拟

使用 `exec.CommandCollector` 捕获而非真正执行命令：

```go
mock := exec.CommandCollector{}
ctx = td.WithExecRunFn(ctx, mock.Run)
// ... 调用被测函数 ...
require.Len(t, mock.Commands(), 1)
cmd := mock.Commands()[0]
assert.Equal(t, "/fake/path/to/node/bin/node", cmd.Name)
assert.Equal(t, expectedArgs, cmd.Args)
```

这允许验证命令参数而无需实际运行 Node.js 或 Puppeteer。

### 临时目录管理

```go
input, err := ioutil.TempDir("", "inputs")
require.NoError(t, err)
defer testutils.RemoveAll(t, input)
```

每个测试创建独立的临时目录，测试后自动清理。

### 完整的 JSON 验证

测试不仅验证结构，还逐字比较完整的 JSON 输出：

```go
b, err := ioutil.ReadFile(outputFile)
require.NoError(t, err)
assert.Equal(t, `{完整的期望 JSON}`, string(b))
```

这确保：
- JSON 格式正确（缩进、换行）
- 所有字段都存在
- 数值计算精确

### 数值精度验证

测试数据包含已知的统计结果：

```go
"avg_render_frame_ms": 5.662692,     // 预计算的平均值
"median_render_frame_ms": 0.795,     // 预计算的中位数
"stddev_render_frame_ms": 17.463467, // 预计算的标准差
```

这些值是手工计算或通过独立脚本验证的，确保统计函数的正确性。

## 依赖关系

### 测试库

```go
import (
    "github.com/stretchr/testify/assert"    // 断言
    "github.com/stretchr/testify/require"   // 必需条件检查
    "go.skia.org/infra/go/exec"             // 命令执行模拟
    "go.skia.org/infra/go/testutils"        // Skia 测试工具
    "go.skia.org/infra/task_driver/go/td"   // 任务驱动测试框架
)
```

### 标准库

```go
import (
    "context"
    "io/ioutil"
    "os"
    "path/filepath"
    "testing"
)
```

### 被测模块

所有测试函数都测试 `perf_puppeteer_skottie_frames.go` 中定义的函数。

## 设计模式与设计决策

### 表驱动测试原则

虽然没有显式使用表驱动测试，但 CPU 和 GPU 测试使用类似结构，便于添加新配置：

```go
// CPU 测试
perfObj := perfJSONFormat{Key: map[string]string{perfKeyCpuOrGPU: "CPU"}}

// GPU 测试
perfObj := perfJSONFormat{Key: map[string]string{perfKeyCpuOrGPU: "GPU"}}
```

### 黄金文件策略

使用完整的 JSON 字符串作为期望输出：

```go
assert.Equal(t, `{
  "gitHash": "032631e490db494128e0610a19adce4cab9706d1",
  ...
}`, string(b))
```

这类似于黄金文件（golden file）测试，但内联在代码中。优点：
- 容易查看期望输出
- 无需管理外部文件
- 变更时强制显式更新

### 依赖注入

通过上下文注入模拟的命令执行函数：

```go
ctx = td.WithExecRunFn(ctx, mock.Run)
```

这是依赖注入的一种形式，使得单元测试无需真实的系统调用。

### 隔离性原则

每个测试函数都：
1. 创建独立的临时目录
2. 使用独立的命令收集器
3. 不依赖其他测试的状态
4. 完全清理资源

这确保了测试的可重复性和并行执行能力。

### 真实性与可测试性的平衡

测试样本数据 `skottieFramesSampleOne` 和 `skottieFramesSampleTwo` 包含真实的数据分布：
- 第一帧通常较慢（冷启动）
- 后续帧有波动但整体稳定
- 偶尔有异常值（第 2 帧和第 16 帧）

这使测试既可重现又接近真实场景。

## 性能考量

### 测试速度

测试使用模拟而非真实执行：
- 不启动 Node.js 进程
- 不运行 Puppeteer
- 不渲染实际动画

单个测试通常在毫秒级完成，整个套件在秒级完成。

### 内存使用

测试数据相对较小：
- 每个 JSON 样本约 1 KB
- 临时文件立即写入磁盘
- 使用 `defer` 确保清理

即使并行运行多个测试，内存占用也很低。

### 文件系统操作

最小化磁盘 I/O：
- 只创建必需的测试文件
- 重用临时目录结构
- 延迟清理避免竞态条件

## 相关文件

### 被测试的模块

- **perf_puppeteer_skottie_frames.go**: 主程序逻辑

### 测试基础设施

- **go.skia.org/infra/task_driver/go/td**: 任务驱动测试框架
- **go.skia.org/infra/go/testutils**: 通用测试工具

### 真实数据源

测试样本数据基于真实的 Puppeteer 输出：
- **tools/perf-puppeteer/**: 包含生成这些数据的脚本
- **skottie-frames.html**: 测试页面模板

### CI 集成

这些测试作为 Skia CI 流程的一部分运行：
- 每次代码审查都运行
- 提交前必须通过
- 防止性能测试回归

### 相关测试

- **infra/bots/task_drivers/testutils/testutils_test.go**: 测试工具的测试
- **其他任务驱动的测试文件**: 使用类似模式

### 测试覆盖率

该测试套件覆盖了主程序的核心功能：
- `setup()`: 100% 覆盖
- `benchSkottieFrames()`: 主要路径覆盖（跳过列表逻辑未完全覆盖）
- `processSkottieFramesData()`: 100% 覆盖
- `parseSkottieFramesMetrics()`: 100% 覆盖
- `summarize()`: 通过集成测试间接覆盖

未覆盖的部分：
- `main()`: 集成测试函数，通常不进行单元测试
- 错误处理路径：某些边缘情况（如磁盘满、权限错误）

这种覆盖率确保了性能测试流程的可靠性，是 Skia 质量保证策略的重要组成部分。
