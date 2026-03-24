# helpers - Unicode 比较工具通用辅助函数

> 源文件: `tools/unicode_comparison/go/helpers/helpers.go`

## 概述

helpers.go 提供 Unicode 比较工具链中共用的辅助函数，包括错误检查、绝对值计算、字符串分割解析、路径展开和文件写入。

## 架构位置

位于 `tools/unicode_comparison/go/helpers/` 目录，被 bridge、extract_info、download_wiki 和 generate_table 等包共同引用。

## 主要类与结构体

无。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Check(e error)` | 错误检查，非 nil 时 panic |
| `Abs(x int)` | 整数绝对值 |
| `SplitAsInts(str, sep)` | 按分隔符分割字符串并转为整数数组 |
| `ExpandPath(path)` | 展开 `~/` 为用户主目录 |
| `WriteTextFile(fullFileName, text)` | 写入文本文件 |

## 内部实现细节

- `Check` 使用 panic 进行快速失败，适合脚本/工具型应用
- `ExpandPath` 通过 `os.UserHomeDir()` 获取主目录

## 依赖关系

- Go 标准库: `os`, `path/filepath`, `strconv`, `strings`

## 设计模式与设计决策

- **快速失败**: `Check` 函数简化错误处理，适合一次性运行的工具

## 性能考量

所有函数均为简单操作，无性能瓶颈。

## 相关文件

- 被 `bridge`, `extract_info`, `download_wiki`, `generate_table` 包引用
