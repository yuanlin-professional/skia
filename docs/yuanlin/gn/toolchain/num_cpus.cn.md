# num_cpus.py

> 源文件: gn/toolchain/num_cpus.py

## 概述

`num_cpus.py` 是一个极简的 Python 工具,用于检测系统可用的 CPU 核心数量。该脚本在 Skia 构建系统中用于优化并行编译配置,通过查询系统的物理或逻辑处理器数量,帮助构建工具(如 Ninja)确定最佳的并行任务数,从而最大化构建性能。

尽管功能简单,但该工具在构建性能优化中扮演关键角色,使构建系统能够自动适应不同硬件配置,无需手动调优。

## 架构位置

`num_cpus.py` 在 Skia 构建工具链中的位置:

```
skia/
├── gn/
│   └── toolchain/
│       ├── num_cpus.py              # 本脚本 - CPU 核心数检测
│       ├── BUILD.gn                 # 工具链构建配置
│       └── ...                      # 其他工具链配置
├── BUILD.gn                         # 主构建文件
└── out/
    └── <config>/
        └── args.gn                  # 可能使用 CPU 数配置并行度
```

典型使用场景:
- **并行编译配置**: 设置 Ninja 的 `-j` 参数
- **测试并行度**: 确定并行运行的测试实例数
- **资源分配**: 根据 CPU 数量调整内存和线程池大小

## 主要类与结构体

该脚本采用函数式编程风格,不定义任何类或结构体。

## 公共 API 函数

### 主函数逻辑

```python
from __future__ import print_function

import multiprocessing

print(multiprocessing.cpu_count())
```

**功能**: 打印系统的 CPU 核心数量

**参数**: 无命令行参数

**返回值**: 通过标准输出打印一个整数,表示 CPU 核心数

**调用示例**:

```bash
# 直接运行
python gn/toolchain/num_cpus.py
# 输出示例: 8

# 在 shell 中使用
NUM_CPUS=$(python gn/toolchain/num_cpus.py)
echo "Building with $NUM_CPUS parallel jobs"
```

### GN 构建系统集成

```gn
# 在 .gn 或 BUILD.gn 文件中
declare_args() {
  # 自动检测 CPU 数量用于并行构建
  concurrent_jobs = exec_script(
    "gn/toolchain/num_cpus.py",
    [],
    "trim string"
  )
}

# 配置 Ninja 并行度
default_concurrent_jobs = concurrent_jobs
```

### Ninja 构建配置

```bash
# 使用脚本输出配置 Ninja
ninja -j $(python gn/toolchain/num_cpus.py) -C out/Release
```

## 内部实现细节

### multiprocessing.cpu_count() 函数

```python
multiprocessing.cpu_count()
```

**功能**: 返回系统中的 CPU 核心数

**检测机制** (平台相关):

**Linux**:
- 读取 `/proc/cpuinfo` 或使用 `os.sysconf('SC_NPROCESSORS_ONLN')`
- 返回在线(online)的逻辑处理器数量

**macOS**:
- 使用 `sysctl` 系统调用查询 `hw.ncpu`
- 返回逻辑处理器数量(包括超线程)

**Windows**:
- 查询 `NUMBER_OF_PROCESSORS` 环境变量
- 或使用 Windows API `GetSystemInfo()`

**返回值**:
- 逻辑处理器数量(包括超线程/SMT)
- 例如:4 核 8 线程的 CPU 返回 8

### 物理 vs 逻辑核心

**逻辑核心**:
- `cpu_count()` 返回逻辑核心数
- 包括超线程(Hyper-Threading)或 SMT(Simultaneous Multithreading)
- 例如: Intel i7-8700(6 核 12 线程)返回 12

**物理核心**:
- 需要其他方法检测(如 `psutil.cpu_count(logical=False)`)
- 本脚本未区分物理和逻辑核心

**构建优化考虑**:
- 使用逻辑核心数通常是最佳实践
- I/O 密集型任务(如编译)可以充分利用超线程
- CPU 密集型任务可能需要调整系数

### Python 2/3 兼容性

```python
from __future__ import print_function
```

确保在 Python 2.7 中也使用函数式 `print()`,保持跨版本兼容性。

### 错误处理

**隐式错误处理**:
```python
# 没有 try-except,依赖 multiprocessing 的内部错误处理
```

**可能的异常**:
- `NotImplementedError`: 在极少数平台上 `cpu_count()` 未实现
- 实际上几乎不会发生(主流平台都支持)

**失败后果**:
- 脚本异常退出
- 构建系统捕获错误并报告
- 可能回退到默认值(如 GN 配置的默认值)

## 依赖关系

### Python 标准库

```python
import multiprocessing  # 提供 cpu_count() 函数
```

**multiprocessing 模块**:
- Python 2.6+ 和 Python 3.x 都包含
- 主要用于多进程编程,但也提供系统信息查询

**无外部依赖**: 完全基于标准库,确保最大兼容性。

### 与构建系统的数据流

```
系统硬件信息
    ↓
multiprocessing.cpu_count()
    ↓
stdout 输出
    ↓
GN exec_script() 捕获
    ↓
构建变量赋值
    ↓
Ninja 并行度配置
    ↓
编译任务分配
```

## 设计模式与设计决策

### 最小化设计

**为什么不添加更多功能?**
- 不计算推荐的并行度(留给调用者)
- 不区分物理和逻辑核心
- 不考虑 CPU 负载或内存限制
- 不提供配置选项

**设计理由**:
- 单一职责:仅报告 CPU 数量
- 调用者可根据需求调整(如 `cpu_count - 1` 避免过载)
- 简单意味着可靠

### 信任平台 API

```python
multiprocessing.cpu_count()  # 直接使用,不验证
```

**假设**:
- Python 标准库的实现是正确的
- 操作系统提供的信息是准确的
- 不需要二次验证或校准

### 输出格式选择

```python
print(multiprocessing.cpu_count())  # 纯数字,无额外文本
```

**格式决策**:
- 仅输出数字,便于解析
- 无单位或描述文本
- 兼容 shell 的命令替换 `$()`
- 适合 GN 的 `trim string` 模式

## 性能考量

### 执行效率

**操作时间**:
- Python 启动: ~30-50ms
- `cpu_count()` 调用: < 1ms (系统调用)
- 总时间: ~30-50ms

**缓存特性**:
- `cpu_count()` 通常缓存结果(首次调用后)
- 但脚本每次都是新进程,无法利用缓存
- 对于构建配置阶段(仅调用一次)可接受

### 调用频率

**典型使用**:
- **GN 配置**: 每次 `gn gen` 调用一次
- **构建脚本**: 可能在 shell 脚本中多次调用
- **热路径**: 不在编译热路径上,性能影响可忽略

### 系统调用开销

**平台差异**:
- **Linux**: `sysconf()` 或文件读取,~0.1ms
- **macOS**: `sysctl()`,~0.1ms
- **Windows**: 环境变量查询或 API 调用,~0.1ms
- 所有平台都非常快

## 相关文件

### 同类工具

**Skia 构建工具**:
- `gn/checkdir.py`: 检查目录存在性
- `gn/highest_version_dir.py`: 查找最高版本目录

**系统信息工具**:
- `nproc` (Linux): 显示可用处理器数量
- `sysctl -n hw.ncpu` (macOS): macOS 等价命令
- `echo %NUMBER_OF_PROCESSORS%` (Windows): Windows 环境变量

### 典型使用场景

**GN 配置文件**:
```gn
# .gn 或 args.gn
declare_args() {
  num_cpus = exec_script("gn/toolchain/num_cpus.py", [], "trim string")

  # 推荐的并行任务数(留一个核心给系统)
  concurrent_jobs = num_cpus - 1
}
```

**构建脚本**:
```bash
#!/bin/bash
NUM_CPUS=$(python gn/toolchain/num_cpus.py)
echo "Detected $NUM_CPUS CPUs"

# 使用 80% 的核心进行构建
PARALLEL_JOBS=$((NUM_CPUS * 4 / 5))
ninja -j $PARALLEL_JOBS -C out/Release
```

**测试并行化**:
```python
import subprocess
num_cpus = int(subprocess.check_output(['python', 'gn/toolchain/num_cpus.py']))
# 运行并行测试
test_parallel_degree = min(num_cpus, 16)  # 最多 16 个并行测试
```

### Ninja 集成

**自动并行度**:
```bash
# Ninja 默认使用 cpu_count + 2 的并行度
ninja  # 自动检测

# 显式设置
ninja -j $(python gn/toolchain/num_cpus.py)

# 考虑 I/O 和内存,使用更多任务
JOBS=$(($(python gn/toolchain/num_cpus.py) * 2))
ninja -j $JOBS
```

### 替代实现

**使用 psutil 库**(更强大但需要安装):
```python
import psutil
print(psutil.cpu_count(logical=True))   # 逻辑核心
print(psutil.cpu_count(logical=False))  # 物理核心
```

**纯 shell 实现**:
```bash
# Linux
nproc

# macOS
sysctl -n hw.ncpu

# 跨平台(使用 Python)
python -c "import multiprocessing; print(multiprocessing.cpu_count())"
```

**为什么单独成文件?**
- 便于 GN 的 `exec_script()` 调用
- 统一的调用接口
- 可添加 shebang 直接执行
- 便于维护和测试

### 构建性能影响

**并行度推荐**:
```python
# 常见策略
num_cpus = cpu_count()
parallel_jobs = num_cpus  # 基本策略
parallel_jobs = num_cpus - 1  # 保留一个核心
parallel_jobs = int(num_cpus * 1.5)  # I/O 密集型任务
parallel_jobs = int(num_cpus * 0.75)  # 高内存使用时
```

**实际性能测试**(示例):
- 8 核机器编译 Skia:
  - `-j1`: 60 分钟
  - `-j4`: 20 分钟
  - `-j8`: 12 分钟
  - `-j16`: 11 分钟(收益递减)

该脚本提供了一个简单可靠的 CPU 核心数检测方案,是构建系统自动化并行度配置的基础工具,通过适应不同硬件环境优化编译性能。
