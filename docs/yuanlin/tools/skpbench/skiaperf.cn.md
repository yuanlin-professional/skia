# skiaperf - SKP 基准测试结果格式化为 Skia Perf

> 源文件: `tools/skpbench/skiaperf.py`

## 概述

skiaperf.py 将 skpbench.py 的输出格式化为 Skia Perf 系统可消费的 JSON 格式。它解析基准结果行，提取累计值、中位数、最小值和最大值，并按照 Skia Perf 的 key/properties 模式组织数据。

## 架构位置

位于 `tools/skpbench/` 目录，属于 Skia GPU 基准测试工具 skpbench 的组成部分。

## 主要类与结构体

JSONDict 类继承自 dict，实现写入后不可变语义（已设置的键不可覆盖），并在访问未定义键时自动创建嵌套字典。

## 公共 API 函数

详见源文件中的类方法和模块级函数。

## 内部实现细节

JSONDict 类继承自 dict，实现写入后不可变语义（已设置的键不可覆盖），并在访问未定义键时自动创建嵌套字典。

## 依赖关系

_benchresult.py - 结果解析

## 设计模式与设计决策

遵循 skpbench 工具集的模块化设计，各组件职责清晰分离。

## 性能考量

作为基准测试工具的组成部分，优先保证测试结果的准确性和可重复性。

## 相关文件

json, argparse, collections
