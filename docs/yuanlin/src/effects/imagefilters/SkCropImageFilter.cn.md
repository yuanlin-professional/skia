# SkCropImageFilter

> 源文件: `src/effects/imagefilters/SkCropImageFilter.cpp`

## 概述

`SkCropImageFilter` 实现了图像滤镜的裁剪和平铺功能。它将子滤镜的输出限制在指定的矩形区域内,并支持多种平铺模式(Decal/Clamp/Repeat/Mirror)。该滤镜是 Skia 图像滤镜系统中的基础组件,几乎所有其他滤镜在提供 cropRect 参数时都会在外层包裹一个 SkCropImageFilter。它同时也实现了旧版 `SkImageFilters::Tile()` 的功能。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkCropImageFilter (本文件)
            └─ 输入[0]: 被裁剪的子滤镜

工厂方法:
  SkImageFilters::Crop(rect, tileMode, input)
  SkImageFilters::Empty()           ← 空矩形 + Decal 模式
  SkImageFilters::Tile(src, dst)    ← 双层 Crop 实现
```

## 主要类与结构体

### `SkCropImageFilter`
- 继承自 `SkImageFilter_Base`，接收一个子滤镜输入
- **成员变量**:
  - `fCropRect` (`skif::ParameterSpace<SkRect>`): 裁剪矩形(参数空间浮点数)
  - `fTileMode` (`SkTileMode`): 平铺模式

## 公共 API 函数

### `SkImageFilters::Crop(rect, tileMode, input)`
创建裁剪滤镜。验证裁剪矩形必须有效(`SkIsValidRect`)。

### `SkImageFilters::Empty()`
创建空滤镜(空矩形 + kDecal 模式)。利用裁剪滤镜的空矩形处理逻辑。

### `SkImageFilters::Tile(src, dst, input)`
创建平铺滤镜,实现为两层裁剪:
1. 内层: `Crop(src, kRepeat, input)` - 以重复模式裁剪到源区域
2. 外层: `Crop(dst, kDecal, ...)` - 以衰减模式裁剪到目标区域

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()`:
1. 计算满足裁剪矩形所需的输入区域
2. 获取子滤镜在该区域的输出
3. 调用 `childOutput.applyCrop(context, cropRect, tileMode)` 应用裁剪和平铺

### 裁剪矩形的像素圆整
`cropRect()` 方法根据平铺模式选择不同的圆整策略:
- **kDecal**: `roundOut()`(向外取整) - 保留分数像素的部分覆盖,产生自然的抗锯齿边缘
- **其他模式**: `roundIn()`(向内取整) - 避免分数覆盖引入的透明度被平铺放大

### 所需输入计算
`requiredInput()` 使用 `cropRect.relevantSubset(outputBounds, tileMode)` 计算:
- kDecal: 裁剪矩形与输出的交集
- kRepeat/kMirror/kClamp: 需要完整的裁剪矩形内容才能正确平铺

### 输出边界计算
`onGetOutputLayerBounds()`:
- 若子输出与裁剪矩形无交集,输出为空
- kDecal 模式: 输出为裁剪矩形(有界)
- 其他模式: 裁剪矩形内有非透明内容时输出无界

### 透明黑色影响
- `onAffectsTransparentBlack()`: 仅非 kDecal 模式影响透明黑色(平铺会在裁剪区域外产生非透明内容)
- `ignoreInputsAffectsTransparentBlack()`: 返回 true,阻止递归检查子滤镜的透明黑色影响

### 序列化兼容
- 支持旧版 `SkTileImageFilter` 的反序列化(双矩形格式 -> Tile())
- 新版支持平铺模式字段(版本 >= kCropImageFilterSupportsTiling)

## 依赖关系

- `include/core/SkTileMode.h` - 平铺模式枚举
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkValidationUtils.h` - `SkIsValidRect` 验证

## 设计模式与设计决策

### CropRect 统一化
Skia 将所有滤镜的 cropRect 参数转化为外层的 `SkCropImageFilter`,而非在每个滤镜内部处理裁剪。这大大简化了其他滤镜的实现。

### Tile 作为双层 Crop
`Tile(src, dst)` 被优雅地实现为 `Crop(dst, Decal, Crop(src, Repeat, input))`，复用了裁剪滤镜的平铺支持。

### Empty 作为特殊 Crop
`Empty()` 滤镜使用空矩形的裁剪滤镜实现，利用了裁剪逻辑对空矩形的正确处理。

### 圆整策略区分
Decal 和非 Decal 模式使用不同的圆整方向，这一精细的设计决策避免了平铺时边缘透明度被放大的视觉问题。

## 性能考量

- 裁剪操作将子滤镜的期望输出限制为裁剪矩形与实际需求的相关子集
- kDecal 模式产生有界输出,可以有效限制后续滤镜的处理范围
- `applyCrop` 可能延迟到最终绘制时执行,与其他操作合并
- `relevantSubset` 在 Repeat/Mirror 模式下精确计算所需的源数据范围

## 平铺模式行为详解

| 模式 | 裁剪矩形外的行为 | 输出范围 | 圆整方向 | 典型用途 |
|------|----------------|---------|---------|---------|
| kDecal | 透明 | 有界(=裁剪矩形) | 向外 | 标准裁剪 |
| kClamp | 边缘像素拉伸 | 无界 | 向内 | 背景扩展 |
| kRepeat | 内容重复 | 无界 | 向内 | 图案平铺 |
| kMirror | 内容镜像重复 | 无界 | 向内 | 对称平铺 |

向内圆整对非 Decal 模式至关重要:若向外圆整,分数像素处的透明度会被平铺放大,在 Clamp 模式下尤为明显(边缘半透明像素被无限拉伸)。

## Crop 在滤镜系统中的核心地位

几乎所有图像滤镜的 `cropRect` 参数都转化为外层的 SkCropImageFilter:

```
SkImageFilters::Blur(sigma, input, cropRect)
  -> Crop(cropRect, Decal, Blur(sigma, input))

SkImageFilters::Blur(sigma, tileMode, input, cropRect)
  -> Crop(cropRect, Decal, Blur(sigma, Crop(cropRect, tileMode, input)))

SkImageFilters::Empty()
  -> Crop(EmptyRect, Decal, nullptr)

SkImageFilters::Tile(src, dst, input)
  -> Crop(dst, Decal, Crop(src, Repeat, input))
```

这种设计将裁剪逻辑集中在一个类中,其他滤镜不需要各自实现裁剪。

## requiredInput 与 relevantSubset

`requiredInput` 方法委托给 `cropRect.relevantSubset(outputBounds, tileMode)`:
- **kDecal**: 返回裁剪矩形与输出的交集(仅需可见部分)
- **kRepeat**: 需要完整裁剪矩形的一个周期(任何输出位置都可能采样到裁剪矩形内的任何像素)
- **kMirror**: 类似 Repeat
- **kClamp**: 需要完整裁剪矩形(边缘像素会被无限拉伸)

## 版本兼容性

- 旧版 `SkTileImageFilter` / `SkTileImageFilterImpl` -> 通过 `LegacyTileCreateProc` 转换为 Tile()
- 旧版无平铺模式字段(版本 < kCropImageFilterSupportsTiling 时默认 kDecal)
- 新版序列化: 基类数据 + cropRect(SkRect) + tileMode(int32)

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/core/SkValidationUtils.h` - 矩形验证工具
