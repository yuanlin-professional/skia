# HardwarePixel - Pixel/Pixel XL 硬件基准测试控制

> 源文件: `tools/skpbench/_hardware_pixel.py`

## 概述

HardwarePixel 为 Google Pixel 和 Pixel XL 设备提供专门的硬件锁定配置。锁定 2 个快速核心（CPU 2-3），关闭 2 个慢速核心，并将 GPU 和 DDR 频率固定为性能模式。

## 架构位置

位于 `tools/skpbench/` 目录，继承自 `HardwareAndroid`。

## 主要类与结构体

### `HardwarePixel(HardwareAndroid)`
- CPU_CLOCK_RATE = 1670400
- GPU_CLOCK_RATE = 315000000
- 锁定核心 2-3，关闭核心 0-1

## 内部实现细节

停止 thermal-engine/perfd，设置 DDR 最小频率为 13763，GPU 为 performance governor，power level=4。

## 相关文件

- `_hardware_android.py`, `_hardware_pixel2.py`, `_hardware_nexus_6p.py`
