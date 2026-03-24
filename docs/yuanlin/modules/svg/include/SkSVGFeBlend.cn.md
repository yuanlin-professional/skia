# SkSVGFeBlend

> 源文件: modules/svg/include/SkSVGFeBlend.h

## 概述

`SkSVGFeBlend` 实现 SVG `<feBlend>` 滤镜原语,混合两个输入图像。支持多种混合模式,如 normal, multiply, screen 等。继承自 `SkSVGFe`。

## 主要功能

- 混合两个输入源(in, in2)
- 支持标准 SVG 混合模式
- 映射到 Skia `SkBlendMode`
- 用于滤镜效果合成

## 核心属性

- `mode`: 混合模式(normal, multiply, screen, darken, lighten)
- `in`: 第一个输入源
- `in2`: 第二个输入源
- `result`: 输出标识符

## 混合模式

支持 SVG 规范定义的混合模式,映射到 Skia 的混合模式枚举。常用模式包括普通混合、正片叠底、滤色、变暗、变亮等。

## 相关文件

- `modules/svg/src/SkSVGFeBlend.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类
- `include/core/SkBlendMode.h`: Skia 混合模式

该滤镜原语支持图层混合效果,是复合滤镜的重要组成部分。
