# parse_perf_csvs - Skottie WASM 性能 CSV 比较工具

> 源文件: `tools/skottie-wasm-perf/parse_perf_csvs.py`

## 概述

parse_perf_csvs.py 是一个 Python 辅助脚本，用于比较从 perf.skia.org 下载的两个 CSV 性能数据文件。它读取两组性能数据，移除异常值后计算各测试用例的平均值，并输出包含测试名称、两组平均值及百分比差异的合并 CSV 文件。

## 架构位置

位于 `tools/skottie-wasm-perf/` 目录，属于 Skottie WASM 性能测试工具集的一部分。与 `skottie-wasm-perf.js` 配合使用，用于性能数据的后处理和对比分析。

## 主要类与结构体

无类定义。文件由独立函数组成。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `read_from_csv(csv_file)` | 从 CSV 文件读取测试数据，返回 {test_name: avg_value} 字典 |
| `combine_results(d1, d2)` | 合并两组数据，计算百分比差异 |
| `write_to_csv(output_dict, output_csv)` | 将合并结果写入输出 CSV |
| `parse_and_output(csv1, csv2, output_csv)` | 完整流程：读取、合并、输出 |
| `main()` | 入口函数，解析命令行参数 |

## 内部实现细节

- 使用正则表达式 `^.*,test=(.*),$` 从 CSV 的 id 列中提取测试名称
- 异常值处理：对每组数据排序后，移除前后各 `NUM_OUTLIERS_TO_REMOVE`(=2) 个数据点
- 百分比差异计算公式: `(v2 - v1) / ((v2 + v1) / 2) * 100`
- 缺失数据用 `'N/A'` 标记

## 依赖关系

- Python 标准库: `csv`, `optparse`, `sys`, `re`

## 设计模式与设计决策

- **简单管道模式**: 读取 -> 合并 -> 写入的线性处理流
- **对称处理**: 两个 CSV 中独有的测试用例均保留在输出中

## 性能考量

- 适用于中小规模性能数据，不涉及大数据处理优化
- 使用 Python 2 的 `reduce` 函数计算平均值

## 相关文件

- `tools/skottie-wasm-perf/skottie-wasm-perf.js` - Skottie WASM 性能测试驱动
- `tools/skottie-wasm-perf/skottie-wasm-perf.html` - 测试页面
