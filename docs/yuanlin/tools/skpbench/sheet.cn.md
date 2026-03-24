# sheet - SKP 基准测试结果 CSV 格式化工具

> 源文件: `tools/skpbench/sheet.py`

## 概述

sheet.py 将 skpbench.py 的输出格式化为 CSV 电子表格，支持在浏览器中通过 Chrome 的 "Office Editing" 扩展打开为 Google Sheet。它解析基准结果、按配置组织列、按测试用例组织行，并计算算术平均和几何平均。

## 架构位置

位于 `tools/skpbench/` 目录，是基准测试结果可视化工具。

## 主要类与结构体

### `FullConfig`
namedtuple，包含 config、sample_ms、clock、metric 字段。提供 `qualified_name` 方法生成带限定符的配置名。

### `Parser`
核心解析器，维护 sheet_qualifiers（全局通用的限定符）、config_qualifiers（配置特定限定符）、fullconfigs 列表和行/列数据字典。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Parser.parse_file(infile)` | 解析输入文件 |
| `Parser.print_csv(outfile)` | 输出 CSV |
| `main()` | 入口，支持 `--open` 在浏览器中打开 |

## 内部实现细节

- 自动检测全局共享的限定符和配置特定的限定符
- 计算 MEAN 和 GEOMEAN 汇总行
- `--open` 模式创建临时文件并通过 `webbrowser.open` 打开

## 依赖关系

- `_benchresult.BenchResult` - 结果解析
- Python 标准库: `collections`, `operator`, `tempfile`, `webbrowser`

## 设计模式与设计决策

- **增量解析**: 逐行处理输入，自动推断限定符分类

## 性能考量

适用于常规规模的基准测试结果，无大数据优化。

## 相关文件

- `_benchresult.py` - 结果解析器
- `skiaperf.py` - Skia Perf 格式输出
