# SkSGClipEffect -- 裁剪效果节点

> 源文件: `modules/sksg/include/SkSGClipEffect.h`

## 概述

`SkSGClipEffect.h` 定义了 Skia Scene Graph 中的裁剪效果节点 `ClipEffect`。该节点将一个 `GeometryNode` 作为裁剪区域应用到其子渲染节点上，限制子节点的可见范围。它支持抗锯齿裁剪和强制裁剪模式，并包含一个优化机制：当子节点完全位于裁剪区域内时，自动跳过裁剪操作。

## 架构位置

`ClipEffect` 在 sksg 节点层次中的位置：

```
Node
└── RenderNode
    └── EffectNode
        └── ClipEffect (裁剪效果)
            ├── fChild (继承自 EffectNode 的子渲染节点)
            └── fClipNode (裁剪几何体)
```

ClipEffect 是 `EffectNode` 的子类，接受两个输入：一个子渲染节点（来自 EffectNode 基类）和一个裁剪几何节点。在渲染时，先将裁剪几何体设置为 Canvas 的裁剪区域，再渲染子节点。

## 主要类与结构体

### `ClipEffect`
```cpp
class ClipEffect final : public EffectNode {
public:
    static sk_sp<ClipEffect> Make(sk_sp<RenderNode> child, sk_sp<GeometryNode> clip,
                                  bool aa = false, bool force_clip = false);
    ~ClipEffect() override;
protected:
    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
private:
    const sk_sp<GeometryNode> fClipNode;
    const bool fAntiAlias, fForceClip;
    bool fNoop = false;
};
```

## 公共 API 函数

### `ClipEffect::Make(child, clip, aa, force_clip)`
工厂方法，创建裁剪效果节点。

- `child`: 被裁剪的子渲染节点（不可为空）
- `clip`: 裁剪几何体（不可为空）
- `aa`: 是否使用抗锯齿裁剪（默认 false）
- `force_clip`: 是否强制裁剪，禁用 noop 优化（默认 false）

两个输入都不能为空，否则返回 nullptr。

## 内部实现细节

- **裁剪 noop 优化**：在 `onRevalidate` 中，如果子节点边界完全包含在裁剪路径内（通过 `SkPath::conservativelyContainsRect` 检测），则设置 `fNoop = true`，渲染时跳过裁剪操作。这是一个保守检测——可能存在误报（不优化），但不会漏报。

- **force_clip 模式**：某些场景需要裁剪不仅用于视觉效果，还用于确定 saveLayer 缓冲区大小。此时即使子节点在裁剪区域内，也不能省略裁剪。`fForceClip` 标志禁用 noop 优化。

- **边界计算**：`onRevalidate` 返回子节点边界与裁剪边界的交集。如果不相交，返回空矩形。

- **命中测试**：`onNodeAt` 先检查点是否在裁剪区域内，不在则直接返回 nullptr，避免不必要的子节点遍历。

- **Canvas 状态管理**：`onRender` 使用 `SkAutoCanvasRestore` 在非 noop 模式下保存/恢复 Canvas 状态。

## 依赖关系

- `modules/sksg/include/SkSGEffectNode.h` -- 基类 EffectNode
- `modules/sksg/include/SkSGGeometryNode.h` -- 裁剪几何体类型
- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode / RenderContext
- `include/core/SkRect.h` -- 边界矩形

## 设计模式与设计决策

1. **双输入效果节点**：不同于大多数 EffectNode 只有一个子节点，ClipEffect 额外持有一个 GeometryNode 作为裁剪源，形成 DAG 中的多输入结构。

2. **保守优化**：noop 检测使用 `conservativelyContainsRect`，优先保证正确性（宁可不优化也不错误跳过裁剪）。

3. **const 布尔成员**：`fAntiAlias` 和 `fForceClip` 为 `const`，创建后不可更改，避免运行时意外修改裁剪行为。

4. **失效观察**：构造时 `observeInval(fClipNode)` 监听裁剪几何体的变化，析构时 `unobserveInval` 解除监听。

## 性能考量

- noop 优化在子节点完全被裁剪区域包含时避免了不必要的 Canvas 裁剪操作和状态保存/恢复。
- `conservativelyContainsRect` 是一个快速的保守检测，不涉及复杂的路径运算。
- 命中测试中的 `fClipNode->contains(p)` 提前剔除了裁剪区域外的测试点。
- 抗锯齿裁剪（`aa = true`）比非抗锯齿裁剪有额外的性能开销。

## 相关文件

- `modules/sksg/src/SkSGClipEffect.cpp` -- ClipEffect 的实现
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 基类
- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode 和 RenderContext
