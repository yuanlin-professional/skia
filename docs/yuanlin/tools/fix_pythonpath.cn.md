# fix_pythonpath - Python 路径修复工具

> 源文件: `tools/fix_pythonpath.py`

## 概述

`fix_pythonpath.py` 将 Skia checkout 根目录添加到 `sys.path`,使其他 Python 脚本能够导入 Skia 仓库中的模块。

## 架构位置

属于 Skia Python 工具的基础设施。

## 公共 API 函数

- **`add_to_pythonpath(path)`**: 将指定目录添加到 sys.path
- 模块级代码自动将 checkout 根目录添加到路径

## 内部实现细节

通过脚本自身位置推算 checkout 根目录(`os.pardir` 上溯一级)。

## 依赖关系

- Python 标准库: `os`, `sys`

## 相关文件

- 其他需要导入 Skia 模块的 Python 脚本
