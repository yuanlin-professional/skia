---
title: 'Canvas2D 整形文本扩展'
linkTitle: 'Canvas2D 文本扩展'
---

[整形文本 (Shaped Text)](/docs/dev/design/text_shaper) 是一个暴露浏览器文本整形引擎的提案。它接收一段（带注释的）文本，并返回正确测量、命中测试和绘制文本所需的底层信息——即定位后的字形 (positioned glyph)。每当在浏览器中测量或绘制文本时都需要此处理步骤，且此处理可能复杂而耗时。然而，此处理的输出很简单，可以非常高效地渲染。输出是与特定字型 (Typeface) 和大小绑定的字形 ID 和 x,y 位置的运行 (run)。

本提案扩展了 Canvas2D，允许它直接绘制这些字形，并包含用于查询字形属性的实用工具（绘制不需要，但对其他操作有用）。

### 原则
* 绘制定位字形应至少与现有的 fillText() 方法一样灵活。
* 预期绘制字形可以比 fillText() 更快——不需要整形/处理。
* 借助额外的实用工具，新效果应易于实现且高效。

## 绘制字形

本提案的核心是与 fillText/strokeText 的对应...

```js
context.fillGlyphs(glyphs, positions, Font);

context.strokeGlyphs(glyphs, positions, Font);
```

这些方法遵循与其"Text"等效方法相同的所有设置（例如当前变换、裁剪、样式），但以下实际文本属性除外：
- font
- textAlign
- textBaseline
- direction

这些属性被忽略，因为它们已经由整形文本处理"计算"过了，其结果体现在 glyphs、positions 和 [Font](/docs/dev/design/text_shaper) 参数中。

[Font](/docs/dev/design/text_shaper) 在此扩展中比现有的 context.font 属性更加具体。在当前的 canvas2d 中，"font" 持有字型的高级描述：它是一个包含字体名称的字符串，需要解析才能找到实际的（一组）资源。对于整形文本 (Shaped Text)，此解析已经完成。字形 ID 特定于恰好 1 个资源（即文件/二进制数据），因此 Font 接口包含的不是名称，而是实际资源的句柄。

这种特定性的好处在于性能：所有"回退"和整形已经完成，绘制调用可以更快地执行。

## 字体实用工具

[整形文本 (Shaped Text)](/docs/dev/design/text_shaper) 引入了 Font 接口，但对于整形而言，它只需要指定资源（Typeface 对象）、大小信息以及（作为输入时的）可选字体特性 (font-feature)。整形完成后，客户端可能需要查询该 Font 中特定字形的信息。这些扩展方法在此介绍。

```WebIDL
interface Font {
    // return array of advance widths for the specified glyphs.
    //
    sequence<float> getGlyphAdvances(sequene<unsigned short> glyphs);

    // return array of [left, top, right, bottom] coordinates for the specified glyphs,
    //
    // If positions are provided, then the rectangles are relative to each glyph's postion.
    // If no positions are provided, then the rectangles are all relateive to (0,0).
    // Note: positions are stored as (x,y) pairs
    //
    sequence<float> getGlyphBounds(sequene<unsigned short> glyphs, sequence<float> positions?);

    // return array of Path2D objects for the specified glyphs,
    //
    // If positions are provided, then the paths are relative to each glyph's postion.
    // If no positions are provided, then the paths are all relateive to (0,0).
    // Note: positions are stored as (x,y) pairs
    //
    // If a glyph has no visual representation (e.g. a SPACE) then its path will be null.
    // If a glyph has an image for its representation, then its path will be undefined.
    //
    sequence<Path2D> getGlyphPaths(sequene<unsigned short> glyphs, sequence<float> positions?);

    // A glyph may be represented with an image (e.g. emoji). getGlyphImage() for these glyphs
    // will return a GlyphImage object. If the glyph does not have an Image, null is returned.
    //
    GlyphImage getGlyphImage(unsigned short glyphID);
};

interface GlyphImage {
    readonly attribute ImageBitmap image;
    readonly attribute DOMMatrix transform;
};
```

[概述文档](/docs/dev/design/text_overview)

## 贡献者：
 [mikerreed](https://github.com/mikerreed),
