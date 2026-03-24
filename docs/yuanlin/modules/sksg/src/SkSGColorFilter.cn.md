# SkSGColorFilter 实现 -- 颜色过滤效果实现

> 源文件: `modules/sksg/src/SkSGColorFilter.cpp`

## 概述

`SkSGColorFilter.cpp` 实现了 Skia Scene Graph 中三种颜色过滤效果节点的完整运行时逻辑：`ColorFilter` 基类、`ExternalColorFilter`、`ModeColorFilter` 和 `GradientColorFilter`。其中 `GradientColorFilter` 的实现最为复杂，包含两种不同的色调映射算法：2 色渐变使用颜色矩阵，多色渐变使用颜色查找表。

## 架构位置

本文件实现了 `SkSGColorFilter.h` 中声明的所有类。在 sksg 模块的实现层中，它提供了颜色过滤器的创建、缓存和渲染应用逻辑。

```
SkSGColorFilter.cpp
├── ColorFilter::onRender/onNodeAt/onRevalidate (基类实现)
├── ExternalColorFilter::Make/onRender (外部过滤包装)
├── ModeColorFilter::Make/onRevalidateFilter (混合模式过滤)
└── GradientColorFilter::Make/onRevalidateFilter (渐变色调映射)
    ├── Make2ColorGradient (2色，颜色矩阵)
    └── MakeNColorGradient (N色，查找表)
```

## 主要类与结构体

（类声明见头文件文档。此处专注于实现细节。）

### 匿名命名空间辅助函数

#### `Make2ColorGradient(color0, color1)`
使用颜色矩阵实现 2 色渐变。算法：
1. 计算输入像素亮度 L = R*kR + G*kG + B*kB（使用 BT.709 亮度系数）
2. 在 color0 和 color1 之间按 L 线性插值
3. 两步运算合并为单个 5x4 颜色矩阵

#### `MakeNColorGradient(colors)`
使用查找表实现多色渐变。算法：
1. 将 256 级灰度空间均匀分割为 N-1 个区间
2. 每个区间内在相邻两色之间线性插值，填充 R/G/B 三个 256 字节查找表
3. 先通过亮度矩阵将输入转换为灰度，再通过查找表映射到目标颜色

## 公共 API 函数

### 工厂方法

- `ExternalColorFilter::Make(child)` -- 空指针检查后创建
- `ModeColorFilter::Make(child, color, mode)` -- 需要 child 和 color 都非空
- `GradientColorFilter::Make(child, c0, c1)` -- 委托给多色版本
- `GradientColorFilter::Make(child, colors)` -- 需要 child 非空且颜色数量 > 1

## 内部实现细节

### ColorFilter 基类实现

```cpp
void ColorFilter::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    const auto local_ctx = ScopedRenderContext(canvas, ctx)
        .modulateColorFilter(fColorFilter);
    this->INHERITED::onRender(canvas, local_ctx);
}
```
渲染时将缓存的 `SkColorFilter` 累积到 `RenderContext` 中，然后委托给 EffectNode 基类渲染子节点。

```cpp
SkRect ColorFilter::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    fColorFilter = this->onRevalidateFilter();
    return this->INHERITED::onRevalidate(ic, ctm);
}
```
重新验证时调用子类的 `onRevalidateFilter` 更新缓存，然后委托给基类验证子节点。

### ExternalColorFilter 的 BoundingBox 模式

```cpp
void ExternalColorFilter::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    auto local_ctx = ScopedRenderContext(canvas, ctx).modulateColorFilter(fColorFilter);
    if (fCoverage == Coverage::kBoundingBox) {
        canvas->save();
        canvas->clipRect(this->bounds(), true);
        local_ctx.setIsolation(this->bounds(), canvas->getTotalMatrix(), true);
    }
    this->INHERITED::onRender(canvas, local_ctx);
}
```
在 kBoundingBox 模式下，额外执行裁剪和隔离操作，确保颜色过滤应用到整个边界框（包括透明区域）。

### ModeColorFilter 实现

```cpp
sk_sp<SkColorFilter> ModeColorFilter::onRevalidateFilter() {
    fColor->revalidate(nullptr, SkMatrix::I());
    return SkColorFilters::Blend(fColor->getColor(), fMode);
}
```
先 revalidate Color 节点获取最新颜色值，然后创建混合模式颜色过滤器。

### GradientColorFilter 的 2 色算法

核心思想是将亮度计算和颜色插值合并为一个 5x4 颜色矩阵：

```
亮度矩阵:
| kR, kG, kB, 0, 0 |    r' = L
|  0,  0,  0, 0, 0 |    g' = 0
|  0,  0,  0, 0, 0 |    b' = 0
|  0,  0,  0, 1, 0 |    a' = a

插值矩阵（L 存于 R 通道）:
| dR, 0, 0, 0, c0.r |
| dG, 0, 0, 0, c0.g |
| dB, 0, 0, 0, c0.b |
|  0, 0, 0, 1,    0 |

组合结果:
| dR*kR, dR*kG, dR*kB, 0, c0.r |
| dG*kR, dG*kG, dG*kB, 0, c0.g |
| dB*kR, dB*kG, dB*kB, 0, c0.b |
|     0,     0,     0, 1,    0 |
```

### GradientColorFilter 的多色算法

1. 构建 256 级 R/G/B 查找表，区间均匀分布
2. 使用 `SkColorFilters::TableARGB` 创建查找表过滤器
3. 通过 `makeComposed` 与亮度矩阵组合

### 权重控制

```cpp
sk_sp<SkColorFilter> GradientColorFilter::onRevalidateFilter() {
    // ... revalidate colors ...
    if (fWeight <= 0) return nullptr;  // 完全禁用
    auto gradientCF = (fColors.size() > 2) ? MakeNColorGradient(...) : Make2ColorGradient(...);
    return SkColorFilters::Lerp(fWeight, nullptr, std::move(gradientCF));
}
```
使用 `SkColorFilters::Lerp` 在原始颜色（nullptr = identity）和映射后颜色之间按 `fWeight` 插值。

## 依赖关系

- `modules/sksg/include/SkSGColorFilter.h` -- 头文件声明
- `modules/sksg/include/SkSGPaint.h` -- Color 节点
- `modules/sksg/include/SkSGRenderNode.h` -- ScopedRenderContext
- `include/core/SkColorFilter.h` -- SkColorFilters 工厂方法
- `src/core/SkColorData.h` -- SK_LUM_COEFF_R/G/B 亮度系数
- `<cmath>` -- std::round（查找表填充）

## 设计模式与设计决策

1. **两种算法路径**：2 色渐变使用颜色矩阵（数学上精确，GPU 友好），多色渐变使用查找表（支持任意颜色数，但精度有限为 256 级）。自动根据颜色数量选择最优路径。

2. **颜色矩阵优化**：2 色情况将亮度计算和线性插值合并为单个矩阵乘法，减少了 GPU 着色器的指令数。

3. **Lerp 权重混合**：使用 Skia 内置的 `SkColorFilters::Lerp` 而非手动混合，利用了 Skia 的优化实现。

4. **短路优化**：`fWeight <= 0` 时直接返回 nullptr，完全跳过颜色过滤。

5. **失效链传播**：所有 Color 节点通过 `observeInval` 参与场景图的失效机制，颜色动画自动触发过滤器重建。

## 性能考量

- 2 色渐变的颜色矩阵方案在 GPU 上非常高效（单次矩阵乘法）。
- 多色渐变的查找表方案需要 768 字节额外内存（3 x 256 字节），但查找操作本身很快。
- `MakeNColorGradient` 中的 `std::round` 调用可能较慢，但只在 revalidate 时执行。
- GradientColorFilter 的 revalidation 串行执行所有 Color 节点的 revalidate，颜色数量多时开销线性增长。
- ExternalColorFilter 的 kBoundingBox 模式需要额外的 save/clipRect/setIsolation 操作。
- `SkColorFilters::Lerp` 创建复合过滤器，可能比简单过滤器有更高的运行时开销。

## 相关文件

- `modules/sksg/include/SkSGColorFilter.h` -- 类声明
- `modules/sksg/include/SkSGPaint.h` -- Color 节点
- `modules/sksg/include/SkSGRenderNode.h` -- ScopedRenderContext
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `src/core/SkColorData.h` -- 亮度系数常量
