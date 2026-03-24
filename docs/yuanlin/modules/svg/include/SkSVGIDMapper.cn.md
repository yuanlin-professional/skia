# SkSVGIDMapper

> 源文件: modules/svg/include/SkSVGIDMapper.h

## 概述

`SkSVGIDMapper` 管理 SVG 元素 ID 到节点对象的映射,支持通过 ID 查找元素。这是 SVG 引用机制(如 `url(#id)`)的基础设施。

## 主要功能

- 注册元素 ID 和节点指针的映射
- 通过 ID 查找节点
- 支持渐变、滤镜、裁剪路径等资源引用
- 处理 ID 冲突

## 核心接口

```cpp
void set(const SkSVGIRI& id, sk_sp<SkSVGNode> node);
sk_sp<SkSVGNode> find(const SkSVGIRI& id) const;
```

## 使用场景

当 SVG 元素通过 `fill="url(#gradient)"`, `filter="url(#blur)"` 等方式引用其他元素时,通过 IDMapper 查找目标元素。

## 相关文件

- `modules/svg/src/SkSVGIDMapper.cpp`: 实现
- `SkSVGDOM.h`: 包含 IDMapper 实例

该类是 SVG 引用和复用机制的核心,支持模块化的 SVG 文档结构。
