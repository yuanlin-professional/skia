# CanvasKit 段落排版 C++ 绑定 (paragraph_bindings)

> 源文件: `modules/canvaskit/paragraph_bindings.cpp`

## 概述

`paragraph_bindings.cpp` 是 CanvasKit 中段落文本排版功能的核心 C++ 绑定文件，约 860 行代码。它通过 Emscripten 的 `embind` 机制，将 Skia 的 skparagraph 模块完整暴露给 JavaScript，涵盖段落创建与布局、文本样式配置、字体管理、行度量查询、字形信息获取以及客户端 ICU 数据支持等功能。该文件是 CanvasKit 实现高质量文本排版的关键绑定层。

## 架构位置

```
JavaScript (paragraph.js)
  └── ParagraphBuilder._Make() / _MakeFromFontProvider()
      └── paragraph_bindings.cpp
          ├── SimpleParagraphStyle / SimpleTextStyle / SimpleStrutStyle ← JS 值对象
          ├── toParagraphStyle() / toTextStyle() / toStrutStyle() ← 转换函数
          ├── para::ParagraphBuilderImpl ← 段落构建器
          ├── para::Paragraph ← 段落对象（布局、查询、渲染）
          ├── para::TypefaceFontProvider ← 自定义字体提供器
          ├── para::FontCollection ← 字体集合
          └── EMSCRIPTEN_BINDINGS(Paragraph) ← 绑定声明
```

## 主要类与结构体

### SimpleFontStyle

字体样式的简化表示：

| 字段 | 类型 | 说明 |
|------|------|------|
| `slant` | `SkFontStyle::Slant` | 字体倾斜度 |
| `weight` | `SkFontStyle::Weight` | 字体粗细 |
| `width` | `SkFontStyle::Width` | 字体宽度 |

### SimpleTextStyle

文本样式的完整简化表示（约 20 个字段），包含：
- 颜色（文本色、前景色、背景色、装饰色）— 通过 WASM 指针传递
- 装饰（下划线、删除线等）
- 字体属性（大小、字间距、词间距、行高等）
- 字体族列表、区域设置
- 阴影列表（颜色、偏移、模糊半径）
- OpenType 字体特性和可变字体轴

### SimpleStrutStyle

支柱样式，控制段落的行距基准线：

| 字段 | 说明 |
|------|------|
| `fontFamilies` | 支柱字体族 |
| `fontStyle` | 支柱字体样式 |
| `fontSize` | 支柱字体大小 |
| `heightMultiplier` | 行高倍数 |
| `halfLeading` | 半行间距 |
| `leading` | 行间距 |
| `strutEnabled` | 启用支柱 |
| `forceStrutHeight` | 强制使用支柱高度 |

### SimpleParagraphStyle

段落样式，包含：省略号、行高、最大行数、文本对齐/方向、文本高度行为、文本样式、支柱样式等。

### SimpleTextBox

文本框结果结构：`SkRect` + 文本方向（0.0 = RTL, 1.0 = LTR）。

## 公共 API 函数

### Paragraph 类方法

| 方法 | 说明 |
|------|------|
| `didExceedMaxLines()` | 是否超出最大行数 |
| `getAlphabeticBaseline()` | 字母基线位置 |
| `getIdeographicBaseline()` | 表意文字基线位置 |
| `getGlyphPositionAtCoordinate(x, y)` | 坐标处的字形位置 |
| `getHeight()` / `getMaxWidth()` | 段落高度/最大宽度 |
| `getLongestLine()` | 最长行宽度 |
| `getMaxIntrinsicWidth()` / `getMinIntrinsicWidth()` | 最大/最小固有宽度 |
| `getNumberOfLines()` | 行数 |
| `getLineMetrics()` / `getLineMetricsAt(n)` | 行度量信息 |
| `getLineNumberAt(offset)` | 偏移处的行号 |
| `_getGlyphInfoAt(index)` | 指定索引的字形信息 |
| `_getClosestGlyphInfoAtCoordinate(x, y)` | 坐标最近的字形信息 |
| `_getRectsForRange(start, end, heightStyle, widthStyle)` | 文本范围的矩形列表 |
| `_getRectsForPlaceholders()` | 占位符矩形列表 |
| `getShapedLines()` | 获取完整的塑形行数据（行/run/字形/位置） |
| `getWordBoundary(offset)` | 词边界 |
| `layout(width)` | 按指定宽度布局段落 |
| `unresolvedCodepoints()` | 未解析的码点列表 |

### ParagraphBuilder 类方法

| 方法 | 说明 |
|------|------|
| `_Make(style, fontMgr)` | 使用字体管理器创建构建器 |
| `_MakeFromFontProvider(style, fontProvider)` | 使用字体提供器创建构建器 |
| `_MakeFromFontCollection(style, fontCollection)` | 使用字体集合创建构建器 |
| `_ShapeText(text, runs, width)` | 静态方法：直接进行文本塑形 |
| `addText(text)` | 添加文本内容 |
| `_pushStyle(textStyle)` / `_pushPaintStyle(textStyle, fg, bg)` | 推入文本样式 |
| `pop()` | 弹出当前样式 |
| `build()` | 构建 Paragraph 对象 |
| `reset()` | 重置构建器 |
| `_addPlaceholder(width, height, alignment, baseline, offset)` | 添加占位符 |
| `getText()` | 获取当前文本 |
| `_setWordsUtf8/16()` | 设置客户端词边界数据 |
| `_setGraphemeBreaksUtf8/16()` | 设置客户端字素边界数据 |
| `_setLineBreaksUtf8/16()` | 设置客户端换行数据 |
| `RequiresClientICU()` | 是否需要客户端 ICU 数据 |

### TypefaceFontProvider

| 方法 | 说明 |
|------|------|
| `Make()` | 创建空的字体提供器 |
| `_registerFont(typeface, familyPtr)` | 注册字体 |

### FontCollection

| 方法 | 说明 |
|------|------|
| `Make()` | 创建空的字体集合 |
| `setDefaultFontManager(fontManager)` | 设置默认字体管理器 |
| `enableFontFallback()` | 启用字体回退 |

## 内部实现细节

### 样式转换函数

- **`toTextStyle(SimpleTextStyle)`**: 将简化结构转换为 `para::TextStyle`，处理颜色指针解引用、字体族列表解码、阴影数组构建、OpenType 特性和可变字体轴标签解析
- **`toStrutStyle(SimpleStrutStyle)`**: 转换支柱样式，使用 -1 作为"未设置"哨兵值
- **`toParagraphStyle(SimpleParagraphStyle)`**: 组合文本样式和支柱样式，设置省略号、行数限制等

### TextBox 打包

`TextBoxesToFloat32Array` 将 `std::vector<TextBox>` 打包为紧凑的 `Float32Array`，每个 TextBox 占 5 个 float（4 个 Rect + 1 个方向标志）。

### GetShapedLines 实现

使用 `Paragraph::visit()` 回调遍历每一行和每个 run，在访问过程中：
- 维护 `LineAccumulate` 结构累计行指标（最小上升、最大下降、基线、偏移范围）
- 每个 run 的位置加上 `origin` 偏移，并追加一个尾部位置
- 在行结束信号（`info == nullptr`）时，设置行的 textRange、top、bottom、baseline

### 客户端 ICU 支持

通过 `SK_UNICODE_CLIENT_IMPLEMENTATION` 条件编译，支持由客户端提供词/字素/换行边界数据，避免在 WASM 中包含完整的 ICU 数据。换行数据以 [位置, 类型, 位置, 类型, ...] 的交替数组格式传入。

### Unicode 初始化

`get_unicode()` 优先使用 ICU 实现（`SK_UNICODE_ICU_IMPLEMENTATION`），否则返回 nullptr。注释提到未来应由客户端显式创建 Unicode 实例。

### 字体特性与可变字体

`toTextStyle` 解析 4 字节的 OpenType 标签字符串，通过 `SkSetFourByteTag` 转换为 tag 值。可变字体轴标签同样要求恰好 4 个字符。

## 依赖关系

| 类别 | 依赖项 |
|------|-------|
| Skia 核心 | SkColor, SkFontStyle, SkPictureRecorder, SkString |
| 段落排版 | DartTypes.h, Paragraph.h, TextStyle.h, TypefaceFontProvider.h, ParagraphBuilderImpl.h, ParagraphImpl.h |
| Unicode | SkUnicode.h, SkUnicode_icu.h（条件）, SkUnicode_client.h（条件） |
| CanvasKit | WasmCommon.h |
| Emscripten | emscripten.h, emscripten/bind.h |

## 设计模式与设计决策

- **简化值对象模式**: 使用 Simple* 前缀的扁平结构体（通过 `value_object` 绑定）在 JS/C++ 间传输复杂配置，避免绑定嵌套对象
- **指针传递颜色**: 颜色以 WASM 堆指针形式传递，由 C++ 端通过 `reinterpret_cast` 读取，避免颜色对象的绑定开销
- **工厂方法多态**: 提供 `_Make`、`_MakeFromFontProvider`、`_MakeFromFontCollection` 三种构建器工厂，适应不同字体管理场景
- **哨兵值约定**: 使用 -1 和 0 作为"未设置"的标记值（如 `fontSize != -1` 时才设置字体大小）
- **条件编译 ICU**: 通过编译标志控制是否包含 ICU 数据或使用客户端提供的 Unicode 数据

## 性能考量

- `GetShapedLines` 在每次调用时遍历所有行和 run，构建完整的 JS 对象树。对大段落可能产生显著开销
- `TextBoxesToFloat32Array` 使用紧凑的浮点数组而非对象数组，减少 JS 端内存分配
- `_ShapeText` 作为一次性文本塑形工具，内部创建完整的段落构建管线，不适合高频调用
- 字体族名称列表通过指针数组传递，避免多次跨边界的字符串拷贝
- 客户端 ICU 模式允许 WASM 包不包含 ICU 数据，显著减小文件大小

## 相关文件

- `modules/canvaskit/paragraph_bindings_gen.cpp` — 段落枚举绑定（自动生成）
- `modules/canvaskit/paragraph.js` — JS 端段落辅助层
- `modules/skparagraph/include/Paragraph.h` — 段落核心 API
- `modules/skparagraph/src/ParagraphBuilderImpl.h` — 段落构建器实现
- `modules/skparagraph/include/TextStyle.h` — 文本样式定义
- `modules/skparagraph/include/TypefaceFontProvider.h` — 字体提供器
- `modules/canvaskit/WasmCommon.h` — WASM 辅助类型
