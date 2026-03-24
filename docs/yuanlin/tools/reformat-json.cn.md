# reformat-json - JSON 格式化工具

> 源文件: `tools/reformat-json.py`

## 概述

`reformat-json.py` 将 JSON 文件重写为 Python 标准的 pretty-print 格式。这确保后续的 `rebaseline.py` 运行产生有意义的 diff(只显示实际的校验和差异,不被格式差异遮蔽)。

## 架构位置

属于 Skia GM (Graphical Model) 测试基线管理工具链。

## 公共 API 函数

- **`Reformat(filename)`**: 重新格式化单个 JSON 文件
- **`_Main()`**: 解析命令行参数,处理所有指定文件

## 内部实现细节

通过 `gm_json` 模块读取和写入 JSON,利用 Python 的标准格式化。

## 依赖关系

- `gm_json` 模块(从 `gm/` 目录导入)

## 性能考量

逐文件处理,读入内存后重写。

## 相关文件

- `gm/gm_json.py` - GM JSON 读写工具
