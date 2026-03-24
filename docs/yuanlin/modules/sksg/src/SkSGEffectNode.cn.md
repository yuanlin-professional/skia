# SkSGEffectNode 实现 -- 效果节点基类实现

> 源文件: `modules/sksg/src/SkSGEffectNode.cpp`

## 概述

`SkSGEffectNode.cpp` 实现了 Skia Scene Graph 中 `EffectNode` 基类的运行时逻辑。作为所有效果节点（变换、裁剪、滤镜、颜色过滤等）的共同基类，`EffectNode` 提供了将渲染、命中测试和重新验证操作透传到单个子节点的默认实现。该文件非常精简，仅包含构造/析构、渲染、命中测试和重新验证四个方法的实现。

## 架构位置

`EffectNode.cpp` 是 sksg 模块中最基础的效果实现文件之一，所有具体效果节点（TransformEffect、ClipEffect、ColorFilter 等）都依赖于它提供的默认行为。

```
SkSGEffectNode.cpp
├── EffectNode::EffectNode (构造 + 失效监听)
├── EffectNode::~EffectNode (析构 + 解除监听)
├── EffectNode::onRender (透传渲染)
├── EffectNode::onNodeAt (透传命中测试)
└── EffectNode::onRevalidate (透传验证)
```

## 主要类与结构体

（类声明见头文件文档。）

## 公共 API 函数

EffectNode 没有公共方法，所有方法都是 protected 或 private。公共接口继承自 RenderNode。

## 内部实现细节

### 构造函数

```cpp
EffectNode::EffectNode(sk_sp<RenderNode> child, uint32_t inval_traits)
    : INHERITED(inval_traits)
    , fChild(std::move(child)) {
    this->observeInval(fChild);
}
```

关键行为：
1. 将 `inval_traits` 传递给 RenderNode 基类（如 `kBubbleDamage_Trait`）。
2. 通过 `std::move` 接管子节点所有权。
3. 调用 `observeInval(fChild)` 注册为子节点的失效观察者，当子节点失效时，效果节点也会被标记为失效。

### 析构函数

```cpp
EffectNode::~EffectNode() {
    this->unobserveInval(fChild);
}
```

解除失效监听关系，防止悬挂指针。这是 RAII 模式在失效系统中的体现。

### 渲染透传

```cpp
void EffectNode::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    fChild->render(canvas, ctx);
}
```

直接将渲染调用委托给子节点，不做任何修改。子类通过覆盖此方法在委托前后添加效果（如 TransformEffect 在调用前 concat 矩阵，ClipEffect 在调用前设置裁剪）。

### 命中测试透传

```cpp
const RenderNode* EffectNode::onNodeAt(const SkPoint& p) const {
    return fChild->nodeAt(p);
}
```

直接将命中测试委托给子节点。子类可覆盖此方法添加坐标变换（如 TransformEffect 映射测试点）或过滤逻辑（如 ClipEffect 检查点是否在裁剪区域内）。

### 重新验证透传

```cpp
SkRect EffectNode::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    SkASSERT(this->hasInval());
    return fChild->revalidate(ic, ctm);
}
```

验证子节点并返回其边界。`SkASSERT(this->hasInval())` 确保此方法只在节点确实失效时被调用。子类可覆盖此方法修改 CTM（如 TransformEffect 组合自己的变换矩阵）或修改返回的边界。

## 依赖关系

- `modules/sksg/include/SkSGEffectNode.h` -- 头文件声明
- `modules/sksg/include/SkSGNode.h` -- Node 基类（observeInval/unobserveInval）
- `include/private/base/SkAssert.h` -- SkASSERT 断言

## 设计模式与设计决策

1. **透明装饰器**：默认实现完全透明，不修改任何行为。这是"零代价抽象"的体现——如果子类不覆盖任何方法，EffectNode 等价于不存在。

2. **RAII 失效管理**：构造时 observe，析构时 unobserve，保证失效关系的生命周期正确性。

3. **断言保护**：`SkASSERT(this->hasInval())` 确保 revalidate 不会在已验证的节点上被无效调用，有助于调试失效传播问题。

4. **非虚析构的间接保护**：虽然 `EffectNode::~EffectNode` 不是虚函数本身，但它覆盖了 Node 的虚析构函数，确保通过基类指针删除时正确调用。

## 性能考量

- 透传实现的开销仅为虚函数调用 + 函数调用开销，通常可以被内联优化。
- `observeInval`/`unobserveInval` 维护了一个简单的观察者列表（Node 内部的 union 实现），单观察者时为直接指针，多观察者时为 vector。
- `fChild->render` 和 `fChild->revalidate` 是虚函数调用，无法被编译器去虚化。
- 整个文件的实现非常精简（约 25 行有效代码），是 sksg 模块中最轻量的实现文件之一。

## 相关文件

- `modules/sksg/include/SkSGEffectNode.h` -- 类声明
- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode 基类
- `modules/sksg/include/SkSGNode.h` -- Node 基类和失效机制
- `modules/sksg/src/SkSGTransform.cpp` -- TransformEffect 子类实现
- `modules/sksg/src/SkSGClipEffect.cpp` -- ClipEffect 子类实现
- `modules/sksg/src/SkSGColorFilter.cpp` -- ColorFilter 子类实现
