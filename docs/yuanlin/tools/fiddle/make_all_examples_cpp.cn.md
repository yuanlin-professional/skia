# make_all_examples_cpp - Fiddle 示例汇总文件生成器

> 源文件: `tools/fiddle/make_all_examples_cpp.py`

## 概述

make_all_examples_cpp.py 是一个 Python 脚本，用于在添加或删除 Fiddle 示例后重新生成 `all_examples.cpp` 文件。它扫描 `docs/examples/` 目录中的所有 `.cpp` 文件，按字母顺序生成 `#include` 指令列表。

## 架构位置

位于 `tools/fiddle/` 目录，是 Fiddle 构建流程的维护工具。

## 主要类与结构体

无类定义。

## 公共 API 函数

无函数定义。脚本以顶层执行方式运行。

## 内部实现细节

- 使用 `glob.glob('../../docs/examples/*.cpp')` 查找所有示例文件
- 对路径排序后剥离 `../../` 前缀
- 支持 `--print-diff` 参数，输出新旧文件的 unified diff

## 依赖关系

- Python 标准库: `argparse`, `difflib`, `glob`, `os`

## 设计模式与设计决策

- **代码生成**: 自动化维护大型 include 列表，减少人工错误

## 性能考量

无。一次性脚本。

## 相关文件

- `tools/fiddle/all_examples.cpp` - 生成的目标文件
