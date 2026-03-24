# test_all - 全量单元测试运行器

> 源文件: `tools/test_all.py`

## 概述

`test_all.py` 递归发现并运行 `tools/` 目录树下所有匹配 `*_test.py` 模式的 Python 单元测试,使用 `unittest` 框架的自动发现功能。

## 架构位置

属于 Skia Python 工具的测试入口。

## 公共 API 函数

- **`main()`**: 使用 `unittest.TestLoader().discover()` 发现并运行测试

## 内部实现细节

- 发现根目录为脚本所在目录
- 匹配模式: `*_test.py`
- 使用 verbosity=2 的 TextTestRunner 输出详细结果
- 任何测试失败都会抛出异常

## 依赖关系

- Python `unittest` 标准库

## 性能考量

运行时间取决于发现的测试数量。

## 相关文件

- `tools/` 目录下的 `*_test.py` 文件
