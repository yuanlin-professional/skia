# Adb - Android Debug Bridge 封装

> 源文件: `tools/skpbench/_adb.py`

## 概述

Adb 类封装 Android Debug Bridge 命令行工具，提供 shell 命令执行、root 权限获取、设备重启等功能。支持指定设备序列号和自定义 ADB 二进制路径。

## 架构位置

位于 `tools/skpbench/` 目录，属于 Skia GPU 基准测试工具 skpbench 的组成部分。

## 主要类与结构体

内部使用 subprocess 执行 ADB 命令。__establish_connection 确保设备已启动（循环检查 sys.boot_completed 属性）。支持 echo 模式用于调试。

## 公共 API 函数

详见源文件中的类方法和模块级函数。

## 内部实现细节

内部使用 subprocess 执行 ADB 命令。__establish_connection 确保设备已启动（循环检查 sys.boot_completed 属性）。支持 echo 模式用于调试。

## 依赖关系

被 _hardware_android.py, skpbench.py 引用

## 设计模式与设计决策

遵循 skpbench 工具集的模块化设计，各组件职责清晰分离。

## 性能考量

作为基准测试工具的组成部分，优先保证测试结果的准确性和可重复性。

## 相关文件

subprocess, time, re
