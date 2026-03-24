---
title: 'SkBlendMode 概述'
linkTitle: 'SkBlendMode Overview'

weight: 260
---

描述目标<a href='undocumented#Pixel'>像素</a>如何被自身与源<a href='undocumented#Pixel'>像素</a>的组合所替换。
<a href='#Blend_Mode'>混合模式 (Blend_Mode)</a> 可以使用源、目标或两者。
<a href='#Blend_Mode'>混合模式</a>可以独立地对每个
<a href='https://api.skia.org/SkColor_8h.html'>颜色</a>分量进行操作，也可以让所有源<a href='undocumented#Pixel'>像素</a>分量贡献给一个目标<a href='undocumented#Pixel'>像素</a>分量。

<a href='#Blend_Mode'>混合模式</a>不使用相邻像素来确定结果。

<a href='#Blend_Mode'>混合模式</a>使用源和读取的目标
<a href='https://api.skia.org/SkColor_8h.html#a918cf5a3a68406ac8107f6be48fb906e'>Alpha</a>
来确定写入的目标
<a href='https://api.skia.org/SkColor_8h.html#a918cf5a3a68406ac8107f6be48fb906e'>Alpha</a>；
源和目标
<a href='https://api.skia.org/SkColor_8h.html#a918cf5a3a68406ac8107f6be48fb906e'>Alpha</a>
也可能影响写入的目标
<a href='https://api.skia.org/SkColor_8h.html'>颜色</a>分量。

无论
<a href='https://api.skia.org/SkColor_8h.html#a918cf5a3a68406ac8107f6be48fb906e'>Alpha</a>
在源和目标<a href='undocumented#Pixel'>像素</a>中如何编码，
几乎所有<a href='#Image_Info_Color_Type'>颜色类型 (Color_Type)</a>都将其视为从零到一的范围。并且，几乎所有<a href='#Blend_Mode'>混合模式</a>算法都会限制输出，使所有结果也在零到一的范围内。

两个例外是
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kPlus'>kPlus</a>
和
<a href='https://api.skia.org/SkImageInfo_8h.html#a9ac0b62b3d2c6c7e1a80db557243f93e'>kRGBA_F16_SkColorType</a>。

<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kPlus'>kPlus</a>
允许计算大于一的
<a href='https://api.skia.org/SkColor_8h.html#a918cf5a3a68406ac8107f6be48fb906e'>Alpha</a>
和<a href='https://api.skia.org/SkColor_8h.html'>颜色</a>分量值。对于
<a href='https://api.skia.org/SkImageInfo_8h.html#a9ac0b62b3d2c6c7e1a80db557243f93e'>kRGBA_F16_SkColorType</a>
以外的<a href='#Image_Info_Color_Type'>颜色类型</a>，
结果的
<a href='https://api.skia.org/SkColor_8h.html#a918cf5a3a68406ac8107f6be48fb906e'>Alpha</a>
和分量值会被钳位 (clamp) 到一。

<a href='https://api.skia.org/SkImageInfo_8h.html#a9ac0b62b3d2c6c7e1a80db557243f93e'>kRGBA_F16_SkColorType</a>
允许值超出零到一的范围。客户端需要负责确保结果在零到一的范围内，因此是明确定义的。

<a name='Porter_Duff'></a>

<a href='https://graphics.pixar.com/library/Compositing/paper.pdf'>Compositing
Digital Images</a></a> 描述了
<a href='#Blend_Mode_Overview_Porter_Duff'>Porter_Duff</a> 模式
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kClear'>kClear</a>
到
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kXor'>kXor</a>。

使用带有透明度的<a href='https://api.skia.org/classSkBitmap.html'>位图</a>和 <a href='#Blend_Mode_Overview_Porter_Duff'>Porter_Duff</a> 合成进行绘制可以自由清除目标。

![Porter_Duff](https://fiddle.skia.org/i/819903e0bb125385269948474b6c8a84_raster.png)

使用带有透明度的 <a href='#Blend_Mode_Overview_Porter_Duff'>Porter_Duff</a> 合成绘制几何图形不会组合透明的源像素，使几何图形外的目标保持不变。

![Porter_Duff](https://fiddle.skia.org/i/8f320c1e94e77046e00f7e9e843caa27_raster.png)

<a name='Lighten_Darken'></a>

模式
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kPlus'>kPlus</a>
和
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kScreen'>kScreen</a>
使用简单的算术来提亮或变暗目标。模式
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kOverlay'>kOverlay</a>
到
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kMultiply'>kMultiply</a>
使用更复杂的算法来提亮或变暗；有时一种模式同时具有两种效果，如<a href='https://en.wikipedia.org/wiki/Blend_modes'>混合模式</a></a>所述。

![Lighten_Darken](https://fiddle.skia.org/i/23a33fa04cdd0204b2490d05e340f87c_raster.png)

<a name='Modulate_Blend'></a>

<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kModulate'>kModulate</a>
是
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kSrcATop'>kSrcATop</a>
和
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kMultiply'>kMultiply</a>
的混合体。
它乘以所有分量，包括
<a href='https://api.skia.org/SkColor_8h.html#a918cf5a3a68406ac8107f6be48fb906e'>Alpha</a>；
不像
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kMultiply'>kMultiply</a>，
如果源或目标是透明的，结果也是透明的。
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kModulate'>kModulate</a>
使用<a href='undocumented#Premultiply'>预乘 (Premultiplied)</a> 值来计算乘积；
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kMultiply'>kMultiply</a>
使用<a href='undocumented#Unpremultiply'>非预乘 (Unpremultiplied)</a> 值来计算乘积。

![Modulate_Blend](https://fiddle.skia.org/i/877f96610ab7638a310432674b04f837_raster.png)

<a name='Color_Blends'></a>

模式
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kHue'>kHue</a>、
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kSaturation'>kSaturation</a>、
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kColor'>kColor</a>
和
<a href='https://api.skia.org/SkBlendMode_8h.html#ad96d76accb8ff5f3eafa29b91f7a25f0'>SkBlendMode</a>::<a href='#SkBlendMode_kLuminosity'>kLuminosity</a>
使用所有<a href='https://api.skia.org/SkColor_8h.html'>颜色</a>信息分量来转换源和目标像素，使用
<a href='https://www.w3.org/TR/compositing-1/#blendingnonseparable'>不可分离混合模式 (non-separable blend modes)</a></a>。

![Color_Blends](https://fiddle.skia.org/i/630fe21aea8369b307231f5bcf8b2d50_raster.png)
