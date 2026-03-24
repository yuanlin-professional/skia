# FillEffect - Skottie 填充效果

> 源文件: `modules/skottie/src/effects/FillEffect.cpp`

## 概述

FillEffect 实现了 After Effects 中的填充（Fill）效果，该效果将图层的可见区域填充为指定的纯色。通过 `SkBlendMode::kSrcIn` 混合模式，填充色仅作用于图层原有的不透明区域，保留图层的 alpha 形状。支持颜色和不透明度两个可动画参数，并通过颜色属性分发系统对外暴露颜色控制。

## 架构位置

FillEffect 位于 Skottie 效果子系统中，使用颜色滤镜（ModeColorFilter）管线。

```
EffectBuilder::attachFillEffect()
  |
  +-> FillAdapter (效果适配器)
        |
        +-> sksg::Color (颜色节点)
        +-> sksg::ModeColorFilter (SrcIn 混合颜色滤镜)
        +-> EffectBinder [绑定 Color + Opacity]
        +-> dispatchColorProperty() [颜色属性外部化]
```

## 主要类与结构体

### FillAdapter
- 继承自 `AnimatablePropertyContainer`
- 持有 `sksg::Color` 颜色节点和 `sksg::ModeColorFilter` 滤镜节点
- 属性：
  - `fColor` (ColorValue) - 填充颜色
  - `fOpacity` (ScalarValue) - 不透明度（0.0-1.0）
- `onSync()` 将颜色和不透明度组合后设置到颜色节点
- JSON 属性索引：kColor_Index = 2, kOpacity_Index = 6

## 公共 API 函数

### `EffectBuilder::attachFillEffect`
```cpp
sk_sp<sksg::RenderNode> attachFillEffect(const skjson::ArrayValue& jprops,
                                          sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `FillAdapter` 绑定参数
- 通过 `attachDiscardableAdapter` 管理生命周期
- 返回 FillAdapter 的滤镜节点

## 内部实现细节

### 颜色合成
```cpp
void onSync() override {
    auto c = static_cast<SkColor4f>(fColor);
    c.fA = SkTPin(fOpacity, 0.0f, 1.0f);
    fColorNode->setColor(c.toSkColor());
}
```
- 从 `fColor` 获取 RGB 分量
- 用 `fOpacity` 替换 alpha 分量（限制在 [0, 1] 范围内）
- 转换为 SkColor 并设置到颜色节点

### ModeColorFilter 机制
- 使用 `SkBlendMode::kSrcIn`：结果 = 源颜色 * 目标 alpha
- 效果：将图层内容替换为纯色，但保留原始的 alpha 通道形状
- 这意味着图层的轮廓/透明度不受影响，仅颜色被替换

### 颜色属性分发
- 调用 `abuilder.dispatchColorProperty(fColorNode)` 将颜色节点注册到属性系统
- 允许外部通过 Skottie 的属性 API 动态修改填充颜色

### 未使用的参数
JSON 属性中存在但未绑定的参数（注释标记）：
- kFillMask_Index = 0
- kAllMasks_Index = 1
- kInvert_Index = 3
- kHFeather_Index = 4
- kVFeather_Index = 5

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkBlendMode.h` | SrcIn 混合模式 |
| `SkColor.h` | SkColor / SkColor4f |
| `SkTPin.h` | 不透明度范围限制 |
| `SkSGColorFilter.h` | ModeColorFilter |
| `SkSGPaint.h` | Color 颜色节点 |
| `Animator.h` | AnimatablePropertyContainer |
| `Effects.h` | EffectBinder |
| `SkottieValue.h` | ColorValue / ScalarValue |

## 设计模式与设计决策

- **适配器模式**：FillAdapter 将 AE 填充效果的参数语义映射到 Skia 的颜色滤镜系统。
- **SrcIn 混合**：巧妙利用混合模式实现"保形填充"——颜色替换但形状保留。
- **属性外部化**：通过 `dispatchColorProperty` 将颜色控制暴露给外部，支持运行时交互式修改。
- **工厂方法**：`FillAdapter::Make` 静态工厂方法封装了复杂的构造逻辑。

## 性能考量

- `ModeColorFilter` 作为颜色滤镜在 GPU 管线中高效执行。
- 仅两个可动画参数，属性更新开销极小。
- 颜色节点和滤镜节点的更新通过 Scene Graph 失效机制按需触发。
- `SkTPin` 在 `onSync` 中执行简单的范围限制，开销可忽略。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder、效果注册
- `modules/skottie/src/effects/TintEffect.cpp` - 类似的颜色替换效果
- `modules/sksg/include/SkSGColorFilter.h` - ModeColorFilter
- `modules/sksg/include/SkSGPaint.h` - Color 节点
- `modules/skottie/src/animator/Animator.h` - AnimatablePropertyContainer
