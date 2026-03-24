# SkSGMaskEffect - 场景图遮罩效果节点

> 源文件: `modules/sksg/src/SkSGMaskEffect.cpp`

## 概述

`SkSGMaskEffect.cpp` 实现了 Skia 场景图 (sksg) 中的 `MaskEffect` 类，用于在渲染时对子节点应用遮罩效果。遮罩效果支持四种模式，由两个独立的位控制：遮罩源（alpha 通道 / 亮度 luma）和遮罩类型（正常 / 反转）。该类在 Lottie 动画渲染中用于实现 After Effects 的 Track Matte 功能。

四种模式的组合如下：
- **Normal Alpha**: 使用遮罩的 alpha 通道作为覆盖度
- **Inverted Alpha**: 使用遮罩 alpha 通道的反转值 (1 - alpha) 作为覆盖度
- **Normal Luma**: 将遮罩的 RGB 转换为亮度值后用作覆盖度
- **Inverted Luma**: 使用亮度值的反转作为覆盖度

## 架构位置

`MaskEffect` 位于 sksg 模块的效果节点层，是场景图 DAG 中的中间节点。它持有两个子渲染节点：被遮罩的内容节点（通过基类管理）和遮罩节点（`fMaskNode`）。在渲染管线中，它通过 Canvas 的 `saveLayer` 机制实现双层混合，将遮罩的覆盖度应用到内容上。

在 Skottie 的场景图结构中，`MaskEffect` 通常出现在图层节点下方：
```
TransformEffect
  └─ MaskEffect
       ├─ child: Draw(PaintNode, GeometryNode)  // 被遮罩的内容
       └─ mask:  Draw(PaintNode, GeometryNode)   // 遮罩形状
```

## 主要类与结构体

### `MaskEffect`
```cpp
MaskEffect::MaskEffect(sk_sp<RenderNode> child, sk_sp<RenderNode> mask, Mode mode)
    : INHERITED(std::move(child))
    , fMaskNode(std::move(mask))
    , fMaskMode(mode) {
    this->observeInval(fMaskNode);
}
```

- **`fMaskNode`**: 用作遮罩的渲染节点
- **`fMaskMode`**: 遮罩模式，编码在一个枚举值的低两位中

### 辅助函数
```cpp
static bool is_inverted(sksg::MaskEffect::Mode mode);  // 检查 bit 0: 是否反转
static bool is_luma(sksg::MaskEffect::Mode mode);       // 检查 bit 1: 是否使用亮度
```

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `MaskEffect(child, mask, mode)` | 构造函数，注册遮罩节点的失效观察 |
| `~MaskEffect()` | 析构函数，取消遮罩节点的失效观察 |
| `void onRender(SkCanvas*, const RenderContext*) const` | 通过双层 saveLayer 实现遮罩渲染 |
| `const RenderNode* onNodeAt(const SkPoint&) const` | 遮罩感知的命中测试 |
| `SkRect onRevalidate(InvalidationController*, const SkMatrix&)` | 重新验证并计算遮罩后的边界 |

## 内部实现细节

### 遮罩模式编码
遮罩模式通过枚举值的低两位编码两个独立属性：
- **Bit 0** (`is_inverted`): 控制遮罩覆盖度的解释方式
  - `0` = 正常: `coverage' = coverage`
  - `1` = 反转: `coverage' = 1 - coverage`
- **Bit 1** (`is_luma`): 控制遮罩覆盖度的生成方式
  - `0` = Alpha 通道: `coverage = mask_alpha`
  - `1` = 亮度: `coverage = luma(mask_rgb)`

### 渲染流程 (`onRender`)
使用嵌套的 `saveLayer` 实现遮罩混合：

1. **外层 (遮罩层)**:
   - 应用上下文的所有可选覆盖
   - 如果是 luma 模式，应用 `SkLumaColorFilter` 将 RGB 转换为亮度
   - 渲染遮罩节点到此层（覆盖度存储在 alpha 通道中）

2. **内层 (内容层)**:
   - 使用 `SkBlendMode::kSrcIn`（正常模式）或 `SkBlendMode::kSrcOut`（反转模式）
   - 渲染被遮罩的内容节点

```cpp
canvas->saveLayer(this->bounds(), &mask_layer_paint);   // 外层
fMaskNode->render(canvas, &mask_render_context);
    canvas->saveLayer(this->bounds(), &content_layer_paint); // 内层
    this->INHERITED::onRender(canvas, nullptr);
```

### 命中测试 (`onNodeAt`)
```cpp
const RenderNode* MaskEffect::onNodeAt(const SkPoint& p) const {
    const auto mask_hit = (SkToBool(fMaskNode->nodeAt(p)) == !is_inverted(fMaskMode));
    if (!mask_hit) return nullptr;
    return this->INHERITED::onNodeAt(p);
}
```

命中测试需要考虑遮罩的反转状态：
- **正常模式**: 遮罩节点命中 (`nodeAt` 返回非 null) 才继续检查内容节点
- **反转模式**: 遮罩节点未命中 (`nodeAt` 返回 null) 才继续检查内容节点
- 使用 `SkToBool` 将指针转换为布尔值，然后与反转标志的否定进行比较

### 边界计算 (`onRevalidate`)
```cpp
SkRect MaskEffect::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    const auto maskBounds = fMaskNode->revalidate(ic, ctm);
    auto childBounds = this->INHERITED::onRevalidate(ic, ctm);
    return (is_inverted(fMaskMode) || childBounds.intersect(maskBounds))
        ? childBounds : SkRect::MakeEmpty();
}
```

- **正常模式**: 返回子节点边界和遮罩边界的交集（不可见区域外没有内容）
- **反转模式**: 直接返回子节点边界（遮罩外区域都是可见的，边界不缩小）
- 先重新验证遮罩节点，再重新验证内容子节点，确保两者的边界都是最新的
- 使用短路逻辑：反转模式直接返回 `childBounds`，不需要计算交集

## 依赖关系

- **直接依赖**:
  - `SkSGMaskEffect.h` — 类声明及 `Mode` 枚举
  - `SkBlendMode.h` — `kSrcIn`/`kSrcOut` 混合模式
  - `SkCanvas.h` — `saveLayer`/`SkAutoCanvasRestore`
  - `SkColorFilter.h` — 颜色滤镜基类
  - `SkPaint.h` — 画笔属性
  - `SkLumaColorFilter.h` — 亮度到 alpha 的颜色滤镜
  - `SkAssert.h` — 断言宏
  - `SkTo.h` — 类型安全转换
  - `SkSGNode.h` — 节点基类（`InvalidationController`）
- **前向声明**: `SkMatrix`、`SkPoint` — 仅在函数签名中使用
- **观察者模式**: 通过 `observeInval`/`unobserveInval` 监听遮罩节点的失效事件
- **被使用**: Skottie 模块中用于实现 After Effects 的 Track Matte 和遮罩功能

## 设计模式与设计决策

- **组合模式**: `MaskEffect` 组合了两个独立的渲染子树（内容和遮罩），而非简单的单子节点装饰。这与 `OpacityEffect` 等单子节点效果形成对比，体现了更复杂的节点关系
- **观察者模式**: 构造函数中 `this->observeInval(fMaskNode)` 注册失效观察，析构函数中 `this->unobserveInval(fMaskNode)` 取消。这确保了遮罩节点属性变化时，`MaskEffect` 会被正确标记为失效并在下一帧重新渲染
- **位编码枚举**: 使用位操作 (`static_cast<uint32_t>(mode) & 1/2`) 来编码两个正交的模式维度，使得四种模式组合紧凑且高效。这避免了使用两个独立的枚举或布尔标志
- **混合模式选择**: 使用 `kSrcIn`（保留目标中与源重叠的部分）和 `kSrcOut`（保留目标中与源不重叠的部分）而非手动 alpha 计算，充分利用 GPU 硬件加速的混合能力
- **上下文清空**: `onRender` 中内容层使用 `nullptr` 作为上下文传给父类，因为所有上下文效果已在外层遮罩层中处理
- **边界交集逻辑**: `onRevalidate` 中反转模式返回完整子边界而非交集，这是因为反转遮罩意味着遮罩区域外的内容是可见的

## 性能考量

- **双层 saveLayer 开销**: 每次渲染需要两个 `saveLayer` 调用，这是遮罩效果的固有开销。每个 `saveLayer` 都需要分配离屏纹理，这在 GPU 渲染中是最昂贵的操作之一。代码中有 TODO 注释提到可能使用 A8（alpha-only）格式的层来减少内存占用——这将把纹理大小减少到 1/4
- **边界裁剪**: 使用 `this->bounds()` 作为 `saveLayer` 的边界参数，限制 GPU 纹理分配到必要的最小区域，避免全屏大小的离屏缓冲区
- **子 DAG 重新验证**: 遮罩节点的 revalidation 与内容节点的 revalidation 顺序执行，确保边界计算的正确性。两者不能并行化，因为最终边界依赖于两者的结果
- **亮度模式额外开销**: luma 模式需要额外创建 `SkLumaColorFilter` 实例并将其应用到遮罩渲染上下文中，比 alpha 模式多一次 RGB 到亮度的颜色空间转换计算
- **命中测试效率**: `onNodeAt` 需要先查询遮罩节点的命中测试结果，增加了一次额外的节点遍历
- **Canvas 状态管理**: 使用 `SkAutoCanvasRestore` RAII 对象管理 Canvas 状态，确保即使在异常路径上也能正确恢复

## 相关文件

- `modules/sksg/include/SkSGMaskEffect.h` — 类声明及 `Mode` 枚举定义
- `modules/sksg/src/SkSGOpacityEffect.cpp` — 类似但更简单的单子节点渲染效果
- `modules/sksg/src/SkSGRenderNode.cpp` — `RenderContext` 和 `ScopedRenderContext` 实现
- `include/effects/SkLumaColorFilter.h` — 亮度颜色滤镜，将 RGB 转换为亮度值存入 alpha
- `include/core/SkBlendMode.h` — 混合模式定义（`kSrcIn`、`kSrcOut`）
- `modules/skottie/src/layers/` — Skottie 中使用遮罩效果的代码
