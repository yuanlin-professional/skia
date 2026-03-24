# SkSVGTransformableNode

> 源文件: modules/svg/include/SkSVGTransformableNode.h

## 概述

`SkSVGTransformableNode` 是支持坐标变换的 SVG 节点基类,为 `<g>`, `<rect>`, `<circle>` 等可变换元素提供变换属性支持。继承自 `SkSVGNode`。

## 主要功能

- 管理 `transform` 属性
- 应用累积变换到渲染上下文
- 支持变换组合(translate, rotate, scale, skew, matrix)
- 计算变换后的边界框

## 变换类型

- `translate(tx, ty)`: 平移
- `rotate(angle, cx, cy)`: 旋转(可选旋转中心)
- `scale(sx, sy)`: 缩放
- `skewX(angle)`, `skewY(angle)`: 倾斜
- `matrix(a, b, c, d, e, f)`: 任意矩阵变换

## 变换组合

多个变换从左到右依次应用,形成变换矩阵链。例如: `transform="translate(50,50) rotate(45)"` 先平移再旋转。

## 派生类

几乎所有可见的 SVG 元素都继承自该类,包括形状、容器、文本等。

## 边界框计算

提供变换后的对象边界框计算,用于裁剪、遮罩和布局。

## 相关文件

- `modules/svg/src/SkSVGTransformableNode.cpp`: 实现
- `SkSVGNode.h`: 节点基类
- `include/core/SkMatrix.h`: Skia 矩阵

该基类为 SVG 元素提供了灵活的坐标变换能力,是 SVG 图形变换的核心。
