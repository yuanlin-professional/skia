# TritoneEffect - Skottie 三色调效果

> 源文件: `modules/skottie/src/effects/TritoneEffect.cpp`

## 概述

TritoneEffect 实现了 After Effects 中的"Tritone"（三色调）效果。该效果将图层转换为三色调渐变映射：原始图像的暗部、中间调和高光分别映射到用户指定的三种颜色，产生风格化的色彩分级效果。实现基于 `sksg::GradientColorFilter` 场景图节点，该节点按照亮度值在三个颜色之间进行渐变插值。

## 架构位置

该文件位于 Skottie 效果子系统中（`skottie::internal` 命名空间）。TritoneAdapter 使用 `AnimatablePropertyContainer` 作为基类，管理颜色与权重属性，并通过 `sksg::GradientColorFilter` 节点实现渐变颜色映射。

```
AnimationBuilder
  └── EffectBuilder::attachTritoneEffect()
        └── TritoneAdapter (AnimatablePropertyContainer)
              └── sksg::GradientColorFilter
                    ├── sksg::Color (Lo)
                    ├── sksg::Color (Mi)
                    └── sksg::Color (Hi)
```

## 主要类与结构体

### `TritoneAdapter`
- 继承自 `AnimatablePropertyContainer`
- 管理三个 `sksg::Color` 节点（低、中、高色调）和一个 `sksg::GradientColorFilter` 节点
- 动画属性包括三个颜色值和一个混合量参数

### 属性索引枚举
- `kHiColor_Index = 0`：高光颜色
- `kMiColor_Index = 1`：中间调颜色
- `kLoColor_Index = 2`：阴影颜色
- `kBlendAmount_Index = 3`：混合量（控制效果强度）

## 公共 API 函数

### `EffectBuilder::attachTritoneEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachTritoneEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- **功能**：将三色调效果附加到目标图层
- **参数**：`jprops` 包含 Lottie JSON 效果属性，`layer` 为目标渲染节点
- **返回值**：附加效果后的 `GradientColorFilter` 节点

## 内部实现细节

### 构造过程

构造函数创建三个 `sksg::Color` 节点（初始化为黑色），然后将它们传递给 `sksg::GradientColorFilter::Make()` 构建渐变颜色滤镜。使用 `EffectBinder` 将 JSON 属性绑定到适配器的动画属性。

### onSync 方法

当动画属性更新时：
1. 更新三个颜色节点的颜色值
2. 计算并设置混合权重：`fCF->setWeight((100 - fWeight) / 100)`

注意权重的反转逻辑：AE 中 `fWeight` 为 0 时效果完全生效（权重为 1），为 100 时效果完全不生效（权重为 0）。这是一个 100 基的反转映射。

### 颜色映射

`GradientColorFilter` 将输入图像的亮度值映射到三个颜色之间的渐变：
- 亮度 0.0（暗部）-> Lo 颜色
- 亮度 0.5（中间调）-> Mi 颜色
- 亮度 1.0（高光）-> Hi 颜色

## 依赖关系

- **Skia 核心**：`SkColor`
- **Skottie 内部**：`SkottiePriv.h`、`SkottieValue.h`（`ColorValue`、`ScalarValue`）、`Effects.h`（`EffectBinder`）、`Animator.h`（`AnimatablePropertyContainer`）
- **SkSG（场景图）**：`SkSGColorFilter.h`（`GradientColorFilter`）、`SkSGPaint.h`（`Color`）

## 设计模式与设计决策

1. **颜色节点分离**：三个颜色使用独立的 `sksg::Color` 节点，允许场景图的失效/重新验证机制精确追踪颜色变化。

2. **反转权重**：`(100 - fWeight) / 100` 映射遵循 AE 的语义，其中 blend amount 为 0 表示完全应用效果。

3. **工厂方法模式**：`Make()` 静态方法确保对象通过 `sk_sp` 引用计数指针管理。

4. **节点所有权**：颜色节点在构造函数初始化列表中创建并作为 `const` 成员保存，确保生命周期与适配器一致。

## 性能考量

- `GradientColorFilter` 基于 GPU 友好的渐变查找表实现，性能优良
- 仅在动画属性变化时更新颜色节点和权重，利用场景图的失效传播机制避免不必要的重绘
- 颜色节点设为 `const sk_sp`，避免引用计数的多余操作

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBuilder 定义
- `modules/sksg/include/SkSGColorFilter.h` - GradientColorFilter 节点实现
- `modules/sksg/include/SkSGPaint.h` - Color 节点实现
- `modules/skottie/src/effects/BlackAndWhiteEffect.cpp` - 类似的颜色映射效果
- `modules/skottie/src/effects/LevelsEffect.cpp` - 另一个颜色校正效果
