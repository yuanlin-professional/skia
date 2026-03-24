# SkSGRenderNode - 场景图渲染节点基类与渲染上下文

> 源文件: `modules/sksg/src/SkSGRenderNode.cpp`

## 概述

`SkSGRenderNode.cpp` 实现了 Skia 场景图 (sksg) 中渲染节点的核心基础设施，包括 `RenderNode` 基类、`RenderContext` 渲染上下文、`ScopedRenderContext` 作用域渲染上下文以及 `CustomRenderNode` 自定义渲染节点。该文件共 261 行，是 sksg 渲染管线中最关键的文件之一，定义了所有可渲染节点的公共行为，包括可见性控制、渲染上下文传递、隔离层管理以及效果组合机制。

该文件的核心设计思想是"延迟渲染效果"：不透明度、颜色滤镜、着色器和遮罩等效果不是在遇到时立即创建 `saveLayer`，而是累积在 `RenderContext` 中沿渲染树向下传递，仅在需要隔离时才创建图层。这种机制大幅减少了 GPU 离屏渲染的开销。

## 架构位置

`RenderNode` 是 sksg 渲染层的基石，位于 `Node` 基类之上，是所有可渲染场景图节点（`OpacityEffect`、`MaskEffect`、`Draw` 等）的直接或间接基类。它定义了渲染、命中测试和上下文传递的核心协议。`RenderContext` 和 `ScopedRenderContext` 是渲染管线中效果组合的核心机制，实现了延迟渲染效果应用。

在 sksg 的类继承层次中：
```
Node (基类, SkSGNode.h)
  └─ RenderNode (渲染基类, 本文件)
       ├─ EffectNode (单子节点效果基类)
       │    ├─ OpacityEffect
       │    └─ MaskEffect
       ├─ Draw (几何 + 画笔绘制)
       ├─ Group (多子节点容器)
       └─ CustomRenderNode (外部自定义渲染)
```

## 主要类与结构体

### `RenderNode`
渲染节点基类，管理可见性状态和渲染/命中测试入口。

### `RenderNode::RenderContext`
```cpp
struct RenderContext {
    float fOpacity = 1;
    sk_sp<SkColorFilter> fColorFilter;
    sk_sp<SkShader> fShader;
    SkMatrix fShaderCTM = SkMatrix::I();
    sk_sp<SkShader> fMaskShader;
    SkMatrix fMaskCTM = SkMatrix::I();
    sk_sp<SkBlender> fBlender;
};
```
承载在渲染树中向下传递的累积效果参数。

### `RenderNode::ScopedRenderContext`
作用域渲染上下文，支持链式 API 来组合多个效果，并在析构时自动恢复 Canvas 状态。

### `CustomRenderNode`
允许外部代码实现自定义渲染逻辑的基类，管理多个子节点。

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `RenderNode::isVisible() const` | 检查节点是否可见 |
| `RenderNode::setVisible(bool)` | 设置可见性并触发失效 |
| `RenderNode::render(SkCanvas*, const RenderContext*) const` | 渲染入口，检查可见性和边界 |
| `RenderNode::nodeAt(const SkPoint&) const` | 命中测试入口 |
| `RenderContext::requiresIsolation() const` | 判断是否需要隔离层 |
| `RenderContext::modulatePaint(ctm, paint, is_layer) const` | 将上下文效果应用到画笔 |
| `ScopedRenderContext::modulateOpacity(float)` | 调制不透明度 |
| `ScopedRenderContext::modulateColorFilter(sk_sp<SkColorFilter>)` | 调制颜色滤镜 |
| `ScopedRenderContext::modulateShader(sk_sp<SkShader>, SkMatrix)` | 调制着色器 |
| `ScopedRenderContext::modulateMaskShader(sk_sp<SkShader>, SkMatrix)` | 调制遮罩着色器 |
| `ScopedRenderContext::modulateBlender(sk_sp<SkBlender>)` | 调制混合器 |
| `ScopedRenderContext::setIsolation(bounds, ctm, bool)` | 创建隔离层 |
| `ScopedRenderContext::setFilterIsolation(bounds, ctm, filter)` | 创建带图像滤镜的隔离层 |

## 内部实现细节

### 可见性管理
```cpp
void RenderNode::setVisible(bool v) {
    if (v == this->isVisible()) return;
    this->invalidate();
    fNodeFlags = v ? (fNodeFlags & ~kInvisible_Flag) : (fNodeFlags | kInvisible_Flag);
}
```
使用位标志 `kInvisible_Flag` 管理可见性，变更时触发失效。

### 渲染入口
```cpp
void RenderNode::render(SkCanvas* canvas, const RenderContext* ctx) const {
    SkASSERT(!this->hasInval());
    if (this->isVisible() && !this->bounds().isEmpty()) {
        this->onRender(canvas, ctx);
    }
}
```
双重断言确保渲染前已完成 revalidation。

### 本地着色器变换 (`LocalShader`)
```cpp
static sk_sp<SkShader> LocalShader(const sk_sp<SkShader>& shader,
                                   const SkMatrix& base, const SkMatrix& ctm) {
    // 计算 Inv(T) = Inv(ctm) x baseCTM
    // 撤销延迟应用的变换，使着色器在声明时的坐标系下操作
}
```
这是效果延迟机制的核心：由于效果被延迟应用，Canvas 的当前变换可能已经改变，需要计算补偿矩阵。

### 渲染上下文调制
`modulatePaint` 将上下文中累积的所有效果应用到 `SkPaint`：
- 不透明度: 缩放 alpha 值
- 颜色滤镜: 通过 `Compose` 组合
- 着色器: 通过 `LocalShader` 应用本地变换
- 混合器: 直接设置
- 遮罩着色器: 仅用于非隔离层画笔，使用 `SrcIn` 混合

### 隔离层管理 (`setIsolation`)
```cpp
if (isolation && fCtx.requiresIsolation()) {
    SkPaint layer_paint;
    fCtx.modulatePaint(ctm, &layer_paint, true);
    fCanvas->saveLayer(bounds, &layer_paint);
    // 保存遮罩着色器用于 restore 时应用
    if (fCtx.fMaskShader) {
        fMaskShader = LocalShader(fCtx.fMaskShader, fCtx.fMaskCTM, ctm);
    }
    // 重置已应用到隔离层的属性
    fCtx.fColorFilter = nullptr;
    fCtx.fMaskShader = nullptr;
    fCtx.fBlender = nullptr;
    fCtx.fOpacity = 1;
}
```

### ScopedRenderContext 析构
```cpp
~ScopedRenderContext() {
    if (fRestoreCount >= 0) {
        if (fMaskShader) {
            SkPaint mask_paint;
            mask_paint.setBlendMode(SkBlendMode::kDstIn);
            mask_paint.setShader(std::move(fMaskShader));
            fCanvas->drawPaint(mask_paint);  // 在 restore 前应用遮罩
        }
        fCanvas->restoreToCount(fRestoreCount);
    }
}
```

### 遮罩着色器组合 (`modulateMaskShader`)
多个遮罩着色器通过 `SrcIn` 混合模式组合，并计算相对变换矩阵以正确对齐：
```cpp
const auto relative_transform = SkMatrix::Concat(invMaskCTM, ctm);
fCtx.fMaskShader = SkShaders::Blend(SkBlendMode::kSrcIn,
                                    fCtx.fMaskShader,
                                    ms->makeWithLocalMatrix(relative_transform));
```

### 图像滤镜隔离 (`setFilterIsolation`)
当存在着色器时，将其转换为图像滤镜并通过 `SrcIn` 混合，因为着色器和图像滤镜不能直接组合。

### CustomRenderNode
```cpp
CustomRenderNode::CustomRenderNode(std::vector<sk_sp<RenderNode>>&& children)
    : INHERITED(kOverrideDamage_Trait)  // 保守地覆盖损坏区域
    , fChildren(std::move(children)) {
    for (const auto& child : fChildren) {
        this->observeInval(child);
    }
}
```
- 使用 `kOverrideDamage_Trait` 因为自定义节点的损坏行为不可预测，必须保守地假设整个节点区域可能被修改
- 在构造时注册所有子节点的失效观察，在析构时取消
- `hasChildrenInval()` 方法使用 `NodePriv::HasInval()` 遍历检查所有子节点的失效状态，提供给子类在 `onRevalidate` 中使用

## 依赖关系

- **直接依赖**: `SkSGRenderNode.h`、`SkCanvas.h`、`SkPaint.h`、`SkBlendMode.h`、`SkImageFilter.h`、`SkImageFilters.h`、`SkColorFilter.h`
- **内部依赖**: `SkSGNodePriv.h`（用于 `CustomRenderNode::hasChildrenInval`）
- **被继承**: `OpacityEffect`、`MaskEffect`、`Draw`、所有渲染效果节点
- **核心角色**: 这是 sksg 渲染管线的基础，几乎所有 sksg 渲染节点都直接或间接依赖此文件

## 设计模式与设计决策

- **延迟渲染效果**: 效果（不透明度、颜色滤镜、着色器等）不是立即应用到 Canvas 上，而是累积在 `RenderContext` 中，在需要时通过隔离层或直接调制画笔来应用。这减少了 `saveLayer` 的调用次数
- **链式 API**: `ScopedRenderContext` 的 `modulate*` 方法返回右值引用 (`&&`)，支持流畅的链式调用：`ScopedRenderContext(canvas, ctx).modulateOpacity(0.5).setIsolation(...)`
- **RAII 模式**: `ScopedRenderContext` 在析构时自动恢复 Canvas 状态和应用遮罩，确保资源管理的异常安全性
- **变换补偿**: `LocalShader` 函数通过矩阵逆运算补偿延迟应用导致的坐标系偏移，这是整个延迟渲染机制的数学基础
- **保守损坏覆盖**: `CustomRenderNode` 使用 `kOverrideDamage_Trait`，因为外部自定义代码的渲染行为不可预测

## 性能考量

- **隔离层最小化**: `requiresIsolation()` 仅在确实需要时才创建隔离层（即存在非默认的不透明度、颜色滤镜、遮罩着色器或混合器时），避免不必要的 GPU 纹理分配。对于仅有着色器效果的节点不创建隔离层
- **Alpha 缩放优化**: `ScaleAlpha` 使用 `sk_float_round2int` 进行浮点到整数的精确转换，避免简单截断导致的 alpha 值偏差
- **着色器优先级**: `modulateShader` 中最外层的着色器优先（if `!fCtx.fShader`），后续的着色器调制被忽略。这避免了嵌套着色器组合的复杂性和性能开销
- **遮罩延迟应用**: 遮罩着色器在 `ScopedRenderContext` 析构时才通过 `drawPaint` 应用，这意味着遮罩混合在图层 restore 之前执行，允许整个子树渲染完成后统一应用遮罩
- **边界裁剪**: 隔离层的 `saveLayer` 使用精确边界参数，将 GPU 离屏纹理的大小限制在实际需要的最小区域
- **可见性短路**: `render()` 方法在节点不可见或边界为空时直接返回，避免进入虚方法调用
- **渲染断言**: 双重 `SkASSERT(!this->hasInval())` 确保渲染路径不会在失效状态下执行，这在 debug 构建中帮助及早发现重新验证遗漏
- **矩阵逆运算缓存**: `LocalShader` 函数中的矩阵逆运算 (`ctm.invert(&lm)`) 在逆矩阵不存在时回退到单位矩阵，保证在奇异变换下的鲁棒性
- **颜色滤镜组合**: `modulateColorFilter` 使用 `SkColorFilters::Compose` 将新旧颜色滤镜组合，而非逐层应用，减少了额外的 GPU pass

## 相关文件

- `modules/sksg/include/SkSGRenderNode.h` — 类声明、`RenderContext` 和 `ScopedRenderContext` 定义
- `modules/sksg/src/SkSGNodePriv.h` — 节点私有访问辅助（用于 `CustomRenderNode`）
- `modules/sksg/src/SkSGOpacityEffect.cpp` — 使用 `ScopedRenderContext::modulateOpacity` 的实际案例
- `modules/sksg/src/SkSGMaskEffect.cpp` — 使用 `RenderContext::modulatePaint` 的实际案例
- `include/core/SkCanvas.h` — Canvas saveLayer/restore API
- `include/core/SkPaint.h` — 画笔属性
- `include/core/SkBlendMode.h` — 混合模式枚举（`kSrcIn`、`kDstIn`）
- `include/effects/SkImageFilters.h` — 图像滤镜组合
- `include/core/SkColorFilter.h` — 颜色滤镜基类和 `SkColorFilters::Compose`
