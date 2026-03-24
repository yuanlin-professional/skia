# SharpenEffect - Skottie 锐化效果

> 源文件: `modules/skottie/src/effects/SharpenEffect.cpp`

## 概述

SharpenEffect 实现了 After Effects 中的锐化（Sharpen）效果。该效果通过 3x3 矩阵卷积滤镜增强图像边缘细节，使用单一的锐化强度参数控制效果程度。实现基于 Skia 的 `SkImageFilters::MatrixConvolution` 图像滤镜，将效果应用为图层级别的图像滤镜。

## 架构位置

SharpenEffect 位于 Skottie 效果子系统中，使用图像滤镜效果（ImageFilterEffect）管线。

```
EffectBuilder::attachSharpenEffect()
  |
  +-> SharpenAdapter (效果适配器)
  |     +-> DiscardableAdapterBase<..., sksg::ExternalImageFilter>
  |     +-> EffectBinder [绑定 Amount 参数]
  |     +-> onSync() [构建卷积核并设置滤镜]
  |
  +-> sksg::ImageFilterEffect [应用图像滤镜到图层]
```

## 主要类与结构体

### SharpenAdapter
- 继承自 `DiscardableAdapterBase<SharpenAdapter, sksg::ExternalImageFilter>`
- 单一属性 `fAmount`（锐化强度，百分比）
- `onSync()` 方法根据 fAmount 构建 3x3 卷积核并设置到 ExternalImageFilter 节点

## 公共 API 函数

### `EffectBuilder::attachSharpenEffect`
```cpp
sk_sp<sksg::RenderNode> attachSharpenEffect(const skjson::ArrayValue& jprops,
                                             sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `SharpenAdapter` 绑定动画参数
- 创建 `sksg::ImageFilterEffect` 将图像滤镜应用到图层
- 返回包装后的渲染节点

## 内部实现细节

### 卷积核构建
```cpp
SkScalar intensity = 1 + (fAmount * 0.01f);
SkScalar discount = (1 - intensity) / 8.0f;
SkScalar kernel[9] = {
    discount, discount, discount,
    discount, intensity, discount,
    discount, discount, discount,
};
```

- `intensity` = 1 + fAmount/100（fAmount=0 时无效果，fAmount=100 时 intensity=2）
- `discount` = (1 - intensity) / 8（8 个邻居像素的权重）
- 核心特性：中心像素权重 = `intensity`，周围 8 个像素权重 = `discount`
- 核权重之和 = `intensity + 8 * discount = intensity + (1 - intensity) = 1`（归一化）
- fAmount > 0 时：intensity > 1，discount < 0，增强中心像素并减去周围，实现锐化
- fAmount < 0 时：intensity < 1，discount > 0，模糊效果

### MatrixConvolution 参数
- 核大小：3x3
- gain：1（不缩放）
- bias：0（不偏移）
- 核原点：(1,1)（中心）
- 平铺模式：`SkTileMode::kRepeat`（边缘像素重复采样）
- convolveAlpha：`true`（同时处理 alpha 通道）

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkImageFilter.h` / `SkImageFilters.h` | MatrixConvolution 图像滤镜 |
| `Adapter.h` | DiscardableAdapterBase 基类 |
| `Effects.h` | EffectBinder 属性绑定 |
| `SkSGRenderEffect.h` | ExternalImageFilter / ImageFilterEffect |
| `SkottieValue.h` | ScalarValue 类型 |
| `SkottiePriv.h` | AnimationBuilder 定义 |

## 设计模式与设计决策

- **适配器模式**：`SharpenAdapter` 将 AE 的锐化参数映射到 Skia 的矩阵卷积滤镜参数。
- **归一化卷积核**：核权重之和恒为 1，确保锐化不改变整体亮度。
- **图像滤镜管线**：通过 `ExternalImageFilter` + `ImageFilterEffect` 的组合，将锐化作为后处理滤镜应用，不修改原始图层内容。
- **百分比参数映射**：fAmount 以百分比表示，通过 `* 0.01f` 转换，AE 惯例。

## 性能考量

- 3x3 卷积核是最小的实用卷积核大小，GPU 实现高效。
- 每帧仅在参数变化时重建滤镜对象。
- `SkTileMode::kRepeat` 避免边缘像素的特殊处理。
- 图像滤镜通过 Skia 的 GPU 管线执行，利用硬件加速。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase
- `modules/sksg/include/SkSGRenderEffect.h` - ExternalImageFilter / ImageFilterEffect
- `include/effects/SkImageFilters.h` - MatrixConvolution API
