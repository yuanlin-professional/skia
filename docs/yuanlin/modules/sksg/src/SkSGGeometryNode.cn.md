# SkSGGeometryNode 实现 -- 几何节点基类实现

> 源文件: `modules/sksg/src/SkSGGeometryNode.cpp`

## 概述

`SkSGGeometryNode.cpp` 实现了 Skia Scene Graph 中所有几何节点的基类 `GeometryNode` 的运行时逻辑。该文件非常精简（仅约 25 行有效代码），实现了四个公共方法的委托逻辑：`clip`、`draw`、`contains` 和 `asPath`，以及构造函数。每个方法都包含断言检查确保节点已经过验证（无失效状态），然后委托到子类的虚函数实现。

## 架构位置

`GeometryNode` 是 sksg 几何体系的基石，所有具体几何节点（Path、Rect、RRect、Plane、Text、GeometryEffect）都继承自它。

```
Node
└── GeometryNode  ← 当前文件
    ├── Path
    ├── Rect / RRect
    ├── Plane
    ├── Text
    └── GeometryEffect
        ├── TrimEffect, DashEffect, ...
```

GeometryNode 提供了几何体的统一接口，供 Draw 节点和 ClipEffect 使用。它不直接参与渲染（不是 RenderNode），而是作为渲染的数据源。

## 主要类与结构体

（类声明见 `SkSGGeometryNode.h` 文档。）

## 公共 API 函数

### `GeometryNode::clip(canvas, aa)`
```cpp
void GeometryNode::clip(SkCanvas* canvas, bool aa) const {
    SkASSERT(!this->hasInval());
    this->onClip(canvas, aa);
}
```
将几何体设为 Canvas 的裁剪区域。断言确保节点已验证。委托到 `onClip` 虚函数。

### `GeometryNode::draw(canvas, paint)`
```cpp
void GeometryNode::draw(SkCanvas* canvas, const SkPaint& paint) const {
    SkASSERT(!this->hasInval());
    this->onDraw(canvas, paint);
}
```
使用指定画笔绘制几何体到 Canvas。断言确保节点已验证。委托到 `onDraw` 虚函数。

### `GeometryNode::contains(point)`
```cpp
bool GeometryNode::contains(const SkPoint& p) const {
    SkASSERT(!this->hasInval());
    return this->bounds().contains(p.x(), p.y()) ? this->onContains(p) : false;
}
```
检测点是否在几何体内。包含两级检测：
1. 快速的边界矩形检测 (`bounds().contains`)
2. 精确的几何体包含检测 (`onContains`)

边界矩形检测作为快速排除路径，避免了昂贵的精确检测。

### `GeometryNode::asPath()`
```cpp
SkPath GeometryNode::asPath() const {
    SkASSERT(!this->hasInval());
    return this->onAsPath();
}
```
将几何体转换为 SkPath 表示。委托到 `onAsPath` 虚函数。

## 内部实现细节

### 构造函数

```cpp
GeometryNode::GeometryNode() : INHERITED(kBubbleDamage_Trait) {}
```

使用 `kBubbleDamage_Trait` 标志，表示几何节点不直接生成损坏区域。几何节点的损坏通过其聚合祖先（Draw 节点）传播。这是因为几何节点本身不渲染任何内容，只有当 Draw 节点组合几何和画笔后才产生可见输出。

### 断言模式

所有四个方法都以 `SkASSERT(!this->hasInval())` 开头，确保在调用这些方法前已经通过 `revalidate` 更新了节点状态。这是"先验证后使用"契约的运行时检查。

### contains 的两级检测

```cpp
return this->bounds().contains(p.x(), p.y()) ? this->onContains(p) : false;
```

- 第一级：`bounds().contains` 是 O(1) 的矩形包含测试
- 第二级：`onContains` 可能是 O(n) 的路径包含测试（如 `SkPath::contains`）

这种分层检测模式在大量命中测试时能显著减少昂贵的精确测试次数。

## 依赖关系

- `modules/sksg/include/SkSGGeometryNode.h` -- 头文件声明
- `include/core/SkPath.h` -- asPath 返回类型
- `include/core/SkPoint.h` -- contains 参数类型
- `include/core/SkRect.h` -- bounds 返回类型
- `include/private/base/SkAssert.h` -- SkASSERT

## 设计模式与设计决策

1. **非虚公共接口 (NVI)**：公共方法（clip/draw/contains/asPath）是非虚的，执行前置检查（断言）后委托到虚的 `on*` 方法。这是经典的 NVI 模式，确保所有子类都遵守"先验证后使用"的契约。

2. **kBubbleDamage_Trait**：几何节点的损坏不直接报告给 InvalidationController，而是向上冒泡到最近的 Draw 祖先节点。这避免了几何变化时产生不精确的损坏区域（几何本身没有视觉范围，Draw 节点才有）。

3. **快速排除路径**：`contains` 中的边界矩形预检测是一个典型的空间剔除优化。

4. **最小实现**：基类只做委托和断言，不包含任何实际的几何逻辑。所有几何运算都在具体子类中实现。

## 性能考量

- 所有方法的开销仅为断言（Debug 构建中）+ 虚函数调用。Release 构建中断言被移除，开销极小。
- `contains` 的两级检测对于命中测试密集的交互场景（如动画编辑器）非常重要，大部分测试点会被边界矩形快速排除。
- `asPath` 返回 SkPath 值类型，但 SkPath 使用 COW（写时复制）语义，拷贝成本低。
- `kBubbleDamage_Trait` 减少了失效系统中的损坏区域报告数量。

## 相关文件

- `modules/sksg/include/SkSGGeometryNode.h` -- 类声明和虚函数接口
- `modules/sksg/include/SkSGNode.h` -- Node 基类和 kBubbleDamage_Trait
- `modules/sksg/include/SkSGPath.h` -- 最常用的具体几何节点
- `modules/sksg/include/SkSGRect.h` -- Rect/RRect 几何节点
- `modules/sksg/include/SkSGDraw.h` -- Draw 节点（几何节点的消费者）
- `modules/sksg/include/SkSGClipEffect.h` -- ClipEffect（另一个几何节点消费者）
