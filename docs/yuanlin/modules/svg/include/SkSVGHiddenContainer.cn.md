# SkSVGHiddenContainer

> 源文件: modules/svg/include/SkSVGHiddenContainer.h

## 概述

`SkSVGHiddenContainer` 是不直接渲染的容器元素基类,用于 `<defs>`, `<symbol>` 等定义性元素。继承自 `SkSVGContainer`。

## 主要功能

- 存储子元素但不渲染
- 支持通过 ID 引用
- 用于可复用元素的定义
- 管理符号库和资源定义

## 派生类

- `SkSVGDefs`: `<defs>` 定义容器
- (可能) `SkSVGSymbol`: `<symbol>` 符号定义

## 渲染行为

重写 `onRender()` 为空操作,子元素不参与正常渲染流程,仅在被引用时渲染(如通过 `<use>`)。

## 使用场景

存储渐变、滤镜、图案、裁剪路径等可复用资源,或定义符号供多次实例化。

## 相关文件

- `modules/svg/src/SkSVGHiddenContainer.cpp`: 实现
- `SkSVGContainer.h`: 基类

该类支持 SVG 的声明式和复用特性,是模块化 SVG 文档的基础。
