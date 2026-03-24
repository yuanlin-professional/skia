# SkSGColorFilter -- 颜色过滤效果节点

> 源文件: `modules/sksg/include/SkSGColorFilter.h`

## 概述

`SkSGColorFilter.h` 定义了 Skia Scene Graph 中的颜色过滤效果体系。包含抽象基类 `ColorFilter`、外部颜色过滤包装器 `ExternalColorFilter`、混合模式颜色过滤 `ModeColorFilter` 以及渐变色调映射过滤 `GradientColorFilter`。这些节点在渲染时对子节点的颜色输出进行修改，常用于实现 Lottie 动画中的色彩效果（如调色、染色、色调映射等）。

## 架构位置

```
Node
└── RenderNode
    └── EffectNode
        ├── ColorFilter (颜色过滤基类)
        │   ├── ModeColorFilter (混合模式颜色过滤)
        │   └── GradientColorFilter (渐变色调映射)
        └── ExternalColorFilter (外部颜色过滤包装)
```

注意 `ColorFilter` 和 `ExternalColorFilter` 都继承自 `EffectNode`，但它们之间没有继承关系。`ColorFilter` 使用模板方法模式管理 `SkColorFilter` 缓存，而 `ExternalColorFilter` 直接持有外部提供的 `SkColorFilter`。

## 主要类与结构体

### `ColorFilter` (抽象基类)
```cpp
class ColorFilter : public EffectNode {
protected:
    explicit ColorFilter(sk_sp<RenderNode>);
    void onRender(SkCanvas*, const RenderContext*) const final;
    const RenderNode* onNodeAt(const SkPoint&) const final;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) final;
    virtual sk_sp<SkColorFilter> onRevalidateFilter() = 0;
private:
    sk_sp<SkColorFilter> fColorFilter;
};
```
颜色过滤基类，所有渲染相关虚函数为 `final`，子类只需实现 `onRevalidateFilter` 返回具体的 `SkColorFilter`。

### `ExternalColorFilter`
```cpp
class ExternalColorFilter final : public EffectNode {
public:
    static sk_sp<ExternalColorFilter> Make(sk_sp<RenderNode> child);
    enum class Coverage { kNormal, kBoundingBox };
    SG_ATTRIBUTE(ColorFilter, sk_sp<SkColorFilter>, fColorFilter)
    SG_ATTRIBUTE(Coverage, Coverage, fCoverage)
};
```
外部颜色过滤包装器，允许直接设置 `SkColorFilter` 对象。`Coverage` 枚举控制效果的覆盖范围：`kNormal` 仅应用于实际内容，`kBoundingBox` 扩展到整个边界框（用于需要全区域颜色效果的场景）。

### `ModeColorFilter`
```cpp
class ModeColorFilter final : public ColorFilter {
public:
    static sk_sp<ModeColorFilter> Make(sk_sp<RenderNode> child,
                                       sk_sp<Color> color, SkBlendMode mode);
private:
    const sk_sp<Color> fColor;
    const SkBlendMode fMode;
};
```
使用指定颜色和混合模式创建颜色过滤。内部使用 `SkColorFilters::Blend` 实现。Color 节点参与场景图的失效机制，颜色变化时自动更新过滤器。

### `GradientColorFilter`
```cpp
class GradientColorFilter final : public ColorFilter {
public:
    static sk_sp<GradientColorFilter> Make(sk_sp<RenderNode> child,
                                           sk_sp<Color> c0, sk_sp<Color> c1);
    static sk_sp<GradientColorFilter> Make(sk_sp<RenderNode> child,
                                           std::vector<sk_sp<Color>>);
    SG_ATTRIBUTE(Weight, float, fWeight)
private:
    const std::vector<sk_sp<Color>> fColors;
    float fWeight = 0;
};
```
色调/多色调映射过滤器。根据输入像素的亮度将 RGB 颜色映射到颜色梯度上，然后按 `Weight` 权重与原始颜色混合。支持 2 色和多色两种模式。

## 公共 API 函数

### `ExternalColorFilter::Make(child)`
创建外部颜色过滤包装器，之后通过 `setColorFilter` 设置具体的过滤器。

### `ModeColorFilter::Make(child, color, mode)`
创建混合模式颜色过滤，需要子节点、颜色节点和混合模式三个参数。

### `GradientColorFilter::Make(child, c0, c1)` / `Make(child, colors)`
创建渐变色调映射，支持双色和多色两种形式。至少需要 2 个颜色。

### 属性访问器
- `ExternalColorFilter`: `getColorFilter/setColorFilter`, `getCoverage/setCoverage`
- `GradientColorFilter`: `getWeight/setWeight` -- 控制效果强度（0 = 无效果，1 = 完全映射）

## 内部实现细节

- **ColorFilter 的 RenderContext 调制**：`onRender` 使用 `ScopedRenderContext::modulateColorFilter` 将颜色过滤累积到 RenderContext 中，延迟到实际绘制时应用。这种延迟机制允许在某些情况下将颜色过滤直接合并到 Paint 上，避免创建不必要的 saveLayer。

- **ColorFilter 的 onRevalidate**：先调用 `onRevalidateFilter()` 获取子类创建的 `SkColorFilter` 并缓存到 `fColorFilter`，然后调用基类的 `onRevalidate` 验证子渲染节点。

- **ColorFilter 的 onNodeAt**：当前实现直接委托给基类（即子节点），源码中有 TODO 注释表明可能需要更复杂的逻辑来处理颜色过滤对命中测试的影响。

- **ExternalColorFilter 的 BoundingBox Coverage**：在 kBoundingBox 模式下，执行三步操作：(1) `canvas->save()` 保存状态；(2) `canvas->clipRect` 裁剪到内容边界；(3) `setIsolation` 创建隔离层。这确保了颜色过滤应用到整个边界框区域（包括透明区域），而非仅应用于有内容的像素。

- **GradientColorFilter 双路径实现**：
  - 2 色渐变使用颜色矩阵实现：将 BT.709 亮度计算（L = 0.2126*R + 0.7152*G + 0.0722*B）和颜色插值合并为一个 5x4 矩阵
  - 多色渐变（3+）使用查找表实现：构建 3 个 256 字节的 R/G/B 查找表，每个区间内线性插值，然后与亮度矩阵组合

- **GradientColorFilter 的 Weight 控制**：使用 `SkColorFilters::Lerp(weight, nullptr, gradientCF)` 实现。`nullptr` 作为第一个过滤器表示恒等变换（原始颜色），weight=0 时完全使用原始颜色，weight=1 时完全使用映射后的颜色。weight<=0 时短路返回 nullptr，完全跳过效果。

- **失效观察**：ModeColorFilter 和 GradientColorFilter 在构造时 `observeInval` 其所有 Color 节点，析构时 `unobserveInval`。颜色值的任何变化都会触发过滤器重建。GradientColorFilter 对颜色向量中的每个 Color 节点都单独建立监听关系。

## 依赖关系

- `include/core/SkColorFilter.h` -- SkColorFilter 类
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `modules/sksg/include/SkSGNode.h` -- SG_ATTRIBUTE 宏
- `modules/sksg/include/SkSGPaint.h` -- Color 节点（ModeColorFilter/GradientColorFilter 使用）

## 设计模式与设计决策

1. **模板方法模式**：ColorFilter 基类定义了缓存更新和渲染应用的完整流程（final），子类只需实现 `onRevalidateFilter` 创建逻辑。

2. **内部/外部二分法**：ColorFilter 用于场景图内部管理的过滤器，ExternalColorFilter 用于外部提供的过滤器。后者直接继承 EffectNode 而非 ColorFilter。

3. **Color 节点作为动态输入**：ModeColorFilter 和 GradientColorFilter 使用 Color 场景图节点而非静态 SkColor 值，支持颜色的动画化。

4. **权重混合**：GradientColorFilter 的 Weight 属性允许在原始颜色和映射后颜色之间平滑过渡，支持效果强度动画。

## 性能考量

- **SkColorFilter 缓存**：ColorFilter 基类在 `onRevalidate` 中缓存 `SkColorFilter` 对象，避免每帧重建。只有当节点被标记为失效时才会调用 `onRevalidateFilter` 重新创建。

- **2 色 vs 多色算法选择**：2 色渐变使用颜色矩阵实现，这是一个 GPU 非常友好的操作（单次矩阵向量乘法）。多色渐变使用查找表，需要额外的纹理采样或内存查找。系统根据颜色数量自动选择最优路径。

- **ExternalColorFilter 的 BoundingBox 开销**：kBoundingBox 模式需要额外的 `canvas->save()`、`clipRect` 和 `setIsolation`（创建 saveLayer）操作。saveLayer 是相对昂贵的操作，涉及临时缓冲区分配和后续的合成步骤。

- **GradientColorFilter 的颜色 revalidation**：所有 Color 节点的 revalidation 在 `onRevalidateFilter` 中串行执行。对于 N 个颜色节点，开销为 O(N)。

- **Weight 短路优化**：`fWeight <= 0` 时 GradientColorFilter 返回 nullptr（无过滤器），完全跳过颜色过滤效果。这对于效果强度动画从 0 开始的场景非常重要。

- **RenderContext 延迟应用**：颜色过滤通过 RenderContext 累积而非直接应用到 Canvas，允许在叶节点的 Draw 中将多个效果合并到单个 Paint，避免不必要的 saveLayer 创建。

## 相关文件

- `modules/sksg/src/SkSGColorFilter.cpp` -- 各过滤器的实现
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `modules/sksg/include/SkSGPaint.h` -- Color 节点
- `modules/sksg/include/SkSGRenderEffect.h` -- 其他渲染效果
- `modules/sksg/include/SkSGRenderNode.h` -- RenderContext / ScopedRenderContext
