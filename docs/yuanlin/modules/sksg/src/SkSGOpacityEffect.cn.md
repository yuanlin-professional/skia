# SkSGOpacityEffect - 场景图不透明度效果节点

> 源文件: `modules/sksg/src/SkSGOpacityEffect.cpp`

## 概述

`SkSGOpacityEffect.cpp` 实现了 Skia 场景图 (sksg) 中的 `OpacityEffect` 类，这是一个用于控制子节点不透明度的渲染效果节点。该类继承自 `RenderNode` 的子类（通过 `INHERITED` 宏引用），通过浮点数 `fOpacity`（范围 0.0~1.0）来调制子节点的渲染透明度。当不透明度为 0 时完全禁用渲染，为 1 时无效果直接透传，中间值则通过 `ScopedRenderContext` 进行不透明度调制。

## 架构位置

`OpacityEffect` 位于 sksg 模块的效果节点层，是场景图 DAG (有向无环图) 中的中间节点。它位于渲染树中父节点和子渲染节点之间，作为一种轻量级的视觉效果修饰器。在 Lottie 动画 (Skottie) 中被广泛用于实现图层和形状的透明度动画。

## 主要类与结构体

### `OpacityEffect`
```cpp
OpacityEffect::OpacityEffect(sk_sp<RenderNode> child, float opacity)
    : INHERITED(std::move(child))
    , fOpacity(opacity) {}
```

- 持有一个子渲染节点和一个不透明度值 `fOpacity`
- 通过继承链管理子节点的生命周期和失效传播

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `OpacityEffect(sk_sp<RenderNode> child, float opacity)` | 构造函数，接受子节点和初始不透明度 |
| `void onRender(SkCanvas*, const RenderContext*) const` | 重写渲染回调，应用不透明度效果 |
| `const RenderNode* onNodeAt(const SkPoint& p) const` | 重写命中测试，透明节点不可命中 |
| `SkRect onRevalidate(InvalidationController*, const SkMatrix&)` | 重写重新验证，完全透明时跳过子 DAG |

## 内部实现细节

### 渲染逻辑 (`onRender`)
```cpp
void OpacityEffect::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    if (fOpacity <= 0) return;           // 完全透明：跳过渲染
    if (fOpacity >= 1) {                 // 完全不透明：直接透传
        this->INHERITED::onRender(canvas, ctx);
        return;
    }
    // 中间值：通过 ScopedRenderContext 调制不透明度
    const auto local_context = ScopedRenderContext(canvas, ctx).modulateOpacity(fOpacity);
    this->INHERITED::onRender(canvas, local_context);
}
```

三个分支分别处理三种情况：
1. **opacity <= 0**: 直接返回，不渲染任何内容
2. **opacity >= 1**: 无修改地委托给父类渲染
3. **0 < opacity < 1**: 创建局部渲染上下文，将不透明度值乘入上下文中

### 命中测试 (`onNodeAt`)
当 `fOpacity > 0` 时委托给父类进行命中测试，否则返回 `nullptr`（不可命中）。

### 重新验证 (`onRevalidate`)
当 `fOpacity <= 0` 时返回空矩形，同时跳过整个子 DAG 的重新验证，这是一个重要的性能优化。

## 依赖关系

- **直接依赖**: `SkSGOpacityEffect.h`（头文件声明）、`SkAssert.h`
- **运行时依赖**: `SkCanvas`、`SkMatrix`、`SkPoint`（前向声明）
- **被使用**: 主要被 Skottie 模块用于实现 After Effects 中的不透明度动画属性

## 设计模式与设计决策

- **装饰器模式**: `OpacityEffect` 装饰单个子渲染节点，在不改变子节点行为的前提下添加不透明度效果
- **短路优化**: 对边界值 (0 和 1) 进行特殊处理，避免不必要的上下文创建和图层操作
- **延迟渲染上下文**: 使用 `ScopedRenderContext` 将不透明度值累积到渲染上下文中，而非立即创建 save layer，这允许多个效果的不透明度进行组合优化
- **子 DAG 剪枝**: 当不透明度为 0 时，`onRevalidate` 跳过整个子 DAG 的重新验证，避免无用计算

## 性能考量

- **零开销透传**: 当 `fOpacity >= 1` 时不创建任何额外对象，直接委托渲染
- **子树剪枝**: `fOpacity <= 0` 时在 revalidation 阶段就跳过整个子树，这对于包含大量隐藏图层的 Lottie 动画非常重要
- **上下文调制 vs. 图层**: 不透明度通过渲染上下文传递而非直接创建 `saveLayer`，这允许在最终渲染时合并多个不透明度修饰，减少 save layer 的数量

## 相关文件

- `modules/sksg/include/SkSGOpacityEffect.h` — 类声明头文件
- `modules/sksg/src/SkSGRenderNode.cpp` — `ScopedRenderContext` 和 `modulateOpacity` 的实现
- `modules/sksg/src/SkSGMaskEffect.cpp` — 类似的渲染效果节点实现
- `modules/skottie/src/layers/` — Skottie 图层中使用 OpacityEffect 的代码
