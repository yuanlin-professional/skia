# SkSVGStop

> 源文件: modules/svg/include/SkSVGStop.h

## 概述

`SkSVGStop` 实现 SVG `<stop>` 元素,定义渐变中的颜色停止点。用于 `<linearGradient>` 和 `<radialGradient>` 的子元素。

## 核心属性

- `offset`: 停止点位置(0.0 到 1.0 或 0% 到 100%)
- `stop-color`: 停止点颜色
- `stop-opacity`: 停止点不透明度

## 主要功能

定义渐变中的颜色过渡点,多个停止点组成渐变的颜色映射,支持任意数量的停止点。

## 使用示例

```xml
<linearGradient id="grad">
  <stop offset="0%" stop-color="red"/>
  <stop offset="50%" stop-color="yellow"/>
  <stop offset="100%" stop-color="blue"/>
</linearGradient>
```

## 相关文件

- `modules/svg/src/SkSVGStop.cpp`: 实现
- `SkSVGGradient.h`: 渐变基类

停止点是渐变定义的核心元素,控制颜色插值的关键位置和颜色。
