# SkSVGLine

> 源文件: modules/svg/include/SkSVGLine.h

## 概述

`SkSVGLine` 实现 SVG `<line>` 元素,表示两点之间的直线段。继承自 `SkSVGShape`,支持起点和终点坐标定义。

## 核心属性

- `x1`, `y1`: 起点坐标
- `x2`, `y2`: 终点坐标

## 主要功能

使用 `SkCanvas::drawLine()` 绘制直线,支持描边属性(填充属性不适用于线段)。可转换为包含单个 `moveTo/lineTo` 的路径。

## 相关文件

- `modules/svg/src/SkSVGLine.cpp`: 实现
- `SkSVGPoly.h`: 折线/多边形(多段线)

该类提供 SVG 基础线段元素的高效渲染实现。
