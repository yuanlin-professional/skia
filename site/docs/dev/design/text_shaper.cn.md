---
title: '塑形文本（Shaped Text）'
linkTitle: '塑形文本（Shaped Text）'
---

一系列对象模型，用于描述多行格式化文本的底层构建器，以及暴露文本塑形结果的对象。这些工作在 DOM 文本节点之外完成，也不依赖于任何特定的渲染模型（例如 canvas2d 或 webgl）。

一个相关的说明文档专注于建议的 [canvas2d 扩展](/docs/dev/design/text_c2d)，使其能够高效地渲染塑形结果，并提供辅助对象用于检查字体的有用属性。

[概述文档](/docs/dev/design/text_overview)

## 目标受众

我们希望面向的 Web 应用已经选择在 canvas2d、webgl 或其他方式中渲染其内容，但仍然希望访问浏览器内置的强大国际化文本塑形和排版服务。对于 canvas2d 来说，它已经具备了一些文本功能，我们希望补充缺失的服务，并提供创建交互式文本编辑或高性能渲染和动画所需的底层结果。

我们提议采用显式的两步模型，而不是"扩展"现有的 canvas2d fillText() 方法：将"富文本"输入处理为塑形结果，然后将这些结果暴露给客户端，允许他们按照自己的方式进行绘制、编辑或使用。

JavaScript 框架是另一个目标受众。本提案深受原生平台（桌面和移动端）上成功 API 的影响，旨在提供类似的控制力和性能。因此，复杂的框架在这些接口之上进行构建是很自然的，提供更"友好"且受约束的功能版本。这是预期中的，因为多种"高级"文本模型都是合理的，每种都有自己的偏好和权衡。本 API 的目标是暴露核心服务和结果，将带有主观设计的层留给 JavaScript 社区。

### 原则
* 命令式的、对 JavaScript 友好的文本表示。
* 限制输入仅包含塑形和度量所需的内容。
* 装饰（即颜色、下划线、阴影、效果）明确不在规范范围内，因为这些会因渲染技术（和客户端的想象力）而有很大差异。

## 调用顺序

为了最大程度地复用和提高效率，从富文本描述到最终塑形和格式化结果的过程被分为多个阶段。每个"阶段"执行特定的处理，并依次成为返回下一阶段实例的工厂。

`TextBuilder`、`ShapedText` 和 `FormattedText` 对象按顺序使用：

```js
const builder = new ParagraphBuilder(font-fallback-chain);
const shaped = builder.shape(DOMString text, sequence<TextBlock> blocks);
const formatted = shaped.format(double width, double height, alignment);
```

Block（块）是文本运行的描述符。目前有两种特化形式，但可以在不破坏设计的情况下添加其他形式。

```WebIDL
interface Typeface {
    // Number or opaque object: Whatever is needed for the client to know exactly
    // what font-resource (e.g. file, byte-array, etc.) is being used.
    // Without this, the glyph IDs would be meaningless.
    //
    // This interface is really an "instance" of the font-resource. It includes
    // any font-wide modifies that the client (or the shaper) may have requested:
    //    e.g. variations, synthetic-bold, …
    //
    // Factories to create Typeface can be described elsewhere. The point here
    // is that such a unique identifier exists for each font-asset-instance,
    // and that they can be passed around (in/out of the browser), and compared
    // to each other.
};

interface TextBlock {
    unsigned long length;  // number of codepoints in this block
};

interface InFont {
    attribute sequence<Typeface> typefaces; // for preferred fallback faces
    attribute double size;
    attribute double scaleX?;   // 1.0 if not specified
    attribute double skewX?:    // 0.0 if not specified (for oblique)

    attribute sequence<FontFeature> features?;
    // additional attributes for letter spacing, etc.
};

interface FontBlock : TextBlock {
    attribute InFont font;
};

interface PlaceholderBlock : TextBlock {
    attribute double width;
    attribute double height;
    attribute double offsetFromBaseline;
};

interface ShapedTextBuilder {
    constructor(TextDirection,          // default direction (e.g. R2L, L2R)
                sequence<Typeface>?,    // optional shared fallback sequence (after TextBlock's)
                ...);

    ShapedText shape(DOMString text, sequence<TextBlock>);
};
```

以下是一个简单的示例，为文本指定了 3 个块。

```js
const fontA = new Font({family-name: "Helvetica", size: 14});
const fontB = new Font({family-name: "Times", size: 18});
const blocks = [
  { length: 6, font: fontA },
  { length: 5, font: fontB },
  { length: 6, font: fontA },
];

const shaped = builder.shape("Hello text world.", blocks);

// now we can format the shaped text to get access to glyphs and positions.

const formatted = shaped.format({width: 50, alignment: CENTER});
```

这被明确设计为高效的，无论是对浏览器的处理还是对客户端按需复用复合对象（即在此示例中复用 fontA）。

如果文本字符串的长度与各块长度之和不匹配，则会抛出异常。

## 访问塑形和格式化的结果
FormattedText 具有方法和原始数据结果：

```WebIDL
typedef unsigned long TextIndex;

interface TextPosition {
    readonly attribute TextIndex textIndex;
    readonly attribute unsigned long lineIndex;
    readonly attribute unsigned long runIndex;
    readonly attribute unsigned long glyphIndex;
};

interface FormattedText {
    // Interaction methods

    // Given a valid index into the text, adjust it for proper grapheme
    // boundaries, and return the TextPosition.
    TextPosition indexToPosition(TextIndex index);

    // Given an x,y position, return the TextPosition
    // (adjusted for proper grapheme boundaries).
    TextPosition hitTextToPosition(double x, double y);

    // Given two logical text indices (e.g. the start and end of a selection range),
    // return the corresponding visual set of ranges (e.g. for highlighting).
    sequence<TextPosition> indicesToVisualSelection(TextIndex t0, TextIndex t1);

    // Raw data

    readonly attribute Rect bounds;

    readonly attribute sequence<TextLine> lines;
};
```

TextLine 序列实际上是一个数组的数组：每一行包含一个 Run（运行）的数组（目前包括字形 (Glyph) 或占位符 (Placeholder)）。

```WebIDL
// Shared by all output runs, specifying the range of code-points that produced
// this run. Known subclasses: TextRun, PlaceholderRun.
interface TextRun {
    readonly attribute TextIndex startIndex;
    readonly attribute TextIndex endIndex;
};

interface GlyphRunFont {
    // Information to know which font-resource (typeface) to use,
    // and at what transformation (size, etc.) to use it.
    //
    readonly attribute Typeface typeface;
    readonly attribute double size;
    readonly attribute double scaleX?;   // 1.0 if not specified
    readonly attribute double skewX?:    // 0.0 if not specified (could be a bool)
};

interface GlyphRun : TextRun {
    readonly attribute GlyphRunFont font;

    // Information to know what positioned glyphs are in the run,
    // and what the corresponding text offsets are for those glyphs.
    // These "offsets" are not needed to correctly draw the glyphs, but are needed
    // during selections and editing, to know the mapping back to the original text.
    //
    readonly attribute sequence<unsigned short> glyphs;     // N glyphs
    readonly attribute sequence<float> positions;           // N+1 x,y pairs
    readonly attribute sequence<TextIndex> indices;         // N+1 indices
};

interface PlaceholderRun : TextRun {
    readonly attribute Rect bounds;
};

interface TextLine {
    readonly attribute TextIndex startIndex;
    readonly attribute TextIndex endIndex;

    readonly attribute double top;
    readonly attribute double bottom;
    readonly attribute double baselineY;

    readonly attribute sequence<TextRun> runs;
};
```

借助这些数据结果（特别是特定 Typeface 对象的字形和位置），调用者将拥有以任何方式绘制结果所需的一切。相应的起始/结束文本索引允许他们将每个运行映射回原始文本。

最后一点是设计的核心。我们认识到，创建富注释文本的客户端会将塑形（例如字体）信息以及任意装饰和其他注释与每个文本块关联。在每个 Run 中返回相应的文本范围，使客户端可以"查找"该运行的所有自定义附加信息（例如颜色、阴影、下划线、占位符等）。这使浏览器无需支持甚至理解所有可能装饰的并集（这显然是不可能的）。


## 替代方案和先驱工作

本模型被设计为底层的，以吸引对性能敏感的应用（例如动画）和复杂文本（编辑器）。它也旨在让来自原生应用环境（桌面或移动端）的开发者感到"自然"。

我们认识到，许多（更普通的）用户可能也想访问其中一些服务。这是合理的，但我们认为，有了正确的原语和暴露的数据，这样的高级模型可以由 JavaScript 社区自己构建，无论是作为正式的框架还是精炼的示例代码。

一个优秀的高级数据模型示例是 [Formatted Text](https://github.com/WICG/canvas-formatted-text/blob/main/explainer-datamodel.md)，我们希望探索将这两个提案分层的方法，允许高级客户端使用其数据模型，但仍然可以选择访问我们的底层访问器。

## 在 Canvas2D 中渲染
[下一篇说明文档](/docs/dev/design/text_c2d) 描述了如何获取这些结果并将它们渲染到（扩展的）Canvas 上下文中。

## 贡献者：
 [mikerreed](https://github.com/mikerreed),
