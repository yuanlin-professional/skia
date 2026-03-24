# SkSVGSVG

> 源文件: modules/svg/include/SkSVGSVG.h

## 概述

`SkSVGSVG` 实现 SVG `<svg>` 元素,可作为文档根元素或嵌套 SVG 容器。继承自 `SkSVGContainer`,定义视口和坐标系统。

## 核心属性

- `x`, `y`: SVG 容器位置
- `width`, `height`: SVG 容器尺寸
- `viewBox`: 定义用户坐标系统
- `preserveAspectRatio`: 纵横比保持策略

## 主要功能

作为根元素时建立初始坐标系统和视口,支持嵌套 SVG(创建新的坐标空间),处理 viewBox 到视口的映射,管理纵横比保持。

## viewBox 处理

`viewBox` 属性定义用户坐标系统,与视口尺寸的映射关系由 `preserveAspectRatio` 控制,支持缩放和平移。

## 相关文件

- `modules/svg/src/SkSVGSVG.cpp`: 实现
- `SkSVGContainer.h`: 基类

`<svg>` 是 SVG 文档的核心容器,定义了图形的坐标空间和渲染区域。
