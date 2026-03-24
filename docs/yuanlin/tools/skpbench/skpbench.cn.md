# skpbench - SKP GPU 基准测试工具

> 源文件: `tools/skpbench/skpbench.py`, `tools/skpbench/skpbench.cpp`

## 概述

skpbench 是 Skia 的 GPU 渲染性能基准测试工具，由 Python 驱动脚本（skpbench.py）和 C++ 基准测试二进制（skpbench.cpp）组成。Python 脚本管理测试执行、硬件监控和结果过滤，C++ 二进制负责实际的 SKP/SVG 文件加载和 GPU 渲染计时。

## 架构位置

位于 `tools/skpbench/` 目录，是 Skia 性能测试基础设施的核心组件。Python 脚本通过子进程调用 C++ 二进制。

## 主要类与结构体

### Python 端 (skpbench.py)

#### `SKPBench`
核心测试执行器，管理子进程生命周期和结果处理。类属性 `ARGV` 在模块加载时根据命令行参数构建基础命令行。
- `execute(hardware)` - 执行测试，监控硬件状态
- `run_warmup(warmup_time, config)` - 运行预热
- `get_header()` - 获取结果表头

#### `SubprocessMonitor(Thread)`
后台线程，逐行读取子进程 stdout 并放入消息队列。

#### `StddevException`
当结果标准差超过阈值时抛出，触发重试。

### C++ 端 (skpbench.cpp)

#### `Sample`
测试采样结果，包含帧数和持续时间。支持 ms 和 fps 两种指标模式。

#### `GpuSync`
GPU 同步工具，使用 FlushFinishTracker 实现最多 3 帧延迟的流水线。

#### `SkpProducer` (接口)
SKP 绘制接口，有 `StaticSkp`（单帧）和 `MultiFrameSkp`（多帧动画）两个实现。

#### `MultiFrameSkp`
从 .mskp 文件加载多帧 SKP 动画，支持 SkSharingDeserialContext 和 SkMultiPictureDocument。

## 公共 API 函数

### Python 命令行参数
| 参数 | 说明 |
|------|------|
| `skpbench` | C++ 二进制路径 |
| `--adb` | 通过 ADB 在设备上执行 |
| `--max-stddev` | 最大允许标准差（默认 4%）|
| `--config` | GPU 配置（默认 gl）|
| `--ddl` | DDL 模式 |
| `--lock-clocks` | 锁定设备时钟 |
| `srcs` | SKP/SVG 文件列表 |

### C++ 命令行标志
| 标志 | 说明 |
|------|------|
| `--duration` | 测试持续时间（默认 5000ms）|
| `--sampleMs` | 最小采样时长（默认 50ms）|
| `--gpuClock` | 使用 GPU 时钟计时 |
| `--fps` | 使用 FPS 而非 ms 指标 |
| `--ddl` | DDL 渲染模式 |
| `--src` | 输入文件 |

## 内部实现细节

### Python 驱动层
- 使用消息队列（`multiprocessing.Queue`）实现线程安全的子进程输出处理
- 定时器（每秒）触发硬件健康检查
- 标准差超阈值时指数退避重试（阈值乘以 sqrt(2)）
- 支持根据设备型号自动选择硬件控制类（Pixel C/Pixel/Pixel 2/Nexus 6P）

### C++ 基准层
- `run_benchmark`: CPU 时钟模式，收集采样直到达到 benchDuration
- `run_gpu_time_benchmark`: GPU 时钟模式，使用 GpuTimer 查询 GPU 端计时
- `run_ddl_benchmark`: DDL 模式，使用 DDLTileHelper 和多线程录制
- 结果统计：计算中位数、标准差（相对标准差百分比）
- 预热机制：首先 flush kNumFlushesToPrimeCache(3) 次以填充缓存
- 支持从 SVG 文件创建 SkPicture（需 SK_ENABLE_SVG）
- 最大渲染目标尺寸限制为 2048x2048

## 依赖关系

### Python
- `_adb.Adb`, `_benchresult.BenchResult`, `_hardware.*` - 内部模块
- `multiprocessing`, `threading`, `subprocess` - 并发和进程管理

### C++
- `include/gpu/ganesh/` - Ganesh GPU 后端
- `tools/ganesh/DDLTileHelper.h`, `DDLPromiseImageHelper.h` - DDL 支持
- `tools/ganesh/GpuTimer.h` - GPU 计时
- `tools/flags/` - 命令行标志

## 设计模式与设计决策

- **分层架构**: Python 层处理编排和监控，C++ 层专注于渲染性能测量
- **观察者模式**: SubprocessMonitor 异步观察子进程输出
- **策略模式**: 不同的 SkpProducer 实现处理不同类型的输入文件
- **重试机制**: 标准差过高时自动重新排队，逐步放宽阈值
- **单配置设计**: 每次进程只测一个配置/SKP 对，保证结果可重复

## 性能考量

- 3 帧流水线 GPU 同步 (`kMaxFrameLag=3`) 平衡 CPU/GPU 并行度和延迟
- DDL 模式支持多线程录制（ddlNumRecordingThreads）和独立 GPU 线程
- 采样时间保证为奇数，便于取中位数
- warmup 运行在实际测试前预热 GPU 缓存和驱动程序

## 相关文件

- `tools/skpbench/_hardware*.py` - 各设备硬件控制
- `tools/skpbench/_benchresult.py` - 结果解析
- `tools/skpbench/skiaperf.py` - Skia Perf 输出
- `tools/skpbench/sheet.py` - CSV 输出
