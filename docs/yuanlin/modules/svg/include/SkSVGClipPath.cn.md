# SkSVGClipPath

> 源文件: modules/svg/include/SkSVGClipPath.h

## 概述

`SkSVGClipPath` 实现 SVG `<clipPath>` 元素,定义裁剪区域用于限制图形的可见部分。继承自 `SkSVGHiddenContainer`,裁剪路径本身不渲染。

## 核心属性

- `clipPathUnits`: 坐标系统(objectBoundingBox 或 userSpaceOnUse)
- 包含定义裁剪区域的形状元素

## 主要功能

定义裁剪区域(由子元素形状组成),应用于目标元素(通过 `clip-path` 属性),支持复杂形状的裁剪,转换为 Skia `SkPath` 用于裁剪。

## 裁剪规则

裁剪路径内的区域可见,路径外的区域被裁剪。多个形状会合并为单个裁剪区域(通常使用 union)。

## 使用示例

```xml
<clipPath id="clip">
  <circle cx="50" cy="50" r="40"/>
</clipPath>
<rect width="100" height="100" fill="red" clip-path="url(#clip)"/>
```

## 与遮罩的区别

裁剪是二值的(可见或不可见),而遮罩支持渐变透明度。裁剪更高效,但灵活性较低。

## 相关文件

- `modules/svg/src/SkSVGClipPath.cpp`: 实现
- `SkSVGMask.h`: 遮罩(更灵活的可见性控制)
- `include/core/SkPath.h`: Skia 路径(用于裁剪)

裁剪路径是实现复杂形状可见性控制的重要工具,广泛用于图形设计和布局。
