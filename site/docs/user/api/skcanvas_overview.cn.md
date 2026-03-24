
---
title: "SkCanvas 概述"
linkTitle: "SkCanvas Overview"

weight: 240

---


*绘图上下文*

<!-- Updated Mar 4, 2011 -->

预览
-------

这是一组绘图命令的示例，用于绘制一个填充的七角星。此函数可以剪切并粘贴到 [fiddle.skia.org](https://fiddle.skia.org/) 中使用。

<fiddle-embed-sk name='@skcanvas_star'></fiddle-embed-sk>

详细说明
-------

SkCanvas 是 Skia 的绘图上下文 (drawing context)。它知道将绘图指向何处（即屏幕或离屏像素的位置），并维护一个矩阵和裁剪的栈。但请注意，与其他 API（如 postscript、cairo 或 awt）中的类似上下文不同，Skia 不会在上下文中存储任何其他绘图属性（如颜色、画笔大小）。相反，这些属性在每次绘制调用中通过 SkPaint 显式指定。

<fiddle-embed-sk name='@skcanvas_square'></fiddle-embed-sk>

上面的代码将绘制一个旋转了 45 度的矩形。矩形将以什么颜色和样式绘制由画笔 (paint) 描述，而不是画布 (canvas)。

查看关于[创建 SkCanvas 对象](../skcanvas_creation)的更多详细信息。

首先，我们可能想要擦除整个画布。我们可以通过绘制一个巨大的矩形来实现，但有更简单的方法。

<!--?prettify lang=cc?-->

    void draw(SkCanvas* canvas) {
        SkPaint paint;
        paint.setColor(SK_ColorWHITE);
        canvas->drawPaint(paint);
    }

这会用画笔指定的任何颜色或着色器 (shader)（以及传输模式 (xfermode)）填充整个画布（当然会遵守当前的裁剪）。如果画笔中有着色器，它也会遵守画布上的当前矩阵（参见 SkShader）。如果你只想绘制一种颜色（可选传输模式），你可以直接调用 drawColor()，省去分配画笔的步骤。

<!--?prettify lang=cc?-->

    void draw(SkCanvas* canvas) {
        canvas->drawColor(SK_ColorWHITE);
    }

所有其他绘图 API 都类似，每个都以一个画笔参数结尾。

<fiddle-embed-sk name='@skcanvas_paint'></fiddle-embed-sk>

在某些调用中，我们传递的是指针而不是画笔的引用。在这些情况下，画笔参数可以为 null。在所有其他情况下，画笔参数是必需的。

下一步：[SkPaint](../skpaint_overview)
