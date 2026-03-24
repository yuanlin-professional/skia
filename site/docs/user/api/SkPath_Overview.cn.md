---
title: 'SkPath 概述'
linkTitle: 'SkPath Overview'

weight: 270
---

<a href='https://api.skia.org/classSkPath.html'>路径 (Path)</a> 包含
<a href='undocumented#Line'>线段</a>和
<a href='undocumented#Curve'>曲线</a>，可以进行描边或填充。
<a href='#Contour'>轮廓 (Contour)</a> 由一系列连接的
<a href='undocumented#Line'>线段</a>和
<a href='undocumented#Curve'>曲线</a>组成。
<a href='https://api.skia.org/classSkPath.html'>Path</a> 可以包含零个、一个或多个 <a href='#Contour'>轮廓</a>。每条
<a href='undocumented#Line'>线段</a>和<a href='undocumented#Curve'>曲线</a>
由动词 (Verb)、
<a href='https://api.skia.org/structSkPoint.html'>点</a>和可选的
<a href='#Path_Conic_Weight'>路径圆锥权重 (Path_Conic_Weight)</a> 描述。

每对连接的<a href='undocumented#Line'>线段</a>和
<a href='undocumented#Curve'>曲线</a>共享一个公共
<a href='https://api.skia.org/structSkPoint.html'>点</a>；例如，
<a href='https://api.skia.org/classSkPath.html'>Path</a> 包含两条
连接的<a href='undocumented#Line'>线段</a>，由
<a href='#Path_Verb'>路径动词 (Path_Verb)</a> 序列描述：
<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_kMove_Verb'>kMove_Verb</a>、
<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_kLine_Verb'>kLine_Verb</a>、
<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_kLine_Verb'>kLine_Verb</a>；
以及一个包含三个条目的<a href='https://api.skia.org/structSkPoint.html'>点</a>序列，其中中间条目作为第一条
<a href='undocumented#Line'>线段</a>的终点和第二条
<a href='undocumented#Line'>线段</a>的起点共享。

<a href='https://api.skia.org/classSkPath.html'>Path</a> 的组成部分
<a href='undocumented#Arc'>弧线 (Arc)</a>、
<a href='https://api.skia.org/classSkPath.html#af037025a1adad16072abbbcd83b621f2'>矩形 (Rect)</a>、
<a href='#RRect'>圆角矩形 (Round_Rect)</a>、<a href='undocumented#Circle'>圆形 (Circle)</a> 和
<a href='undocumented#Oval'>椭圆 (Oval)</a> 由
<a href='undocumented#Line'>线段</a>和
<a href='undocumented#Curve'>曲线</a>组成，使用精确描述所需的尽可能多的
<a href='https://api.skia.org/classSkPath.html#ac36f638ac96f3428626e993eacf84ff0'>动词</a>
和<a href='https://api.skia.org/structSkPoint.html'>点</a>。一旦添加到
<a href='https://api.skia.org/classSkPath.html'>Path</a> 中，这些组成部分可能会失去其身份；尽管
<a href='https://api.skia.org/classSkPath.html'>Path</a> 可以被检查以确定它是否描述了单个
<a href='https://api.skia.org/classSkPath.html#af037025a1adad16072abbbcd83b621f2'>矩形</a>、
<a href='undocumented#Oval'>椭圆</a>、<a href='#RRect'>圆角矩形</a>等。

### 示例

<div><fiddle-embed-sk name="93887af0c1dac49521972698cf04069c"><div><a href='https://api.skia.org/classSkPath.html'>Path</a> 包含三个<a href='#Contour'>轮廓</a>：<a href='undocumented#Line'>线段</a>、<a href='undocumented#Circle'>圆形</a>和<a href='https://api.skia.org/classSkPath.html#ad75d5a934476ac6543d6d7ddd8dbb90a'>二次曲线 (Quad)</a>。<a href='undocumented#Line'>线段</a>被描边但不填充。<a href='undocumented#Circle'>圆形</a>被描边和填充；<a href='undocumented#Circle'>圆形</a>描边形成一个环。<a href='https://api.skia.org/classSkPath.html#ad75d5a934476ac6543d6d7ddd8dbb90a'>二次曲线</a>被描边和填充，但由于它没有闭合，<a href='https://api.skia.org/classSkPath.html#ad75d5a934476ac6543d6d7ddd8dbb90a'>二次曲线</a>不会描边形成环。
</div></fiddle-embed-sk></div>

<a href='https://api.skia.org/classSkPath.html'>Path</a> 包含一个
<a href='#Path_Fill_Type'>路径填充类型 (Path_Fill_Type)</a>，它决定重叠的<a href='#Contour'>轮廓</a>形成填充还是孔洞。
<a href='#Path_Fill_Type'>路径填充类型</a>还决定
<a href='undocumented#Line'>线段</a>和
<a href='undocumented#Curve'>曲线</a>内部还是外部的区域被填充。

### 示例

<div><fiddle-embed-sk name="36a995442c081ee779ecab2962d36e69"><div><a href='https://api.skia.org/classSkPath.html'>Path</a> 先以填充方式绘制，然后以描边方式绘制，最后以描边加填充方式绘制。
</div></fiddle-embed-sk></div>

<a href='https://api.skia.org/classSkPath.html'>Path</a> 的内容永远不会被共享。通过值复制 <a href='https://api.skia.org/classSkPath.html'>Path</a> 实际上会创建一个独立于原始路径的新
<a href='https://api.skia.org/classSkPath.html'>Path</a>。在内部，副本不会复制其内容直到被编辑，以减少内存使用并提高性能。

<a name='Contour'></a>

---

<a href='#Contour'>轮廓</a>包含一个或多个
<a href='https://api.skia.org/classSkPath.html#ac36f638ac96f3428626e993eacf84ff0'>动词</a>，
以及满足<a href='#Path_Verb_Array'>路径动词数组 (Path_Verb_Array)</a> 所需数量的<a href='https://api.skia.org/structSkPoint.html'>点</a>。
<a href='https://api.skia.org/classSkPath.html'>Path</a> 中的第一个
<a href='#Path_Verb'>路径动词</a>始终是
<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_kMove_Verb'>kMove_Verb</a>；
之后的每个
<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_kMove_Verb'>kMove_Verb</a>
都会开始一个新的<a href='#Contour'>轮廓</a>。

### 示例

<div><fiddle-embed-sk name="0374f2dcd7effeb1dd435205a6c2de6f"><div>每个 <a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_moveTo'>moveTo</a> 开始一个新的<a href='#Contour'>轮廓</a>，<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_close'>close()</a> 之后的内容也会开始一个新的<a href='#Contour'>轮廓</a>。由于 <a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_conicTo'>conicTo</a> 前面没有
<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_moveTo'>moveTo</a>，第三个<a href='#Contour'>轮廓</a>的第一个<a href='https://api.skia.org/structSkPoint.html'>点</a>从第二个<a href='#Contour'>轮廓</a>的最后一个<a href='https://api.skia.org/structSkPoint.html'>点</a>开始。
</div></fiddle-embed-sk></div>

如果<a href='#Contour'>轮廓</a>中的最后一个<a href='#Path_Verb'>路径动词</a>是
<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_kClose_Verb'>kClose_Verb</a>，
<a href='undocumented#Line'>线段</a>会连接
<a href='#Contour'>轮廓</a>中的<a href='#Path_Last_Point'>路径最后一个点 (Path_Last_Point)</a>
和第一个<a href='https://api.skia.org/structSkPoint.html'>点</a>。一个闭合的
<a href='#Contour'>轮廓</a>在描边时，会在
<a href='#Path_Last_Point'>路径最后一个点</a>和第一个
<a href='https://api.skia.org/structSkPoint.html'>点</a>处绘制
<a href='#Paint_Stroke_Join'>描边连接 (Paint_Stroke_Join)</a>。如果没有
<a href='https://api.skia.org/classSkPath.html'>SkPath</a>::<a href='#SkPath_kClose_Verb'>kClose_Verb</a>
作为最后的动词，<a href='#Path_Last_Point'>路径最后一个点</a>和第一个
<a href='https://api.skia.org/structSkPoint.html'>点</a>不会连接；
<a href='#Contour'>轮廓</a>保持开放。一个开放的
<a href='#Contour'>轮廓</a>在描边时，会在
<a href='#Path_Last_Point'>路径最后一个点</a>和第一个
<a href='https://api.skia.org/structSkPoint.html'>点</a>处绘制
<a href='#Paint_Stroke_Cap'>描边端点 (Paint_Stroke_Cap)</a>。

### 示例

<div><fiddle-embed-sk name="7a1f39b12d2cd8b7f5b1190879259cb2"><div><a href='https://api.skia.org/classSkPath.html'>Path</a> 以描边方式绘制，包含一个开放的<a href='#Contour'>轮廓</a>和一个闭合的<a href='#Contour'>轮廓</a>。
</div></fiddle-embed-sk></div>

<a name='Contour_Zero_Length'></a>

---

<a href='#Contour'>轮廓</a>的长度是从第一个
<a href='https://api.skia.org/structSkPoint.html'>点</a>到
<a href='#Path_Last_Point'>路径最后一个点</a>的行程距离，加上如果
<a href='#Contour'>轮廓</a>是闭合的，从
<a href='#Path_Last_Point'>路径最后一个点</a>到第一个
<a href='https://api.skia.org/structSkPoint.html'>点</a>的距离。即使
<a href='#Contour'>轮廓</a>长度为零，如果
<a href='#Paint_Stroke_Cap'>描边端点</a>使描边的
<a href='undocumented#Line'>线段</a>可见，它们仍然会被绘制。

### 示例

<div><fiddle-embed-sk name="62848df605af6258653d9e16b27d8f7f"></fiddle-embed-sk></div>
