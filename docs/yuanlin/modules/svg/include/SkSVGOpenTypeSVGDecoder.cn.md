# SkSVGOpenTypeSVGDecoder

> 源文件: modules/svg/include/SkSVGOpenTypeSVGDecoder.h

## 概述

`SkSVGOpenTypeSVGDecoder` 实现 OpenType SVG 字体表的解码器,支持 SVG 格式的字形渲染。这是字体渲染系统的扩展,允许使用 SVG 图形作为字形。

## 主要功能

- 解码 OpenType SVG 表数据
- 将 SVG 字形渲染为位图或路径
- 支持彩色字体和复杂图形
- 集成到 Skia 字体渲染管线

## 使用场景

用于支持包含 SVG 字形的彩色字体,如 emoji 字体、装饰字体等。相比传统的轮廓字体,SVG 字形可以包含渐变、图案和复杂效果。

## 相关文件

- `modules/svg/src/SkSVGOpenTypeSVGDecoder.cpp`: 实现
- `include/core/SkTypeface.h`: 字体接口

该解码器扩展了 Skia 的字体支持能力,实现现代彩色字体标准。
