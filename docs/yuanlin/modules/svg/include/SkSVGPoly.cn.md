# SkSVGPoly

> 源文件: modules/svg/include/SkSVGPoly.h

## 概述

`SkSVGPoly` 是 SVG 多边形和折线元素的基类,支持 `<polygon>` 和 `<polyline>` 元素。通过点序列定义路径。

## 核心属性

- `points`: 点坐标列表(SkSVGPointsType)

## 主要功能

解析空格或逗号分隔的点坐标序列,构建路径。`<polygon>` 自动闭合路径,`<polyline>` 不闭合。支持填充和描边渲染。

## 派生类

- `SkSVGPolygon`: 闭合多边形
- `SkSVGPolyline`: 开放折线

## 相关文件

- `modules/svg/src/SkSVGPoly.cpp`: 基类实现

该类提供基于点序列的形状定义方式,适用于规则和不规则多边形。
