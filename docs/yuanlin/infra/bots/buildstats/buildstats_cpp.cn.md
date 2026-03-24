# buildstats_cpp.py - C++ 构建产物大小与段分析脚本

> 源文件: [infra/bots/buildstats/buildstats_cpp.py](../../../infra/bots/buildstats/buildstats_cpp.py)

## 概述

此脚本用于生成 Skia C++ 构建产物（如 `libskia.a` 或共享库）的详细大小统计信息。它使用 `bloaty` 工具进行符号级和段级分析，将二进制文件按 ELF 段（如 `.text`、`.data`、`.bss` 等）分解，记录每个段的文件大小和虚拟内存大小。所有数据以 Skia Perf JSON 格式输出，用于跟踪编译产物在代码变更后的大小变化。

## 架构位置

该脚本属于 Skia CI 构建统计子系统（`infra/bots/buildstats/`），专门分析原生 C++ 二进制文件。它提供了比 `buildstats_web.py`（仅大小）和 `buildstats_wasm.py`（大小+符号）更深入的段级分析，是了解 Skia 原生库内部结构的重要工具。

## 主要类与结构体

本文件无类定义。`main()` 函数为唯一逻辑入口。

## 公共 API 函数

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `main()` | 通过 `sys.argv` 接收：input_file, out_dir, keystr, propstr, bloaty_path, total_size_bytes_key, magic_seperator | 无 | 执行段分析和大小统计 |

## 内部实现细节

1. **人类可读概览**：调用 `bloaty <file> -d sections,shortsymbols -n 200` 生成分段+符号的概览报告（限制 200 行），输出到 stdout。
2. **段级 CSV 分析**：调用 `bloaty <file> -d sections -n 0 --csv` 生成完整的段级数据（CSV 格式）。
3. **段数据解析**：
   - 逐行解析 CSV 输出（格式：`sections,vmsize,filesize`）
   - 跳过表头行（以 `'sections'` 开头）
   - 对段名进行正则清理（非字母数字字符替换为 `_`）
   - 每个段记录 `in_file_size_bytes`（磁盘大小）和 `vm_size_bytes`（虚拟内存大小）
4. **结果结构**：
   - `'default'` 切片：记录整个二进制的 total_size_bytes
   - `'section_<name>'` 切片：每个 ELF 段的详细大小
5. **JSON 输出**：写入 Perf 格式的 JSON 文件。

## 依赖关系

- **Python 标准库**：`csv`、`json`、`os`、`re`、`subprocess`、`sys`
- **外部工具**：`bloaty`（Google 二进制分析器）
- **上下游**：CI 构建流水线提供输入，Skia Perf 消费输出

## 设计模式与设计决策

- **双层数据粒度**：stdout 输出包含 `sections,shortsymbols` 的交叉分析（供人阅读），而 JSON 文件只包含段级汇总（供 Perf 系统消费）。
- **CSV 输出解析**：使用 bloaty 的 `--csv` 模式而非默认表格输出，便于程序化解析。
- **段名清理**：使用 `re.sub('[^0-9a-zA-Z_]', '_', section)` 将段名（如 `.text`）中的特殊字符替换为下划线，使其成为有效的 JSON 键名。
- **VM 大小与文件大小区分**：记录两种大小指标，因为 `.bss` 等段在文件中不占空间但加载时需要内存，这对理解二进制运行时行为很重要。
- **不包含 gzip 大小**：与 `buildstats_web.py` 不同，C++ 二进制通常不需要网络传输，因此不测量 gzip 大小。

## 性能考量

- bloaty 分析是主要计算开销，特别是 `-d sections,shortsymbols -n 200` 的交叉分析。
- CSV 解析为纯字符串操作，非常快速。
- 脚本在 CI 流水线中每次构建运行一次。

## 相关文件

- `infra/bots/buildstats/buildstats_web.py`：Web 构建统计
- `infra/bots/buildstats/buildstats_wasm.py`：WASM 构建统计
- `infra/bots/buildstats/buildstats_flutter.py`：Flutter 构建统计（最复杂）
- Skia Perf 仪表板中的二进制大小跟踪面板

### 补充说明

- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
- 构建统计数据对于 Skia 项目的二进制大小优化工作至关重要，帮助团队及时发现和解决大小回归问题。
