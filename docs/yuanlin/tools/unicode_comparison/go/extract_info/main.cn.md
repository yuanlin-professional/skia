# extract_info - Unicode 实现信息提取工具

> 源文件: `tools/unicode_comparison/go/extract_info/main.go`

## 概述

extract_info/main.go 为给定的 ICU 实现收集性能、内存和实际 Unicode 属性数据。它遍历输入文本文件，调用 SkUnicode 桥接库计算各种代码单元标志（字素簇、换行、词边界等），并将结果写入结构化的输出文件供比较工具使用。

## 架构位置

位于 `tools/unicode_comparison/go/extract_info/` 目录，是比较工具链的数据采集阶段。通过 bridge 包调用具体的 Unicode 实现。

## 主要类与结构体

无自定义类型。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `walkRecursively(input, output)` | 递归遍历输入目录，镜像创建输出目录并处理文件 |
| `writeInfo(inputPath, outputPath)` | 处理单个文件，计算 Unicode 属性并写入输出 |
| `main()` | 入口，解析 `--root` 和 `--impl` 参数 |

## 内部实现细节

- 输出文件格式：第一行为计算耗时，后续各行分别记录 graphemes、soft breaks、hard breaks、whitespaces、words、controls 的位置列表
- 通过 `bridge.PerfComputeCodeunitFlags` 获取计算耗时
- 逐字节遍历文本，用 `bridge.GetFlags` 获取每个位置的标志位

## 依赖关系

- `go.skia.org/skia/tools/unicode_comparison/go/bridge` - C++ 桥接
- `go.skia.org/skia/tools/unicode_comparison/go/helpers` - 辅助函数

## 设计模式与设计决策

- **目录镜像**: 输出目录结构完全镜像输入目录，便于后续按文件对比

## 性能考量

- 逐字节遍历和 CGo 调用可能较慢，但准确性优先于速度

## 相关文件

- `tools/unicode_comparison/go/bridge/bridge.go` - 桥接层
- `tools/unicode_comparison/go/generate_table/main.go` - 表格生成
