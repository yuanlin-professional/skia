---
title: 'SkSL 与运行时效果'
linkTitle: 'SkSL'
---

## 概述

**SkSL** 是 Skia 的
[着色语言](https://en.wikipedia.org/wiki/Shading_language)。
**`SkRuntimeEffect`** 是一个 Skia C++ 对象，可用于创建行为由
SkSL 代码控制的 `SkShader`、`SkColorFilter` 和 `SkBlender` 对象。

你可以在 https://shaders.skia.org/ 上实验 SkSL。语法与 GLSL 非常
相似。在 Skia 应用中使用 SkSL 效果时，有一些重要的差异
（与 GLSL 相比）需要记住。这些差异大多源于一个基本事实：
**使用 GPU 着色语言时，你是在编程
[GPU 管线](https://www.khronos.org/opengl/wiki/Rendering_Pipeline_Overview)的一个阶段。
而使用 SkSL 时，你是在编程 Skia 管线的一个阶段。**

具体来说，GLSL 片段着色器 (fragment shader) 控制着光栅化器 (rasterizer) 和混合 (blending) 硬件之间
GPU 的全部行为。该着色器完成计算颜色的所有工作，它生成的颜色
就是送入管线固定功能混合阶段的内容。

SkSL 效果 (effect) 作为更大的 Skia 管线的一部分存在。当你发出画布
绘制操作时，Skia（通常）组装一个单独的 GPU 片段着色器来完成
所有必需的工作。这个着色器通常包含几个部分。例如，它可能包括：

- 评估像素是否落在正在绘制的形状内部或外部
  （或在边界上，可能应用抗锯齿）。
- 评估像素是否落在裁剪区域 (clipping region) 内部或外部
  （同样，边界像素可能有抗锯齿逻辑）。
- `SkPaint` 上 `SkShader` 的逻辑。`SkShader` 实际上可以是一棵
  对象树（由于 `SkShaders::Blend` 和下面描述的其他功能）。
- `SkColorFilter` 的类似逻辑（也可以是一棵树，由于
  `SkColorFilters::Compose`、`SkColorFilters::Blend` 和下面描述的功能）。
- 混合代码（用于某些 `SkBlendMode`，或使用
  `SkPaint::setBlender` 指定的自定义混合）。
- 色彩空间转换代码，作为 Skia [色彩管理](/docs/user/color)的一部分。

即使 `SkPaint` 在 `SkShader`、`SkColorFilter` 或 `SkBlender` 字段中有
复杂的对象树，仍然只有 _一个_ GPU 片段着色器。该树中的每个节点
创建一个函数。裁剪代码和几何代码各创建一个函数。混合代码
可能创建一个函数。整体片段着色器然后调用所有这些函数（这些函数
可能调用其他函数，例如在 `SkShader` 树的情况下）。

**你的 SkSL 效果为 GPU 的片段着色器贡献一个函数。**

---

## 评估（采样）其他 SkShader

在 GLSL 中，片段着色器可以采样纹理 (texture)。使用运行时效果 (runtime effect) 时，
你绑定的对象（在 C++ 中）是一个 `SkShader`，在 SkSL 中表示为 `shader`。
为了明确你操作的对象将发出自己的着色器代码，你不使用 `sample`。
相反，`shader` 对象有一个 `.eval()` 方法。无论如何，Skia 有简单的方法
从 `SkImage` 创建 `SkShader`，因此在运行时效果中使用图像很容易：

<fiddle-embed-sk name='@SkSL_EvaluatingImageShader'></fiddle-embed-sk>

因为你绑定和评估的对象是 `SkShader`，你可以直接使用任何 Skia 着色器，
而不必先将其转换为图像（纹理）。例如，你可以评估线性渐变。
在这个示例中，没有创建纹理来保存渐变。Skia 生成一个单独的
片段着色器，计算渐变颜色，从图像纹理中采样，然后将两者相乘：

<fiddle-embed-sk name='@SkSL_EvaluatingTwoShaders'></fiddle-embed-sk>

当然，你甚至可以调用另一个运行时效果，允许你动态组合着色器片段：

<fiddle-embed-sk name='@SkSL_EvaluatingNestedShaders'></fiddle-embed-sk>

---

## 坐标空间

要理解 SkSL 中坐标的工作方式，你首先需要理解
[它们在 Skia 中的工作方式](/docs/user/coordinates)。如果你熟悉
Skia 的坐标空间，那么只需记住传递给 `main()` 的坐标是**局部**坐标。
它们将相对于 `SkShader` 的坐标空间。这将匹配画布的局部空间和
任何 `localMatrix` 变换。此外，如果着色器被另一个着色器调用，
那个父着色器可能会任意修改它们。

此外，从 `SkImage` 生成的 `SkShader` 不使用归一化坐标
（像 GLSL 中的纹理那样）。它使用左上角的 `(0, 0)`
和右下角的 `(w, h)`。通常，这正是你想要的。如果你使用基于
传递给你的坐标来评估 `SkImageShader`，比例是正确的。然而，如果你想调整
这些坐标（进行某种图像重映射），记住坐标是按图像尺寸缩放的：

<fiddle-embed-sk name='@SkSL_CoordinateSpaces'></fiddle-embed-sk>

---

## 色彩空间

使用 Skia 的应用程序通常是[色彩管理的](/docs/user/color)。
表面（目标）的色彩空间决定了绘制的工作色彩空间 (working color space)。
源内容（如着色器，包括 `SkImageShader`）也有色彩空间。
默认情况下，SkSL 着色器的输入将被转换到工作色彩空间。
不过，某些输入需要特殊处理才能获得（或抑制）这种行为。

首先，让我们看看 Skia 色彩管理的实际效果。这里我们绘制了 mandrill 图像的一部分两次。
第一次，我们正常绘制，遵循文件中存储的色彩空间（这恰好是 [sRGB](https://en.wikipedia.org/wiki/SRGB)
色彩空间）。第二次，我们将 Rec. 2020 色彩空间分配给图像。
这只是告诉 Skia 将存储的颜色视为实际在该色彩空间中。然后 Skia 将这些值
从 Rec. 2020 转换到目标表面的色彩空间（sRGB）。结果是所有颜色看起来
更鲜艳。更重要的是，如果图像真的 *是* 在其他色彩空间中，或者
如果目标表面在其他色彩空间中，这种自动转换是理想的，
因为它确保内容在任何用户的屏幕上看起来一致正确。

<fiddle-embed-sk name='@SkSL_ColorSpaces'></fiddle-embed-sk>

### Uniform 变量

Skia 和 SkSL 不知道你的 `uniform` 变量是否包含颜色，因此不会
自动对它们应用颜色转换。在下面的示例中，声明了两个 uniform：
`color` 和 `not_a_color`。SkSL 简单地水平淡入两个 uniform "颜色"之一，
对着色器的上半部分和下半部分选择不同的 uniform。代码向两个 uniform
传递相同的值，四个浮点值 `{1,0,0,1}` 代表"红色"。

为了真正看到自动 uniform 转换的效果，fiddle 绘制到
[Rec. 2020](https://en.wikipedia.org/wiki/Rec._2020) 色彩空间的离屏表面。
Rec. 2020 有非常 _广的色域_ (wide gamut)，这意味着它可以表示比
常见默认 [sRGB](https://en.wikipedia.org/wiki/SRGB) 色彩空间更鲜艳的颜色。
特别是，sRGB 中最纯的红色与 Rec. 2020 中的纯红色相比相当暗淡。

为了理解这个 fiddle 中发生的事情，我们将解释两种不同情况的步骤。
对于上半部分，我们使用 `not_a_color`。Skia 和 SkSL 不知道
你打算将此用作颜色，因此你提供的原始浮点值直接馈送到 SkSL 着色器。
换句话说 - 当 SkSL 执行时，无论表面的色彩空间如何，
`not_a_color` 将包含 `{1,0,0,1}`。这产生了目标色彩空间中
最鲜艳的红色（在这种情况下看起来像非常亮的红色）。

对于下半部分，我们使用特殊语法 `layout(color)` 声明了 uniform `color`。
这告诉 SkSL 该变量将用作颜色。`layout(color)` 只能用于
`vec3`（即 RGB）或 `vec4`（即 RGBA）类型的 uniform 值。
在任何情况下，提供 uniform 数据时提供的颜色应该是未预乘的 sRGB 颜色。
这些颜色可以包含 `[0,1]` 范围之外的值，如果你想提供广色域颜色。
这与 Skia 在 `SkPaint` 上接受和存储颜色的方式相同。当 SkSL 执行时，
Skia 将 uniform 值转换到工作色彩空间。在这种情况下，这意味着
`color`（最初是 sRGB 红色）被转换为 Rec. 2020 色彩空间中代表
相同颜色的值。

这里的总体效果是使正确标记的 uniform 变得更暗淡，但
这实际上是你在处理 uniform 颜色时想要的。通过这样标记 uniform
颜色，你的源颜色（放在 uniform 中的）将代表
相同的、一致的颜色，而不管目标表面的色彩空间如何。

<fiddle-embed-sk name='@SkSL_Uniforms'></fiddle-embed-sk>

### 原始图像着色器

虽然大多数图像包含应该进行色彩管理的颜色，但某些图像
包含的数据实际上不是颜色。这包括存储法线 (normals)、
材质属性（例如粗糙度）、高度图 (heightmaps) 或任何其他纯粹
碰巧存储在图像中的数学数据。在 SkSL 中使用这些
图像时，你可能想使用 *原始* (raw) 图像着色器，使用
`SkImage::makeRawShader` 创建。它们的工作方式类似于常规图像着色器（包括
过滤和平铺），但有几个主要区别：
  - 永远不会应用色彩空间转换（图像的色彩空间被忽略）。
  - alpha 类型为 kUnpremul 的图像**不会**自动预乘。
  - 不支持双三次过滤 (Bicubic filtering)。在调用 `makeRawShader` 时
    请求双三次过滤将返回 `nullptr`。

这里，我们创建了一个包含球形法线贴图 (normal map) 的图像。然后我们将其与
光照着色器一起使用，展示渲染到不同色彩空间时会发生什么。
如果我们使用常规图像着色器，法线将被视为颜色，并被
转换到工作色彩空间。这会错误地改变法线。
在最后的绘制中，我们使用原始图像着色器，返回原始法线，
忽略工作色彩空间。

<fiddle-embed-sk name='@SkSL_RawImageShaders'></fiddle-embed-sk>

### 在已知色彩空间中工作

在 SkSL 着色器内部，你不知道工作色彩空间是什么。对于许多
效果，这没问题 - 评估图像着色器和进行简单的颜色数学
通常会给出合理的结果（特别是如果你知道应用程序的
工作色彩空间始终是 sRGB）。但对于
某些效果，在固定的、已知的色彩空间中进行某些数学运算可能很重要。
最常见的例子是光照 -- 要获得物理上准确的
光照，数学运算应在 _线性_ 色彩空间中完成。为此，
SkSL 提供了两个内置函数：

```
vec3 toLinearSrgb(vec3 color);
vec3 fromLinearSrgb(vec3 color);
```

这些函数在工作色彩空间和线性 sRGB 色彩空间之间转换颜色。
该空间使用 sRGB 颜色原色（色域），以及线性传递函数。
它使用扩展范围值（低于 0.0 和高于 1.0）表示 sRGB 色域之外的值。
这对应于 Android 的
[LINEAR_EXTENDED_SRGB](https://developer.android.com/reference/android/graphics/ColorSpace.Named.html#LINEAR_EXTENDED_SRGB)
或 Apple 的
[extendedLinearSRGB](https://developer.apple.com/documentation/coregraphics/cgcolorspace/1690961-extendedlinearsrgb)。

这是一个示例，展示了一个球体，光照数学分别在默认
工作空间（sRGB）和线性空间中完成：

<fiddle-embed-sk name='@SkSL_LinearSRGB'></fiddle-embed-sk>

---

## 预乘 Alpha

处理透明颜色时，有两种（常见的）
[可能的表示方式](https://en.wikipedia.org/wiki/Alpha_compositing#Straight_versus_premultiplied)。
Skia 将它们称为 _未预乘_ (unpremultiplied)（维基百科称之为 _straight_）和
_预乘_ (premultiplied)。在 Skia 管线中，每个 `SkShader` 返回预乘颜色。

如果你熟悉 OpenGL 混合，可以用混合方程来理解。对于常见的 alpha 混合（称为
[source-over](https://developer.android.com/reference/android/graphics/PorterDuff.Mode#SRC_OVER)），
你通常会将混合函数配置为
`(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)`。Skia 将 source-over 混合定义为
混合函数为 `(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)`。

Skia 使用预乘 alpha 意味着：

- 如果你从一个未预乘的 `SkImage`（如 PNG）开始，将其转换为
  `SkImageShader`，并评估该着色器... 结果颜色将是
  `[R*A, G*A, B*A, A]`，**而不是** `[R, G, B, A]`。
- 如果你的 SkSL 将返回透明颜色，必须确保将
  `RGB` 乘以 `A`。
- 对于更复杂的着色器，你必须了解哪些颜色是
  预乘的还是未预乘的。如果混合两种颜色，许多操作将没有意义。

下面的图像演示了这一点：正确预乘的颜色在 alpha 降低时产生平滑的
渐变。未预乘的颜色会导致渐变显示不正确，
在 alpha 变化时变得过亮并偏移色相。

<fiddle-embed-sk name='@SkSL_PremultipliedAlpha'></fiddle-embed-sk>

---

## 压缩的 SkSL

Skia 包含一个压缩工具 (minifier)，可以自动减小运行时效果
或 SkMesh 代码的大小。该工具消除空白和注释，缩短函数和变量名，
并删除未引用的代码。

作为示例，这里是上一个演示的压缩形式。着色器代码大约减小到
原始大小的一半，同时显示完全相同的结果。

<fiddle-embed-sk name='@SkSL_MinifiedSkSL'></fiddle-embed-sk>

要启用此工具，将 `skia_compile_modules = true` 添加到你的 gn 参数列表。（在命令行
输入 `gn args out/yourbuild` 来访问参数，或直接编辑文件 `out/yourbuild/args.gn`。）
使用 `ninja` 再次编译 Skia，输出目录中将出现一个名为 `sksl-minify` 的新工具。

压缩 mesh 程序时，你必须提供与 SkMeshSpecification 对应的
`struct Varyings` 和 `struct Attributes`。这些结构体将从压缩后的程序中
删除以方便使用。

`sksl-minify` 接受以下命令行参数：

- 输出路径，例如 `MyShader.minified.sksl`
- 输入路径，例如 `MyShader.sksl`
- （可选）传递 `--stringify` 将压缩后的 SkSL 文本包装在带引号的 C++ 字符串中。
  默认情况下，输出文件将包含纯 SkSL。上面示例代码中的压缩着色器字符串
  就是使用 --stringify 创建的。
- （可选）传递 `--shader`、`--colorfilter`、`--blender`、`--meshfrag` 或 `--meshvert` 来设置
  程序类型。默认值为 `--shader`。
