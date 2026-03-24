---
title: 'API 参考与概述'
linkTitle: 'API Reference and Overview'

weight: 5
---

Skia 文档正在积极开发中。

一些关键类包括：

- [SkAutoCanvasRestore](https://api.skia.org/classSkAutoCanvasRestore.html#details) -
  画布 (Canvas) 保存栈管理器
- [SkBitmap](https://api.skia.org/classSkBitmap.html#details) - 二维光栅像素数组
- [SkBlendMode](https://api.skia.org/SkBlendMode_8h.html) - 像素颜色算术运算
- [SkCanvas](https://api.skia.org/classSkCanvas.html#details) - 绘图上下文
- [SkColor](https://api.skia.org/SkColor_8h.html) - 使用整数编码的颜色
- [SkFont](https://api.skia.org/classSkFont.html#details) - 文本样式和字体
- [SkImage](https://api.skia.org/classSkImage.html#details) - 用于绘制的二维像素数组
- [SkImageInfo](https://api.skia.org/structSkImageInfo.html#details) - 像素尺寸和特性
- [SkIPoint](https://api.skia.org/structSkIPoint.html#details) - 两个整数坐标
- [SkIRect](https://api.skia.org/structSkIRect.html#details) - 整数矩形
- [SkMatrix](https://api.skia.org/classSkMatrix.html#details) - 3x3 变换矩阵
- [SkPaint](https://api.skia.org/classSkPaint.html#details) - 颜色、描边、字体、效果
- [SkPath](https://api.skia.org/classSkPath.html#details) - 连接的线段和曲线序列
- [SkPicture](https://api.skia.org/classSkPicture.html#details) - 绘图命令序列
- [SkPixmap](https://api.skia.org/classSkPixmap.html#details) - 像素映射：图像信息和像素地址
- [SkPoint](https://api.skia.org/structSkPoint.html#details) - 两个浮点坐标
- [SkRRect](https://api.skia.org/classSkRRect.html#details) - 浮点圆角矩形
- [SkRect](https://api.skia.org/structSkRect.html#details) - 浮点矩形
- [SkRegion](https://api.skia.org/classSkRegion.html#details) - 压缩裁剪遮罩
- [SkSurface](https://api.skia.org/classSkSurface.html#details) - 绘图目标
- [SkTextBlob](https://api.skia.org/classSkTextBlob.html#details) - 字形序列
- [SkTextBlobBuilder](https://api.skia.org/classSkTextBlobBuilder.html#details) -
  字形序列构造器

所有公开 API 都由 Doxygen 索引。

- [Skia Doxygen](https://api.skia.org)

## 概述

Skia 围绕 `SkCanvas` 对象组织。它是"绘图"调用的宿主：`drawRect`、`drawPath`、`drawText` 等。每个调用都有两个组成部分：被绘制的图元 (primitive)（`SkRect`、`SkPath` 等）和颜色/样式属性（`SkPaint`）。

<!--?prettify lang=cc?-->

    canvas->drawRect(rect, paint);

画笔 (paint) 持有描述矩形（在此例中）如何绘制的大部分状态：它是什么颜色，是填充还是描边，应该如何与之前绘制的内容混合。

画布 (canvas) 持有相对较少的状态。它指向实际被绘制的像素，并维护一个矩阵和裁剪的栈。因此在上面的调用中，画布的当前矩阵可能会变换矩形的坐标（平移、旋转、倾斜、透视），画布的当前裁剪可能会限制矩形在画布上的绘制区域，但绘图的所有其他样式属性都由画笔控制。

使用 SkCanvas API：

1.  [SkCanvas 概述](/docs/user/api/skcanvas_overview) - 绘图上下文
2.  [SkPaint 概述](/docs/user/api/skpaint_overview) - 颜色、描边、字体、效果
3.  [SkCanvas 创建](/docs/user/api/skcanvas_creation)
