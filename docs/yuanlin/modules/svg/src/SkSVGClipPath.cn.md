# SkSVGClipPath

> 源文件: [modules/svg/src/SkSVGClipPath.cpp](../../../../modules/svg/src/SkSVGClipPath.cpp)

## 概述

`SkSVGClipPath` 实现了 SVG `<clipPath>` 元素的功能，用于定义裁剪路径。裁剪路径是 SVG 中一种重要的合成机制，它限制了被裁剪元素的可见区域——只有裁剪路径内部的部分会被渲染。

该类负责解析 `clipPathUnits` 属性，并将裁剪路径从本地坐标系转换到目标元素的坐标系中。

## 架构位置

```
SkSVGNode
  └── SkSVGContainer
        └── SkSVGHiddenContainer
              └── SkSVGClipPath       ← 本文件
```

`SkSVGClipPath` 继承自 `SkSVGHiddenContainer`，因为裁剪路径本身不直接渲染，仅在被其他元素通过 `clip-path` 属性引用时才生效。

## 主要类与结构体

### `SkSVGClipPath`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fClipPathUnits` | `SkSVGObjectBoundingBoxUnits` | 裁剪路径的坐标系统，可选 `userSpaceOnUse` 或 `objectBoundingBox` |

## 公共 API 函数

### `parseAndSetAttribute(const char* n, const char* v)`
解析 `clipPathUnits` 属性，决定裁剪路径使用的坐标系统：
- `userSpaceOnUse` - 使用创建裁剪路径时的用户坐标系
- `objectBoundingBox` - 使用被裁剪元素的边界框坐标系

### `resolveClip(const SkSVGRenderContext& ctx) const`
核心方法，将裁剪路径解析为最终的 `SkPath`：
1. 调用 `asPath()` 获取裁剪路径的基础形状
2. 根据 `clipPathUnits` 获取 OBB（object bounding box）变换信息
3. 构建变换矩阵（平移 + 缩放）
4. 应用变换到路径上

## 内部实现细节

### 坐标系变换

`resolveClip` 方法通过 `ctx.transformForCurrentOBB(fClipPathUnits)` 获取当前对象边界框的变换参数（偏移量和缩放因子），然后构建变换矩阵：

```
矩阵 = Translate(offset.x, offset.y) * Scale(scale.x, scale.y)
```

当 `clipPathUnits` 为 `objectBoundingBox` 时，裁剪路径的坐标会被缩放到目标元素的边界框大小；当为 `userSpaceOnUse` 时，偏移和缩放均为单位值，不影响路径。

## 依赖关系

- **Skia Core**: `SkM44`, `SkMatrix`
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGRenderContext`, `SkSVGHiddenContainer`

## 设计模式与设计决策

1. **隐藏容器**: 裁剪路径作为 `SkSVGHiddenContainer` 的子类，不参与正常渲染流程，只在被引用时通过 `resolveClip` 解析。

2. **OBB 变换抽象**: 坐标系转换逻辑委托给 `SkSVGRenderContext::transformForCurrentOBB()`，统一了 `objectBoundingBox` 和 `userSpaceOnUse` 的处理方式。

3. **路径组合**: 裁剪路径的内容通过 `asPath()` 递归地将所有子元素合并为一条路径，利用了 `SkSVGNode` 基类的路径转换能力。

## 性能考量

- `asPath()` 调用可能触发递归路径合并，对于包含大量子元素的裁剪路径可能产生较大开销
- `makeTransform()` 创建路径的变换副本，涉及内存分配
- 裁剪路径在每次应用时都重新解析，缺少缓存机制

## 相关文件

- `modules/svg/include/SkSVGClipPath.h` - 头文件定义
- `modules/svg/include/SkSVGHiddenContainer.h` - 隐藏容器基类
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文，提供 OBB 变换
- `modules/svg/src/SkSVGNode.cpp` - `asPath()` 中的 clip-path 布尔运算
