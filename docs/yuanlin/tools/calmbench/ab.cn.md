# ab.py

> 源文件: tools/calmbench/ab.py

## 概述

`ab.py` 是 Skia 性能基准测试系统 `calmbench` 的核心 A/B 测试工具脚本。该脚本通过统计分析方法，对两个版本（A 和 B）的 nanobench 性能测试结果进行比较，识别性能回归。它使用分位数估计和自适应采样策略，在合理的测试时间内高置信度地检测性能差异。

该脚本实现了一个智能的迭代测试流程：首先进行初始测试，然后对可疑的性能回归项进行更多次测试以缩小不确定性，最终输出有统计学意义的性能回归报告。

## 架构位置

该文件位于 Skia 性能测试工具集中：

```
skia/
  tools/
    calmbench/
      ab.py           # 本文件（A/B 测试核心逻辑）
      calmbench.py    # 用户友好的封装脚本
    nanobench/        # 底层性能测试工具
```

在 Skia 测试架构中的位置：
- **性能测试层**: 驱动 nanobench 进行基准测试
- **统计分析层**: 对测试结果进行统计学分析
- **回归检测层**: 自动识别性能回归
- **CI/CD 集成**: 用于持续集成系统中的性能监控

## 主要类与结构体

### ThreadWithException

自定义线程类，捕获线程中的异常。

```python
class ThreadWithException(Thread):
    def __init__(self, target):
        super(ThreadWithException, self).__init__(target = target)
        self.exception = None
```

**功能**:
- 继承自 `threading.Thread`
- 捕获并保存线程执行中的异常
- 允许主线程检查子线程的异常状态

**核心方法**:
- `run()`: 包装目标函数，捕获异常
- `join()`: 等待线程完成

### ThreadRunner

简单的多线程任务执行器。

```python
class ThreadRunner:
    """Simplest and stupidiest threaded executer."""
    def __init__(self, args):
        self.concise = args.concise
        self.threads = []
```

**功能**:
- 管理并发执行的线程池
- 限制同时运行的线程数量
- 提供进度指示器（可选）
- 收集并重新抛出线程异常

**核心方法**:
- `add(args, fn)`: 添加任务到线程池
- `wait()`: 等待所有线程完成

## 公共 API 函数

### parse_args()

```python
def parse_args():
    parser = ArgumentParser(description=HELP)
    # ... 参数定义
    return args
```

**功能**: 解析命令行参数。

**关键参数**:
- `outdir`: 输出目录
- `a`, `b`: A 和 B 的名称
- `nano_a`, `nano_b`: A 和 B 的 nanobench 二进制路径
- `arg_a`, `arg_b`: A 和 B 的 nanobench 参数
- `repeat`: 初始运行次数
- `skip_b`: 是否跳过 B 的运行（复用旧数据）
- `config`: nanobench 配置（如 8888, gl, vulkan）
- `threads`: 线程数
- `noinit`: 是否跳过初始化运行

**返回值**: 解析后的参数对象

### add_time(args, name, bench, t, unit)

```python
def add_time(args, name, bench, t, unit):
    normalized_t = t * 1000 ** UNITS.index(unit)
```

**功能**: 添加基准测试时间到全局字典。

**特性**:
- 时间单位标准化为纳秒
- 自动分类到 `timesA` 或 `timesB`
- 按基准测试名称组织数据

### append_times_from_file(args, name, filename)

```python
def append_times_from_file(args, name, filename):
    with open(filename) as f:
        lines = f.readlines()
    for line in lines:
        # 解析 nanobench 输出格式
```

**功能**: 从 nanobench 输出文件中提取时间数据。

**解析格式**:
- 正则表达式匹配时间和单位: `([+-]?\d*.?\d+)(s|ms|µs|ns)`
- 过滤指定的 config
- 提取基准测试名称

### run(args, threadRunner, name, nano, arg, i)

```python
def run(args, threadRunner, name, nano, arg, i):
    def task():
        file_i = "%s/%s.out%d" % (args.outdir, name, i)
        # 运行 nanobench 并收集结果
    threadRunner.add(args, task)
```

**功能**: 在线程中运行单次 nanobench 测试。

**流程**:
1. 生成输出文件名
2. 判断是否需要运行（或复用缓存）
3. 执行 nanobench 命令
4. 解析输出文件并添加到全局时间字典

### init_run(args)

```python
def init_run(args):
    threadRunner = ThreadRunner(args)
    for i in range(1, max(args.repeat, args.threads / 2) + 1):
        run(args, threadRunner, args.a, args.nano_a, args.arg_a, i)
        run(args, threadRunner, args.b, args.nano_b, args.arg_b, i)
    threadRunner.wait()
```

**功能**: 执行初始的多次 nanobench 运行。

**特性**:
- 并行运行 A 和 B 的测试
- 运行次数取决于 `repeat` 和线程数
- 为后续分析收集基础数据

### get_lower_upper(values)

```python
def get_lower_upper(values):
    i = max(0, (len(values) - 1) / FACTOR)
    return values[i], values[-i - 1]
```

**功能**: 计算分布的下分位数和上分位数。

**算法**:
- 使用 `FACTOR = 3` 计算 1/3 和 2/3 分位数
- 假设数据已排序
- 返回 (lower_quantile, upper_quantile)

### different_enough(lower1, upper2)

```python
def different_enough(lower1, upper2):
    return upper2 < DIFF_T * lower1
```

**功能**: 判断两个分布是否有显著差异。

**逻辑**:
- 如果 B 的上分位数 < 0.99 * A 的下分位数，则认为有显著差异
- `DIFF_T = 0.99` 是阈值常量

## 内部实现细节

### 全局变量

```python
timesLock = Lock()
timesA  = {}  # {bench_name: [time1, time2, ...]}
timesB  = {}
```

**作用**:
- `timesA`, `timesB`: 存储 A 和 B 的测试时间
- `timesLock`: 保护全局字典的线程安全

### 常量配置

```python
FACTOR  = 3     # 下/上分位数因子
DIFF_T  = 0.99  # 差异显著性阈值
TERM    = 10    # 无可疑变化后终止的迭代次数
MAXTRY  = 30    # 缩小可疑项的最大尝试次数
UNITS   = "ns µs ms s".split()
```

### 时间单位标准化

```python
normalized_t = t * 1000 ** UNITS.index(unit)
```

- `ns` (纳秒): 索引 0, 乘数 1
- `µs` (微秒): 索引 1, 乘数 1000
- `ms` (毫秒): 索引 2, 乘数 1000000
- `s` (秒): 索引 3, 乘数 1000000000

### 线程池管理

```python
def add(self, args, fn):
    if len(self.threads) >= args.threads:
        self.wait()  # 等待有线程完成
    t = ThreadWithException(target = fn)
    t.daemon = True
    self.threads.append(t)
    t.start()
```

**特性**:
- 限制并发线程数
- 守护线程模式
- 自动等待空闲槽位

### 进度指示器

```python
def spin():
    spinners = [".  ", ".. ", "..."]
    while len(self.threads) > 0:
        sys.stderr.write(
            "\r" + spinners[i % len(spinners)] +
            " (%d threads running)" % len(self.threads)
        )
        time.sleep(0.5)
```

**特性**:
- 动画效果的进度指示
- 显示当前运行的线程数
- 可通过 `--concise` 禁用

### 参数分割

```python
def split_arg(arg):
    raw = shlex.split(arg)
    result = []
    for r in raw:
        if '~' in r:
            result.append(os.path.expanduser(r))
        else:
            result.append(r)
    return result
```

**功能**:
- 使用 `shlex.split` 正确处理引号
- 自动展开 `~` 为用户主目录

### 自适应采样策略

该脚本实现了智能采样策略（代码未完全包含在片段中）：

1. **初始阶段**: 对所有基准测试运行 `repeat` 次
2. **分析阶段**: 计算每个基准测试的分位数区间
3. **可疑筛选**: 识别分位数区间不重叠的基准测试
4. **迭代细化**: 仅对可疑项增加测试次数
5. **终止条件**: 连续 `TERM` 次迭代无新可疑项，或达到 `MAXTRY` 次

## 依赖关系

**标准库依赖**:
- `re`: 正则表达式解析
- `os`, `sys`: 系统操作
- `subprocess`: 执行外部命令
- `shlex`: Shell 参数解析
- `multiprocessing`: 获取 CPU 核心数
- `threading`: 多线程支持
- `argparse`: 命令行参数解析
- `json`: JSON 处理
- `time`: 时间相关
- `traceback`: 异常追踪
- `pdb`: 调试（已导入但未使用）

**外部依赖**:
- `nanobench`: Skia 的基准测试二进制
- `calmbench.py`: 封装脚本（调用本脚本）

**依赖图**:
```
calmbench.py (用户接口)
    ↓
ab.py (本文件)
    ↓
nanobench (A 版本) | nanobench (B 版本)
    ↓
基准测试结果文件
    ↓
统计分析 → 回归报告
```

## 设计模式与设计决策

### 设计模式

1. **生产者-消费者模式**: 线程池执行任务
2. **模板方法模式**: `run()` 定义任务模板
3. **策略模式**: 自适应采样策略
4. **单例模式**: 全局时间字典

### 设计决策

**1. 分位数估计而非均值**:
- 均值对离群值敏感
- 分位数更稳定，反映分布中心趋势
- 1/3 和 2/3 分位数避免极端值影响

**2. 迭代细化策略**:
- 初始全量测试开销大
- 仅对可疑项增加测试次数
- 平衡测试时间和准确性

**3. 多线程并发**:
- 提高测试吞吐量
- CPU 基准测试（8888, 565）使用多线程
- GPU 基准测试使用单线程（避免竞争）

**4. 时间单位标准化**:
- 统一为纳秒，避免单位混乱
- 便于比较和排序

**5. 文件缓存机制**:
- 支持跳过 B 的运行（`skip_b`）
- 复用历史测试结果
- 加速迭代开发

**6. 线程安全**:
- 使用锁保护全局字典
- 避免数据竞争

**7. 异常处理**:
- 自定义线程类捕获异常
- 主线程统一处理
- 确保测试失败可见

### 统计学原理

**分位数区间不重叠判断**:
```
A: [---lower1========upper1---]
B:          [---lower2========upper2---]

如果 upper2 < 0.99 * lower1，则认为 A 显著快于 B
```

**置信度**:
- 1/3 和 2/3 分位数对应约 33% 的置信区间
- 通过多次测试收窄置信区间

## 性能考量

### 优化策略

1. **并行测试**: 利用多核 CPU
2. **自适应采样**: 避免过度测试
3. **结果缓存**: 复用历史数据
4. **早停策略**: `TERM` 和 `MAXTRY` 限制

### 时间复杂度

- **初始阶段**: O(repeat * num_benches * test_time)
- **迭代阶段**: O(MAXTRY * num_suspects * test_time)
- **总时间**: 取决于可疑项数量，通常远小于全量测试

### 内存占用

- **时间字典**: O(num_benches * num_runs)
- **线程池**: O(threads)
- **总体**: 轻量级，内存不是瓶颈

### 典型运行时间

| 场景 | 基准测试数 | 线程数 | 估计时间 |
|------|----------|--------|---------|
| 快速检查 | ~100 | 4 | ~5 分钟 |
| 标准测试 | ~500 | 8 | ~20 分钟 |
| 全面测试 | ~1000 | 8 | ~60 分钟 |

## 相关文件

### 同目录文件
- `tools/calmbench/calmbench.py`: 用户友好的封装脚本
- `tools/calmbench/README.md`: 使用文档（如果存在）

### Skia 性能测试工具
- `tools/nanobench/`: nanobench 源代码
- `bench/`: 基准测试用例

### 配置文件
- `infra/bots/`: CI 机器人配置
- 性能监控系统配置

### 输出文件
- `{outdir}/{name}.out{i}`: nanobench 原始输出
- `{outdir}/suspects.txt`: 可疑回归列表（推测）
- `{outdir}/report.json`: 回归报告（推测）

### 相关文档
- Skia 性能测试指南
- nanobench 使用文档
- CI/CD 性能监控文档
