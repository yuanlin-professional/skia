# HardwareAndroid - Android 硬件基准测试控制

> 源文件: `tools/skpbench/_hardware_android.py`

## 概述

HardwareAndroid 类控制 Android 设备的硬件状态以获得可重复的基准测试结果。它禁用后台服务（WiFi、蓝牙、GPS）、杀死 GUI 进程、禁用 ASLR、锁定 CPU 和 GPU 时钟频率。

## 架构位置

位于 `tools/skpbench/` 目录，属于 Skia GPU 基准测试工具 skpbench 的组成部分。

## 主要类与结构体

HardwareAndroid 继承 Hardware 基类，通过 ADB shell 命令控制设备。__enter__ 启用飞行模式、禁用后台服务、锁定最快的 3 个 CPU 核心（其余关闭）、锁定 Adreno GPU 频率。__exit__ 通过硬重启恢复设备。

## 公共 API 函数

详见源文件中的类方法和模块级函数。

## 内部实现细节

HardwareAndroid 继承 Hardware 基类，通过 ADB shell 命令控制设备。__enter__ 启用飞行模式、禁用后台服务、锁定最快的 3 个 CPU 核心（其余关闭）、锁定 Adreno GPU 频率。__exit__ 通过硬重启恢复设备。

## 依赖关系

_hardware.py - 基类, _adb.py - ADB 封装

## 设计模式与设计决策

遵循 skpbench 工具集的模块化设计，各组件职责清晰分离。

## 性能考量

作为基准测试工具的组成部分，优先保证测试结果的准确性和可重复性。

## 相关文件

adb shell 命令
