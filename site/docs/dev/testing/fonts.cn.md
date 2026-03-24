
---
title: "字体与 GM 测试"
linkTitle: "字体与 GM 测试"

---


概述
--------

gm 目录中的每个测试都会绘制一个参考图像。它们的主要目的是检测图像何时发生了意外变化，表明引入了渲染错误。

gm 测试还有一个次要目的：它们检测不同平台和配置之间的渲染差异。

GM 字体选择
-----------------

每个 gm 在绘制文本时指定要使用的字体 (typeface)。要创建可移植的字体，请使用：

~~~~
SkTypeface* typeface = ToolUtils::CreatePortableTypeface(const char* name,
SkFontStyle style);
~~~~
