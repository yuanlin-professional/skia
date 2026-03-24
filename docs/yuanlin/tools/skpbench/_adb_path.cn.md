# _adb_path - ADB 远程路径工具

> 源文件: `tools/skpbench/_adb_path.py`

## 概述

_adb_path.py 提供在 Android 设备上通过 ADB 查找 SKP 文件的辅助函数。使用 ADB shell 的 find 命令在设备文件系统上搜索。

## 架构位置

位于 `tools/skpbench/` 目录，属于 Skia GPU 基准测试工具 skpbench 的组成部分。

## 主要类与结构体

find_skps 先获取 root 权限（因为 SKP 可能在受保护目录中），然后通过 shell find 命令搜索 .skp 和 .mskp 文件。

## 公共 API 函数

详见源文件中的类方法和模块级函数。

## 内部实现细节

find_skps 先获取 root 权限（因为 SKP 可能在受保护目录中），然后通过 shell find 命令搜索 .skp 和 .mskp 文件。

## 依赖关系

_adb.py - ADB 封装

## 设计模式与设计决策

遵循 skpbench 工具集的模块化设计，各组件职责清晰分离。

## 性能考量

作为基准测试工具的组成部分，优先保证测试结果的准确性和可重复性。

## 相关文件

re, subprocess
