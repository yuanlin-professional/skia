# skplaintexteditor/src - 文本编辑器实现代码

## 概述

`modules/skplaintexteditor/src/` 目录包含纯文本编辑器模块的核心实现。`editor.cpp` 实现了编辑器的全部文本操作和渲染逻辑,`shape.cpp` 封装了文本整形流程,`stringslice.cpp` 实现了可变字符串的内存管理,`word_boundaries.cpp` 提供了单词边界检测功能。

文本整形 (`shape.cpp`) 是性能敏感的核心组件。`Shape()` 函数使用 `SkShaper` 对给定的 UTF-8 文本进行布局,生成 `SkTextBlob` 和每个字形的位置信息,同时检测换行点和单词边界。

## 目录结构

```
src/
+-- editor.cpp          # Editor 类完整实现
+-- stringslice.cpp     # StringSlice 内存管理 (realloc)
+-- shape.h             # Shape() 函数声明与 ShapeResult 结构
+-- shape.cpp           # 文本整形实现 (调用 SkShaper)
+-- word_boundaries.h   # 单词边界检测声明
+-- word_boundaries.cpp # 单词边界检测实现
```

## 关键实现

| 文件 | 核心逻辑 |
|------|---------|
| `editor.cpp` | insert/remove 文本修改、move 光标导航、paint 渲染 (背景/选区/文本/光标) |
| `shape.cpp` | `Shape()` 使用 SkShaper 整形,收集 glyphBounds 用于光标定位 |
| `stringslice.cpp` | `insert()`/`remove()` 使用 memmove 实现高效的就地修改 |
| `word_boundaries.cpp` | 基于 Unicode 属性的单词边界检测 |

## 相关文档与参考

- 公共 API: `modules/skplaintexteditor/include/`
- SkShaper: `modules/skshaper/`
