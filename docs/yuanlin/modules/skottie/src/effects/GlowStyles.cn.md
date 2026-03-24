# GlowStyles

> 源文件: modules/skottie/src/effects/GlowStyles.cpp

## 概述

GlowStyles 模块实现了 Skottie 动画库中的发光样式效果,包括外发光(Outer Glow)和内发光(Inner Glow)两种视觉效果。该模块通过图像滤镜和颜色矩阵变换来实现类似 Adobe After Effects 中的发光效果,为图层提供模糊和颜色化的光晕处理。

## 架构位置

GlowStyles 位于 Skottie 动画引擎的效果系统中:

```
modules/skottie/
  └── src/
      └── effects/
          ├── GlowStyles.cpp     # 发光样式实现
          └── Effects.h          # 效果系统接口
```

该模块作为 EffectBuilder 的扩展,为图层渲染节点提供发光效果处理能力。它依赖于 Skia 的图像滤镜系统和场景图(Scene Graph)框架。

## 主要类与结构体

### GlowAdapter

发光效果适配器类,负责管理发光效果的参数和渲染。

```cpp
class GlowAdapter final : public DiscardableAdapterBase<GlowAdapter, sksg::ExternalImageFilter>
```

**关键成员变量:**
- `Type fType` - 发光类型(外发光或内发光)
- `ColorValue fColor` - 发光颜色
- `ScalarValue fOpacity` - 不透明度(百分比)
- `ScalarValue fSize` - 发光大小
- `ScalarValue fChoke` - 阻塞/扩散参数
- `ScalarValue fInnerSource` - 内发光源类型(边缘或中心)

**类型枚举:**
```cpp
enum Type {
    kOuterGlow,   // 外发光
    kInnerGlow,   // 内发光
};

enum InnerSource {
    kEdge   = 1,  // 边缘源
    kCenter = 2,  // 中心源
};
```

### EffectBuilder 扩展方法

EffectBuilder 类通过以下方法提供发光效果接口:

- `attachOuterGlowStyle()` - 附加外发光样式
- `attachInnerGlowStyle()` - 附加内发光样式

## 公共 API 函数

### attachOuterGlowStyle

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachOuterGlowStyle(
    const skjson::ObjectValue& jstyle,
    sk_sp<sksg::RenderNode> layer) const
```

为图层附加外发光效果。

**参数:**
- `jstyle` - JSON 格式的样式配置
- `layer` - 待处理的渲染节点

**返回值:** 包装了发光效果的新渲染节点

### attachInnerGlowStyle

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachInnerGlowStyle(
    const skjson::ObjectValue& jstyle,
    sk_sp<sksg::RenderNode> layer) const
```

为图层附加内发光效果。参数和返回值与 `attachOuterGlowStyle` 相同。

## 内部实现细节

### 发光效果渲染管线

发光效果的实现遵循以下步骤:

1. **Alpha 通道提取** - 使用颜色矩阵提取源图像的 alpha 通道
2. **颜色化处理** - 将 alpha 通道替换为发光颜色,同时应用不透明度
3. **模糊处理** - 应用高斯模糊,模糊强度由 `fSize * kBlurSizeToSigma` 计算
4. **阻塞/扩散** - 通过 alpha 缩放实现边缘扩散或收缩效果
5. **合成** - 将发光结果与原图像合成

### 颜色矩阵变换

提取 alpha 通道的基础矩阵:
```cpp
SkColorMatrix mask_cm{
    0, 0, 0, 0, 0,
    0, 0, 0, 0, 0,
    0, 0, 0, 0, 0,
    0, 0, 0, 1, 0
};
```

对于内发光的边缘模式,需要 alpha 反转:
```cpp
mask_cm.preConcat({
    1, 0, 0, 0, 0,
    0, 1, 0, 0, 0,
    0, 0, 1, 0, 0,
    0, 0, 0,-1, 1
});
```

### Choke/Spread 算法

阻塞参数控制发光的扩散程度:
- **choke = 0** - 无效果,保持原始模糊
- **choke = 1** - 所有非透明值变为完全不透明(最大扩散)
- **0 < choke < 1** - 非线性渐变过渡

实现使用 alpha 缩放因子:
```cpp
const auto alpha_scale = std::min(
    sk_ieee_float_divide(1, 1 - std::pow(choke, kChokeGamma)),
    kMaxAlphaScale
);
```

其中 `kChokeGamma = 0.2f` 用于非线性映射,`kMaxAlphaScale = 1e6f` 防止数值溢出。

### 内发光特殊处理

内发光需要额外的混合和遮罩步骤:
```cpp
// 使用 DstIn 模式将发光限制在源图像范围内
f = SkImageFilters::Blend(SkBlendMode::kDstIn, std::move(f));

// 将发光与原图像合并
this->node()->setImageFilter(SkImageFilters::Merge(std::move(f), std::move(source)));
```

## 依赖关系

### Skia 核心依赖
- `SkBlendMode` - 混合模式定义
- `SkColorFilter` / `SkColorMatrix` - 颜色变换
- `SkImageFilter` - 图像滤镜基础
- `SkImageFilters` - 滤镜工厂方法

### Skottie 内部依赖
- `Adapter.h` - 适配器基类
- `SkottiePriv.h` - 内部工具和常量
- `SkottieValue.h` - 可动画值类型
- `effects/Effects.h` - 效果系统接口

### Scene Graph 依赖
- `sksg::ExternalImageFilter` - 外部图像滤镜节点
- `sksg::ImageFilterEffect` - 图像滤镜效果包装器
- `sksg::RenderNode` - 渲染节点基类

## 设计模式与设计决策

### 适配器模式

`GlowAdapter` 继承自 `DiscardableAdapterBase`,使用适配器模式将 Lottie 动画格式的发光效果参数适配到 Skia 渲染系统。

### 可丢弃适配器

使用 `DiscardableAdapterBase` 允许在内存压力下释放不常用的效果资源,优化内存使用。

### 工厂方法模式

```cpp
static sk_sp<sksg::RenderNode> make_glow_effect(
    const skjson::ObjectValue& jstyle,
    const AnimationBuilder& abuilder,
    sk_sp<sksg::RenderNode> layer,
    GlowAdapter::Type type)
```

统一的工厂方法创建发光效果,减少外发光和内发光的代码重复。

### 延迟颜色化

当需要 alpha choke 时,颜色化步骤被推迟到 choke 处理之后,确保缩放后的 alpha 值被正确裁剪到 [0,1] 范围。

## 性能考量

### 模糊优化

- 使用 `kBlurSizeToSigma` 常量将 AE 样式的模糊大小转换为 Skia sigma 值
- 仅在 `sigma > 0` 时应用模糊滤镜,避免不必要的计算

### Choke 条件计算

```cpp
const auto requires_alpha_choke = (sigma > 0 && choke > 0);
```

仅在需要时创建额外的 choke 滤镜链,减少滤镜层数。

### 矩阵合并

当不需要 alpha choke 时,将颜色矩阵与遮罩矩阵合并:
```cpp
if (!requires_alpha_choke) {
    mask_cm.postConcat(color_cm);
}
```

减少颜色滤镜的数量,提升渲染性能。

### 数值稳定性

使用 `sk_ieee_float_divide` 和 `kMaxAlphaScale` 限制确保除法安全和 alpha 缩放的数值稳定性,避免浮点异常。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - 效果系统接口定义
- `modules/skottie/src/effects/ShadowStyles.cpp` - 阴影样式(类似实现)
- `modules/skottie/src/Adapter.h` - 适配器基类
- `modules/sksg/include/SkSGRenderEffect.h` - 渲染效果节点
- `include/effects/SkImageFilters.h` - Skia 图像滤镜 API
- `include/effects/SkColorMatrix.h` - 颜色矩阵变换工具
