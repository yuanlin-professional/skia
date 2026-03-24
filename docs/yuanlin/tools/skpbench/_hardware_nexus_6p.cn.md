# HardwareNexus6P - Nexus 6P 硬件基准测试控制

> 源文件: `tools/skpbench/_hardware_nexus_6p.py`

## 概述

HardwareNexus6P 为 Google Nexus 6P 设备提供硬件锁定配置。锁定 3 个大核心（CPU 4-6），关闭所有其他核心，并锁定 GPU 和 DDR 频率。

## 架构位置

位于 `tools/skpbench/` 目录，继承自 `HardwareAndroid`。

## 主要类与结构体

### `HardwareNexus6P(HardwareAndroid)`
- CPU_CLOCK_RATE = 1728000
- GPU_CLOCK_RATE = 510000000
- 参考 Qualcomm ADB 性能调优文档设置 GPU/DDR 参数

## 内部实现细节

使用 force_bus_on、force_rail_on、force_clk_on 以及 1000000 idle_timer 确保 GPU 保持活跃。DDR 使用 performance governor 锁定为 9887。

## 相关文件

- `_hardware_android.py`, `_hardware_pixel.py`
