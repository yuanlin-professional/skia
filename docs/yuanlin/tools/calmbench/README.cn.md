# Skia Calmbench 低噪声基准测试工具

## 概述

`tools/calmbench` 是 Skia 的"安静"（calm）基准测试工具，用于在两个 Git 分支之间进行低噪声性能 A/B 对比测试。其名称中的"calm"表示它通过多次运行和统计分析来消除测量噪声，从而可靠地检测性能回归。它基于 nanobench 构建，通过自动化分支切换、多轮测试和智能剪枝来提供高置信度的性能比较结果。

## 目录结构

```
tools/calmbench/
├── calmbench.py   # 主入口脚本，管理 Git 分支切换和 nanobench 调用
└── ab.py          # A/B 测试核心算法，实现统计分析和智能剪枝
```

## 核心组件

### calmbench.py

主驱动脚本，负责：

- 解析命令行参数（目标分支、配置、重复次数等）
- 在 Git 分支之间切换并编译 nanobench
- 并行调度 A/B 测试运行
- 聚合和展示最终结果

**基本用法：**

```bash
# 对比 TEST_GIT_BRANCH 和 main 分支在 8888 配置下的性能
python tools/calmbench/calmbench.py TEST_GIT_BRANCH

# 指定 GL 配置和额外资源
python tools/calmbench/calmbench.py TEST_GIT_BRANCH --config gl \
    --extraarg "--svgs ~/Desktop/bots/svgs --skps ~/Desktop/bots/skps"
```

**主要参数：**

| 参数 | 说明 |
|------|------|
| `TEST_GIT_BRANCH` | 要测试的 Git 分支名（位置参数） |
| `--config` | nanobench 配置（默认 8888） |
| `--reps` | 初始重复次数 |
| `--extraarg` | 传递给 nanobench 的额外参数 |
| `--threads` | 并行线程数（默认 CPU 核心数的一半） |
| `--skiadir` | Skia 源码根目录 |

### ab.py

A/B 测试的核心统计算法：

**统计方法：**
- 对每个基准测试收集多次 `min_ms` 测量值的分布
- 计算 1/3 和 2/3 分位数作为分布的代表区间
- 如果 A 和 B 的分位数区间完全不相交，则报告为回归

**智能剪枝策略：**
- 初始对所有基准测试进行少量测量
- 随着迭代进行，剪除分位数区间已重叠的基准测试
- 仅对仍然存疑的基准测试继续增加测量次数
- 在指定最大迭代次数后终止

**关键常量：**

```python
FACTOR  = 3     # 上下分位数因子
DIFF_T  = 0.99  # "足够不同"的阈值
TERM    = 10    # 无嫌疑变化后的终止迭代数
MAXTRY  = 30    # 缩小嫌疑范围的最大 nanobench 尝试次数
```

## 工作流程

```
1. calmbench.py 接收目标分支参数
2. 编译 main 分支的 nanobench (版本 A)
3. 切换到目标分支，编译 nanobench (版本 B)
4. ab.py 开始 A/B 测试循环：
   a. 对所有基准测试运行 A 和 B
   b. 收集 min_ms 测量值
   c. 计算分位数区间
   d. 剪除已确定无差异的测试
   e. 对存疑测试增加测量次数
   f. 重复直到满足终止条件
5. 输出最终回归报告
```

## 输出结果

工具会报告：
- 检测到显著性能变化的基准测试列表
- 每个基准测试的 A/B 分位数区间
- 变化方向（回归或改进）和幅度

## 与其他模块的关系

- **bench/nanobench**: calmbench 底层使用 nanobench 执行实际测量
- **tools/skpbench/**: skpbench 专注于 Android SKP 回放，calmbench 专注于 A/B 分支比较
- **perf.skia.org**: 线上持续性能监控系统
