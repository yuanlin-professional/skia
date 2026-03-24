# SkSVGText

> 源文件: modules/svg/include/SkSVGText.h

## 概述

`SkSVGText` 实现 SVG 文本元素,包括 `<text>`, `<tspan>`, `<textPath>` 等。支持复杂的文本布局、样式和路径文本。继承自 `SkSVGTransformableNode`。

## 核心属性

- `x`, `y`: 文本位置
- `dx`, `dy`: 相对偏移
- 字体属性: `font-family`, `font-size`, `font-weight`, `font-style`
- 文本锚点: `text-anchor`(start, middle, end)

## 主要功能

渲染文本内容,支持多行文本和复杂布局,处理字体选择和样式,支持路径文本(文本沿路径排列),处理文本锚点和对齐。

## 文本元素层次

- `<text>`: 顶层文本容器
- `<tspan>`: 文本跨度,用于局部样式
- `<textPath>`: 路径文本,使文本沿 SVG 路径排列

## 使用场景

SVG 中的文字渲染,支持丰富的排版效果,可应用填充、描边和滤镜。

## 相关文件

- `modules/svg/src/SkSVGText.cpp`: 实现
- `include/core/SkFont.h`: Skia 字体

文本元素使 SVG 能够展示和排版文字内容,支持丰富的样式和效果。
