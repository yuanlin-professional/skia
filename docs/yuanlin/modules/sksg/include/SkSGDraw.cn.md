# SkSGDraw -- 绘制节点

> 源文件: `modules/sksg/include/SkSGDraw.h`

## 概述

`SkSGDraw.h` 定义了 Skia Scene Graph 中的核心绘制节点 `Draw`。`Draw` 是场景图中实际执行绘制操作的叶渲染节点，它将一个 `GeometryNode`（几何体）和一个 `PaintNode`（画笔）组合在一起，对应于 Skia 中 `SkCanvas::drawFoo(foo, paint)` 风格的绘制调用。它是场景图 DAG 从数据描述到像素输出的关键桥梁。

## 架构位置

```
Node
└── RenderNode
    ├── EffectNode (效果链)
    │   └── ...
    └── Draw  ← 当前文件（叶绘制节点）
        ├── fGeometry → GeometryNode (几何数据)
        └── fPaint    → PaintNode (画笔数据)
```

`Draw` 是 `RenderNode` 的直接子类（非 EffectNode 子类），是场景图渲染的终端节点。它从两个数据源节点（GeometryNode 和 PaintNode）获取绘制参数，在渲染时组合两者调用 Canvas API。

## 主要类与结构体

### `Draw`
```cpp
class Draw : public RenderNode {
public:
    static sk_sp<Draw> Make(sk_sp<GeometryNode> geo, sk_sp<PaintNode> paint) {
        return (geo && paint) ? sk_sp<Draw>(new Draw(std::move(geo), std::move(paint)))
                              : nullptr;
    }

protected:
    Draw(sk_sp<GeometryNode>, sk_sp<PaintNode> paint);
    ~Draw() override;

    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    sk_sp<GeometryNode> fGeometry;
    sk_sp<PaintNode>    fPaint;
};
```

注意 `Draw` 没有标记为 `final`，理论上可以被继承扩展。

## 公共 API 函数

### `Draw::Make(geo, paint)`
工厂方法，创建绘制节点。接受几何节点和画笔节点，两者都不能为空。返回 `sk_sp<Draw>` 或 nullptr。

## 内部实现细节

- **双数据源**：Draw 同时持有 GeometryNode 和 PaintNode，在构造和析构时分别 `observeInval`/`unobserveInval` 两个数据源。任一数据源变化都会触发 Draw 节点失效。

- **渲染流程**：`onRender` 从 PaintNode 获取 SkPaint，从 RenderContext 获取附加的渲染属性（颜色过滤、着色器、不透明度等），然后调用 GeometryNode 的 `draw(canvas, paint)` 方法。

- **命中测试**：`onNodeAt` 通过 GeometryNode 的 `contains(point)` 方法检测点是否在几何体内。如果命中，返回 `this`（Draw 本身作为命中目标）。

- **边界计算**：`onRevalidate` 先 revalidate 两个数据源节点，然后返回几何节点的边界。

- **RenderContext 集成**：Draw 是 RenderContext 效果累积链的终端。在渲染时，从祖先效果节点累积下来的颜色过滤、着色器、不透明度等会通过 `RenderContext::modulatePaint` 应用到画笔上。

## 依赖关系

- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode 基类和 RenderContext
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 几何数据源
- `modules/sksg/include/SkSGPaint.h` -- PaintNode 画笔数据源
- `include/core/SkRect.h` -- 边界矩形

## 设计模式与设计决策

1. **组合模式**：Draw 组合了几何和画笔两个独立维度，而非将它们融合在一起。这允许同一个几何体与不同画笔配对，或同一画笔用于不同几何体。

2. **叶节点定位**：Draw 是渲染 DAG 的叶节点，不接受子渲染节点。所有效果应通过祖先的 EffectNode 应用。

3. **对应 Canvas API**：设计注释明确指出"Think Skia SkCanvas::drawFoo(foo, paint) calls"，Draw 的设计直接对应 Canvas 的绘制语义。

4. **非 final 类**：Draw 没有标记为 final，留有扩展可能性，但当前代码库中似乎没有子类。

## 性能考量

- Draw 是渲染链的终端，每帧可能被大量调用。其渲染路径应尽可能轻量。
- 两个数据源的 revalidation 是独立的，但在 Draw 的 `onRevalidate` 中串行执行。
- RenderContext 的 modulatePaint 可能需要创建复合的颜色过滤或着色器，产生一定开销。
- 如果 RenderContext 需要内容隔离（requiresIsolation），Draw 的渲染会触发 saveLayer。

## 相关文件

- `modules/sksg/src/SkSGDraw.cpp` -- Draw 的实现
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 基类
- `modules/sksg/include/SkSGPaint.h` -- PaintNode（Color 等）
- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode 和 RenderContext
- `modules/sksg/include/SkSGPath.h` -- 常用的几何体类型
- `modules/sksg/include/SkSGRect.h` -- 常用的几何体类型
