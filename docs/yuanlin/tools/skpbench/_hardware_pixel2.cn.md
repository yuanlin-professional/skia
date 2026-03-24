# HardwarePixel2 - Pixel 2 硬件基准测试控制

> 源文件: `tools/skpbench/_hardware_pixel2.py`

## 概述

HardwarePixel2 类为 Google Pixel 2 设备提供专门的硬件锁定配置，用于获得可重复的 GPU 基准测试结果。它锁定特定的 CPU、GPU 和内存频率，禁用热管理引擎，并验证硬件状态是否在预期范围内。

## 架构位置

位于 `tools/skpbench/` 目录，继承自 `HardwareAndroid`，是设备特定硬件控制层。

## 主要类与结构体

### `HardwarePixel2(HardwareAndroid)`
- **预设频率**: CPU=2035200 KHz, GPU=670000000 Hz, MEM=13763
- **核心布局**: 关闭 0-3,7 号核心，锁定 4-6 号快速核心
- **sanity_check**: 验证电池电量(>30%)、在线 CPU(4-6)、时钟频率、GPU 温度和节流状态

## 公共 API 函数

继承自 HardwareAndroid，覆写 `__enter__` 和 `sanity_check`。

## 内部实现细节

- 停止 thermal-engine 和 perfd 守护进程
- 设置 CPU 为 userspace governor 并锁定频率
- 设置 GPU bus_split=0, idle_timer=10000
- 锁定内存频率（cpubw/gpubw/mincpubw/memlat-cpu0）
- GPU 设为 performance governor 并锁定频率和 power level
- 验证 msm_therm(zone10) 和 pm8998_tz(zone7) 热区温度

## 依赖关系

- `_hardware.Expectation` - 硬件状态验证
- `_hardware_android.HardwareAndroid` - Android 硬件基类

## 设计模式与设计决策

- **模板方法**: 覆写父类的进入/检查方法，提供设备特定的配置

## 性能考量

锁定在 66% 的最大频率（GPU_POWER_LEVEL=1），在保证稳定性的同时避免过热。

## 相关文件

- `_hardware_android.py` - Android 硬件基类
- `_hardware_pixel.py`, `_hardware_nexus_6p.py` - 其他设备实现
