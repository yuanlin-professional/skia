# SkSGRenderNode -- 可渲染节点基类

> 源文件: `modules/sksg/include/SkSGRenderNode.h`

## 概述

`SkSGRenderNode.h` 定义了 Skia Scene Graph 中所有可渲染节点的基类 `RenderNode` 及其核心的渲染上下文机制 `RenderContext`/`ScopedRenderContext`。`RenderNode` 是场景图中能够在 Canvas 上产生可视输出的节点的共同祖先，提供渲染、命中测试和可见性控制等基础功能。该文件还定义了 `CustomRenderNode`，供外部客户端扩展自定义渲染节点。

## 架构位置

```
Node (场景图节点基类)
└── RenderNode  ← 当前文件（可渲染节点基类）
    ├── EffectNode (效果节点基类)
    │   ├── TransformEffect, ClipEffect, ColorFilter, ...
    ├── Draw (绘制节点)
    ├── Group (组节点)
    └── CustomRenderNode (外部扩展基类)
```

`RenderNode` 是 sksg 渲染体系的基石。它在 `Node` 的基础上增加了渲染、命中测试和可见性管理，同时定义了 `RenderContext` 机制来处理从祖先效果节点累积下来的画笔属性（颜色过滤、着色器、不透明度、混合模式等）。

## 主要类与结构体

### `RenderNode`
```cpp
class RenderNode : public Node {
public:
    void render(SkCanvas*, const RenderContext* = nullptr) const;
    const RenderNode* nodeAt(const SkPoint& point) const;
    bool isVisible() const;
    void setVisible(bool);
protected:
    explicit RenderNode(uint32_t inval_traits = 0);
    virtual void onRender(SkCanvas*, const RenderContext*) const = 0;
    virtual const RenderNode* onNodeAt(const SkPoint& p) const = 0;
};
```

### `RenderContext`
```cpp
struct RenderContext {
    sk_sp<SkColorFilter> fColorFilter;
    sk_sp<SkShader>      fShader;
    sk_sp<SkShader>      fMaskShader;
    sk_sp<SkBlender>     fBlender;
    SkMatrix             fShaderCTM = SkMatrix::I();
    SkMatrix             fMaskCTM   = SkMatrix::I();
    float                fOpacity   = 1;

    bool requiresIsolation() const;
    void modulatePaint(const SkMatrix& ctm, SkPaint*, bool is_layer_paint = false) const;
};
```
渲染上下文，在渲染树的遍历过程中从祖先效果节点累积画笔属性。`requiresIsolation` 检测当前属性组合是否需要内容隔离（saveLayer）。`modulatePaint` 将累积的属性应用到 SkPaint 上。

### `ScopedRenderContext`
```cpp
class ScopedRenderContext final {
public:
    ScopedRenderContext(SkCanvas*, const RenderContext*);
    ~ScopedRenderContext();

    ScopedRenderContext&& modulateOpacity(float opacity);
    ScopedRenderContext&& modulateColorFilter(sk_sp<SkColorFilter>);
    ScopedRenderContext&& modulateShader(sk_sp<SkShader>, const SkMatrix& shader_ctm);
    ScopedRenderContext&& modulateMaskShader(sk_sp<SkShader>, const SkMatrix& ms_ctm);
    ScopedRenderContext&& modulateBlender(sk_sp<SkBlender>);
    ScopedRenderContext&& setIsolation(const SkRect& bounds, const SkMatrix& ctm, bool do_isolate);
    ScopedRenderContext&& setFilterIsolation(const SkRect& bounds, const SkMatrix& ctm,
                                             sk_sp<SkImageFilter>);
};
```
RAII 作用域渲染上下文管理器。提供链式调用的 modulate 方法来累积画笔属性，并在析构时恢复 Canvas 状态。

### `CustomRenderNode`
```cpp
class CustomRenderNode : public RenderNode {
protected:
    explicit CustomRenderNode(std::vector<sk_sp<RenderNode>>&& children);
    ~CustomRenderNode() override;
    const std::vector<sk_sp<RenderNode>>& children() const;
    bool hasChildrenInval() const;
};
```
供外部客户端（非 sksg 内部）使用的自定义渲染节点基类。管理多个子节点的生命周期和失效状态。

## 公共 API 函数

### `RenderNode::render(canvas, ctx)`
将节点及其子节点渲染到 Canvas 上。可选的 `RenderContext` 携带从祖先累积的画笔属性。不可见的节点（`isVisible() == false`）会跳过渲染。

### `RenderNode::nodeAt(point)`
前向到后向命中测试，返回位于指定点的 RenderNode。通常在 Draw 叶节点处停止。

### `RenderNode::isVisible() / setVisible(bool)`
控制节点的可见性。不可见节点不渲染但仍参与 revalidation。

### `RenderContext::requiresIsolation()`
判断当前渲染上下文是否需要内容隔离。当存在非平凡的颜色过滤、着色器或不透明度且需要应用到非原子绘制时，返回 true。

### `RenderContext::modulatePaint(ctm, paint, is_layer_paint)`
将渲染上下文中累积的属性应用到 SkPaint。`is_layer_paint` 标志用于区分是直接绘制画笔还是 saveLayer 画笔。

## 内部实现细节

- **可见性标志**：存储在 Node 基类的 `fNodeFlags` 位字段中，RenderNode 通过友元关系访问。

- **ScopedRenderContext 的移动语义**：所有 modulate 方法返回右值引用（`&&`），支持流畅的链式调用：
  ```cpp
  ScopedRenderContext(canvas, ctx)
      .modulateOpacity(0.5f)
      .modulateColorFilter(cf)
      .setIsolation(bounds, ctm, true);
  ```

- **ScopedRenderContext 禁止堆分配**：`operator new` 被删除，只能作为栈对象使用，保证 RAII 语义。

- **ScopedRenderContext 转移所有权**：移动赋值时通过设置 `fRestoreCount = -1` 使源对象的析构函数成为 noop。

- **着色器 CTM 追踪**：`fShaderCTM` 和 `fMaskCTM` 记录着色器附加时的坐标变换矩阵，用于在最终应用时进行正确的坐标转换。

- **隔离层 (Isolation)**：当 RenderContext 的属性需要应用到包含多个绘制操作的子树时，必须通过 saveLayer 创建隔离层，将属性统一应用到层上而非每个绘制操作。

## 依赖关系

- `modules/sksg/include/SkSGNode.h` -- Node 基类
- `include/core/SkBlender.h` -- SkBlender 类
- `include/core/SkColorFilter.h` -- SkColorFilter 类
- `include/core/SkShader.h` -- SkShader 类
- `include/core/SkMatrix.h` -- 坐标变换矩阵

## 设计模式与设计决策

1. **延迟画笔应用**：RenderContext 不直接修改 Canvas 或 Paint，而是累积属性直到叶节点的绘制时刻。这允许在可能的情况下将多个效果合并到单个 Paint 中，避免不必要的 saveLayer。

2. **RAII 作用域管理**：ScopedRenderContext 通过构造/析构自动管理 Canvas 状态保存和恢复，防止状态泄漏。

3. **内容隔离策略**：`requiresIsolation` 实现了一种启发式判断，只在确实需要时才创建 saveLayer。对于单个原子绘制操作，通常可以直接将效果应用到 Paint 上。

4. **CustomRenderNode 扩展点**：将内部 API（如 `hasChildrenInval`）暴露给外部扩展者，同时保持核心 RenderNode 的封装性。

5. **可见性与失效分离**：不可见节点仍参与 revalidation，确保场景图的缓存状态始终正确，即使节点当前不可见。

## 性能考量

- 延迟画笔应用避免了大量不必要的 saveLayer 创建，这是关键的性能优化。
- `requiresIsolation` 的判断逻辑直接影响 saveLayer 的频率，过于保守会降低性能，过于激进会产生渲染错误。
- ScopedRenderContext 的栈分配策略消除了堆分配开销。
- 可见性检查在 render 入口处进行，不可见的子树完全跳过渲染。
- RenderContext 使用 `sk_sp` 管理 Skia 对象的引用计数，在频繁的 modulate 调用中可能产生引用计数操作开销。

## 相关文件

- `modules/sksg/src/SkSGRenderNode.cpp` -- RenderNode 和 RenderContext 的实现
- `modules/sksg/include/SkSGNode.h` -- Node 基类
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `modules/sksg/include/SkSGDraw.h` -- Draw 叶节点
- `modules/sksg/include/SkSGRenderEffect.h` -- 使用 ScopedRenderContext 的效果节点
- `modules/sksg/include/SkSGColorFilter.h` -- 使用 ScopedRenderContext 的颜色过滤
