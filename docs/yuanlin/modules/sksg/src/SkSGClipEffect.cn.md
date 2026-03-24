# SkSGClipEffect 实现 -- 裁剪效果节点实现

> 源文件: `modules/sksg/src/SkSGClipEffect.cpp`

## 概述

`SkSGClipEffect.cpp` 实现了 Skia Scene Graph 中 `ClipEffect` 裁剪效果节点的完整运行时逻辑。该文件包含构造/析构、渲染、命中测试和重新验证四个核心方法的实现。其中最有价值的是 `onRevalidate` 中的 noop 优化逻辑：当子节点完全被裁剪区域包含时，自动跳过裁剪操作以提升渲染性能。

## 架构位置

本文件实现了 `SkSGClipEffect.h` 中声明的 `ClipEffect` 类。在 sksg 模块中，它是效果节点实现的一部分。

```
SkSGClipEffect.cpp
├── ClipEffect::ClipEffect (构造 + 监听裁剪节点)
├── ClipEffect::~ClipEffect (析构 + 解除监听)
├── ClipEffect::onRender (条件裁剪渲染)
├── ClipEffect::onNodeAt (裁剪区域命中测试)
└── ClipEffect::onRevalidate (noop 检测 + 边界交集)
```

## 主要类与结构体

（类声明见头文件文档。）

## 公共 API 函数

（Make 工厂方法在头文件中内联实现，本文件无额外的公共 API。）

## 内部实现细节

### 构造函数

```cpp
ClipEffect::ClipEffect(sk_sp<RenderNode> child, sk_sp<GeometryNode> clip,
                        bool aa, bool force_clip)
    : INHERITED(std::move(child))
    , fClipNode(std::move(clip))
    , fAntiAlias(aa)
    , fForceClip(force_clip) {
    this->observeInval(fClipNode);
}
```

关键细节：
- 子渲染节点传递给 EffectNode 基类
- 裁剪几何节点存储在 `fClipNode` 中
- 通过 `observeInval(fClipNode)` 监听裁剪几何体的变化
- `fAntiAlias` 和 `fForceClip` 为 const 成员，创建后不可更改

### 析构函数

```cpp
ClipEffect::~ClipEffect() {
    this->unobserveInval(fClipNode);
}
```
解除对裁剪节点的失效监听。注意 EffectNode 基类的析构函数会处理子渲染节点的 unobserveInval。

### 渲染实现

```cpp
void ClipEffect::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    SkAutoCanvasRestore acr(canvas, !fNoop);
    if (!fNoop) {
        fClipNode->clip(canvas, fAntiAlias);
    }
    this->INHERITED::onRender(canvas, ctx);
}
```

核心优化逻辑：
1. `SkAutoCanvasRestore` 的第二个参数控制是否实际保存/恢复 Canvas 状态。`!fNoop` 时保存，`fNoop` 时跳过。
2. 非 noop 模式：调用 `fClipNode->clip(canvas, fAntiAlias)` 将裁剪几何体应用到 Canvas。
3. 无论是否 noop，都调用基类的 `onRender` 渲染子节点。

### 命中测试实现

```cpp
const RenderNode* ClipEffect::onNodeAt(const SkPoint& p) const {
    return fClipNode->contains(p) ? this->INHERITED::onNodeAt(p) : nullptr;
}
```

先检查测试点是否在裁剪区域内。不在则直接返回 nullptr（被裁剪的区域不可命中）。GeometryNode::contains 已经包含了快速边界矩形预检测。

### 重新验证实现

```cpp
SkRect ClipEffect::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    SkASSERT(this->hasInval());

    const auto clipBounds = fClipNode->revalidate(ic, ctm);
    auto childBounds = this->INHERITED::onRevalidate(ic, ctm);

    fNoop = !fForceClip && fClipNode->asPath().conservativelyContainsRect(childBounds);

    return childBounds.intersect(clipBounds) ? childBounds : SkRect::MakeEmpty();
}
```

这是本文件最核心的逻辑：

1. **验证裁剪节点**：`fClipNode->revalidate(ic, ctm)` 获取裁剪区域的边界。
2. **验证子节点**：`INHERITED::onRevalidate(ic, ctm)` 获取子渲染节点的边界。
3. **Noop 检测**：
   - 条件：`!fForceClip`（非强制裁剪模式）且裁剪路径保守地包含子节点边界
   - `conservativelyContainsRect` 是快速的保守检测，可能返回 false negative（不优化），但不会返回 false positive（错误跳过裁剪）
4. **边界计算**：返回子节点边界与裁剪边界的交集。如果不相交（`intersect` 返回 false），返回空矩形。

注意 `childBounds.intersect(clipBounds)` 是就地操作，会修改 `childBounds`。

### force_clip 的使用场景

代码注释解释了 `fForceClip` 的必要性：某些情况下裁剪不仅用于视觉效果，还影响 `saveLayer` 缓冲区的大小。即使子节点完全在裁剪区域内，也不能省略裁剪操作，因为省略会导致 `saveLayer` 分配过大的缓冲区。

## 依赖关系

- `modules/sksg/include/SkSGClipEffect.h` -- 头文件声明
- `include/core/SkCanvas.h` -- SkAutoCanvasRestore
- `include/core/SkPath.h` -- conservativelyContainsRect
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode::clip/contains/asPath
- `modules/sksg/include/SkSGNode.h` -- observeInval/unobserveInval

## 设计模式与设计决策

1. **条件裁剪优化**：通过 `fNoop` 标志在 revalidate 时预计算裁剪的必要性，渲染时直接使用缓存结果，避免了渲染期间的昂贵判断。

2. **保守正确性**：`conservativelyContainsRect` 宁可不优化（误认为需要裁剪）也不错误跳过裁剪。这保证了视觉正确性。

3. **SkAutoCanvasRestore 的条件保存**：利用 RAII 对象的布尔参数控制是否实际执行保存/恢复，避免了 noop 路径中不必要的 Canvas 状态操作。

4. **双输入失效管理**：ClipEffect 同时监听子渲染节点（通过 EffectNode 基类）和裁剪几何节点的失效，确保任一变化都触发重新验证。

## 性能考量

- noop 优化在子节点完全被裁剪区域包含时避免了 Canvas 状态保存/恢复和裁剪操作，这在深层场景图中可以显著减少 Canvas 操作次数。
- `conservativelyContainsRect` 通常是 O(n) 复杂度（n 为路径的段数），但对于简单裁剪区域（矩形、圆角矩形）非常快。
- `asPath()` 可能创建路径拷贝，但 SkPath 的 COW 语义使拷贝成本低。
- 命中测试中的 `contains` 使用两级检测（边界矩形 + 精确路径），高效排除远离裁剪区域的点。
- 边界交集计算是简单的矩形运算，开销可忽略。

## 相关文件

- `modules/sksg/include/SkSGClipEffect.h` -- 类声明
- `modules/sksg/src/SkSGEffectNode.cpp` -- EffectNode 基类实现
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 接口
- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode / RenderContext
