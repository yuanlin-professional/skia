# SkSVGPath

> 源文件: modules/svg/include/SkSVGPath.h

## 概述

`SkSVGPath` 实现 SVG `<path>` 元素,支持任意复杂的矢量图形路径。继承自 `SkSVGShape`,是最通用的 SVG 形状元素。

## 核心属性

- `d`: 路径数据字符串(SVG path commands: M, L, C, Q, A, Z 等)

## 主要功能

解析 SVG 路径语法(使用 `SkParsePath`),转换为 `SkPath` 对象并渲染。支持所有标准 SVG 路径命令,包括曲线(贝塞尔曲线、圆弧)和闭合路径。

## 设计特点

依赖 `SkParsePath` 工具类进行路径字符串解析,支持绝对和相对坐标命令。路径是最灵活的 SVG 元素,可表示任意形状。

## 相关文件

- `modules/svg/src/SkSVGPath.cpp`: 实现
- `include/utils/SkParsePath.h`: 路径解析工具

该类是 SVG 图形表达能力的核心,支持复杂矢量图形的精确渲染。
