# sanitize_source_files - 源代码清理工具

> 源文件: `tools/sanitize_source_files.py`

## 概述

`sanitize_source_files.py` 递归扫描源代码目录,对 C/C++ 源文件(.cpp/.h/.c)应用一系列行修改器和文件修改器,进行格式清理。支持去除尾部空白、CRLF 转 LF、Tab 转空格、确保文件末尾只有一个换行符,以及检查 SVN EOL 属性。

## 架构位置

属于 Skia 的代码格式化和维护工具链。

## 主要类与结构体

无类定义,使用函数组织。

## 公共 API 函数

- **`SanitizeFilesWithModifiers()`**: 核心函数,递归处理目录
- **行修改器**: `TrailingWhitespaceRemover`, `CrlfReplacer`, `TabReplacer`
- **文件修改器**: `CopywriteChecker`, `EOFOneAndOnlyOneNewlineAdder`, `SvnEOLChecker`

## 内部实现细节

- 忽略 `.git`, `.svn`, `third_party` 子目录
- 仅修改实际变更的文件(write_to_file 标志)
- Tab 替换为 4 个空格
- EOF 修改器确保文件以恰好一个 `\n` 结尾

## 依赖关系

- Python 2 (`commands` 模块, `file()` 内置)
- SVN 命令行工具(SvnEOLChecker)

## 设计模式与设计决策

- **管道模式**: 行修改器和文件修改器可自由组合
- **最小写入**: 只有实际变更的文件才写回磁盘

## 性能考量

逐文件逐行处理,大型代码库可能耗时数秒。

## 相关文件

- `tools/rewrite_includes.py` - include 路径清理
