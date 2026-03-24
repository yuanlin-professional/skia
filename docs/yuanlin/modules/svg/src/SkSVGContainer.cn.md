# SkSVGContainer

> 源文件: [modules/svg/src/SkSVGContainer.cpp](../../../../modules/svg/src/SkSVGContainer.cpp)

## 概述

`SkSVGContainer` 是 SVG DOM 中容器节点的基类，实现了子节点管理、递归渲染、路径合并和边界框计算等核心功能。它对应 SVG 中可以包含子元素的节点（如 `<g>`、`<svg>`、`<defs>` 等），为所有容器类型提供统一的子节点遍历和渲染框架。

## 架构位置

```
SkSVGNode
  └── SkSVGTransformableNode
        └── SkSVGContainer  ← 本文件实现
              ├── SkSVGSVG
              ├── SkSVGG
              ├── SkSVGDefs
              ├── SkSVGHiddenContainer
              └── ... (其他容器节点)
```

`SkSVGContainer` 是 SVG 节点树中所有可包含子节点的元素的共同基类，是 SVG DOM 树结构的核心支撑类。

## 主要类与结构体

### SkSVGContainer
- 继承链中的中间类，继承自 `INHERITED`（通常是 `SkSVGTransformableNode`）
- 维护 `fChildren` 子节点数组
- 提供子节点管理、渲染遍历、路径合并、边界框计算等功能

## 公共 API 函数

### `appendChild`
```cpp
void appendChild(sk_sp<SkSVGNode> node);
```
添加一个子节点。使用 `SkASSERT` 确保传入的节点非空，使用 `std::move` 转移所有权。

### `hasChildren`
```cpp
bool hasChildren() const;
```
检查是否有子节点。

### `onRender`
```cpp
void onRender(const SkSVGRenderContext& ctx) const;
```
递归渲染所有子节点，按顺序调用每个子节点的 `render` 方法（即画家算法——先添加的先渲染，后添加的覆盖在上方）。

### `onAsPath`
```cpp
SkPath onAsPath(const SkSVGRenderContext& ctx) const;
```
将容器的所有子节点转换为路径，使用 `SkPathOps::Op` 以 `kUnion_SkPathOp`（并集）操作逐一合并，最后通过 `mapToParent` 变换到父坐标系。

### `onTransformableObjectBoundingBox`
```cpp
SkRect onTransformableObjectBoundingBox(const SkSVGRenderContext& ctx) const;
```
计算所有子节点边界框的并集，使用 `SkRect::join` 逐一合并。

## 内部实现细节

- **路径合并**: `onAsPath` 使用 `SkPathOps` 的布尔运算（并集）来合并子路径，这确保了重叠区域的正确处理，但比简单的 `addPath` 更为精确。如果路径操作失败（`Op` 返回空的 optional），则保留当前路径不变。
- **渲染顺序**: 子节点按数组顺序渲染，对应 SVG 的文档顺序（Document Order），即后面的元素绘制在前面的元素之上。
- **边界框计算**: 从空矩形开始，逐一 `join` 子节点的边界框。对于空容器，返回空矩形。

## 依赖关系

- **Skia 核心**: `SkPath`
- **Skia 路径运算**: `SkPathOps`（路径布尔运算）
- **Skia 私有工具**: `SkAssert`
- **SVG 模块**: 基类（`SkSVGTransformableNode` 或其他）

## 设计模式与设计决策

1. **组合模式（Composite Pattern）**: `SkSVGContainer` 是经典组合模式的实现，允许将单个节点和容器节点统一处理。子节点可以是叶子节点也可以是其他容器。

2. **画家算法**: `onRender` 的顺序遍历实现了 SVG 规范要求的画家算法渲染顺序。

3. **路径布尔运算**: 使用 `kUnion_SkPathOp` 而非简单的 `addPath` 来合并子路径，确保重叠区域的正确几何表示，适用于裁剪路径等场景。

4. **所有权管理**: 使用 `sk_sp<SkSVGNode>` 智能指针管理子节点生命周期，`std::move` 避免不必要的引用计数操作。

## 性能考量

- `onRender` 的时间复杂度为 O(N)，N 为子节点数量，每个子节点递归渲染。
- `onAsPath` 的路径布尔运算（`SkPathOps::Op`）开销较大，特别是当子路径复杂时。不过此方法通常仅在需要路径表示时调用（如裁剪路径），不在常规渲染路径中。
- `onTransformableObjectBoundingBox` 的 `join` 操作非常轻量，仅涉及矩形坐标比较。

## 相关文件

- `modules/svg/include/SkSVGContainer.h` - 类声明
- `modules/svg/include/SkSVGTransformableNode.h` - 可变换节点基类
- `modules/svg/include/SkSVGNode.h` - SVG 节点基类
- `include/core/SkPath.h` - 路径类
- `include/pathops/SkPathOps.h` - 路径布尔运算
