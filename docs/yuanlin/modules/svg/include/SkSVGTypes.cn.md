# SkSVGTypes

> 源文件: modules/svg/include/SkSVGTypes.h

## 概述

`SkSVGTypes.h` 定义了 Skia SVG 模块使用的所有核心数据类型,包括长度、颜色、变换、单位等。这是 SVG 类型系统的基础,确保类型安全和正确的单位处理。

## 主要类型

### SkSVGLength
表示 SVG 长度值,支持多种单位(px, %, em, pt, cm, mm 等)。包含值和单位类型,在渲染时根据上下文解析为实际像素值。

### SkSVGColor
表示 SVG 颜色,支持命名颜色、十六进制、RGB、HSL 等格式。

### SkSVGPaint
表示填充或描边值,可以是颜色、渐变引用、图案引用或 "none"。

### SkSVGTransformType
表示 SVG 变换(translate, rotate, scale, skew, matrix)。

### SkSVGPreserveAspectRatio
控制 viewBox 到视口的映射方式。

### SkSVGFillRule
填充规则: nonzero 或 evenodd。

### SkSVGLineCap / SkSVGLineJoin
线条端点和连接样式。

### SkSVGVisibility / SkSVGDisplay
元素可见性控制。

## 设计特点

类型封装了 SVG 规范中定义的数据格式,保留原始单位信息直到渲染时,支持继承和默认值,提供类型安全的 API。

## 相关文件

- `modules/svg/src/SkSVGTypes.cpp`: 类型实现
- `SkSVGAttributeParser.h`: 类型解析

该文件是 SVG 类型系统的核心,确保 SVG 属性值的正确表示和处理。
