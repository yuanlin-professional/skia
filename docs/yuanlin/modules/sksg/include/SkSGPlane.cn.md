# SkSGPlane -- 无限平面几何节点

> 源文件: `modules/sksg/include/SkSGPlane.h`

## 概述

`SkSGPlane.h` 定义了 Skia Scene Graph 中的平面几何节点 `Plane`。`Plane` 表示一个无限大的平面（即整个 Canvas 区域），是最简单的几何节点之一。它没有任何可配置属性，主要用作全屏背景填充或全画布裁剪区域。

## 架构位置

```
Node
└── GeometryNode
    ├── Path, Rect, RRect, Text
    └── Plane  ← 当前文件（表示整个画布）
```

`Plane` 是 `GeometryNode` 的特化实现，代表无界几何体。在几何节点家族中，它是最简单的成员，不需要任何路径或矩形数据来描述形状。

## 主要类与结构体

### `Plane`
```cpp
class Plane final : public GeometryNode {
public:
    static sk_sp<Plane> Make() { return sk_sp<Plane>(new Plane()); }

protected:
    void onClip(SkCanvas*, bool antiAlias) const override;
    void onDraw(SkCanvas*, const SkPaint&) const override;
    bool onContains(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    SkPath onAsPath() const override;

private:
    Plane();
};
```

`Plane` 标记为 `final`，不可继承。私有构造函数，只能通过 `Make` 创建。没有数据成员。

## 公共 API 函数

### `Plane::Make()`
唯一的公共接口，创建一个 Plane 实例。内联实现，直接调用私有构造函数。

## 内部实现细节

- `onDraw` 预期实现为 `canvas->drawPaint(paint)`，即使用 Paint 填充整个 Canvas。
- `onClip` 预期为空操作或裁剪为整个 Canvas，因为无限平面不限制任何区域。
- `onContains` 始终返回 `true`，因为无限平面包含所有点。
- `onRevalidate` 返回极大的边界矩形（或者 `SkRect::MakeLargest()`），表示无限范围。
- `onAsPath` 返回一个极大的矩形路径作为平面的路径表示。

## 依赖关系

- `include/core/SkPath.h` -- `onAsPath` 返回类型
- `include/core/SkRect.h` -- 边界矩形
- `modules/sksg/include/SkSGGeometryNode.h` -- 基类

## 设计模式与设计决策

1. **无状态设计**：Plane 没有任何成员变量，所有实例行为完全相同。这使得它可以被安全地共享。

2. **特化几何体**：虽然可以用一个极大的 Rect 来近似无限平面，但 Plane 通过专用类实现了更清晰的语义和更高效的操作（`drawPaint` 比 `drawRect` 更高效）。

3. **Null Object 模式**：Plane 可以看作裁剪操作的 Null Object -- 当不需要裁剪时使用 Plane 作为裁剪区域，语义上等于"不裁剪"。

## 性能考量

- Plane 没有数据成员，占用最小内存。
- `drawPaint` 操作直接填充整个 Canvas，不需要路径裁剪或几何计算。
- `onContains` 始终返回 true，是 O(1) 操作。
- revalidate 没有实际计算，返回固定值。

## 相关文件

- `modules/sksg/src/SkSGPlane.cpp` -- Plane 的实现
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 基类
- `modules/sksg/include/SkSGRect.h` -- 有界矩形几何节点
- `modules/sksg/include/SkSGDraw.h` -- 与 PaintNode 组合使用
