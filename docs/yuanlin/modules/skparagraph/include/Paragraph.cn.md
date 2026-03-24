# Paragraph

> 源文件: [modules/skparagraph/include/Paragraph.h](../../../../modules/skparagraph/include/Paragraph.h)

## 概述

`Paragraph` 是 Skia 段落排版模块（skparagraph）的核心抽象基类，定义了文本段落的布局、渲染、查询和编辑的完整接口。它封装了文本排版引擎的主要功能，包括段落布局计算、画布绘制、文本区域查询（如获取文本矩形范围、字形位置、行度量）、以及实验性的编辑 API（如获取字形信息、字体信息、行号查询）。该类主要由 Flutter 引擎调用，同时也为其他需要高质量文本排版的客户端提供服务。

## 架构位置

```
skia::textlayout 命名空间
  └── Paragraph (抽象基类)  ← 本文件定义
        └── ParagraphImpl (内部实现类)
              ├── 由 ParagraphBuilder::Build() 创建
              └── 使用 FontCollection 进行字体查找
```

`Paragraph` 是面向公共 API 的抽象接口层，实际实现由 `ParagraphImpl` 提供。

## 主要类与结构体

### Paragraph
- 抽象基类，定义段落排版的完整公共接口
- 构造函数接受 `ParagraphStyle` 和 `FontCollection`
- 内部维护布局结果的度量值

### Paragraph::VisitorInfo
- 访问器信息结构体，用于遍历段落中的字形信息
- 包含：`font`（字体）、`origin`（原点）、`advanceX`（水平推进量）、`count`（字形数）、`glyphs`（字形 ID 数组）、`positions`（位置数组）、`utf8Starts`（UTF-8 起始位置数组）、`flags`（标志位）

### Paragraph::ExtendedVisitorInfo
- 扩展访问器信息，在 `VisitorInfo` 基础上增加：`advance`（SkSize 类型）、`bounds`（边界矩形数组）
- `positions` 为非 const 指针，允许修改

### Paragraph::GlyphClusterInfo
- 字形簇信息：`fBounds`（边界矩形）、`fClusterTextRange`（文本范围）、`fGlyphClusterPosition`（文本方向）

### Paragraph::GlyphInfo
- 字形与字素簇信息：`fGraphemeLayoutBounds`（字素布局边界）、`fGraphemeClusterTextRange`（字素簇文本范围）、`fDirection`（方向）、`fIsEllipsis`（是否为省略号）

### Paragraph::FontInfo
- 字体信息：`fFont`（SkFont）、`fTextRange`（关联的文本范围）

### Paragraph::VisitorFlags
- `kWhiteSpace_VisitorFlag = 1 << 0`：标记当前运行为空白字符

## 公共 API 函数

### 布局与度量
- `getMaxWidth()` - 获取段落最大宽度
- `getHeight()` - 获取段落高度
- `getMinIntrinsicWidth()` - 获取最小固有宽度
- `getMaxIntrinsicWidth()` - 获取最大固有宽度
- `getAlphabeticBaseline()` - 获取字母基线位置
- `getIdeographicBaseline()` - 获取表意文字基线位置
- `getLongestLine()` - 获取最长行的宽度
- `didExceedMaxLines()` - 检查是否超过最大行数限制

### 核心操作
- `layout(SkScalar width)` - 纯虚函数，执行段落布局
- `paint(SkCanvas*, SkScalar x, SkScalar y)` - 绘制到 SkCanvas
- `paint(ParagraphPainter*, SkScalar x, SkScalar y)` - 通过自定义画笔绘制

### 文本区域查询
- `getRectsForRange(...)` - 获取指定字形范围的边界矩形列表
- `getRectsForPlaceholders()` - 获取所有占位符的边界矩形
- `getGlyphPositionAtCoordinate(dx, dy)` - 根据坐标获取字形位置
- `getWordBoundary(offset)` - 获取单词边界

### 行信息
- `getLineMetrics(vector<LineMetrics>&)` - 获取所有行的度量信息
- `lineNumber()` - 获取总行数
- `getLineNumberAt(TextIndex)` - 根据 UTF-8 索引获取行号
- `getLineNumberAtUTF16Offset(size_t)` - 根据 UTF-16 偏移获取行号
- `getLineMetricsAt(int, LineMetrics*)` - 获取指定行的度量信息
- `getActualTextRange(int, bool)` - 获取指定行的可见文本范围

### 编辑 API
- `getGlyphClusterAt(TextIndex, GlyphClusterInfo*)` - 获取字形簇信息
- `getClosestGlyphClusterAt(dx, dy, GlyphClusterInfo*)` - 获取最近的字形簇
- `getGlyphInfoAtUTF16Offset(size_t, GlyphInfo*)` - UTF-16 偏移处的字形信息
- `getClosestUTF16GlyphInfoAt(dx, dy, GlyphInfo*)` - 最近的 UTF-16 字形信息

### 字体信息
- `getFontAt(TextIndex)` - 获取指定位置的字体
- `getFontAtUTF16Offset(size_t)` - UTF-16 偏移处的字体
- `getFonts()` - 获取段落中使用的所有字体

### 访问器模式
- `visit(const Visitor&)` - 遍历段落字形信息
- `extendedVisit(const ExtendedVisitor&)` - 扩展遍历（含边界信息）

### 路径与检测
- `getPath(int lineNumber, SkPath* dest)` - 获取指定行的路径
- `GetPath(SkTextBlob*)` - 静态方法，获取文本 blob 的路径
- `containsEmoji(SkTextBlob*)` - 检测是否含 emoji
- `containsColorFontOrBitmap(SkTextBlob*)` - 检测是否含彩色字体或位图

### 实验性更新 API
- `updateTextAlign(TextAlign)` - 更新文本对齐方式
- `updateFontSize(from, to, fontSize)` - 更新字体大小
- `updateForegroundPaint(from, to, paint)` - 更新前景画笔
- `updateBackgroundPaint(from, to, paint)` - 更新背景画笔

### 其他
- `markDirty()` - 标记段落需要重新布局
- `unresolvedGlyphs()` - 获取未解析的字形数量
- `unresolvedCodepoints()` - 获取未解析的码点集合

## 内部实现细节

### 保护成员

段落的度量数据存储在 `protected` 成员中，供 `ParagraphImpl` 直接访问：
- `fFontCollection` - 字体集合引用
- `fParagraphStyle` - 段落样式
- 布局度量：`fAlphabeticBaseline`、`fIdeographicBaseline`、`fHeight`、`fWidth`、`fMaxIntrinsicWidth`、`fMinIntrinsicWidth`、`fLongestLine`、`fExceededMaxLines`

注释 "Things for Flutter" 表明这些度量值的设计主要考虑了 Flutter 框架的需求。

### 纯虚函数设计

大量方法声明为纯虚函数，将实际实现完全委托给子类 `ParagraphImpl`。这提供了清晰的接口与实现分离。

### 双编码支持

API 同时提供 UTF-8（`TextIndex`）和 UTF-16（`size_t` offset）两种文本索引方式，以兼容不同客户端的编码需求。

## 依赖关系

- **Skia 核心**: `SkPath`、`SkCanvas`、`SkFont`、`SkPaint`、`SkScalar`
- **skparagraph 模块**: `FontCollection`、`Metrics`、`ParagraphStyle`、`TextStyle`
- **标准库**: `<unordered_set>`、`<vector>`、`<functional>`

## 设计模式与设计决策

1. **抽象工厂模式**: `Paragraph` 由 `ParagraphBuilder::Build()` 创建，客户端不直接构造。

2. **访问器模式（Visitor）**: 通过 `visit()` 和 `extendedVisit()` 方法，客户端可以遍历段落内部的字形数据而无需了解内部数据结构。

3. **接口与实现分离**: 纯虚函数确保公共 API 的稳定性，实现细节封装在 `ParagraphImpl` 中。

4. **渐进式 API 演化**: 编辑 API 和更新 API 标记为实验性，允许在不破坏主要 API 的情况下迭代新功能。

5. **双绘制接口**: 同时支持 `SkCanvas` 和 `ParagraphPainter`，后者允许客户端自定义绘制行为（如使用 PaintID 而非 SkPaint）。

## 性能考量

- `layout()` 是主要的计算密集型操作，应尽量减少调用次数。`markDirty()` 用于在属性变更后标记需要重新布局。
- 度量值（宽度、高度、基线等）直接存储为成员变量，查询为 O(1)。
- `getRectsForRange` 等查询操作的复杂度取决于实现，但通常为 O(N)（N 为字形数）。
- 实验性的 `updateTextAlign`/`updateFontSize` 等方法旨在提供比完整重建更快的更新路径。

## 相关文件

- `modules/skparagraph/src/ParagraphImpl.h` - 实际实现类
- `modules/skparagraph/include/ParagraphBuilder.h` - 段落构建器
- `modules/skparagraph/include/ParagraphStyle.h` - 段落样式
- `modules/skparagraph/include/TextStyle.h` - 文本样式
- `modules/skparagraph/include/Metrics.h` - 行度量信息
- `modules/skparagraph/include/FontCollection.h` - 字体集合
- `modules/skparagraph/include/ParagraphPainter.h` - 自定义绘制接口
