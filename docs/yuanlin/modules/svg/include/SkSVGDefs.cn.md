# SkSVGDefs

> 源文件: modules/svg/include/SkSVGDefs.h

## 概述

`SkSVGDefs` 实现 SVG `<defs>` 元素,用于定义可复用的图形对象而不直接渲染。继承自 `SkSVGHiddenContainer`。

## 主要功能

- 存储渐变、滤镜、裁剪路径等定义
- 子元素不参与直接渲染
- 通过 ID 引用供其他元素使用
- 支持复用和模块化

## 渲染行为

`<defs>` 元素本身及其直接子元素不渲染,但可通过 `<use>`, `url()` 等机制引用。元素存储在 SVG DOM 中供查找和复用。

## 典型内容

- `<linearGradient>`, `<radialGradient>`: 渐变定义
- `<pattern>`: 图案填充
- `<clipPath>`, `<mask>`: 裁剪和遮罩
- `<filter>`: 滤镜效果
- 可复用的图形元素

## 相关文件

- `modules/svg/src/SkSVGDefs.cpp`: 实现
- `SkSVGHiddenContainer.h`: 基类(隐藏容器)

`<defs>` 是 SVG 模块化和复用机制的基础,支持高效的图形定义管理。
