# TextStyle

> 源文件: [modules/skparagraph/include/TextStyle.h](../../../../modules/skparagraph/include/TextStyle.h)

## 概述

`TextStyle` 是 Skia 段落排版模块中最核心和最复杂的类之一，定义了文本运行（text run）的所有视觉和排版属性。它包含颜色、前景/背景画笔、字体族、字体大小、字体样式、行高、字间距、词间距、文本装饰（下划线/上划线/删除线）、文本阴影、字体特性、字体参数、基线偏移等完整的文本格式化参数集。该文件同时定义了多个辅助类型：装饰样式、占位符对齐、字体特性、占位符样式、文本块（Block）和占位符（Placeholder）等。

## 架构位置

```
skia::textlayout 命名空间
  ParagraphBuilder
    └── pushStyle(TextStyle) → 文本样式栈
          └── TextStyle  ← 本文件定义
                ├── Decoration (装饰配置)
                ├── FontFeature (字体特性)
                ├── PlaceholderStyle (占位符样式)
                ├── TextShadow (文本阴影引用)
                └── FontArguments (字体参数引用)

  Block / Placeholder ← 内部布局使用的文本块结构
```

`TextStyle` 是文本格式化的核心数据载体，在构建、布局和渲染各阶段都被广泛使用。

## 主要类与结构体

### 辅助函数
- `nearlyZero(SkScalar)` - 浮点数接近零判断
- `nearlyEqual(SkScalar, SkScalar)` - 浮点数近似相等判断（处理 Inf == Inf）

### TextDecoration 枚举
- `kNoDecoration = 0x0` - 无装饰
- `kUnderline = 0x1` - 下划线
- `kOverline = 0x2` - 上划线
- `kLineThrough = 0x4` - 删除线
- 位标志设计，支持组合（如 `kUnderline | kOverline`）

### TextDecorationStyle 枚举
- `kSolid` / `kDouble` / `kDotted` / `kDashed` / `kWavy`

### TextDecorationMode 枚举
- `kGaps` - 装饰线在字形间断开
- `kThrough` - 装饰线贯穿（当前默认，兼容 Flutter）

### StyleType 枚举
- `kNone` / `kAllAttributes` / `kFont` / `kForeground` / `kBackground` / `kShadow` / `kDecorations` / `kLetterSpacing` / `kWordSpacing`
- 用于 `matchOneAttribute` 的样式属性分类匹配

### Decoration 结构体
- `fType` - 装饰类型
- `fMode` - 装饰模式
- `fColor` - 装饰颜色
- `fStyle` - 装饰线条样式
- `fThicknessMultiplier` - 厚度乘数

### PlaceholderAlignment 枚举
- `kBaseline` / `kAboveBaseline` / `kBelowBaseline` / `kTop` / `kBottom` / `kMiddle`
- 定义占位符相对于周围文本的垂直对齐方式

### FontFeature 结构体
- `fName`（`SkString`）- OpenType 特性标签
- `fValue`（`int`）- 特性值

### PlaceholderStyle 结构体
- `fWidth` / `fHeight` - 占位符尺寸
- `fAlignment` - 对齐方式
- `fBaseline` - 基线类型
- `fBaselineOffset` - 基线偏移

### TextStyle 类
- 文本样式的主类，包含所有文本格式化属性

### Block 结构体
- 文本块，将文本范围（`TextRange`）与样式（`TextStyle`）关联
- `add(TextRange)` 方法用于扩展块的范围

### Placeholder 结构体
- 占位符数据，包含范围、占位符样式、文本样式、前方块范围和前方文本范围

### 类型别名
- `TextIndex = size_t`
- `TextRange = SkRange<size_t>`
- `BlockIndex = size_t`
- `BlockRange = SkRange<size_t>`

## 公共 API 函数

### TextStyle 核心方法
```cpp
TextStyle cloneForPlaceholder();
bool equals(const TextStyle& other) const;
bool equalsByFonts(const TextStyle& that) const;
bool matchOneAttribute(StyleType styleType, const TextStyle& other) const;
```

### 颜色与画笔
- `getColor()` / `setColor(SkColor)` - 文本颜色
- `hasForeground()` / `getForeground()` / `setForegroundPaint(SkPaint)` - 前景画笔
- `getForegroundPaintOrID()` / `setForegroundPaintID(PaintID)` - 画笔 ID 模式
- `hasBackground()` / `getBackground()` / `setBackgroundPaint(SkPaint)` - 背景画笔
- `getBackgroundPaintOrID()` / `setBackgroundPaintID(PaintID)` - 背景画笔 ID
- `clearForegroundColor()` / `clearBackgroundColor()` - 清除画笔

### 装饰
- `getDecoration()` / `getDecorationType()` / `getDecorationMode()` / `getDecorationColor()` / `getDecorationStyle()` / `getDecorationThicknessMultiplier()`
- `setDecoration(...)` / `setDecorationMode(...)` / `setDecorationStyle(...)` / `setDecorationColor(...)` / `setDecorationThicknessMultiplier(...)`

### 字体
- `getFontStyle()` / `setFontStyle(SkFontStyle)` - 字体样式
- `getFontSize()` / `setFontSize(SkScalar)` - 字体大小（默认 14.0）
- `getFontFamilies()` / `setFontFamilies(vector<SkString>)` - 字体族
- `getTypeface()` / `refTypeface()` / `setTypeface(sk_sp<SkTypeface>)` - 字体面
- `getFontArguments()` / `setFontArguments(...)` - 字体参数（变体轴、调色板）

### 排版
- `getHeight()` / `setHeight(SkScalar)` - 行高乘数
- `getHeightOverride()` / `setHeightOverride(bool)` - 是否覆盖行高
- `getHalfLeading()` / `setHalfLeading(bool)` - 半行距模式
- `getLetterSpacing()` / `setLetterSpacing(SkScalar)` - 字间距
- `getWordSpacing()` / `setWordSpacing(SkScalar)` - 词间距
- `getBaselineShift()` / `setBaselineShift(SkScalar)` - 基线偏移

### 阴影与特性
- `getShadowNumber()` / `getShadows()` / `addShadow(TextShadow)` / `resetShadows()`
- `getFontFeatureNumber()` / `getFontFeatures()` / `addFontFeature(...)` / `resetFontFeatures()`

### 渲染参数
- `getFontEdging()` / `setFontEdging(SkFont::Edging)` - 字体边缘处理
- `getSubpixel()` / `setSubpixel(bool)` - 亚像素定位
- `getFontHinting()` / `setFontHinting(SkFontHinting)` - 字体提示

### 其他
- `getLocale()` / `setLocale(SkString)` - 区域设置
- `getTextBaseline()` / `setTextBaseline(TextBaseline)` - 文本基线类型
- `getFontMetrics(SkFontMetrics*)` - 获取字体度量
- `isPlaceholder()` / `setPlaceholder()` - 占位符标记

## 内部实现细节

### 默认字体族
```cpp
static const std::vector<SkString>* kDefaultFontFamilies;
```
静态成员，存储默认字体族（"sans-serif"），所有 `TextStyle` 实例共享。

### 装饰默认值
默认装饰使用 `SK_ColorTRANSPARENT` 作为颜色（表示未设置），`kThrough` 模式（兼容 Flutter），厚度乘数为 1.0。

### 前景/背景的 variant 存储
前景和背景使用 `ParagraphPainter::SkPaintOrID`（`std::variant<SkPaint, PaintID>`）存储，通过 `fHasForeground`/`fHasBackground` 布尔标志控制是否启用。

### 废弃 API 兼容
`setForegroundColor` 和 `setBackgroundColor` 标记为 DEPRECATED，转发到 `setForegroundPaint` / `setBackgroundPaint`。

### Block 的 add 方法
```cpp
void add(TextRange tail) {
    SkASSERT(fRange.end == tail.start);
    fRange = TextRange(fRange.start, fRange.start + fRange.width() + tail.width());
}
```
用于合并相邻的同样式文本块，要求新范围紧接当前范围之后。

## 依赖关系

- **Skia 核心**: `SkColor`、`SkFont`、`SkFontMetrics`、`SkFontStyle`、`SkPaint`、`SkScalar`、`SkTypeface`
- **skparagraph 模块**: `DartTypes`、`FontArguments`、`ParagraphPainter`、`TextShadow`
- **标准库**: `<optional>`、`<vector>`

## 设计模式与设计决策

1. **值语义类**: `TextStyle` 支持默认拷贝和赋值，作为值类型在样式栈和文本块中传递。

2. **属性分类匹配**: `matchOneAttribute` 方法支持按类别（字体、前景、背景等）比较两个样式，用于样式合并和差异检测。

3. **双 API 模式**: 同时支持 `SkPaint` 和 `PaintID` 两种画笔设置方式，适应不同客户端的需求。

4. **位标志装饰**: `TextDecoration` 使用位标志，允许同时应用多种装饰（如下划线 + 删除线）。

5. **全局默认字体族**: 通过静态成员共享默认字体族字符串，避免每个 `TextStyle` 实例重复分配。

6. **占位符样式与文本样式分离**: `PlaceholderStyle` 独立于 `TextStyle`，但通过 `isPlaceholder()` 标记在同一样式系统中管理。

## 性能考量

- `TextStyle` 对象较大（包含多个向量和可选类型），频繁拷贝可能有开销。`cloneForPlaceholder` 提供了定制化的拷贝。
- `equals()` 需要比较所有属性，`equalsByFonts()` 仅比较字体相关属性，提供更快的部分比较路径。
- `matchOneAttribute` 按类别比较，避免了完整比较的开销。
- 字体族使用 `std::vector<SkString>`，查找为线性时间。
- 前景/背景的 `variant` 存储避免了额外的堆分配。

## 相关文件

- `modules/skparagraph/include/DartTypes.h` - 基础类型定义
- `modules/skparagraph/include/FontArguments.h` - 字体参数
- `modules/skparagraph/include/ParagraphPainter.h` - SkPaintOrID 类型
- `modules/skparagraph/include/TextShadow.h` - 文本阴影
- `modules/skparagraph/include/ParagraphStyle.h` - 段落样式（包含默认 TextStyle）
- `modules/skparagraph/include/Paragraph.h` - 段落接口
- `modules/skparagraph/src/TextStyle.cpp` - 实现文件
