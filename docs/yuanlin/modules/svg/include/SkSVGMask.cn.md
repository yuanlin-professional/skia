# SkSVGMask

> 源文件: modules/svg/include/SkSVGMask.h

## 概述

`SkSVGMask` 实现 SVG `<mask>` 元素,定义 alpha 遮罩用于控制图形的可见性。继承自 `SkSVGHiddenContainer`,遮罩内容的亮度决定目标图形的不透明度。

## 核心属性

- `x`, `y`, `width`, `height`: 遮罩区域
- `maskUnits`: 坐标系统(objectBoundingBox 或 userSpaceOnUse)
- `maskContentUnits`: 遮罩内容坐标系统

## 主要功能

根据遮罩内容的亮度计算目标的 alpha 通道,白色区域完全不透明,黑色区域完全透明,灰色区域半透明,支持复杂的可见性控制。

## 使用场景

实现渐隐效果、复杂形状的裁剪、光照效果等。遮罩比裁剪路径更灵活,支持渐变透明度。

## 相关文件

- `modules/svg/src/SkSVGMask.cpp`: 实现
- `SkSVGClipPath.h`: 裁剪路径(二值遮罩)

遮罩是实现高级透明度效果的核心工具,支持基于亮度的 alpha 合成。
