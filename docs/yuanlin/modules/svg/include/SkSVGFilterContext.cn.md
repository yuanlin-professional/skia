# SkSVGFilterContext

> 源文件: modules/svg/include/SkSVGFilterContext.h

## 概述

`SkSVGFilterContext` 管理 SVG 滤镜渲染的上下文信息,包括输入/输出缓冲区、坐标空间和滤镜区域。用于滤镜效果管线的状态管理。

## 主要功能

- 管理滤镜输入源(SourceGraphic, SourceAlpha, BackgroundImage 等)
- 跟踪中间结果(通过 result 属性)
- 处理滤镜坐标系统(objectBoundingBox 或 userSpaceOnUse)
- 管理滤镜区域和单位

## 核心概念

**内置输入源**:
- `SourceGraphic`: 原始图形
- `SourceAlpha`: 原始图形的 alpha 通道
- `BackgroundImage`: 背景图像
- `BackgroundAlpha`: 背景 alpha
- `FillPaint`, `StrokePaint`: 填充/描边

**坐标系统**:
- `objectBoundingBox`: 相对于对象边界框(0-1 范围)
- `userSpaceOnUse`: 用户空间坐标

## 设计特点

提供滤镜管线所需的完整上下文,支持多步滤镜操作和结果缓存。处理 SVG 滤镜的复杂坐标空间和单位系统。

## 相关文件

- `modules/svg/src/SkSVGFilterContext.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类

该类是 SVG 滤镜渲染的核心支撑,确保滤镜管线的正确执行。
