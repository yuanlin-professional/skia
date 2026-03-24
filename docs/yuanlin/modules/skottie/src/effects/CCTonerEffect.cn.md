# CCTonerEffect - Skottie CC Toner 色调映射效果

> 源文件: `modules/skottie/src/effects/CCTonerEffect.cpp`

## 概述

CCTonerEffect 实现了 After Effects 中的 CC Toner 效果，一种基于亮度的多色调映射工具。该效果支持四种色调模式（Solid、Duotone、Tritone、Pentone），通过 5 个颜色节点的渐变映射将图层的亮度范围映射到用户指定的颜色。支持高光、亮色、中间色、暗色和阴影五个颜色通道以及混合量控制。

## 架构位置

CCTonerEffect 位于 Skottie 效果子系统中，使用多色渐变颜色滤镜管线。

```
EffectBuilder::attachCCTonerEffect()
  |
  +-> CCTonerAdapter (效果适配器)
  |     +-> DiscardableAdapterBase<..., sksg::GradientColorFilter>
  |     +-> 5 个 sksg::Color 颜色节点
  |     +-> EffectBinder [绑定 Tone + 5 Colors + Blend]
  |
  +-> sksg::GradientColorFilter [5 色渐变滤镜]
```

## 主要类与结构体

### CCTonerAdapter
- 继承自 `DiscardableAdapterBase<CCTonerAdapter, sksg::GradientColorFilter>`
- 持有 5 个 `sk_sp<sksg::Color>` 颜色节点的向量
- 属性：
  - `fTone` (ScalarValue) - 色调模式选择（0-3）
  - `fHighlights` / `fBrights` / `fMidtones` / `fDarktones` / `fShadows` (ColorValue) - 五个颜色通道
  - `fBlend` (ScalarValue) - 混合量
- JSON 属性索引：Tone=0, HiColor=1, BrightColor=2, MidColor=3, DarkColor=4, ShadowColor=5, BlendAmount=6

## 公共 API 函数

### `EffectBuilder::attachCCTonerEffect`
```cpp
sk_sp<sksg::RenderNode> attachCCTonerEffect(const skjson::ArrayValue& jprops,
                                             sk_sp<sksg::RenderNode> layer) const;
```
- 创建 5 个初始颜色为 `SK_ColorRED` 的颜色节点
- 创建 `CCTonerAdapter` 绑定参数
- 返回配置好的渲染节点

## 内部实现细节

### 色调模式映射

**Duotone（双色调，fTone=1）：**
```
节点0 = Shadows
节点1 = lerp(Shadows, Highlights, 0.25)
节点2 = lerp(Shadows, Highlights, 0.50)
节点3 = lerp(Shadows, Highlights, 0.75)
节点4 = Highlights
```
5 个节点均匀分布在 Shadows 到 Highlights 之间。

**Tritone（三色调，fTone=2）：**
```
节点0 = Shadows
节点1 = lerp(Shadows, Midtones, 0.5)
节点2 = Midtones
节点3 = lerp(Midtones, Highlights, 0.5)
节点4 = Highlights
```
Shadows -> Midtones -> Highlights 三段渐变。

**Pentone（五色调，fTone=3）：**
```
节点0 = Shadows
节点1 = Darktones
节点2 = Midtones
节点3 = Brights
节点4 = Highlights
```
直接使用 5 个颜色参数，最精细的控制。

**Solid（纯色，default）：**
```
节点0-4 = Midtones
```
所有节点设为同一颜色，整个图层映射为单色。

### 颜色插值
```cpp
static SkColor lerpColor(SkColor c0, SkColor c1, float t) {
    const auto c0_4f = Sk4f_fromL32(c0),
               c1_4f = Sk4f_fromL32(c1),
               c_4f = c0_4f + (c1_4f - c0_4f) * t;
    return Sk4f_toL32(c_4f);
}
```
- 使用 SIMD 4 通道浮点运算进行颜色线性插值
- `Sk4f_fromL32` / `Sk4f_toL32` 在 32 位颜色和 4 通道浮点之间转换
- 在 sRGB 空间直接插值（非线性空间）

### 混合权重
```cpp
this->node()->setWeight((100 - fBlend) / 100);
```
- `fBlend = 0` 时权重 = 1（完全应用效果）
- `fBlend = 100` 时权重 = 0（无效果）
- 注意：混合量的语义是反向的（Blend=0 表示完全效果）

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkColor.h` | SkColor 颜色类型 |
| `SkVx.h` | SIMD 向量运算 |
| `SkSwizzlePriv.h` | Sk4f_fromL32 / Sk4f_toL32 |
| `SkSGColorFilter.h` | GradientColorFilter |
| `SkSGPaint.h` | Color 颜色节点 |
| `Adapter.h` | DiscardableAdapterBase |
| `Effects.h` | EffectBinder |
| `SkottieValue.h` | ScalarValue / ColorValue |

## 设计模式与设计决策

- **多档渐变映射**：通过 5 个颜色节点和 `GradientColorFilter` 实现不同精度的色调映射（2/3/5 色）。不同模式通过调整节点间的插值方式实现。
- **适配器模式**：CCTonerAdapter 将 AE 的复杂色调映射参数映射到 Skia 的 5 色渐变滤镜。
- **SIMD 颜色插值**：使用 Sk4f 进行颜色分量的并行插值，利用 SIMD 指令加速。
- **外部初始化颜色节点**：5 个颜色节点在 `attachCCTonerEffect` 中创建并传入适配器，实现了节点创建与参数绑定的分离。
- **switch-case 模式映射**：4 种色调模式通过 switch-case 实现，每种模式显式设置 5 个颜色节点的值。

## 性能考量

- `GradientColorFilter` 在 GPU 上执行 5 色渐变映射，利用硬件纹理采样。
- `lerpColor` 使用 SIMD 运算，4 个颜色分量同时计算。
- 每帧最多执行 5 次颜色设置和 2 次颜色插值（Duotone 模式下 3 次插值）。
- 颜色节点通过 Scene Graph 失效机制按需更新。
- `SkScalarRoundToInt(fTone)` 将浮点模式值转换为整数进行 switch 分支。

### GradientColorFilter 的工作原理

`sksg::GradientColorFilter` 接受一组颜色节点作为渐变色标，根据输入像素的亮度值在这些颜色之间进行插值：

1. 计算输入像素的亮度值（0 到 1 范围）
2. 将亮度值映射到 5 个颜色节点的渐变范围
3. 在相邻的两个颜色节点之间线性插值
4. `weight` 参数控制效果结果与原始颜色之间的混合比例

5 个颜色节点均匀分布在亮度范围内：节点 0 对应最暗（亮度 = 0），节点 4 对应最亮（亮度 = 1）。

### 颜色初始化

在 `attachCCTonerEffect` 中，5 个颜色节点初始化为 `SK_ColorRED`。这个初始值在首次 `onSync` 调用时会被 AE 的实际颜色参数覆盖，因此初始颜色值不影响最终渲染结果。选择 `SK_ColorRED` 仅作为调试时便于观察的初始占位值。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder
- `modules/skottie/src/effects/TintEffect.cpp` - 更简单的双色调映射（2 色）
- `modules/sksg/include/SkSGColorFilter.h` - GradientColorFilter
- `modules/sksg/include/SkSGPaint.h` - Color 节点
- `src/base/SkVx.h` - SIMD 向量运算
