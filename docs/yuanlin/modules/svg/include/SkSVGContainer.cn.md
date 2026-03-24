# SkSVGContainer

> 源文件: modules/svg/include/SkSVGContainer.h

## 概述

`SkSVGContainer` 是 SVG 容器元素的基类,支持包含子元素的 SVG 节点,如 `<g>`, `<svg>`, `<defs>` 等。继承自 `SkSVGTransformableNode`。

## 主要功能

- 管理子元素集合
- 实现 `appendChild()` 方法
- 递归渲染所有子元素
- 支持变换和样式继承

## 核心接口

```cpp
void appendChild(sk_sp<SkSVGNode>) override;
bool hasChildren() const override;
```

## 渲染行为

遍历子元素,依次调用其 `render()` 方法。容器本身通常不产生图形输出,仅传递渲染上下文和应用变换。

## 派生类

- `SkSVGG`: `<g>` 分组元素
- `SkSVGSVG`: `<svg>` 根元素
- `SkSVGDefs`: `<defs>` 定义容器(子元素不直接渲染)

## 相关文件

- `modules/svg/src/SkSVGContainer.cpp`: 实现

该类是 SVG DOM 树结构的基础,支持层次化的图形组织和管理。
