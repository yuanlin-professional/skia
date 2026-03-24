# SkSVGFeImage

> 源文件: modules/svg/include/SkSVGFeImage.h

## 概述

`SkSVGFeImage` 实现 SVG `<feImage>` 滤镜原语,将外部图像或 SVG 元素引入滤镜管线作为输入源。继承自 `SkSVGFe`。

## 核心属性

- `href`: 图像 URI 或元素引用(url(#id) 或 data URI)
- `preserveAspectRatio`: 纵横比保持策略

## 主要功能

引入外部图像到滤镜,引用 SVG 元素作为纹理,支持 data URI 嵌入图像,可用作滤镜输入源。

## 使用场景

使用图像作为置换图,将 SVG 图形转换为纹理,组合多个图形元素,实现复杂的合成效果。

## 引用类型

- 外部图像: `href="image.png"`
- Data URI: `href="data:image/png;base64,..."`
- SVG 元素: `href="#elementId"`

## 相关文件

- `modules/svg/src/SkSVGFeImage.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类

该滤镜原语扩展了滤镜的输入源,支持使用任意图像数据。
