# find_run_binary - 二进制查找与执行工具

> 源文件: `tools/find_run_binary.py`

## 概述

`find_run_binary.py` 是一个 Python 模块,提供在 Skia 构建输出目录中查找和运行二进制文件的功能。它会在 `out/Release` 和 `out/Debug` 目录中搜索指定的程序(包括 Windows 的 .exe 后缀)。

## 架构位置

属于 Skia 工具链的基础工具模块,被其他脚本导入使用。

## 公共 API 函数

- **`run_command(args)`**: 运行命令行程序并返回 stdout,非零退出码抛出异常
- **`find_path_to_program(program)`**: 在 Release/Debug 输出目录中查找程序的绝对路径

## 内部实现细节

- 搜索顺序: Release 优先于 Debug
- 支持 Windows 平台(.exe 后缀)
- 基于脚本位置推算 trunk 路径

## 依赖关系

- Python 标准库: `os`, `subprocess`, `sys`

## 设计模式与设计决策

- **约定优于配置**: 假设标准的 `out/Release` 和 `out/Debug` 目录结构

## 性能考量

简单的文件存在性检查,开销极小。

## 相关文件

- Skia 构建系统输出目录(`out/Release`, `out/Debug`)
