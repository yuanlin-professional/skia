# TintEffect - Skottie 着色效果

> 源文件: `modules/skottie/src/effects/TintEffect.cpp`

## 概述

TintEffect 实现了 After Effects 中的着色（Tint）效果，将图层的暗部映射到一种颜色、亮部映射到另一种颜色，形成双色渐变映射。效果强度通过混合量（Amount）参数控制。实现基于 Skia 的 `GradientColorFilter`，该滤镜根据输入像素的亮度在两个颜色之间进行线性插值。

## 架构位置

TintEffect 位于 Skottie 效果子系统中，使用渐变颜色滤镜管线。

```
EffectBuilder::attachTintEffect()
  |
  +-> TintAdapter (效果适配器)
        |
        +-> sksg::Color x2 (暗部/亮部颜色节点)
        +-> sksg::GradientColorFilter (渐变颜色滤镜)
        +-> EffectBinder [绑定 MapBlackTo, MapWhiteTo, Amount]
```

## 主要类与结构体

### TintAdapter
- 继承自 `AnimatablePropertyContainer`
- 管理两个颜色节点和一个渐变颜色滤镜
- 属性：
  - `fMapBlackTo` (ColorValue) - 暗部映射颜色
  - `fMapWhiteTo` (ColorValue) - 亮部映射颜色
  - `fAmount` (ScalarValue) - 效果强度（0-100）
- JSON 属性索引：kMapBlackTo = 0, kMapWhiteTo = 1, kAmount = 2

## 公共 API 函数

### `EffectBuilder::attachTintEffect`
```cpp
sk_sp<sksg::RenderNode> attachTintEffect(const skjson::ArrayValue& jprops,
                                          sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `TintAdapter` 绑定参数并应用到图层
- 返回 TintAdapter 的滤镜节点

## 内部实现细节

### 着色同步
```cpp
void onSync() override {
    fColorNode0->setColor(fMapBlackTo);
    fColorNode1->setColor(fMapWhiteTo);
    fFilterNode->setWeight(fAmount / 100);
}
```
- `fColorNode0` 对应暗部颜色（映射黑色像素）
- `fColorNode1` 对应亮部颜色（映射白色像素）
- `fAmount` 以百分比表示，除以 100 转换为 [0, 1] 权重
- 权重 = 0 时无效果（原始图层），权重 = 1 时完全着色

### GradientColorFilter 工作原理
- 基于输入像素的亮度（luminance）在两个颜色之间插值
- 暗像素（亮度接近 0）-> fMapBlackTo 颜色
- 亮像素（亮度接近 1）-> fMapWhiteTo 颜色
- `weight` 参数控制原始颜色与着色结果之间的混合程度

### 未使用的参数
- `kOpacity_Index = 3` 未导出/未绑定

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkColor.h` | SkColor 颜色类型 |
| `SkSGColorFilter.h` | GradientColorFilter |
| `SkSGPaint.h` | Color 颜色节点 |
| `Animator.h` | AnimatablePropertyContainer |
| `Effects.h` | EffectBinder |
| `SkottieValue.h` | ColorValue / ScalarValue |

## 设计模式与设计决策

- **双色渐变映射**：使用两个 `sksg::Color` 节点作为渐变的端点，通过 `GradientColorFilter` 实现亮度到颜色的映射。
- **工厂方法**：`TintAdapter::Make` 封装了节点创建和绑定的复杂逻辑。
- **百分比权重**：Amount 参数以百分比表示（AE 惯例），内部转换为 [0, 1] 范围。
- **颜色滤镜管线**：作为颜色滤镜应用，不改变图层的几何形状或透明度。

## 性能考量

- `GradientColorFilter` 在 GPU 上执行逐像素的颜色映射，高效利用并行计算。
- 仅三个可动画参数，属性更新开销极小。
- 颜色节点通过 Scene Graph 失效机制按需更新。
- 权重为 0 时，GradientColorFilter 可能优化为透传。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder
- `modules/skottie/src/effects/FillEffect.cpp` - 类似的颜色替换效果
- `modules/skottie/src/effects/CCTonerEffect.cpp` - 更复杂的多色调映射
- `modules/sksg/include/SkSGColorFilter.h` - GradientColorFilter
- `modules/sksg/include/SkSGPaint.h` - Color 节点
