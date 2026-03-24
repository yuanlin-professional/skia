# BenchResult - 基准测试结果解析

> 源文件: `tools/skpbench/_benchresult.py`

## 概述

BenchResult 类使用正则表达式从 skpbench 输出的文本行中解析基准测试结果，提取累计值、中位数、最大/最小值、标准差、采样数、时钟类型、指标和配置等字段。

## 架构位置

位于 `tools/skpbench/` 目录，属于 Skia GPU 基准测试工具 skpbench 的组成部分。

## 主要类与结构体

使用复杂的命名捕获组正则表达式 PATTERN 匹配格式化的数字列。format() 方法支持添加配置后缀并重新格式化输出行。

## 公共 API 函数

详见源文件中的类方法和模块级函数。

## 内部实现细节

使用复杂的命名捕获组正则表达式 PATTERN 匹配格式化的数字列。format() 方法支持添加配置后缀并重新格式化输出行。

## 依赖关系

被 skiaperf.py, sheet.py, skpbench.py 引用

## 设计模式与设计决策

遵循 skpbench 工具集的模块化设计，各组件职责清晰分离。

## 性能考量

作为基准测试工具的组成部分，优先保证测试结果的准确性和可重复性。

## 相关文件

re
