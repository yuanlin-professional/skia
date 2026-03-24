# HardwarePixelC - Pixel C 平板硬件基准测试控制

> 源文件: `tools/skpbench/_hardware_pixel_c.py`

## 概述

HardwarePixelC 为 Google Pixel C（Nvidia Tegra X1）平板设备提供硬件锁定配置。它使用 Tegra 特有的 pstate 接口控制 GPU/EMC 频率，关闭第四个核心以减少发热。

## 架构位置

位于 `tools/skpbench/` 目录，继承自 `HardwareAndroid`。

## 主要类与结构体

### `HardwarePixelC(HardwareAndroid)`
- CPU_CLOCK_RATE = 1326000
- GPU_EMC_PROFILE_ID = '04'（307 MHz core, 1065 MHz EMC）
- 使用 `/sys/devices/57000000.gpu/pstate` 控制 GPU

## 内部实现细节

- 所有 CPU 共享相同的频率设置（仅设 cpu0）
- 过滤 NvRm 平台检测的无害警告信息
- 验证皮肤/CPU/GPU 温度和节流状态

## 相关文件

- `_hardware_android.py`, `_hardware_pixel.py`
