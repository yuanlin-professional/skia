# SkSVGFeGaussianBlur

> 源文件: modules/svg/include/SkSVGFeGaussianBlur.h

## 概述

`SkSVGFeGaussianBlur` 实现 SVG `<feGaussianBlur>` 滤镜原语,对输入图像应用高斯模糊效果。继承自 `SkSVGFe`,是最常用的滤镜原语之一。

## 核心属性

- `stdDeviation`: 标准差(控制模糊程度),可指定 X 和 Y 方向的独立值
- `in`: 输入源
- `edgeMode`: 边缘处理模式(duplicate, wrap, none)

## 主要功能

应用高斯模糊算法,支持独立的水平和垂直模糊,转换为 Skia `SkImageFilter`,常用于阴影、发光、景深等效果。

## 标准差说明

`stdDeviation` 值越大,模糊程度越高。值为 0 表示无模糊。可指定单个值(水平和垂直相同)或两个值(分别控制)。

## 使用场景

投影阴影,外发光/内发光效果,背景模糊,景深模拟,柔化边缘。

## 性能考量

高斯模糊是计算密集型操作,标准差越大,性能开销越高。Skia 使用优化的模糊算法提高效率。

## 相关文件

- `modules/svg/src/SkSVGFeGaussianBlur.cpp`: 实现
- `include/effects/SkImageFilters.h`: Skia 图像滤镜

该滤镜是创建各种模糊效果的基础工具,广泛用于 SVG 视觉效果。
