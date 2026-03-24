# skparagraph/include - 段落排版公共接口

## 概述

`include/` 目录包含 skparagraph 模块的所有公共头文件,定义了段落文本排版的完整 API 接口。这些头文件构成了模块的公共契约,客户端代码(如 Flutter 引擎)只需包含此目录中的头文件即可使用段落排版功能。

所有接口定义在 `skia::textlayout` 命名空间下,采用抽象基类设计,具体实现在 `src/` 目录中。接口设计遵循 Dart/Flutter 的文本排版模型,部分类型名直接映射到 Flutter 的 `dart:ui` 库中对应的概念。

## 架构图

```
+---------------------------------------------+
|          客户端代码 (Flutter / 应用)          |
+-----+-------+-------+-------+-------+-------+
      |       |       |       |       |
      v       v       v       v       v
+-------+ +-------+ +-------+ +-------+ +-------+
|Paragraph| |Builder| |Style  | |Font   | |Metrics|
|  .h    | |  .h   | | .h    | |Coll.h | |  .h   |
+-------+ +-------+ +-------+ +-------+ +-------+
      |       |       |       |       |
      |       v       v       v       v
      |   +-----------------------------------------+
      +-->|        src/ 内部实现                     |
          +-----------------------------------------+
```

## 目录结构

```
include/
|-- BUILD.bazel              # Bazel 构建规则
|-- DartTypes.h              # Dart/Flutter 兼容基础类型
|-- FontArguments.h          # 可变字体参数封装
|-- FontCollection.h         # 字体集合管理器
|-- Metrics.h                # 行度量与样式度量
|-- Paragraph.h              # 段落抽象基类(核心接口)
|-- ParagraphBuilder.h       # 段落构建器接口
|-- ParagraphCache.h         # 段落排版结果缓存
|-- ParagraphPainter.h       # 段落绘制抽象接口
|-- ParagraphStyle.h         # 段落样式与支柱(Strut)样式
|-- TextShadow.h             # 文本阴影效果
|-- TextStyle.h              # 文本样式(字体/颜色/装饰/间距)
|-- TypefaceFontProvider.h   # 自定义字体提供器
```

## 关键类与函数

### DartTypes.h - 基础类型定义

此文件定义了段落排版中使用的核心基础类型,名称反映其 Dart/Flutter 对应关系:

| 类型/枚举 | 说明 |
|-----------|------|
| `TextAlign` | 文本对齐方式: kLeft, kRight, kCenter, kJustify, kStart, kEnd |
| `TextDirection` | 文本方向: kLtr (从左到右), kRtl (从右到左) |
| `TextBaseline` | 基线类型: kAlphabetic (字母基线), kIdeographic (表意基线) |
| `TextHeightBehavior` | 行高行为: 控制首行上升和末行下降 |
| `RectHeightStyle` | 选区矩形高度: kTight, kMax, kIncludeLineSpacing*, kStrut |
| `RectWidthStyle` | 选区矩形宽度: kTight, kMax |
| `Affinity` | 光标亲和性: kUpstream (前), kDownstream (后) |
| `PositionWithAffinity` | 带亲和性的位置 |
| `TextBox` | 文本包围框 (SkRect + TextDirection) |
| `SkRange<T>` | 通用范围模板, TextRange = SkRange<size_t> |

### Paragraph.h - 段落核心接口

`Paragraph` 是段落对象的抽象基类,提供布局、绘制和查询的完整接口:

```cpp
class Paragraph {
public:
    // 布局与绘制
    virtual void layout(SkScalar width) = 0;
    virtual void paint(SkCanvas* canvas, SkScalar x, SkScalar y) = 0;
    virtual void paint(ParagraphPainter* painter, SkScalar x, SkScalar y) = 0;

    // 属性查询
    SkScalar getMaxWidth();       // 布局宽度
    SkScalar getHeight();         // 段落总高度
    SkScalar getMinIntrinsicWidth();  // 最小固有宽度
    SkScalar getMaxIntrinsicWidth();  // 最大固有宽度
    SkScalar getLongestLine();    // 最长行宽度

    // 选区与命中测试
    virtual std::vector<TextBox> getRectsForRange(...) = 0;
    virtual PositionWithAffinity getGlyphPositionAtCoordinate(SkScalar dx, SkScalar dy) = 0;
    virtual SkRange<size_t> getWordBoundary(unsigned offset) = 0;

    // 访问者模式
    virtual void visit(const Visitor&) = 0;
    virtual void extendedVisit(const ExtendedVisitor&) = 0;

    // 编辑 API
    virtual int getLineNumberAt(TextIndex codeUnitIndex) const = 0;
    virtual bool getGlyphClusterAt(TextIndex, GlyphClusterInfo*) = 0;
    virtual SkFont getFontAt(TextIndex codeUnitIndex) const = 0;
};
```

### TextStyle.h - 文本样式

`TextStyle` 控制文本的视觉属性:

- **字体**: 字体族(families)、大小(fontSize)、样式(fontStyle: 粗细/宽度/斜体)
- **颜色**: 前景色(foreground)、背景色(background)、支持 PaintID 用于自定义绘制
- **装饰**: 下划线/上划线/删除线, 装饰样式(实线/双线/点线/虚线/波浪线)
- **间距**: 字母间距(letterSpacing)、词间距(wordSpacing)
- **阴影**: 通过 `TextShadow` 实现多层阴影
- **高级**: 字体特性(fontFeatures)、可变字体参数(fontArguments)、基线偏移(baselineShift)

### FontCollection.h - 字体集合

`FontCollection` 管理多个字体管理器,支持字体回退链:

```cpp
class FontCollection : public SkRefCnt {
    void setAssetFontManager(sk_sp<SkFontMgr>);    // 应用内嵌字体
    void setDynamicFontManager(sk_sp<SkFontMgr>);  // 动态加载字体
    void setTestFontManager(sk_sp<SkFontMgr>);     // 测试用字体
    void setDefaultFontManager(sk_sp<SkFontMgr>);  // 系统默认字体(回退)
    sk_sp<SkTypeface> defaultFallback(SkUnichar, ...);  // 字体回退
    ParagraphCache* getParagraphCache();            // 获取缓存
};
```

### ParagraphPainter.h - 抽象绘制器

`ParagraphPainter` 将段落绘制操作抽象化,允许脱离 SkCanvas 使用:

- `drawTextBlob`: 绘制文本
- `drawTextShadow`: 绘制文本阴影
- `drawRect`: 绘制矩形背景
- `drawLine/drawPath/drawFilledRect`: 绘制装饰线
- `clipRect/translate/save/restore`: 画布状态管理
- `SkPaintOrID`: 支持 SkPaint 或整数 PaintID 双模式

## 依赖关系

```
include/ (公共接口)
  |-- Skia Core: SkCanvas, SkFont, SkFontMgr, SkFontStyle, SkPaint,
  |              SkTextBlob, SkPath, SkRect, SkColor, SkScalar, SkRefCnt
  |-- skunicode: SkUnicode (在 ParagraphBuilder.h 中使用)
  |-- 标准库: std::vector, std::string, std::variant, std::optional,
              std::unordered_set, std::map, std::function
```

## 设计模式分析

### 抽象接口与实现分离
所有核心类(`Paragraph`, `ParagraphBuilder`, `ParagraphPainter`)都是抽象基类,具体实现在 `src/` 中。这种分离保证了 ABI 稳定性和实现灵活性。

### 值类型与引用语义混合
- `TextStyle`, `ParagraphStyle`, `StrutStyle` 采用值语义(可拷贝)
- `Paragraph`, `FontCollection` 采用引用语义(通过智能指针管理)
- `ParagraphPainter` 采用非拥有指针语义(生命周期由调用者管理)

### Flutter 优化
多处 API 设计直接服务于 Flutter 的需求:
- `SkPaintOrID` 允许 Flutter 使用整数 ID 代替 SkPaint 对象
- UTF-16 索引 API (`getLineNumberAtUTF16Offset`, `getGlyphInfoAtUTF16Offset`) 对应 Dart 字符串
- `PlaceholderStyle` 支持 Flutter 的 inline widget 功能

## 数据流

```
用户代码
  |
  +-- 创建 ParagraphStyle (对齐/方向/最大行数/省略号)
  +-- 创建 TextStyle (字体/颜色/装饰)
  +-- 创建 FontCollection (配置字体管理器)
  |
  +-- ParagraphBuilder::make(style, fontCollection, unicode)
  |     |-- pushStyle(textStyle)
  |     |-- addText("文本内容")
  |     |-- addPlaceholder(placeholderStyle)
  |     |-- pop()
  |     |-- Build() --> Paragraph
  |
  +-- paragraph->layout(width)
  +-- paragraph->paint(canvas, x, y)
  +-- paragraph->getRectsForRange(start, end, ...)  --> 选区矩形
  +-- paragraph->getGlyphPositionAtCoordinate(x, y) --> 光标位置
```

## 相关文档与参考

- **实现代码**: `modules/skparagraph/src/` - 对应的实现文件
- **Flutter engine**: Flutter 引擎通过 `ParagraphBuilder` 和 `Paragraph` 接口使用本模块
- **Dart API 对应**: `dart:ui` 中的 `Paragraph`, `ParagraphBuilder`, `ParagraphStyle`, `TextStyle`
- **CSS 参考**: `TextAlign::kJustify` 对应 CSS `text-align: justify`
