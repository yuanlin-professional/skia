# skplaintexteditor/include - 文本编辑器公共头文件

## 概述

`modules/skplaintexteditor/include/` 目录包含纯文本编辑器模块的三个公共头文件,定义了编辑器的核心 API 和字符串处理基础设施。

`editor.h` 是核心文件,定义了 `Editor` 类的完整接口,包括文本操作 (insert/remove)、光标控制 (move)、坐标映射 (getPosition/getLocation) 和渲染 (paint)。`stringslice.h` 和 `stringview.h` 提供了轻量级的字符串处理工具。

## 关键类与函数

| 头文件 | 核心类型 | 说明 |
|--------|---------|------|
| `editor.h` | `Editor`, `TextPosition`, `Movement`, `PaintOpts` | 编辑器完整 API |
| `stringslice.h` | `StringSlice` | 可变字符串 (insert/remove/reserve) |
| `stringview.h` | `StringView` | 不可变字符串视图 (data + size) |

## 相关文档与参考

- 编辑器模块概述: `modules/skplaintexteditor/README.md`
- 实现代码: `modules/skplaintexteditor/src/`
