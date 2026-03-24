# skplaintexteditor - 纯文本编辑器模块

## 概述

`modules/skplaintexteditor` 是基于 Skia 构建的纯文本编辑器模块,提供了完整的文本编辑功能,包括文本输入、删除、光标移动、文本选择、复制以及可视化渲染。该模块展示了如何使用 Skia 的文本整形 (SkShaper) 和渲染 (SkTextBlob) API 构建一个功能完整的文本编辑器。

编辑器的核心是 `Editor` 类,它管理一个由 `TextLine` 组成的文本行列表。每个 TextLine 包含原始文本数据 (`StringSlice`)、整形后的文本块 (`SkTextBlob`)、光标位置数组和单词边界信息。当文本内容或显示宽度发生变化时,编辑器会触发重新整形 (reshape) 操作,使用 `SkShaper` 进行文本布局。

文本定位系统使用 `TextPosition` 结构体,通过段落索引 (fParagraphIndex) 和字节偏移 (fTextByteIndex) 来精确标识文本中的位置。光标移动支持多种方向:左右字符移动、上下行移动、行首行尾跳转以及单词级别的左右跳转。

渲染通过 `paint()` 方法实现,支持自定义背景色、前景色、选区颜色和光标颜色。编辑器先绘制背景,然后绘制选区高亮,接着渲染文本,最后绘制光标。

`StringSlice` 是一个轻量级的可变字符串类,不以 NUL 结尾,支持在任意位置插入和删除文本,使用 `realloc` 进行内存管理。`StringView` 则是对应的不可变视图类型。

## 架构图

```
+-------------------------------+
|      editor_application.cpp   |
|      (应用层入口)             |
+-------------------------------+
              |
              v
+-------------------------------+
|        Editor 类               |
| - fLines: vector<TextLine>    |
| - fFont: SkFont               |
| - fWidth: 显示宽度            |
+-------------------------------+
    |         |         |
    v         v         v
+--------+ +--------+ +--------+
| insert | | remove | | move   |
| (插入) | | (删除) | | (光标) |
+--------+ +--------+ +--------+
    |
    v
+-------------------------------+
|  reshapeAll() (重新整形)       |
|  --> Shape() 函数              |
+-------------------------------+
    |
    v
+-------------------------------+
|  SkShaper (文本整形引擎)       |
|  - BiDi 双向文本               |
|  - Script 脚本检测             |
|  - 换行与布局                  |
+-------------------------------+
    |
    v
+-------------------------------+
|  ShapeResult                   |
|  - SkTextBlob (整形结果)       |
|  - lineBreakOffsets (行断点)   |
|  - glyphBounds (字形边界)      |
|  - wordBreaks (单词边界)       |
+-------------------------------+
    |
    v
+-------------------------------+
|  paint(SkCanvas*, PaintOpts)   |
|  1. 绘制背景                   |
|  2. 绘制选区                   |
|  3. 绘制文本 (drawTextBlob)   |
|  4. 绘制光标                   |
+-------------------------------+
```

## 目录结构

```
modules/skplaintexteditor/
+-- BUILD.gn                    # GN 构建配置
+-- README.md                   # 原始 README
+-- include/                    # 公共头文件
|   +-- editor.h                # Editor 核心类
|   +-- stringslice.h           # 可变字符串 StringSlice
|   +-- stringview.h            # 字符串视图 StringView
+-- src/                        # 实现文件
|   +-- editor.cpp              # Editor 类实现
|   +-- stringslice.cpp         # StringSlice 实现
|   +-- shape.h                 # Shape 函数声明与 ShapeResult
|   +-- shape.cpp               # 文本整形实现
|   +-- word_boundaries.h       # 单词边界检测声明
|   +-- word_boundaries.cpp     # 单词边界检测实现
+-- app/
    +-- editor_application.cpp  # 编辑器应用程序入口
```

## 关键类与函数

| 类/函数 | 文件 | 说明 |
|---------|------|------|
| `Editor` | `include/editor.h` | 编辑器核心类,管理文本、光标、选择和渲染 |
| `Editor::TextPosition` | `include/editor.h` | 文本位置 (段落索引 + 字节偏移) |
| `Editor::Movement` | `include/editor.h` | 光标移动方向枚举 (Left/Right/Up/Down/Home/End/WordLeft/WordRight) |
| `Editor::PaintOpts` | `include/editor.h` | 绘制选项 (背景/前景/选区/光标颜色) |
| `Editor::insert()` | `include/editor.h` | 在指定位置插入 UTF-8 文本 |
| `Editor::remove()` | `include/editor.h` | 删除两个位置之间的文本 |
| `Editor::move()` | `include/editor.h` | 按方向移动光标 |
| `Editor::getPosition()` | `include/editor.h` | 从屏幕坐标获取文本位置 |
| `Editor::getLocation()` | `include/editor.h` | 从文本位置获取屏幕矩形 |
| `Editor::paint()` | `include/editor.h` | 渲染编辑器到 SkCanvas |
| `StringSlice` | `include/stringslice.h` | 轻量可变字符串 (非 NUL 结尾) |
| `StringView` | `include/stringview.h` | 不可变字符串视图 (data + size) |
| `Shape()` | `src/shape.h` | 使用 SkShaper 进行文本整形 |
| `ShapeResult` | `src/shape.h` | 整形结果 (blob + 行断点 + 字形边界 + 单词边界) |

## 依赖关系

- **Skia Core**: `SkCanvas`, `SkFont`, `SkTextBlob`, `SkColor`, `SkString`
- **Skia Font**: `SkFontMgr` 字体管理
- **modules/skshaper**: `SkShaper` 文本整形引擎 (BiDi, Script, 换行)

## 设计模式分析

1. **MVC 分离**: `Editor` 类同时承担模型 (文本数据) 和视图 (渲染) 的职责,通过 `TextPosition` 实现控制器逻辑。`editor_application.cpp` 作为外部控制器处理输入事件。

2. **惰性求值 (Lazy Evaluation)**: 文本修改通过 `markDirty()` 标记脏行,只在需要时(渲染前)通过 `reshapeAll()` 进行重新整形,避免频繁的文本布局计算。

3. **值语义 (Value Semantics)**: `TextPosition`、`StringView` 等小型数据结构使用值语义,支持高效的比较和传递。

4. **迭代器模式**: `Editor::Text` 内部类提供了只读的行迭代器接口,允许外部遍历所有文本行。

## 数据流

```
用户输入事件 (键盘/鼠标)
       |
       v
editor_application.cpp
  - 键盘: 映射为 insert()/remove()/move()
  - 鼠标: getPosition() 获取文本位置
       |
       v
Editor::insert(pos, utf8, len) / Editor::remove(pos1, pos2)
  - 修改 StringSlice 文本数据
  - markDirty() 标记受影响的行
       |
       v
Editor::paint(canvas, opts)
  - reshapeAll() (如果有脏行)
    - 对每个脏行调用 Shape()
      - SkShaper 进行文本整形
      - 生成 SkTextBlob + 光标位置
  - 绘制背景
  - 绘制选区 (pos1 到 pos2 之间的矩形)
  - drawTextBlob() 绘制文本
  - drawRect() 绘制光标
```

## 相关文档与参考

- SkShaper 文本整形: `modules/skshaper/`
- Skia SkFont API: `include/core/SkFont.h`
- Skia SkTextBlob: `include/core/SkTextBlob.h`
- Skia SkCanvas: `include/core/SkCanvas.h`
