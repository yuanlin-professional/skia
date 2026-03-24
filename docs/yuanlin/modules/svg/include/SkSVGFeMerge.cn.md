# SkSVGFeMerge

> 源文件: modules/svg/include/SkSVGFeMerge.h

## 概述

`SkSVGFeMerge` 实现 SVG `<feMerge>` 滤镜原语,将多个滤镜输入层叠合并。包含多个 `<feMergeNode>` 子元素,每个指定一个输入源。

## 主要功能

- 合并多个滤镜结果
- 按顺序层叠输入源(后续源覆盖在前面源之上)
- 支持任意数量的输入
- 实现多层滤镜效果组合

## 子元素

`<feMergeNode>`: 指定单个输入源,通过 `in` 属性引用。多个 MergeNode 按声明顺序合并。

## 使用场景

常用于组合多个滤镜效果,如将模糊的阴影与原图合并,或组合多个不同的滤镜输出。

## 相关文件

- `modules/svg/src/SkSVGFeMerge.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类

该滤镜原语提供简单而强大的多输入合并能力,是构建复杂滤镜的基础。
