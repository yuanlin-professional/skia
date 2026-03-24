# ShadowStyles

> 源文件: modules/skottie/src/effects/ShadowStyles.cpp

## 概述

ShadowStyles 模块实现了 Skottie 动画库中的阴影样式效果,包括投影(Drop Shadow)和内阴影(Inner Shadow)。该模块遵循 SVG feDropShadow 规范,通过图像滤镜管线实现高质量的阴影渲染,为图层提供深度感和立体效果。

## 架构位置

ShadowStyles 位于 Skottie 效果系统的核心位置:

```
modules/skottie/
  └── src/
      └── effects/
          ├── ShadowStyles.cpp   # 阴影样式实现
          ├── Effects.h          # 效果接口
          └── GlowStyles.cpp     # 相关的发光效果
```

该模块与 GlowStyles 共享相似的架构模式,都基于图像滤镜管线构建复杂的视觉效果。

## 主要类与结构体

### ShadowAdapter

阴影效果适配器,管理阴影的颜色、模糊、偏移等参数。

```cpp
class ShadowAdapter final : public DiscardableAdapterBase<ShadowAdapter,
                                                          sksg::ExternalImageFilter>
```

**核心成员变量:**
- `Type fType` - 阴影类型(投影/内阴影)
- `ColorValue fColor` - 阴影颜色
- `ScalarValue fOpacity` - 不透明度(百分比,0-100)
- `ScalarValue fAngle` - 光源角度(度数)
- `ScalarValue fSize` - 模糊大小
- `ScalarValue fDistance` - 阴影距离

**类型枚举:**
```cpp
enum Type {
    kDropShadow,    // 投影阴影
    kInnerShadow,   // 内阴影
};
```

## 公共 API 函数

### attachDropShadowStyle

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachDropShadowStyle(
    const skjson::ObjectValue& jstyle,
    sk_sp<sksg::RenderNode> layer) const
```

为图层附加投影阴影效果。投影阴影渲染在图层下方,模拟光源照射产生的阴影。

**参数:**
- `jstyle` - JSON 样式配置,包含颜色、角度、距离等参数
- `layer` - 源渲染节点

**返回值:** 包装了阴影效果的渲染节点

### attachInnerShadowStyle

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachInnerShadowStyle(
    const skjson::ObjectValue& jstyle,
    sk_sp<sksg::RenderNode> layer) const
```

为图层附加内阴影效果。内阴影渲染在图层内部,创建凹陷或雕刻效果。

## 内部实现细节

### 阴影渲染管线

阴影效果遵循标准的 feDropShadow 规范,实现步骤如下:

1. **Alpha 提取与颜色化** - 提取源 alpha 通道并应用阴影颜色
2. **高斯模糊** - 对颜色化的 alpha 应用模糊
3. **位置偏移** - 根据角度和距离计算偏移量
4. **合成** - 将阴影与原图层合成

### 颜色矩阵变换

提取 alpha 并同时着色的颜色矩阵:

```cpp
SkColorMatrix cm{
    0, 0, 0,                  0, color.fR,
    0, 0, 0,                  0, color.fG,
    0, 0, 0,                  0, color.fB,
    0, 0, 0, opacity * color.fA,        0
};
```

这个矩阵实现了两个操作的融合:
- 选择 alpha 通道(第四列为 [0,0,0,opacity*alpha])
- 设置输出颜色(最后一列为 [R,G,B,0])

### 内阴影的 Alpha 反转

内阴影使用 alpha 反转来实现内部效果:

```cpp
if (fType == Type::kInnerShadow) {
    cm.preConcat({
        1, 0, 0, 0, 0,
        0, 1, 0, 0, 0,
        0, 0, 1, 0, 0,
        0, 0, 0,-1, 1   // alpha' = 1 - alpha
    });
}
```

### 偏移量计算

根据角度和距离计算阴影偏移:

```cpp
const auto rad = SkDegreesToRadians(180 + fAngle);  // 0度指向左侧(AE风格)
const auto offset = SkV2{
     fDistance * SkScalarCos(rad),
    -fDistance * SkScalarSin(rad)
};
```

角度加 180 度使得 0 度对应左侧,符合 After Effects 的约定。Y 轴取反是因为图形坐标系中 Y 轴向下。

### 滤镜链构建

```cpp
auto f = SkImageFilters::ColorFilter(SkColorFilters::Matrix(cm), nullptr);

if (sigma > 0) {
    f = SkImageFilters::Blur(sigma, sigma, std::move(f));
}

if (!SkScalarNearlyZero(offset.x) || !SkScalarNearlyZero(offset.y)) {
    f = SkImageFilters::Offset(offset.x, offset.y, std::move(f));
}
```

### 内阴影合成

内阴影需要额外的遮罩和合成步骤:

```cpp
if (fType == Type::kInnerShadow) {
    // 使用 DstIn 混合模式将阴影限制在源图像范围内
    f = SkImageFilters::Blend(SkBlendMode::kDstIn, std::move(f));

    // 交换源和阴影的顺序,使阴影绘制在上层
    std::swap(source, f);
}

this->node()->setImageFilter(SkImageFilters::Merge(std::move(f), std::move(source)));
```

## 依赖关系

### Skia 核心依赖
- `SkBlendMode` - 混合模式(kDstIn)
- `SkColorFilter` / `SkColorMatrix` - 颜色变换
- `SkImageFilter` - 滤镜基类
- `SkImageFilters` - 滤镜工厂(Blur, Offset, Blend, Merge)

### Skottie 框架依赖
- `Adapter.h` - `DiscardableAdapterBase` 基类
- `SkottiePriv.h` - `kBlurSizeToSigma` 等常量
- `SkottieValue.h` - `ColorValue`, `ScalarValue` 类型
- `effects/Effects.h` - `EffectBuilder` 接口

### Scene Graph 依赖
- `sksg::ExternalImageFilter` - 外部图像滤镜节点
- `sksg::ImageFilterEffect` - 滤镜效果包装器
- `sksg::RenderNode` - 渲染节点基类

## 设计模式与设计决策

### 适配器模式

`ShadowAdapter` 使用适配器模式桥接 Lottie 动画参数和 Skia 渲染系统,将声明式的阴影配置转换为命令式的滤镜链。

### 统一工厂函数

```cpp
static sk_sp<sksg::RenderNode> make_shadow_effect(
    const skjson::ObjectValue& jstyle,
    const AnimationBuilder& abuilder,
    sk_sp<sksg::RenderNode> layer,
    ShadowAdapter::Type type)
```

使用工厂函数消除投影和内阴影之间的代码重复,提升代码复用性。

### 规范遵循

实现严格遵循 W3C 的 feDropShadow 规范 [1],确保与标准图形系统的兼容性:
> [1] https://drafts.fxtf.org/filter-effects/#feDropShadowElement

### 条件滤镜

只在必要时添加滤镜节点:
- `sigma > 0` 才添加模糊
- 偏移非零才添加偏移滤镜

减少滤镜链长度,优化性能。

## 性能考量

### 矩阵融合优化

将 alpha 提取和颜色化合并为单个颜色矩阵操作,减少一次颜色滤镜调用。

### 模糊参数转换

```cpp
const auto sigma = fSize * kBlurSizeToSigma;
```

使用预定义常量 `kBlurSizeToSigma` 快速转换 AE 风格的模糊大小到 Skia sigma 值。

### 零值检测

```cpp
if (!SkScalarNearlyZero(offset.x) || !SkScalarNearlyZero(offset.y))
```

使用 `SkScalarNearlyZero` 避免创建无效果的偏移滤镜,同时处理浮点精度问题。

### 参数范围限制

```cpp
const auto opacity = SkTPin(fOpacity / 100, 0.0f, 1.0f);
```

使用 `SkTPin` 限制不透明度在 [0,1] 范围,防止非法值导致的渲染错误。

### 滤镜链最小化

通过条件构建和智能合并,确保滤镜链只包含必要的节点,减少 GPU 开销。

## 相关文件

- `modules/skottie/src/effects/GlowStyles.cpp` - 发光效果(类似架构)
- `modules/skottie/src/effects/Effects.h` - 效果系统接口
- `modules/skottie/src/Adapter.h` - 适配器基类定义
- `modules/sksg/include/SkSGRenderEffect.h` - Scene Graph 渲染效果
- `include/effects/SkImageFilters.h` - Skia 图像滤镜 API
- `include/effects/SkColorMatrix.h` - 颜色矩阵工具
