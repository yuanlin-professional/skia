# SkSVGFeDisplacementMap

> 源文件: modules/svg/include/SkSVGFeDisplacementMap.h

## 概述

`SkSVGFeDisplacementMap` 实现 SVG `<feDisplacementMap>` 滤镜原语,使用一个输入图像的颜色值来置换另一个图像的像素位置,创建扭曲和变形效果。继承自 `SkSVGFe`。

## 核心属性

- `in`: 要被置换的图像
- `in2`: 提供置换值的图像(置换图)
- `scale`: 置换缩放系数
- `xChannelSelector`: 用于 X 位移的颜色通道(R, G, B, A)
- `yChannelSelector`: 用于 Y 位移的颜色通道

## 主要功能

根据置换图的颜色值计算像素位移,创建波浪、涟漪、扭曲等效果,支持独立控制 X 和 Y 方向的置换。

## 置换计算

位移量 = (通道值 - 0.5) * scale
通道值范围 [0, 1],0.5 表示无位移。

## 使用场景

水波纹效果、玻璃折射、热浪扭曲、地图投影变形等。

## 相关文件

- `modules/svg/src/SkSVGFeDisplacementMap.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类

该滤镜提供强大的图像变形能力,是实现动态扭曲效果的核心工具。
