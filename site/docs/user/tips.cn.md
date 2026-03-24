---
title: '技巧与常见问题'
linkTitle: '技巧与常见问题'
---

## 在 Chromium 中的网页上捕获 `.skp` 文件

使用脚本 `experimental/tools/web_to_skp`，_或者_ 执行以下操作：

1.  使用 `--no-sandbox --enable-gpu-benchmarking` 启动 Chrome 或 Chromium
2.  打开 JS 控制台（Windows / Linux 按 Ctrl+Shift+J，MacOS 按 Cmd+Opt+J）
3.  执行：`chrome.gpuBenchmarking.printToSkPicture('/tmp')` 成功时返回
    "undefined"。

在 [Skia Debugger](/docs/dev/tools/debugger) 中打开生成的文件，
使用 `dm` 光栅化它，或使用 Skia 的 `viewer` 查看它：

<!--?prettify lang=sh?-->

    out/Release/dm --src skp --skps /tmp/layer_0.skp -w /tmp \
        --config 8888 gpu pdf --verbose
    ls -l /tmp/*/skp/layer_0.skp.*

    out/Release/viewer --skps /tmp --slide layer_0.skp

---

## 在 Chromium 中的网页上捕获 `.mskp` 文件

多页 Skia Picture 文件 (Multipage Skia Picture) 捕获发送到生成 PDF 和打印文档的命令。

使用脚本 `experimental/tools/web_to_mskp`，_或者_ 执行以下操作：

1.  使用 `--no-sandbox --enable-gpu-benchmarking` 启动 Chrome 或 Chromium
2.  打开 JS 控制台（Windows / Linux 按 Ctrl+Shift+J，MacOS 按 Cmd+Opt+J）
3.  执行：
    `chrome.gpuBenchmarking.printPagesToSkPictures('/tmp/filename.mskp')` 成功时返回 "undefined"。

在 [Skia Debugger](/docs/dev/tools/debugger) 中打开生成的文件或
用 `dm` 处理它。

<!--?prettify lang=sh?-->

    experimental/tools/mskp_parser.py /tmp/filename.mskp /tmp/filename.mskp.skp
    ls -l /tmp/filename.mskp.skp
    # open filename.mskp.skp in the debugger.

    out/Release/dm --src mskp --mskps /tmp/filename.mskp -w /tmp \
        --config pdf --verbose
    ls -l /tmp/pdf/mskp/filename.mskp.pdf

---

## 如何在 Skia 中添加硬件加速

Skia 通过两种方式利用特定硬件。

1.  自定义瓶颈例程 (bottleneck routines)

    Skia 的 blit 内部有一组瓶颈例程，可以在平台上被替换以
    利用特定的 CPU 特性。一个例子是 ARM v7 设备上的
    NEON SIMD 指令。参见
    [src/opts/](https://skia.googlesource.com/skia/+/main/src/opts/)

---

## Skia 是否支持字体微调 (Font hinting)？

Skia 有内置的字体缓存，但它不知道如何实际将 TrueType 等字体文件
渲染到缓存中。为此，它依赖平台提供
`SkScalerContext` 的实例。这是 Skia 与字体缩放引擎 (font scaler engine) 通信的抽象接口。
在 src/ports 中你可以看到对 FreeType、macOS 和
Windows GDI 字体引擎的支持文件。其他字体引擎可以
以类似方式轻松支持。

---

## Skia 是否进行文本排版（字距调整）？

排版 (Shaping) 是将一段 Unicode 文本转换为一组带有适当字体的
定位字形 (positioned glyphs) 的过程。

Skia 不进行文本排版。Skia 提供绘制字形的接口，但不实现文本排版器。
Skia 的客户端通常使用
[HarfBuzz](http://www.freedesktop.org/wiki/Software/HarfBuzz/) 来生成
字形及其位置，包括字距调整 (kerning)。

[这里是如何一起使用 Skia 和 HarfBuzz 的示例](https://github.com/aam/skiaex)。
在该示例中，`SkTypeface` 和 `hb_face_t` 使用相同的
`mmap()` 过的 `.ttf` 字体文件创建。HarfBuzz face 用于将 unicode 文本
排版为字形和位置序列，然后 `SkTypeface` 可以用来
绘制这些字形。

---

## 如何给文本添加阴影？

<fiddle-embed-sk name='1ff4da09e515087f7011c7caec2e98ae'></fiddle-embed-sk>
