# generate_table - Unicode 比较表 HTML 生成器

> 源文件: `tools/unicode_comparison/go/generate_table/main.go`

## 概述

generate_table/main.go 是 Unicode 实现比较工具的核心组件，负责读取多个 ICU 实现的输出数据，生成包含性能、内存和准确性对比的 HTML 表格。它比较不同 Unicode 库（如 ICU、icu4x 等）在字素簇、换行、词边界等方面的结果差异。

## 架构位置

位于 `tools/unicode_comparison/go/generate_table/` 目录，是 Unicode 比较工具链的最终输出生成器。读取 `extract_info` 工具生成的中间数据。

## 主要类与结构体

### `Range` - 范围表示（Start, End, Type）
### `Ratio` - 整数比率（Num/Total），带除法格式化方法
### `FloatRatio` - 浮点比率（Top/Bottom），带百分比格式化方法
### `CalculatedDelta` - 计算差异汇总（性能、内存、磁盘、各类边界差异计数）

## 公共 API 函数

脚本入口通过 `main()` 函数执行，使用 `flag` 包解析命令行参数：
- `--root`: 数据集根目录
- `--impl`: 要比较的实现列表（逗号分隔）

## 内部实现细节

- 递归遍历输入目录，按语言/区域分组比较结果
- 使用 Go HTML 模板引擎生成格式化的比较表格
- 差异计算采用对称差集算法，统计各类 Unicode 属性的不一致数量
- 支持多语言（25种语言区域），包括中文、阿拉伯语、希伯来语等

## 依赖关系

- `go.skia.org/skia/tools/unicode_comparison/go/helpers` - 辅助函数
- Go 标准库: `flag`, `fmt`, `html/template`, `os`, `path/filepath`, `sort`, `strconv`, `strings`

## 设计模式与设计决策

- **模板渲染**: 使用 Go 内置 HTML 模板系统生成输出，分离数据与展示
- **增量聚合**: `CalculatedDelta.Add` 支持逐文件累积统计

## 性能考量

- 文件 I/O 是主要瓶颈，但数据集规模通常较小
- 排序确保输出的确定性和可比性

## 相关文件

- `tools/unicode_comparison/go/extract_info/main.go` - 数据提取
- `tools/unicode_comparison/go/bridge/bridge.go` - C++ 桥接
