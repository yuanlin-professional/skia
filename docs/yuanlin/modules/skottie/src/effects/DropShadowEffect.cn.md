# DropShadowEffect - Skottie 投影效果

> 源文件: `modules/skottie/src/effects/DropShadowEffect.cpp`

## 概述

DropShadowEffect 实现了 After Effects 中的投影（Drop Shadow）效果。该效果在图层下方或替代图层生成一个带模糊的彩色投影。支持阴影颜色、不透明度、方向角度、距离、柔和度（模糊半径）和仅阴影模式的动画控制。实现通过 Skia 的 `DropShadowImageFilter` 图像滤镜完成。

## 架构位置

DropShadowEffect 位于 Skottie 效果子系统中，使用图像滤镜效果管线。

```
EffectBuilder::attachDropShadowEffect()
  |
  +-> DropShadowAdapter (效果适配器)
        |
        +-> sksg::DropShadowImageFilter [投影滤镜]
        +-> sksg::ImageFilterEffect [滤镜效果包装]
        +-> EffectBinder [绑定 6 个参数]
```

## 主要类与结构体

### DropShadowAdapter
- 继承自 `AnimatablePropertyContainer`
- 持有 `sksg::DropShadowImageFilter` 和 `sksg::ImageFilterEffect`
- 属性（6 个可动画参数）：
  - `fColor` (ColorValue) - 阴影颜色（默认黑色）
  - `fOpacity` (ScalarValue) - 不透明度（0-255，默认 255）
  - `fDirection` (ScalarValue) - 方向角度（度，默认 0）
  - `fDistance` (ScalarValue) - 投影距离（默认 0）
  - `fSoftness` (ScalarValue) - 柔和度/模糊半径（默认 0）
  - `fShdwOnly` (ScalarValue) - 仅阴影模式标志（默认 0）
- JSON 属性索引：Color=0, Opacity=1, Direction=2, Distance=3, Softness=4, ShadowOnly=5

## 公共 API 函数

### `EffectBuilder::attachDropShadowEffect`
```cpp
sk_sp<sksg::RenderNode> attachDropShadowEffect(const skjson::ArrayValue& jprops,
                                                sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `DropShadowAdapter` 绑定参数
- 返回 ImageFilterEffect 渲染节点

## 内部实现细节

### 颜色与不透明度合成
```cpp
const SkColor color = fColor;
fDropShadow->setColor(SkColorSetA(color, SkTPin(SkScalarRoundToInt(fOpacity), 0, 255)));
```
- 从 `fColor` 获取 RGB 分量
- 用 `fOpacity`（0-255 范围，四舍五入取整并限制范围）替换 alpha
- `SkColorSetA` 保留 RGB 并设置新的 alpha 值

### 方向-距离到偏移量转换
```cpp
const auto rad = SkDegreesToRadians(90 - fDirection);
fDropShadow->setOffset(SkVector::Make( fDistance * SkScalarCos(rad),
                                      -fDistance * SkScalarSin(rad)));
```
- AE 的方向定义：0 度为正下方，顺时针增加
- 转换为标准数学角度：`rad = 90 - direction`（度转弧度）
- X 偏移 = `distance * cos(rad)`
- Y 偏移 = `-distance * sin(rad)`（Y 轴翻转以匹配屏幕坐标系）

### 模糊 Sigma 计算
```cpp
const auto sigma = fSoftness * kBlurSizeToSigma;
fDropShadow->setSigma(SkVector::Make(sigma, sigma));
```
- `kBlurSizeToSigma` 将 AE 的柔和度值转换为高斯模糊的 sigma 参数
- X 和 Y 方向使用相同的 sigma（各向同性模糊）

### 阴影模式
```cpp
fDropShadow->setMode(SkToBool(fShdwOnly)
    ? sksg::DropShadowImageFilter::Mode::kShadowOnly
    : sksg::DropShadowImageFilter::Mode::kShadowAndForeground);
```
- `kShadowOnly` - 仅显示阴影，原图层隐藏
- `kShadowAndForeground` - 阴影 + 原图层同时显示

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkColor.h` | SkColor / SkColorSetA |
| `SkPoint.h` | SkVector 偏移量 |
| `SkScalar.h` | 角度转换函数 |
| `SkTPin.h` / `SkTo.h` | 范围限制和类型转换 |
| `SkSGRenderEffect.h` | DropShadowImageFilter / ImageFilterEffect |
| `Animator.h` | AnimatablePropertyContainer |
| `Effects.h` | EffectBinder |
| `SkottieValue.h` | ColorValue / ScalarValue |

## 设计模式与设计决策

- **工厂方法**：`DropShadowAdapter::Make` 静态工厂方法封装节点创建和参数绑定。
- **极坐标参数**：使用方向+距离（极坐标）而非 X/Y 偏移（笛卡尔坐标），与 AE 的用户界面一致。
- **图像滤镜管线**：通过 `ImageFilterEffect` 将 `DropShadowImageFilter` 应用到图层，利用 Skia 的图像滤镜基础设施。
- **双模式支持**：ShadowOnly/ShadowAndForeground 两种模式覆盖了 AE 中投影效果的全部使用场景。
- **kBlurSizeToSigma 常量**：统一了 AE 柔和度值与 Skia 高斯模糊 sigma 之间的映射关系。

## 性能考量

- `DropShadowImageFilter` 在 Skia 内部实现高效的高斯模糊，利用 GPU 加速。
- 各向同性模糊允许使用可分离滤波（两次 1D 模糊代替一次 2D 模糊）。
- 三角函数仅在参数变化时计算，不在每像素执行。
- `SkTPin` 和 `SkScalarRoundToInt` 是轻量的内联运算。
- ShadowOnly 模式可能允许跳过原始图层的渲染。

### AE 投影参数到 Skia 参数的映射

After Effects 使用极坐标系统描述投影的偏移（方向 + 距离），而 Skia 的 DropShadowImageFilter 使用笛卡尔坐标（X/Y 偏移）。映射关系如下：

- AE 方向 0 度 = 正下方（Y 正方向）
- AE 方向 90 度 = 向右（X 正方向）
- AE 方向 180 度 = 正上方（Y 负方向）
- AE 方向 270 度 = 向左（X 负方向）

转换公式中 `90 - fDirection` 将 AE 的"从正下方顺时针"坐标系转换为标准数学坐标系（从正右方逆时针），然后通过 cos/sin 分解为 X/Y 分量。Y 分量取负号是因为屏幕坐标系 Y 轴向下。

### DropShadowImageFilter 与 ImageFilterEffect 的关系

`sksg::DropShadowImageFilter` 是一个 Scene Graph 节点，封装了 Skia 的 `SkImageFilters::DropShadow` 或 `SkImageFilters::DropShadowOnly` 图像滤镜。`sksg::ImageFilterEffect` 将该图像滤镜节点应用到子渲染节点上。

这种两层抽象的设计使得：
1. 投影参数（颜色、偏移、模糊）通过 DropShadowImageFilter 节点的属性进行管理
2. 参数变化触发 Scene Graph 的失效和重验证
3. ImageFilterEffect 负责在渲染时正确应用滤镜

### 不透明度范围说明

投影效果的不透明度参数范围是 0-255（8 位整数范围），与大多数其他效果的 0-100 百分比范围不同。这与 AE 内部投影效果的不透明度表示方式一致。`SkScalarRoundToInt` 将浮点值四舍五入到最近的整数，`SkTPin` 限制在 [0, 255] 范围内，然后通过 `SkColorSetA` 设置到阴影颜色的 alpha 通道。

### kBlurSizeToSigma 常量

`kBlurSizeToSigma` 定义在 `Effects.h` 中，用于将 AE 的模糊/柔和度参数值转换为 Skia 高斯模糊的 sigma 参数。AE 的模糊值通常表示模糊的视觉大小（直径或半径），而 Skia 使用高斯函数的标准差（sigma）。两者的关系约为 `sigma ≈ size * kBlurSizeToSigma`。这个常量在多个效果（投影、高斯模糊等）中共享使用。

### 默认参数值

投影效果的默认参数值反映了 AE 中投影效果的常见初始状态：
- 颜色：黑色（`{0, 0, 0, 1}`），最常见的阴影颜色
- 不透明度：255（完全不透明），确保阴影可见
- 方向/距离/柔和度：均为 0，初始状态下阴影不可见（需要用户调整）
- 仅阴影模式：0（关闭），默认同时显示阴影和前景

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder、kBlurSizeToSigma
- `modules/sksg/include/SkSGRenderEffect.h` - DropShadowImageFilter / ImageFilterEffect
- `modules/skottie/src/animator/Animator.h` - AnimatablePropertyContainer
- `modules/skottie/src/effects/SharpenEffect.cpp` - 另一个使用 ImageFilter 的效果
