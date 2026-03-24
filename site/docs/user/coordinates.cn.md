---
title: 'Skia 坐标空间'
linkTitle: '坐标'
---

## 概述

Skia 通常涉及两种不同的坐标空间：**设备坐标** (device) 和
**局部坐标** (local)。设备坐标由你渲染到的表面 (surface)（或其他设备）定义。
它们的范围从表面左上角的 `(0, 0)` 到右下角的 `(w, h)` -- 它们实际上是以像素为单位测量的。

---

## 局部坐标

局部坐标空间是所有几何图形和着色器 (shader) 提供给
`SkCanvas` 的方式。默认情况下，局部坐标系和设备坐标系是相同的。
这意味着几何图形通常以像素为单位指定。在这里，我们
将一个矩形定位在 `(100, 50)`，并指定它宽高各 `50` 个单位：

<fiddle-embed-sk name='96f782b723c5240aab440242f4c7cbfb'></fiddle-embed-sk>

局部坐标也用于定义和评估画笔 (paint) 上的任何 `SkShader`。
在这里，我们定义了一个线性渐变着色器，从绿色（当 `x == 0` 时）
到蓝色（当 `x == 50` 时）：

<fiddle-embed-sk name='97cf81a465fdeff01d2298e07a0802a3'></fiddle-embed-sk>

---

## 着色器不随几何图形移动

现在，让我们尝试在 `(100, 50)` 处绘制渐变填充的正方形：

<fiddle-embed-sk name='3adc73d23d57084f954f52c6b14c8772'></fiddle-embed-sk>

发生了什么？记住，局部坐标空间没有改变。原点
仍然在表面的左上角。我们指定了几何图形应该
定位在 `(100, 50)`，但 `SkShader` 仍然在 `x` 从 `0` 到 `50` 时
产生渐变。我们将矩形滑过了由 `SkShader` 定义的渐变。着色器不随几何图形移动。

---

## 变换局部坐标空间

要获得期望的效果，我们可以创建一个新的渐变着色器，将
位置移动到 `100` 和 `150`。但这会使我们的着色器难以复用。
相反，我们可以使用 `SkCanvas` 上的方法来**改变局部坐标
空间**。这会导致所有局部坐标（几何图形和着色器）在
画布变换矩阵 (transformation matrix) 定义的新空间中被评估：

<fiddle-embed-sk name='ce89b326b2bbe41587eec738706bf155'></fiddle-embed-sk>

---

## <span>变换着色器坐标空间</span>

最后，可以相对于画布局部坐标空间变换 `SkShader` 的坐标空间。
为此，你在创建 `SkShader` 时提供一个
`localMatrix` 参数。在这种情况下，几何图形由 `SkCanvas` 矩阵变换。`SkShader` 由
`SkCanvas` 矩阵**和**该着色器的 `localMatrix` 共同变换。另一种
理解方式是：`localMatrix` 定义了一个将着色器坐标映射到几何图形坐标空间的变换。

为了帮助说明差异，这里是我们的渐变填充方框。它首先
被平移了 `50` 个单位。然后，我们对画布应用 `45` 度旋转
（以方框中心为枢轴）。这会旋转方框的几何图形以及其中的渐变：

<fiddle-embed-sk name='d4b52d94342f1b55900d489c7ba8fd21'></fiddle-embed-sk>

将其与第二个示例进行比较。我们仍然平移 `50` 个单位。
但在这里，我们_仅对着色器_应用 `45` 度旋转，方法是
将其指定为 `SkGradientShader::MakeLinear` 函数的 `localMatrix`。
现在，方框保持不旋转，但渐变在方框内旋转：

<fiddle-embed-sk name='886fa46943b67e0d6aa78486dcfbcc2c'></fiddle-embed-sk>
