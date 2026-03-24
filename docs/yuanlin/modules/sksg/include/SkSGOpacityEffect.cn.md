# SkSGOpacityEffect

> 源文件: modules/sksg/include/SkSGOpacityEffect.h

## 概述

SkSGOpacityEffect 是 Skia 场景图中的效果节点，用于对渲染节点应用不透明度（opacity）控制。它通过修改 Alpha 通道来实现渐隐渐显、透明度动画等视觉效果。OpacityEffect 是场景图中最常用的效果之一，广泛应用于 UI 动画、淡入淡出过渡等场景。

该效果节点继承自 EffectNode，包装一个子渲染节点，并在渲染时应用指定的不透明度值。不透明度值范围为 0.0（完全透明）到 1.0（完全不透明）。

## 架构位置

在 Skia 场景图架构中的位置：

- **继承关系**: OpacityEffect → EffectNode → RenderNode → Node
- **功能定位**: 简单效果节点，控制子节点的透明度
- **输入**: 一个子渲染节点 + 不透明度值
- **输出**: 应用透明度后的渲染结果
- **模块位置**: modules/sksg 效果系统

OpacityEffect 是效果系统中最轻量和常用的效果，相比 MaskEffect 等复杂效果，实现和性能都更简单高效。

## 主要类与结构体

### OpacityEffect 类

```cpp
class OpacityEffect final : public EffectNode {
public:
    static sk_sp<OpacityEffect> Make(sk_sp<RenderNode> child, float opacity = 1);

    SG_ATTRIBUTE(Opacity, float, fOpacity)

protected:
    OpacityEffect(sk_sp<RenderNode>, float);

    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    float fOpacity;

    using INHERITED = EffectNode;
};
```

**关键成员**:
- `fOpacity`: 不透明度值（0.0 - 1.0）

**设计特点**:
- 终态类（final），不可继承
- 使用 SG_ATTRIBUTE 宏提供属性访问
- 构造函数受保护，强制使用工厂方法

## 公共 API 函数

### Make()
```cpp
static sk_sp<OpacityEffect> Make(sk_sp<RenderNode> child, float opacity = 1);
```
创建不透明度效果节点。

**参数**:
- `child`: 被应用效果的子节点
- `opacity`: 初始不透明度值（默认 1.0，完全不透明）

**返回**: 智能指针，如果 child 为空则返回 nullptr

**使用示例**:
```cpp
auto image = sksg::Image::Make(photo);
auto fadeOut = sksg::OpacityEffect::Make(image, 0.5);  // 50% 透明
```

### getOpacity() / setOpacity()
```cpp
float getOpacity() const;
void setOpacity(float v);
```
通过 SG_ATTRIBUTE 宏生成的属性访问器。

**setOpacity 行为**:
- 检查新值是否与当前值不同
- 若不同，更新 fOpacity 并调用 invalidate()
- 触发场景图重新渲染

**常见用法**:
```cpp
// 动画透明度
for (float t = 0; t <= 1.0; t += 0.01) {
    opacityEffect->setOpacity(t);
    renderScene();
}
```

## 内部实现细节

### 渲染实现 (onRender)

透明度应用的典型实现：

```cpp
void OpacityEffect::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    if (fOpacity >= 1.0f) {
        // 优化：完全不透明，直接渲染子节点
        fChild->render(canvas, ctx);
        return;
    }

    if (fOpacity <= 0.0f) {
        // 优化：完全透明，跳过渲染
        return;
    }

    // 创建带透明度的图层
    SkPaint layerPaint;
    layerPaint.setAlphaf(fOpacity);
    canvas->saveLayer(nullptr, &layerPaint);

    // 渲染子节点到图层
    fChild->render(canvas, ctx);

    // 恢复图层，应用透明度
    canvas->restore();
}
```

**关键优化**:
1. 完全不透明时避免 saveLayer 开销
2. 完全透明时跳过渲染
3. 中间值时使用 saveLayer 应用透明度

### 边界计算 (onRevalidate)

```cpp
SkRect OpacityEffect::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    // 透明度不改变几何边界，直接返回子节点边界
    return fChild->revalidate(ic, ctm);
}
```

不透明度效果不影响节点的几何边界，只影响视觉外观。

### 命中测试 (onNodeAt)

```cpp
const RenderNode* OpacityEffect::onNodeAt(const SkPoint& p) const {
    // 即使透明，命中测试通常仍然有效
    // 具体行为可能根据 opacity 值调整
    if (fOpacity <= 0) {
        return nullptr;  // 完全透明不响应交互
    }
    return fChild->nodeAt(p);
}
```

**设计决策**: 接近透明或完全透明的节点是否响应交互可配置。

## 依赖关系

### 核心依赖
- **include/core/SkRect.h**: 边界框
- **include/core/SkRefCnt.h**: 引用计数
- **modules/sksg/include/SkSGEffectNode.h**: 效果节点基类
- **modules/sksg/include/SkSGNode.h**: SG_ATTRIBUTE 宏
- **modules/sksg/include/SkSGRenderNode.h**: 渲染节点

### 渲染依赖
- **SkCanvas**: saveLayer、restore 等 API
- **SkMatrix**: 变换矩阵
- **SkPoint**: 点坐标

### 场景图依赖
- **InvalidationController**: 失效管理

### 标准库
- **<utility>**: std::move

## 设计模式与设计决策

### 1. 终态类设计
声明为 final：
- 不透明度逻辑简单直接
- 不需要进一步扩展
- 优化虚函数调用

### 2. 默认完全不透明
构造函数默认 opacity = 1：
- 符合大多数使用场景
- 避免意外创建透明节点
- 明确的初始状态

### 3. 值语义的 Opacity
fOpacity 直接存储为 float：
- 轻量级数据
- 无需间接访问
- 简单高效

### 4. 属性宏集成
使用 SG_ATTRIBUTE 宏：
- 自动生成 getter/setter
- 自动集成失效机制
- 与其他节点属性风格一致

### 5. 空检查保护
Make() 检查 child 有效性：
- 防止空指针异常
- 返回 nullptr 允许调用者处理
- 防御性编程

## 性能考量

### 1. saveLayer 开销
创建图层是昂贵操作：
- 分配离屏表面
- 额外的绘制通道
- Alpha 合成操作

**优化策略**:
- 完全不透明时避免 saveLayer
- 完全透明时跳过渲染
- 考虑硬件加速支持

### 2. 边界透传
不改变边界，直接返回子节点边界：
- 零额外计算开销
- 重验证效率高

### 3. 失效最小化
属性检查避免不必要失效：
- setOpacity 检查值是否改变
- 相同值不触发失效
- 减少渲染次数

### 4. 透明度动画优化
频繁改变透明度的场景：
- 每次改变都触发重绘
- 考虑使用专用的透明度动画器
- GPU 加速可显著提升性能

### 5. 与其他效果组合
OpacityEffect 可与其他效果嵌套：
- 多层 saveLayer 累积开销
- 考虑合并效果减少图层数
- 平衡效果丰富度和性能

## 相关文件

### 头文件
- **modules/sksg/include/SkSGEffectNode.h**: EffectNode 基类
- **modules/sksg/include/SkSGNode.h**: Node 基类和宏
- **modules/sksg/include/SkSGRenderNode.h**: RenderNode 定义

### 实现文件
- **modules/sksg/src/SkSGOpacityEffect.cpp**: OpacityEffect 实现

### 相关效果节点
- **SkSGMaskEffect.h**: 遮罩效果（更复杂的透明度控制）
- **SkSGClipEffect.h**: 裁剪效果
- **SkSGBlurEffect.h**: 模糊效果（可能存在）
- **SkSGTransformEffect.h**: 变换效果

### 使用场景
- **modules/skottie**: Lottie 动画中的透明度动画
- UI 淡入淡出过渡
- 鼠标悬停高亮效果
- 加载动画中的脉冲效果

### 示例用法
```cpp
// 淡入动画
auto content = sksg::Group::Make({image, text});
auto fadeIn = sksg::OpacityEffect::Make(content, 0.0);

// 动画循环
for (float t = 0; t <= 1.0; t += 0.05) {
    fadeIn->setOpacity(t);
    scene->render(canvas);
}

// 交互式透明度
void onMouseHover(bool hovering) {
    hoverEffect->setOpacity(hovering ? 0.7 : 1.0);
}

// 嵌套效果
auto masked = sksg::MaskEffect::Make(content, mask);
auto faded = sksg::OpacityEffect::Make(masked, 0.5);
```

## 相关概念

### Alpha 合成
OpacityEffect 基于 Alpha 合成理论：
- Porter-Duff 合成运算符
- 预乘 Alpha vs 非预乘 Alpha
- 图层混合模式

### 透明度 vs 可见性
- Opacity = 0：不可见但占据空间
- 完全移除节点：不占据空间
- 根据场景选择合适方式

### 性能 vs 质量
- saveLayer 提供正确的 Alpha 合成
- 某些情况可用混合模式模拟（不精确但快）
- 硬件加速可两全其美
