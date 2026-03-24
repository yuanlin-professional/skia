---
title: "使用 Skia 的 PDF 后端"
linkTitle: "使用 Skia 的 PDF 后端"
---

以下是通过 SkDocument 和 SkCanvas API 使用 Skia 的 PDF 后端 (SkPDF) 的示例。

<fiddle-embed-sk name='@PDF'></fiddle-embed-sk>

<!-- https://fiddle.skia.org/c/@PDF docs/examples/PDF.cpp -->

---

## SkPDF 的限制

Skia 公共 API 中有几个方面是 SkPDF 目前无法处理的，
原因是没有已知的客户使用该功能，或者没有简单的
类 PDF 方式来处理它。

在本文档中：

- **drop（丢弃）** 表示不绘制任何内容。

- **ignore（忽略）** 表示绘制但不带效果

- **expand（展开）** 表示以非类 PDF 的方式实现。这可能意味着
  将矢量图形光栅化，将带路径效果的路径展开为许多
  单独的路径，或将文本转换为路径。

<style scoped><!--
#pdftable {border-collapse:collapse;}
#pdftable tr th, #pdftable tr td {border:#888888 2px solid;padding: 5px;}
--></style>
<table id="pdftable">
<tr><th>效果</th>                  <th>文本</th>   <th>图像</th> <th>其他所有内容</th></tr>
<tr><th>SkMaskFilter</th>            <td>drop</td>   <td>ignore</td> <td>ignore</td></tr>
<tr><th>SkPathEffect</th>            <td>ignore</td> <td>n/a</td>    <td>expand</td></tr>
<tr><th>SkColorFilter</th>           <td>ignore</td> <td>expand</td> <td>ignore</td></tr>
<tr><th>SkImageFilter</th>           <td>expand</td> <td>expand</td> <td>expand</td></tr>
<tr><th>不支持的 SkXferModes</th> <td>ignore</td> <td>ignore</td> <td>ignore</td></tr>
<tr><th>非渐变 SkShader</th>   <td>expand</td> <td>n/a</td>    <td>expand</td></tr>
</table>

备注：

- _SkImageFilter_：当 SkImageFilter 被展开时，文本即文本 (text-as-text) 会丢失。

- _SkXferMode_：以下传输模式 (transfer mode) 不被 PDF 原生支持：
  DstOver、SrcIn、DstIn、SrcOut、DstOut、SrcATop、DstATop 和 Modulate。

其他限制：

- _drawText with VerticalText_ -- drop。没有已知的客户使用
  VerticalText 标志。

- _drawTextOnPath_ -- expand。（文本即文本会丢失。）

- _drawVertices_ -- drop。

- _drawPatch_ -- drop。

---
