# SkSVGFeMorphology

> 源文件: modules/svg/include/SkSVGFeMorphology.h

## 概述

`SkSVGFeMorphology` 实现 SVG `<feMorphology>` 滤镜原语,执行形态学操作(膨胀和腐蚀)。继承自 `SkSVGFe`,用于加粗或细化图形。

## 核心属性

- `operator`: 操作类型(erode 腐蚀或 dilate 膨胀)
- `radius`: X 和 Y 方向的半径

## 主要功能

**膨胀(dilate)**: 扩展图形边界,使对象变粗
**腐蚀(erode)**: 收缩图形边界,使对象变细

转换为 Skia 图像滤镜,常用于创建加粗文本、外发光效果等。

## 使用场景

结合其他滤镜创建描边效果、阴影变化、边缘增强等。

## 相关文件

- `modules/svg/src/SkSVGFeMorphology.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类

该滤镜提供基础的形态学图像处理能力,是实现特殊效果的重要工具。
