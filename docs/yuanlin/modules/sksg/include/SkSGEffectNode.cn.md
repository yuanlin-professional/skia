# SkSGEffectNode -- 效果节点基类

> 源文件: `modules/sksg/include/SkSGEffectNode.h`

## 概述

`SkSGEffectNode.h` 定义了 Skia Scene Graph 中所有效果节点的基类 `EffectNode`。效果节点是一种中间渲染节点，持有一个子 `RenderNode`，在渲染子节点时可以应用各种变换或修改（如裁剪、变换、滤镜、颜色过滤等）。`EffectNode` 提供默认的透传实现，子类通过覆盖相关虚函数来注入特定效果。

## 架构位置

```
Node
└── RenderNode
    └── EffectNode  ← 当前文件
        ├── TransformEffect (变换)
        ├── ClipEffect (裁剪)
        ├── ColorFilter (颜色过滤)
        ├── ShaderEffect (着色器)
        ├── ImageFilterEffect (图像滤镜)
        ├── MaskShaderEffect (遮罩着色器)
        ├── BlenderEffect (混合器)
        └── LayerEffect (图层)
```

`EffectNode` 是场景图中效果链的核心抽象。它实现了单子节点的装饰器模式，默认行为是完全透传渲染、命中测试和边界计算，子类只需覆盖需要修改的行为。

## 主要类与结构体

### `EffectNode`
```cpp
class EffectNode : public RenderNode {
protected:
    explicit EffectNode(sk_sp<RenderNode>, uint32_t inval_traits = 0);
    ~EffectNode() override;

    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

    const sk_sp<RenderNode>& getChild() const { return fChild; }

private:
    sk_sp<RenderNode> fChild;
};
```

## 公共 API 函数

`EffectNode` 没有公共 API 方法，它是一个 `protected` 构造的基类，不能直接实例化。所有公共接口继承自 `RenderNode`（`render`、`nodeAt`、`isVisible`/`setVisible`）。

### 受保护的接口

#### `EffectNode(child, inval_traits)`
构造函数，接受子渲染节点和可选的失效特征标志。自动调用 `observeInval(fChild)` 监听子节点的失效事件。

#### `getChild()`
返回子节点的引用，供子类访问。

#### `onRender(canvas, ctx)`
默认实现：直接将渲染委托给子节点 `fChild->render(canvas, ctx)`。

#### `onNodeAt(point)`
默认实现：直接将命中测试委托给子节点 `fChild->nodeAt(p)`。

#### `onRevalidate(ic, ctm)`
默认实现：验证子节点并返回其边界 `fChild->revalidate(ic, ctm)`。

## 内部实现细节

- 构造时通过 `observeInval(fChild)` 建立失效监听关系，析构时通过 `unobserveInval(fChild)` 解除。
- `inval_traits` 参数传递给 `RenderNode` 基类，允许效果节点自定义失效行为（如 `kBubbleDamage_Trait`）。
- `fChild` 是非 const 的 `sk_sp`，理论上可以更改（但当前没有公开的修改接口）。
- 所有虚函数都提供了透传默认实现，子类可以选择性地覆盖需要的方法。

## 依赖关系

- `modules/sksg/include/SkSGRenderNode.h` -- 基类 RenderNode
- `include/core/SkRect.h` -- 边界矩形
- `include/core/SkRefCnt.h` -- `sk_sp` 智能指针

## 设计模式与设计决策

1. **装饰器模式**：EffectNode 是经典的装饰器，包装子节点并可选地修改其行为。默认透传保证了子类只需关注差异部分。

2. **protected 构造**：不能直接实例化 EffectNode，必须使用具体子类，体现了抽象基类的设计意图。

3. **单子节点**：每个 EffectNode 只有一个子节点，形成简单的链式结构。需要多子节点的场景使用 Group 节点。

4. **可配置的失效特征**：`inval_traits` 允许子类在构造时声明其失效行为特征，而非在运行时动态配置。

## 性能考量

- 默认透传实现几乎零开销，只有虚函数调用的开销。
- 失效监听机制确保只有在子节点实际变化时才触发效果节点的重新验证。
- 效果链的深度直接影响渲染和 revalidation 的递归调用深度。
- `getChild()` 返回引用而非拷贝，避免 `sk_sp` 的引用计数操作。

## 相关文件

- `modules/sksg/src/SkSGEffectNode.cpp` -- EffectNode 的实现
- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode 基类
- `modules/sksg/include/SkSGTransform.h` -- TransformEffect 子类
- `modules/sksg/include/SkSGClipEffect.h` -- ClipEffect 子类
- `modules/sksg/include/SkSGRenderEffect.h` -- ShaderEffect/ImageFilterEffect 等子类
- `modules/sksg/include/SkSGColorFilter.h` -- ColorFilter 子类
