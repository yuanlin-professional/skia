# SkSVGG

> 源文件: modules/svg/include/SkSVGG.h

## 概述

`SkSVGG` 实现 SVG `<g>` 分组元素,用于组织和管理多个图形元素。继承自 `SkSVGContainer`,是最常用的容器元素。

## 主要功能

- 对子元素进行逻辑分组
- 应用共同的变换和样式
- 支持嵌套分组
- 简化 SVG 文档结构

## 使用场景

`<g>` 元素用于:
1. 应用统一变换(translate, rotate, scale)
2. 设置共享样式属性
3. 组织相关图形元素
4. 支持 ID 引用和复用

## 渲染行为

继承容器的渲染逻辑,依次渲染所有子元素,自动传递渲染上下文。

## 相关文件

- `modules/svg/src/SkSVGG.cpp`: 实现
- `SkSVGContainer.h`: 基类

`<g>` 是 SVG 结构组织的核心元素,提供灵活的分组和变换管理能力。
