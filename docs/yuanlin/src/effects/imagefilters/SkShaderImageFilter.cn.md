# SkShaderImageFilter

> 源文件: `src/effects/imagefilters/SkShaderImageFilter.cpp`

## 概述

`SkShaderImageFilter` 实现了将 `SkShader`（着色器）作为图像滤镜输出的功能。它是一个叶子滤镜,使用提供的着色器在整个输出区域生成像素,不依赖任何输入图像。该滤镜可以将任意 SkShader(渐变、图案、噪声等)嵌入到图像滤镜管线中,作为图像源或效果生成器使用。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkShaderImageFilter (本文件)
            └─ 叶子滤镜,无输入子滤镜
            └─ 持有 sk_sp<SkShader>

工厂方法: SkImageFilters::Shader(shader, dither, cropRect)
```

## 主要类与结构体

### `SkShaderImageFilter`
- 继承自 `SkImageFilter_Base`，构造时传递 `nullptr, 0`（无子滤镜输入）
- **成员变量**:
  - `fShader` (`sk_sp<SkShader>`): 着色器对象（非空）
  - `fDither` (`SkImageFilters::Dither`): 是否启用抖动

## 公共 API 函数

### `SkImageFilters::Shader(shader, dither, cropRect) -> sk_sp<SkImageFilter>`
创建着色器滤镜。处理逻辑:
- null 着色器返回 `SkImageFilters::Empty()`
- 若提供 cropRect,在外层包裹 Crop 滤镜

### `computeFastBounds(const SkRect&) const -> SkRect`
返回 `SkRectPriv::MakeLargeS32()`(无限边界),因为着色器可以在任何位置产生非透明像素。

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 委托给 `FilterResult::MakeFromShader(ctx, fShader, dither)`,使用着色器填充期望输出区域。

### 边界计算
- `onGetInputLayerBounds()`: 返回空矩形(叶子滤镜)
- `onGetOutputLayerBounds()`: 返回 `Unbounded()`(着色器输出理论上无界)
- 注释提到可以检查着色器是否包含 decal 平铺模式来确定有界输出,但目前未实现

### 透明黑色影响
`onAffectsTransparentBlack()` 返回 `true`,因为着色器会在整个区域生成像素,包括原本透明的区域。

### 矩阵能力
声明 `MatrixCapability::kComplex`,着色器可以在任意变换下正确评估。

### 序列化兼容
- 旧版存储完整的 `SkPaint`,新版仅存储 `SkShader` 和 dither 布尔值
- `CreateProc` 根据版本号选择解析方式:
  - 旧版:读取 SkPaint,提取 shader(null 则用颜色创建)和 dither
  - 新版:直接读取 shader + bool
- 注册了旧名称 `SkPaintImageFilter` 和 `SkPaintImageFilterImpl`

## 依赖关系

- `include/core/SkShader.h` - 着色器接口
- `include/core/SkPaint.h` - 旧版兼容的 Paint 读取
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkRectPriv.h` - 无限边界工具

## 设计模式与设计决策

### 叶子滤镜模式
与 `SkImageImageFilter` 和 `SkPictureImageFilter` 共享相同的叶子节点设计理念。

### Shader 抽象
使用 `SkShader` 作为通用像素生成器,允许任何类型的着色器(渐变、图像、噪声、运行时)被用作图像滤镜源。

### 从 Paint 到 Shader 的简化
旧版 `SkPaintImageFilter` 接受完整的 SkPaint,但实际只需要 shader 和 dither。新版简化了接口,仅保留必要参数。

### Dither 枚举
使用 `SkImageFilters::Dither` 枚举而非原始 bool,提高 API 的可读性和类型安全性。

## 性能考量

- 作为叶子滤镜,无子树求值开销
- 着色器评估在期望输出区域内进行
- 无 cropRect 时输出无界,可能导致处理区域较大;建议使用 cropRect 限制
- `MakeFromShader` 可能延迟着色器求值到绘制时

## 使用场景

1. **渐变背景**: 使用渐变着色器作为滤镜链中的背景源
2. **噪声生成**: 使用 Perlin 噪声着色器生成纹理作为后续效果的输入
3. **图案填充**: 使用图像着色器(带平铺)创建重复图案
4. **纯色层**: 使用颜色着色器创建纯色图层(等同于旧版 PaintImageFilter 的颜色功能)
5. **运行时效果**: 使用 SkRuntimeShader 生成自定义像素模式

## 从 PaintImageFilter 的演进

旧版 `SkPaintImageFilter` 接受完整的 `SkPaint`,但实际仅使用两个属性:
- `paint.refShader()` -> 着色器(若为 null,使用 paint 的颜色创建纯色着色器)
- `paint.isDither()` -> 抖动标志

新版简化为仅接受 `SkShader` 和 `Dither` 参数,更精确地表达了滤镜的实际功能。

反序列化兼容性:
- 旧版: 读取完整 SkPaint,提取 shader 和 dither
- 新版: 直接读取 shader + bool

## 与其他叶子滤镜的功能对比

| 特性 | ShaderImageFilter | ImageImageFilter | PictureImageFilter |
|------|-------------------|-----------------|-------------------|
| 输入类型 | SkShader | SkImage | SkPicture |
| 输出边界 | 无界 | 有界(dstRect) | 有界(cullRect) |
| 影响透明黑色 | 是 | 否 | 否 |
| 分辨率 | 程序化生成 | 固定位图 | 矢量回放 |
| 典型用途 | 渐变/噪声/图案 | 图像叠加 | 矢量绘制 |

## 着色器类型的无界特性

该滤镜将输出声明为无界(`Unbounded()`),这是因为:
- 大多数着色器(渐变、噪声、运行时效果)在整个坐标空间中定义
- 检查着色器是否有界(如 decal 平铺的图像着色器)需要深入检查着色器树
- 目前未实现此优化,因此保守地返回无界

建议:当使用 ShaderImageFilter 时,总是提供 `cropRect` 参数来限制输出范围。

## 版本兼容性

- 旧版名称: `SkPaintImageFilter` / `SkPaintImageFilterImpl`
- 旧版序列化: 完整 SkPaint 对象
- 新版序列化 (>= kShaderImageFilterSerializeShader): SkShader flattenable + bool dither
- `CreateProc` 根据版本号自动选择正确的反序列化路径

## 边界计算

作为叶子滤镜:
- 输入边界: 始终为空(不依赖任何输入)
- 输出边界: `Unbounded()`(着色器可在任何位置产生像素)
- 快速边界: `MakeLargeS32()`(与输出边界一致)

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `include/core/SkShader.h` - SkShader API
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/effects/imagefilters/SkImageImageFilter.cpp` - 类似的叶子滤镜(基于图像)
- `src/effects/imagefilters/SkPictureImageFilter.cpp` - 类似的叶子滤镜(基于图片)
