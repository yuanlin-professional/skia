# SkSVGRadialGradient

> 源文件: modules/svg/include/SkSVGRadialGradient.h

## 概述

`SkSVGRadialGradient` 实现 SVG `<radialGradient>` 元素,创建从中心点向外辐射的圆形或椭圆形渐变。继承自 `SkSVGGradient`。

## 核心属性

- `cx`, `cy`: 渐变中心坐标
- `r`: 渐变半径
- `fx`, `fy`: 焦点坐标(可选,默认等于中心)
- `fr`: 焦点半径(可选,默认为 0)
- 继承渐变通用属性

## 主要功能

定义径向渐变的几何参数,支持焦点偏移(创建非对称渐变),包含 `<stop>` 子元素定义颜色,转换为 Skia 径向渐变着色器。

## 焦点说明

焦点决定渐变的起始位置,当焦点偏离中心时,创建非对称的径向渐变效果,适合模拟光照和立体感。

## 使用示例

```xml
<radialGradient id="grad" cx="50%" cy="50%" r="50%">
  <stop offset="0%" stop-color="white"/>
  <stop offset="100%" stop-color="blue"/>
</radialGradient>
```

## 应用场景

球形高光,圆形按钮,聚光灯效果,立体感模拟,光晕效果。

## 相关文件

- `modules/svg/src/SkSVGRadialGradient.cpp`: 实现
- `SkSVGGradient.h`: 渐变基类
- `include/effects/SkGradientShader.h`: Skia 渐变着色器

径向渐变是创建圆形和球形效果的重要工具,广泛用于 UI 设计和视觉效果。
