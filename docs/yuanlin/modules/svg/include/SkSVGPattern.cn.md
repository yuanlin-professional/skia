# SkSVGPattern

> 源文件: modules/svg/include/SkSVGPattern.h

## 概述

`SkSVGPattern` 实现 SVG `<pattern>` 元素,定义用于填充或描边的重复图案。继承自 `SkSVGHiddenContainer`,包含构成图案的图形元素。

## 核心属性

- `x`, `y`: 图案平铺起点
- `width`, `height`: 单个图案单元尺寸
- `patternUnits`: 坐标系统(objectBoundingBox 或 userSpaceOnUse)
- `patternContentUnits`: 图案内容坐标系统
- `patternTransform`: 应用于图案的变换
- `viewBox`: 图案内容视口

## 主要功能

定义可重复的图形图案,转换为 Skia `SkShader`,支持平铺和变换,用于复杂的填充效果。

## 使用示例

```xml
<pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">
  <circle cx="10" cy="10" r="5" fill="blue"/>
</pattern>
<rect width="200" height="200" fill="url(#dots)"/>
```

## 相关文件

- `modules/svg/src/SkSVGPattern.cpp`: 实现
- `include/core/SkShader.h`: Skia 着色器

图案是实现纹理填充的强大工具,支持任意复杂的重复图形。
