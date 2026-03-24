# BUILD_simulator - BUILD 文件模拟展开工具

> 源文件: `tools/BUILD_simulator.py`

## 概述

`BUILD_simulator.py` 模拟执行 `BUILD.public` 文件中的 Python 代码,展开 `glob()` 和 `select()` 调用,将变量定义输出到 `tools/BUILD.public.expected` 文件。用于检查 BUILD 文件变更对源文件列表的影响。

## 架构位置

属于 Skia 构建系统的辅助分析工具(面向旧版 BUILD 系统)。

## 公共 API 函数

- **`BUILD_glob(include, exclude)`**: 模拟 BUILD 文件的 glob() 函数
- **`BUILD_glob_single(pattern)`**: 处理单个 glob 模式(含 `**` 支持)
- **`select_simulator(d)`**: 模拟 select(),展开所有分支

## 内部实现细节

- 将 `**` 转换为正则表达式 `.*` 进行递归匹配
- 通过 `execfile` 执行 BUILD.public(Python 2 语法)
- 模拟 `cc_library`, `cc_test`, `exports_files` 为空操作

## 依赖关系

- Python 2 (使用 execfile 和 print >>)

## 设计模式与设计决策

- **代码作配置**: 将 BUILD 文件当作 Python 代码执行,提取变量定义

## 性能考量

需要遍历文件系统进行 glob 匹配。

## 相关文件

- `BUILD.public` - 被模拟的 BUILD 文件
