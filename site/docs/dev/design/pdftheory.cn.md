---
title: 'PDF 工作原理'
linkTitle: 'PDF 工作原理'
---

<!--
PRE-GIT DOCUMENT VERSION HISTORY
    2012-06-25 Steve VanDeBogart
               * Original version
    2015-01-14 Hal Canary.
               * Add section "Using the PDF backend"
               * Markdown formatting
-->

在内部，SkPDFDocument 和 SkPDFDevice 分别表示 PDF 文档和页面。本文档描述了后端的运作方式，但**这些接口不属于公共 API，可能随时发生变化。**

请参阅[使用 Skia 的 PDF 后端](/docs/user/sample/pdf/)了解如何作为调用 Skia 公共 API 的客户端来使用 SkPDF。

---

## PDF 后端的典型用法

SkPDFDevice 是 PDF 后端的主要接口。这个 SkDevice 的子类可以设置在 SkCanvas 上并进行绘制。一旦在画布上的绘制完成（调用 SkDocument::onEndPage()），设备的内容和资源会被添加到拥有该设备的 SkPDFDocument 中。文档中每个需要的页面或图层都应创建一个新的 SkPDFDevice。所有页面添加到文档后，调用 `SkPDFDocument::onClose()` 来完成 PDF 文件的序列化。

## PDF 对象和文档结构

![PDF 逻辑文档结构](../PdfLogicalDocumentStructure.png)

**背景**：PDF 文件格式包含一个头部、一组对象，以及一个包含文档中所有对象目录的尾部（交叉引用表 (cross-reference table)）。目录列出了每个对象的具体字节位置。对象可以引用其他对象，而这些引用的 ASCII 大小取决于被引用对象所分配的对象编号；因此在知道对象大小之前我们无法计算目录，而这又需要分配对象编号。文档使用 SkWStream::bytesWritten() 来查询每个对象的偏移量并构建交叉引用表。

此外，PDF 文件支持一种_线性化_ (linearized) 模式，其中对象按特定顺序排列，使得 PDF 查看器可以更容易地获取显示特定页面所需的对象，例如通过网络字节范围请求。线性化还要求第一页 PDF 中使用或引用的所有对象的对象编号排在其余对象之前。因此，在生成线性化 PDF 之前，必须知道所有对象、它们的大小以及对象引用。Skia 没有实现线性化 PDF 的计划。

    %PDF-1.4
    …objects...
    xref
    0 31  % Total number of entries in the table of contents.
    0000000000 65535 f
    0000210343 00000 n
    …
    0000117055 00000 n
    trailer
    <</Size 31 /Root 1 0 R>>
    startxref
    210399  % Byte offset to the start of the table of contents.
    %%EOF

虚拟类 SkPDFObject 用于管理文件格式的需求。任何要表示 PDF 对象的对象都必须继承自 SkPDFObject 并实现生成二进制表示以及报告所使用的其他 SkPDFObject 资源的方法。SkPDFTypes.h 定义了大多数基本 PDF 对象类型：bool、int、scalar、string、name、array、dictionary 和 stream。（stream 是一个至少包含 Length 条目的 dictionary，后跟 stream 的数据。）

Stream 现在以一种略有不同的方式处理。SkPDFStreamOut() 函数立即压缩并序列化二进制数据，而不是创建新对象。

所有这些 PDF 对象类型（stream 类型除外）都可以以直接和间接方式使用，即数组可以包含内联的 int 或 dictionary 条目，这不需要对象编号。stream 类型不能内联，必须通过对象引用来引用。大多数情况下，其他对象类型也可以通过对象引用来引用，但 PDF 规范中有特定规则要求在某些地方使用内联引用，而在其他地方使用间接引用。所有间接对象 (indirect object) 都必须分配对象编号。

- **布尔值 (bools)**：`true` `false`
- **整数 (ints)**：`42` `0` `-1`
- **标量 (scalars)**：`0.001`
- **字符串 (strings)**：`(strings are in parentheses or byte encoded)` `<74657374>`
- **名称 (name)**：`/Name` `/Name#20with#20spaces`
- **数组 (array)**：`[/Foo 42 (arrays can contain multiple types)]`
- **字典 (dictionary)**：`<</Key1 (value1) /key2 42>>`
- **间接对象 (indirect object)**：
  `5 0 obj (An indirect string. Indirect objects have an object number and a generation number, Skia always uses generation 0 objects) endobj`
- **对象引用 (object reference)**：`5 0 R`
- **流 (stream)**：
  `<</Length 56>> stream ...stream contents can be arbitrary, including binary... endstream`

间接对象要么：

- 在需要时立即序列化，并返回一个新的 SkPDFIndirectReference，要么

- 稍后序列化，但预留一个文档唯一的 SkPDFIndirectReference 以允许其他对象引用它。

示例文档：

    %PDF-1.4
    2 0 obj <<
      /Type /Catalog
      /Pages 1 0 R
    >>
    endobj
    3 0 obj <<
      /Type /Page
      /Parent 1 0 R
      /Resources <>
      /MediaBox [0 0 612 792]
      /Contents 4 0 R
    >>
    endobj
    4 0 obj <> stream
    endstream
    endobj
    1 0 obj <<
      /Type /Pages
      /Kids [3 0 R]
      /Count 1
    >>
    endobj
    xref
    0 5
    0000000000 65535 f
    0000000236 00000 n
    0000000009 00000 n
    0000000062 00000 n
    0000000190 00000 n
    trailer
    <</Size 5 /Root 2 0 R>>
    startxref
    299
    %%EOF

## PDF 绘制

PDF 中的大部分绘制由流的文本指定，称为内容流 (content stream)。内容流的语法与上述文件格式的语法不同，本质上更接近 PostScript。内容流中的命令告诉 PDF 解释器绘制图形，如矩形（`x y w h re`）、图像或文本，或执行元操作，如设置绘制颜色、对绘制坐标应用变换或裁剪后续的绘制操作。引用内容流的页面对象有一个资源列表，可以在内容流中使用字典名称来引用这些资源。资源包括字体对象、图像对象、图形状态对象（一组元操作，如斜接限制、线宽等）。由于 Skia 和 PDF 对透明度的支持存在不匹配（稍后解释），SkPDFDevice 将每个绘制操作记录到一个内部结构（ContentEntry）中，只有在需要内容流时才将该结构列表展平为最终的内容流。

    4 0 obj <<
      /Type /Page
      /Resources <<
        /Font <</F1 9 0 R>>
        /XObject <</Image1 22 0 R /Image2 73 0 R>>
      >>
      /Content 5 0 R
    >> endobj

    5 0 obj <</Length 227>> stream
    % In the font specified in object 9 and a height
    % of 12 points, at (72, 96) draw 'Hello World.'
    BT
      /F1 12 Tf
      72 96 Td
      (Hello World) Tj
    ET
    % Draw a filled rectange.
    200 96 72 72 re B
    ...
    endstream
    endobj

## 驻留对象 (Interned objects)

有许多高级 PDF 对象（如字体、图形状态等）可能会在单个 PDF 中被多次引用。为了确保每个对象只有一个副本，SkPDFDocument 维护了一个从特定类型键到这些对象的 SkPDFIndirectReference 的映射。

## 图形状态 (Graphic States)

PDF 有许多影响绘制方式的参数。与 Skia 中的绘制选项对应的包括：颜色、透明度 (alpha)、线帽 (line cap)、线连接类型 (line join)、线宽 (line width)、斜接限制 (miter limit) 和传输/混合模式 (xfer/blend mode)（关于传输模式请参见后面的章节）。除颜色外，这些都可以在单个 PDF 对象中指定，由 SkPDFGraphicState 类表示。然后，内容流中的一个简单命令就可以将绘制参数设置为该图形状态对象中指定的值。PDF 不允许在图形状态对象中指定颜色，而必须直接在内容流中指定。同样，当前字体和字体大小也直接在内容流中设置。

    6 0 obj <<
      /Type /ExtGState
      /CA 1  % Opaque - alpha = 1
      /LC 0  % Butt linecap
      /LJ 0  % Miter line-join
      /LW 2  % Line width of 2
      /ML 6  % Miter limit of 6
      /BM /Normal  % Blend mode is normal i.e. source over
    >>
    endobj

## 裁剪和变换 (Clip and Transform)

与 Skia 类似，PDF 允许对绘制进行裁剪或变换。但是，有一些注意事项会影响 PDF 后端的设计。PDF 不支持透视变换 (perspective transform)（透视变换被视为单位变换）。然而，裁剪 (clip) 有更多需要处理的问题。PDF 裁剪不能直接取消或扩展。即一旦某个区域被裁剪掉，就无法再向其绘制。不过，PDF 为 PDF 图形状态（包括上文图形状态部分提到的绘制参数以及裁剪和变换）提供了有限深度的栈。因此，要撤销裁剪，必须在应用裁剪之前推入 PDF 图形状态，然后弹出以恢复到应用裁剪之前的图形状态。

当画布向 SkPDFDevice 发出绘制调用时，活动的变换、裁剪区域和裁剪栈被存储在 ContentEntry 结构中。之后，当 ContentEntry 结构被展平为有效的 PDF 内容流时，会比较变换和裁剪以确定在所需状态之间进行高效转换的操作集。目前使用的是局部优化 (local optimization)，来确定从一个状态到下一个状态的最佳转换。全局优化 (global optimization) 可以通过更有效地使用 PDF 格式中提供的图形状态栈来改善效果。

## 生成内容流

对于 SkPDFDevice 上的每个绘制调用，都会创建一个新的 ContentEntry，其中存储了矩阵 (matrix)、裁剪区域 (clip region) 和裁剪栈 (clip stack) 以及绑定参数。大部分绑定参数被捆绑到一个 SkPDFGraphicState（驻留的）中，其余的（颜色、字体大小等）显式存储在 ContentEntry 中。在用所有相关上下文填充 ContentEntry 后，将其与最近使用的 ContentEntry 进行比较。如果上下文匹配，则追加到前一个而不是使用新的。无论哪种情况，在将上下文填充到 ContentEntry 后，允许相应的绘制调用追加到 ContentEntry 中的内容流片段以实现绘制调用的核心——即绘制形状、图像、文本等。

当所有绘制完成后，SkPDFDocument::onEndPage() 将调用 SkPDFDevice::content() 来请求页面的完整内容流。首先要做的是应用部分在构造函数中指定的初始变换，这个变换负责将坐标空间从左下角原点（PDF 默认）更改为左上角（Skia 默认），以及用户请求的任何平移或缩放（例如实现边距或缩放画布）。接下来（好吧，几乎是接下来，请参见下一节），应用裁剪将绘制限制在页面的内容区域（边距内的部分）。然后，在辅助类 GraphicStackState 的帮助下，将每个 ContentEntry 应用到内容流中，该辅助类跟踪 PDF 图形栈的状态并优化输出。对于每个 ContentEntry，将命令发送到最终内容条目以将裁剪从当前状态更新为 ContentEntry 中指定的状态，类似地更新矩阵和绘制状态（颜色、线连接等），然后追加内容条目片段（实际的绘制操作）。

## 绘制细节

某些对象有需要处理的特定属性。图像、图层（见下文）和字体假定使用标准 PDF 坐标系，因此在绘制这些实体之前，我们必须撤销到 Skia 坐标系的任何翻转。我们目前不支持反转路径 (inverted path)，因此填充反转路径会产生错误结果（[issue 40031223](skbug.com/40031223)）。PDF 不会绘制具有对接帽 (butt cap) 或方形帽 (square cap) 的零长度线段，因此这是模拟实现的。

### 图层 (Layers)

PDF 有一种称为表单外部对象 (form x-object) 的高级对象，它基本上是一个 PDF 页面，有资源和内容流，但可以在现有页面上进行变换和绘制。这用于实现图层。SkPDFDevice 有一个方法 makeFormXObjectFromDevice()，它使用 SkPDFDevice::content() 方法从设备构造一个表单外部对象。SkPDFDevice::drawDevice() 通过创建传入设备的表单外部对象，然后在根设备中绘制该表单外部对象来工作。在此过程中需要注意几点。如前所述，我们必须注意坐标系的任何翻转——偶数次翻转会导致错误结果，除非对此进行了修正。传递给绘制命令的 SkClipStack 包含整个裁剪栈，包括在基础图层上完成的裁剪操作。由于表单外部对象将作为单个操作绘制到基础图层上，我们可以假设所有这些裁剪都已生效，无需在图层内再次应用它们。

### 字体 (Fonts)

处理字体有许多细节，因此本文档只讨论一些较重要的方面。几个简短的细节：

- 我们不能假设任意字体在 PDF 查看时可用，因此我们按照现代 PDF 指南嵌入所有字体。
- 目前大多数字体是 TrueType 字体，因此这是大部分工作的重点。
- 因为 Skia 可能只获得文本的字形 ID 编码 (glyph-id encoding) 来进行渲染，而且没有完美的方法来反转编码，所以 PDF 后端始终使用文本的字形 ID 编码。

#### _Type1/Type3 字体_

Linux 支持 Type1 字体，但 Windows 和 Mac 似乎缺乏从字体中提取所需信息的功能，除非解析字体文件。当在任何平台上使用非 TrueType 字体时（Linux 上的 Type1 除外），它会被编码为 Type3 字体。在此上下文中，Type3 字体是一个表单外部对象（内容流）数组，用于绘制字体的每个字形。Type3 字体中不包含提示 (hinting) 或字距调整 (kerning) 信息，只有每个字形的形状。任何设置了禁止嵌入版权保护位的字体也会作为 Type3 字体嵌入。据我所知，形状不受版权保护，但程序受保护，因此通过剥离所有程序信息而只嵌入字形的形状，我们在法律要求的范围内尊重了禁止嵌入位。

PDF 仅支持 Type1 或 Type3 字体的 8 位编码。但是，它们可以包含超过 256 个字形。PDF 后端通过将字形分成 255 个一组（字形 ID 0 始终是未知字形）并将字体呈现为多个字体来处理这个问题，每个字体最多包含 255 个字形。

#### _字体子集化 (Font subsetting)_

许多字体，尤其是支持 CJK（中日韩）的字体相当大，因此对它们进行子集化是有益的。Chrome 使用 HarfBuzz 子集化工具为 Skia 的 TrueType 字体提供子集化支持。

### 着色器 (Shaders)

Skia 有两种预定义的着色器类型：图像着色器 (image shader) 和渐变着色器 (gradient shader)。在这两种情况下，着色器实际上是绝对定位的，因此其可见的初始位置和边界是着色器对象不可变状态的一部分。需要分别考虑和处理 Skia 的每种平铺模式 (tile mode)。我们生成的图像着色器将是平铺的，因此平铺默认就被处理了。为了支持镜像 (mirror)，我们在相应的轴上绘制反转的图像，或在两个轴上加上空象限中的第四个。对于夹紧模式 (clamp mode)，我们提取相应边缘的像素并拉伸单像素宽/长的图像以填充边界。对于 x 和 y 都使用夹紧模式时，我们用适当颜色的矩形填充角落。然后根据请求适当地旋转或缩放合成的着色器。

渐变着色器纯粹通过数学方式处理。首先，变换矩阵使得请求的渐变中的特定点位于预定义位置，例如，渐变的线性距离始终归一化为 1。然后，创建一个 type 4 PDF 函数来实现所需的渐变。type 4 函数是由受限 PostScript 语言定义的函数。生成的函数在边缘处夹紧，因此如果所需的平铺模式是平铺或镜像，我们必须添加更多 PostScript 代码将任何输入参数适当地映射到 0-1 范围。生成 PostScript 代码的代码有些晦涩，因为它试图生成优化的（节省空间的）PostScript 代码，但有大量注释来解释意图。

### 传输模式 (Xfer modes)

PDF 直接支持 Skia 中使用的部分传输模式。对于这些模式，只需将图形状态中的混合模式设置为适当的值即可（Normal/SrcOver、Multiply、Screen、Overlay、Darken、Lighten、ColorDodge、ColorBurn、HardLight、SoftLight、Difference、Exclusion）。除了标准的 SrcOver 模式外，PDF 不直接支持 Porter-Duff 传输模式。其中大多数（Clear、SrcMode、DstMode、DstOver、SrcIn、DstIn、SrcOut、DstOut）可以通过各种方式模拟，主要是通过将部分内容创建为表单外部对象并用另一个表单外部对象作为遮罩来绘制。我还没有找到如何模拟以下模式：SrcATop、DstATop、Xor、Plus。

在撰写本文时 [2012-06-25]，我有一个[修复我对某些模拟模式含义误解的 CL 待审](https://codereview.appspot.com/4631078/)。我将描述应用此更改后的系统。

首先，介绍一些术语和定义。当使用模拟的传输模式绘制时，已经绘制到设备上的内容称为目标 (Dst)，即将绘制的内容是源 (Src)。Src（和 Dst）可以有透明区域（alpha 等于零），但它也有一个固有的形状。对于大多数类型的绘制对象，形状与 alpha 非零的区域相同。然而，对于图像和图层等对象，形状是项目的边界，而不是 alpha 非零的区域。例如，一个 10x10 的图像，除了中心一个 1x1 的点外都是透明的，其形状仍然是 10x10。xfermodes gm 测试展示了形状和 alpha 与 Porter-Duff 传输模式组合时的交互。

Clear 传输模式移除 Dst 中处于 Src 形状内的任何部分。这通过将设备当前内容（Dst）捆绑为单个实体，然后使用 Src 形状的反转作为遮罩来绘制它（我们需要 Src 不在的地方的 Dst）来实现。该实现还需要更多步骤。您可能需要回头参考[内容流部分](#Generating_a_content_stream)。对于任何绘制调用，通过名为 SkPDFDevice::setUpContentEntry() 的方法创建 ContentEntry。此方法检查该绘制操作中生效的传输模式，如果是需要模拟的传输模式，则从设备创建表单外部对象（即创建 Dst），并将其存储以供后续使用。这也会清除该设备上所有现有的 ContentEntry。然后绘制操作按正常方式进行（在大多数情况下，关于形状的说明见下文），但绘制到现在为空的设备上。然后，当绘制操作完成时，调用一个互补的方法 SkPDFDevice::finishContentEntry()，如果当前传输模式是模拟的，则采取行动。在 Clear 的情况下，它将刚绘制的内容打包到另一个表单外部对象中，然后使用 Src 表单外部对象、一个反转函数和 Dst 表单外部对象来用 Src 的反转形状作为遮罩绘制 Dst。当 Src 的形状与绘制的不透明部分相同时，这效果很好，因为 PDF 使用遮罩表单外部对象的 alpha 通道来进行遮罩。当形状与 alpha 通道不匹配时，需要额外的操作。形状和 alpha 不匹配的绘制例程会设置状态来指示形状（始终是矩形），finishContentEntry 会使用它。Clear 传输模式是一个特例；如果需要形状，则不使用 Src，因此有代码在需要形状且传输模式为 Clear 时不去绘制 Src。

SrcMode 是 Clear 加上之后绘制 Src。DstMode 只是省略绘制 Src。DstOver 与 SrcOver 相同，但 Src 和 Dst 互换——这通过在 setUpContentEntry 中将新 ContentEntry 插入到 ContentEntry 列表的开头而不是末尾来实现。SrcIn、SrcOut、DstIn、DstOut 彼此类似，区别在于遮罩是反转还是非反转以及是否交换 Src 和 Dst。SrcIn 是 SrcMode，其中 Src 以 Dst 作为遮罩绘制。SrcOut 类似于 SrcMode，但 Src 以反转的 Dst 作为遮罩绘制。DstIn 是 SrcMode，其中 Dst 以 Src 作为遮罩绘制。最后，DstOut 是 SrcMode，其中 Dst 以反转的 Src 作为遮罩绘制。

## 已知问题

- [issue 40031257](skbug.com/40031257) 不支持 SrcAtop、Xor 和 Plus 传输模式。
- [issue 40031248](skbug.com/40031248) drawVerticies 未实现。
- [issue 40031251](skbug.com/40031251) 大部分情况下，仅_直接_支持 TTF 字体。（用户指标显示几乎所有字体都是 TrueType 字体。）
- [issue 40031270](skbug.com/40031270) 页面旋转是通过指定不同大小的页面来实现的，而不是包含适当的旋转注释。

---
