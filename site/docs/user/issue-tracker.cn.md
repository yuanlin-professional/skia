
---
title: "问题跟踪"
linkTitle: "问题跟踪"

---


Skia 问题跟踪器 (Issue Tracker)
----------------------
[Skia 的问题跟踪器](https://bugs.chromium.org/p/skia/issues/list)
（bug.skia.org 或 skbug.com）是我们跟踪所有缺陷报告和功能请求的主要缺陷数据库。

提交新问题时，请选择合适的模板，最可能是
"Defect report from user" 或 "Feature request"。附上一个示例
[fiddle](https://fiddle.skia.org) 或图片。所有问题将由我们的
项目经理进行分类并分配给相应的功能团队。


Chromium 跟踪器中的 Skia 问题
-----------------------------------
在 Chrome 中发现的 Skia 缺陷可以在 [Chromium 跟踪器](https://bugs.chromium.org/p/chromium/issues/list)（crbug.com）中提交。

### Chromium 开发者的问题分类
  * 要让 Skia 团队对问题进行分类，请添加 `Component:Internals>Skia`。
  * 对于无法在 CL 列表中找到明显负责人的 Skia 滚动 (roll) 相关问题，
    请分配给 Skia 值班人员 (Gardener)，值班人员列在
    [status.skia.org](https://status.skia.org) 的值班人员小部件中，也作为滚动 CL 的审阅者。
    * 如果无法分配给值班人员，请抄送他们并将问题分配给 hcm@。
  * 对于 GPU 特定问题，添加标签 `Hotlist-Ganesh`。
  * 对于图像编码或解码问题，添加
    `Component:Internals>Images>Codecs`。

