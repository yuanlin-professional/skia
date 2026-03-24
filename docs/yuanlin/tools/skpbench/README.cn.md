# Skia skpbench SKP 基准测试工具

## 概述

`tools/skpbench` 是专门用于在 Android 设备上回放 SKP/MSKP 文件并测量帧率性能的基准测试工具。它通过控制设备时钟频率和停止干扰进程来实现低方差的性能测量，是 Skia 在 Android 平台上进行 GPU 性能基准测试的核心工具。

## 目录结构

```
tools/skpbench/
├── README.md                    # 英文使用文档
├── skpbench.cpp                 # C++ 核心基准测试程序（约 31KB）
├── skpbench.py                  # Python 驱动脚本（主入口）
├── skiaperf.py                  # Skia Perf 结果上传脚本
├── sheet.py                     # 电子表格格式输出工具
├── _adb.py                      # ADB 通信封装
├── _adb_path.py                 # ADB 路径查找
├── _benchresult.py              # 基准测试结果解析
├── _hardware.py                 # 硬件控制基类
├── _hardware_android.py         # Android 通用硬件控制
├── _hardware_pixel.py           # Pixel 设备专用配置
├── _hardware_pixel2.py          # Pixel 2 设备专用配置
├── _hardware_pixel_c.py         # Pixel C 设备专用配置
├── _hardware_nexus_6p.py        # Nexus 6P 设备专用配置
├── _os_path.py                  # 操作系统路径工具
└── __init__.py                  # Python 包初始化
```

## 核心组件

### skpbench.cpp

C++ 主程序，负责在设备端执行实际的 SKP 回放和计时：

- 使用 Ganesh GPU 后端（支持 GL ES、Vulkan 等配置）
- 支持 SKP 单帧和 MSKP 多帧文件
- 支持 DDL（Deferred Display List）并行渲染模式
- 使用 GPU 计时器精确测量绘制时间
- 支持 SVG 文件的渲染性能测试

### skpbench.py

Python 驱动脚本，是用户的主要交互入口：

- 通过 ADB 将 skpbench 二进制文件和测试数据推送到设备
- 管理设备硬件状态（CPU/GPU 频率锁定）
- 运行基准测试并收集结果
- 支持多种输出格式（CSV、JSON、Perf 格式）

### 硬件控制模块

各 `_hardware_*.py` 文件实现设备特定的性能优化：

- 锁定 CPU 和 GPU 时钟频率到固定值
- 禁用温控降频
- 停止后台服务和进程
- 确保可重复的测量条件

## 使用流程

### 1. 构建

```bash
# 为 Android arm64 构建
bin/gn gen out/arm64 --args='ndk="~/ndk" target_cpu="arm64" is_debug=false'
ninja -C out/arm64 skpbench
```

### 2. 部署到设备

```bash
adb push out/arm64/skpbench /data/local/tmp
adb push /path/to/test.skp /data/local/tmp/skps/
```

### 3. 运行测试

```bash
python tools/skpbench/skpbench.py \
  --adb \
  --config gles \
  /data/local/tmp/skpbench \
  /data/local/tmp/skps/foo.skp
```

### 4. 输出格式

```
   accum    median       max       min   stddev  samples  sample_ms  clock  metric  config    bench
  0.1834    0.1832    0.1897    0.1707    1.59%      101         50  cpu    ms      gles      foo.skp
```

| 字段 | 说明 |
|------|------|
| `accum` | 累计平均帧时间 |
| `median` | 中位数帧时间 |
| `max/min` | 最大/最小帧时间 |
| `stddev` | 标准差（百分比） |
| `samples` | 采样数 |
| `config` | GPU 配置（gles、vk 等） |

## 生产环境

skpbench 作为 Gerrit 的 tryjob 运行，结果上传到 perf.skia.org：

- 任务名示例: `Perf-Android-Clang-Pixel4XL-GPU-Adreno640-arm64-Release-All-Android_Skpbench`
- Perf 查询: `extra_config=Android_Skpbench`, `sub_result=accum_cpu_ms`

## 与其他模块的关系

- **tools/skp/**: 提供用于测试的 SKP 文件和网页录制工具
- **bench/**: nanobench 提供更广泛的微基准测试，skpbench 专注于 SKP 回放
- **tools/flags/**: 共享命令行参数解析框架
- **tools/ganesh/**: GPU 上下文工厂和 DDL 工具
