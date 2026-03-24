# SkSVGFeOffset

> 源文件: modules/svg/include/SkSVGFeOffset.h

## 概述

`SkSVGFeOffset` 实现 SVG `<feOffset>` 滤镜原语,将输入图像在 X 和 Y 方向上偏移指定距离。继承自 `SkSVGFe`,常用于创建阴影效果。

## 核心属性

- `dx`: X 方向偏移量
- `dy`: Y 方向偏移量
- `in`: 输入源

## 主要功能

简单的图像平移操作,常与模糊滤镜组合创建投影阴影,支持负值偏移。

## 使用场景

投影阴影的第一步(先偏移,再模糊),创建双重图像效果,位移叠加效果。

## 典型用法

```xml
<filter id="shadow">
  <feOffset in="SourceAlpha" dx="4" dy="4"/>
  <feGaussianBlur stdDeviation="2"/>
  <feMerge>
    <feMergeNode/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

## 相关文件

- `modules/svg/src/SkSVGFeOffset.cpp`: 实现

该滤镜虽然简单,但是构建复杂滤镜效果(特别是阴影)的基础工具。
