# SkSVGImage

> 源文件: modules/svg/include/SkSVGImage.h

## 概述

`SkSVGImage` 实现 SVG `<image>` 元素,用于在 SVG 文档中嵌入光栅图像(PNG, JPEG 等)或其他 SVG 文档。继承自 `SkSVGTransformableNode`。

## 核心属性

- `x`, `y`: 图像位置
- `width`, `height`: 图像尺寸
- `href`: 图像源 URI(可以是 data URI 或外部 URL)
- `preserveAspectRatio`: 纵横比保持策略

## 主要功能

支持嵌入式图像(data URI)和外部引用,自动解码图像数据,应用变换和裁剪,处理纵横比。

## 相关文件

- `modules/svg/src/SkSVGImage.cpp`: 实现
- `include/core/SkImage.h`: Skia 图像对象

该元素桥接光栅图像和矢量图形,支持混合内容的 SVG 文档。
