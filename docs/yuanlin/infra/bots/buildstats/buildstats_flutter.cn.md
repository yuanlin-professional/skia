# buildstats_flutter.py - Flutter 中 Skia 体积统计脚本

> 源文件: [infra/bots/buildstats/buildstats_flutter.py](../../../infra/bots/buildstats/buildstats_flutter.py)

## 概述

此脚本用于分析 Flutter 引擎中 Skia 代码所占用的二进制体积。它使用 `bloaty` 工具对 `libflutter.so`（Flutter 的 Android 原生库）进行深度分析，从编译单元（compile unit）和符号两个维度提取出属于 Skia（`third_party/skia`）的代码大小。脚本生成四份详细的人类可读报告，并输出一份包含 Skia 总体积的 Perf JSON 文件，用于持续监控 Skia 在 Flutter 中的体积占比变化。

## 架构位置

该脚本是 Skia CI 构建统计系统（`infra/bots/buildstats/`）中最复杂的分析脚本。它不分析 Skia 自身的构建产物，而是分析 Skia 作为第三方库嵌入 Flutter 后的体积贡献。这对于控制 Flutter 应用的安装包大小至关重要，因为 Skia 是 Flutter 渲染引擎的核心组件。

## 主要类与结构体

本文件包含以下函数（无类定义）：

- **`main()`**：主函数，协调四次 bloaty 分析并输出结果
- **`bytes_or_kb(num)`**：辅助格式化函数
- **`print_skia_lines_file_symbol(lines)`**：按文件-符号维度打印并汇总 Skia 代码大小
- **`print_skia_lines_symbol_file(lines)`**：按符号-文件维度打印 Skia 代码大小

## 公共 API 函数

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `main()` | 通过 `sys.argv` 接收 11 个参数 | 无 | 执行完整的 Flutter/Skia 体积分析 |
| `bytes_or_kb(num)` | `num`: 字节数 | 格式化字符串 | 将字节数格式化为 bytes 或 KiB |
| `print_skia_lines_file_symbol(lines)` | `lines`: bloaty TSV 输出 | `grand_total`: 总字节数 | 按文件分组打印各符号大小 |
| `print_skia_lines_symbol_file(lines)` | `lines`: bloaty TSV 输出 | 无 | 按符号打印所属文件和大小 |

## 内部实现细节

1. **输入参数**（11 个位置参数）：
   - `stripped_file`：已 strip 的 `libflutter.so`
   - `symbols_file`：未 strip 的 `libflutter.so`（含调试符号）
   - `bloaty_path`：bloaty 工具路径
   - `config`：配置名称（用作结果中的键）
   - `lib_name`：库名称
   - 以及标准的 out_dir、keystr、propstr、total_size_bytes_key、magic_seperator

2. **四次 Bloaty 分析**：
   - **文件-符号（短模板）**：`-d compileunits,symbols --demangle=short` — 按编译单元分组，模板被缩短
   - **文件-符号（完整模板）**：`-d compileunits,symbols --demangle=full` — 完整模板参数
   - **符号-文件（短模板）**：`-d symbols,compileunits --demangle=short` — 按符号分组
   - **符号-文件（完整模板）**：`-d symbols,compileunits --demangle=full` — 完整模板参数

3. **Skia 代码过滤**：TSV 输出中只保留路径包含 `'third_party/skia'` 的条目，过滤掉 `.debug` 符号。

4. **文件-符号报告格式**：
   - 按文件分组显示，路径从 `../../third_party/skia` 简化为 `skia`
   - 每个文件下列出各符号及其 filesize
   - 文件小计 + 全局总计

5. **符号-文件报告格式**：
   - 每行显示大小、符号名、所属文件
   - 过滤掉 `section` 类条目

6. **JSON 输出**：仅记录 Skia 代码的 `grand_total`，使用传入的 `config` 和 `lib_name` 作为键。

## 依赖关系

- **Python 标准库**：`json`、`os`、`subprocess`、`sys`
- **外部工具**：`bloaty`（需要 `--debug-file` 支持来读取未 strip 文件中的符号）
- **输入文件**：Flutter 构建产物（stripped 和 unstripped 的 `libflutter.so`）
- **下游**：Skia Perf 系统

## 设计模式与设计决策

- **双文件分析**：使用 stripped 文件测量实际大小，使用 unstripped 文件（`--debug-file`）获取符号和编译单元信息。这是因为 stripped 文件反映真实的发布大小，但不包含调试信息。
- **四维度交叉报告**：通过文件/符号两个维度和短/完整模板两种粒度的组合，提供了全面的分析视角。
- **路径过滤策略**：使用 `'third_party/skia'` 字符串匹配来隔离 Skia 的代码贡献，这是因为 Flutter 将 Skia 作为第三方依赖引入。
- **TSV 格式解析**：使用 bloaty 的 `--tsv` 输出而非默认表格，便于程序化处理制表符分隔的数据。
- **大小格式化**：`bytes_or_kb` 函数在 1024 字节阈值处切换显示单位，提升可读性。

## 性能考量

- 四次 bloaty 调用是主要耗时操作，特别是对大型 Flutter 库（通常 >10MB）。
- 使用 `-s file` 排序选项和 `-n 0`（不限制行数）确保完整数据但增加了处理时间。
- TSV 解析为纯字符串操作，开销可忽略。
- 脚本在 Flutter 相关的 CI 任务中运行，频率相对较低。

## 相关文件

- `infra/bots/buildstats/buildstats_cpp.py`：类似的 C++ 分析脚本（面向 Skia 自身）
- `infra/bots/buildstats/buildstats_wasm.py`：WASM 符号分析脚本
- `infra/bots/buildstats/buildstats_web.py`：最简单的大小统计脚本
- Flutter 引擎构建系统中生成 `libflutter.so` 的构建规则
