---
title: 'SkPaint 概述'
linkTitle: 'SkPaint Overview'

weight: 280
---

每当你在 Skia 中绘制内容，并想指定其颜色、与背景的混合方式、或绘制时使用的样式或字体，你都需要在画笔 (paint) 中指定这些属性。

与 `SkCanvas` 不同，画笔不维护内部状态栈（即画笔没有 save/restore 操作）。然而，画笔相对轻量级，因此客户端可以创建和维护任意数量的画笔对象，每个都针对特定用途进行设置。将所有这些颜色和样式属性从画布状态中分离出来，放入（多个）画笔对象中，使得画布的 save/restore 更加高效，因为它们只需要维护矩阵和裁剪设置的栈。

<fiddle-embed-sk name='@skpaint_skia'></fiddle-embed-sk>

这展示了三个不同的画笔，每个都被设置为以不同的样式绘制。现在调用者可以自由地混合使用这些画笔，直接使用它们或在绘制过程中修改它们。

<fiddle-embed-sk name='@skpaint_mix'></fiddle-embed-sk>

除了颜色、描边和文本值等简单属性外，画笔还支持效果 (effects)。这些是绘制管线 (drawing pipeline) 不同方面的子类，当被画笔引用时（每个都是引用计数的），会被调用以覆盖绘制管线的某些部分。

例如，要使用渐变 (gradient) 而不是单一颜色进行绘制，请将 SkShader 赋值给画笔。

<fiddle-embed-sk name='@skpaint_shader'></fiddle-embed-sk>

现在，使用该画笔绘制的任何内容都将使用 `MakeLinear()` 调用中指定的渐变来绘制。返回的着色器 (shader) 对象是引用计数的。每当任何效果对象（如着色器）被赋值给画笔时，画笔会增加其引用计数。为了平衡这一点，上面示例中的调用者在将着色器赋值给画笔后对其调用 `unref()`。现在画笔是该着色器的唯一"所有者"，当画笔超出作用域或另一个着色器（或 null）被赋值给它时，它会自动对着色器调用 `unref()`。

可以赋值给画笔的效果有 6 种类型：

- **SkPathEffect** - 在生成 alpha 遮罩 (alpha mask) 之前对几何图形（路径）的修改（如虚线效果）
- **SkRasterizer** - 组合自定义遮罩层（如阴影）
- **SkMaskFilter** - 在着色和绘制之前对 alpha 遮罩的修改（如模糊）
- **SkShader** - 如渐变（线性、径向、扫描）、位图图案（钳位、重复、镜像）
- **SkColorFilter** - 在应用混合之前修改源颜色（如颜色矩阵）
- **SkBlendMode** - 如 Porter-Duff 传输模式、混合模式

画笔还持有对 SkTypeface 的引用。字体 (typeface) 代表特定的字体样式，用于测量和绘制文本。说到这里，画笔不仅用于绘制文本，还用于测量文本。

<!--?prettify lang=cc?-->

    paint.measureText(...);
    paint.getTextBounds(...);
    paint.textToGlyphs(...);
    paint.getFontMetrics(...);

## SkBlendMode

以下示例演示了 Skia 所有标准混合模式 (blend modes)。在此示例中，源是带有水平 alpha 渐变的纯品红色，目标是带有垂直 alpha 渐变的纯青色。

<fiddle-embed-sk name='@skpaint_xfer'></fiddle-embed-sk>

## SkShader

定义了几种着色器（除了已经提到的线性渐变）：

- 位图着色器 (Bitmap Shader)

  <fiddle-embed-sk name='@skpaint_bitmap_shader'></fiddle-embed-sk>

- 径向渐变着色器 (Radial Gradient Shader)

  <fiddle-embed-sk name='@skpaint_radial'></fiddle-embed-sk>

- 双点锥形渐变着色器 (Two-Point Conical Gradient Shader)

  <fiddle-embed-sk name='@skpaint_2pt'></fiddle-embed-sk>

- 扫描渐变着色器 (Sweep Gradient Shader)

  <fiddle-embed-sk name='@skpaint_sweep'></fiddle-embed-sk>

- 分形 Perlin 噪声着色器 (Fractal Perlin Noise Shader)

  <fiddle-embed-sk name='@skpaint_perlin'></fiddle-embed-sk>

- 湍流 Perlin 噪声着色器 (Turbulence Perlin Noise Shader)

  <fiddle-embed-sk name='@skpaint_turb'></fiddle-embed-sk>

- 组合着色器 (Compose Shader)

  <fiddle-embed-sk name='@skpaint_compose_shader'></fiddle-embed-sk>

## SkMaskFilter

- 模糊遮罩滤镜 (Blur Mask Filter)

  <fiddle-embed-sk name='@skpaint_blur_mask_filter'></fiddle-embed-sk>

## SkColorFilter

- 颜色矩阵颜色滤镜 (Color Matrix Color Filter)

  <fiddle-embed-sk name='@skpaint_matrix_color_filter'></fiddle-embed-sk>

- 颜色表颜色滤镜 (Color Table Color Filter)

  <fiddle-embed-sk name='@skpaint_color_table_filter'></fiddle-embed-sk>

## SkPathEffect

- SkPath2DPathEffect：使用矩阵定义的格子 (lattice) 将指定路径印章 (stamp) 以填充形状。

  <fiddle-embed-sk name='@skpaint_path_2d_path_effect'></fiddle-embed-sk>

- SkLine2DPathEffect：SkPath2DPathEffect 的特殊情况，其中路径是需要描边的直线，而不是需要填充的路径。

  <fiddle-embed-sk name='@skpaint_line_2d_path_effect'></fiddle-embed-sk>

- SkPath1DPathEffect：通过沿绘制路径复制指定路径来创建类似虚线的效果。

  <fiddle-embed-sk name='@skpaint_path_1d_path_effect'></fiddle-embed-sk>

- SkCornerPathEffect：一种可以将尖角转换为各种处理方式（如圆角）的路径效果。

  <fiddle-embed-sk name='@skpaint_corner_path_effects'></fiddle-embed-sk>

- SkDashPathEffect：实现虚线效果的路径效果。

  <fiddle-embed-sk name='@skpaint_dash_path_effect'></fiddle-embed-sk>

- SkDiscretePathEffect：此路径效果将路径切割成离散的段，并随机位移它们。

  <fiddle-embed-sk name='@skpaint_discrete_path_effect'></fiddle-embed-sk>

- SkComposePathEffect：一种路径效果，其效果是先应用内部路径效果，然后应用外部路径效果（即 outer(inner(path))）。

  <fiddle-embed-sk name='@skpaint_compose_path_effect'></fiddle-embed-sk>

- SkSumPathEffect：一种路径效果，其效果是按顺序应用两个效果（即 first(path) + second(path)）。

  <fiddle-embed-sk name='@skpaint_sum_path_effect'></fiddle-embed-sk>
