# SkSVGLinearGradient

> 源文件: modules/svg/include/SkSVGLinearGradient.h

## 概述

`SkSVGLinearGradient` 实现 SVG `<linearGradient>` 元素,创建沿直线方向的颜色渐变。继承自 `SkSVGGradient`,是最常用的渐变类型。

## 核心属性

- `x1`, `y1`: 渐变起点坐标
- `x2`, `y2`: 渐变终点坐标
- 继承渐变通用属性(gradientUnits, gradientTransform, spreadMethod)

## 主要功能

定义线性渐变方向和范围,包含 `<stop>` 子元素定义颜色停止点,转换为 Skia `SkGradientShader`,支持任意角度的渐变。

## 渐变方向

从 (x1, y1) 到 (x2, y2) 的直线定义渐变方向,垂直于该直线的所有点具有相同颜色。

## 使用示例

```xml
<linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
  <stop offset="0%" stop-color="red"/>
  <stop offset="100%" stop-color="blue"/>
</linearGradient>
```

## 相关文件

- `modules/svg/src/SkSVGLinearGradient.cpp`: 实现
- `SkSVGGradient.h`: 渐变基类
- `include/effects/SkGradientShader.h`: Skia 渐变着色器

线性渐变是最基础和常用的渐变类型,广泛用于背景、按钮等视觉效果。
