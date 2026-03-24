# _os_path - 本地文件系统路径工具

> 源文件: `tools/skpbench/_os_path.py`

## 概述

_os_path.py 提供在本地文件系统上查找 SKP 文件的辅助函数。当 skpbench.py 在本地（非 ADB）模式运行时使用此模块。

## 架构位置

位于 `tools/skpbench/` 目录，属于 Skia GPU 基准测试工具 skpbench 的组成部分。

## 主要类与结构体

find_skps 函数接受路径/glob 列表，展开目录中的 .skp 和 .mskp 文件。

## 公共 API 函数

详见源文件中的类方法和模块级函数。

## 内部实现细节

find_skps 函数接受路径/glob 列表，展开目录中的 .skp 和 .mskp 文件。

## 依赖关系

os.path, glob

## 设计模式与设计决策

遵循 skpbench 工具集的模块化设计，各组件职责清晰分离。

## 性能考量

作为基准测试工具的组成部分，优先保证测试结果的准确性和可重复性。

## 相关文件

被 skpbench.py 导入
