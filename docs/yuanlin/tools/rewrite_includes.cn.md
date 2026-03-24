# rewrite_includes - Include 路径规范化工具

> 源文件: `tools/rewrite_includes.py`

## 概述

`rewrite_includes.py` 扫描 Skia 源码中的 `#include` 指令,将相对路径重写为基于 Skia 顶级目录的规范路径,并对同一块内的 include 进行排序去重。支持干运行(`--dry-run`)模式用于 CI 检查。

## 架构位置

属于 Skia 代码格式化和维护工具链。

## 公共 API 函数

无公共 API,作为命令行工具使用。

## 内部实现细节

- 扫描 roots: bench, dm, docs, experimental, fuzz, gm, include, modules, src, tests, tools 等
- 忽略列表: vulkan 第三方头文件、node_modules、skcms 等
- 支持 .h/.c/.m/.mm/.inc/.cc/.cpp 文件
- 对同一连续块内的 include 排序去重
- 歧义头文件名(多个同名文件)需要手动解决

## 依赖关系

- Python 标准库: `os`, `sys`, `argparse`, `io.StringIO`

## 设计模式与设计决策

- **短名映射**: 建立文件名到完整路径的映射,处理 `#include "Foo.h"` 到 `#include "path/to/Foo.h"` 的转换
- **块排序**: 保持 include 块的逻辑分组同时排序

## 性能考量

遍历整个源码树,大型代码库可能耗时数秒。

## 相关文件

- Skia 代码风格指南
