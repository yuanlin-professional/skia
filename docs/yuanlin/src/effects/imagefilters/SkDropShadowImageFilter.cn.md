# SkDropShadowImageFilter

> 源文件: `src/effects/imagefilters/SkDropShadowImageFilter.cpp`

## 概述

`SkDropShadowImageFilter` 实现了投影(Drop Shadow)图像滤镜效果。与其他图像滤镜不同,该滤镜不再是一个独立的 `SkImageFilter_Base` 子类,而是通过组合现有的图像滤镜构建而成。投影效果被分解为:模糊 -> 着色 -> 偏移 -> 合并(可选)的滤镜图。

## 架构位置

```
SkImageFilters::DropShadow()  ->  组合式滤镜图:
                                    input
                                      │
                                  ┌───┴───┐
                              Blur(sigmaX, sigmaY)
                                      │
                              ColorFilter(Blend(color, SrcIn))
                                      │
                              MatrixTransform(Translate(dx,dy), Linear)
                                      │
                              ┌───────┴───────┐
                           Merge(shadow, input)   ← 仅非 shadowOnly 模式
                                      │
                              Crop(cropRect)       ← 若提供了 cropRect
```

## 主要类与结构体

该文件不定义新的 `SkImageFilter_Base` 子类。仅包含辅助函数和遗留反序列化支持。

### `make_drop_shadow_graph()` (内部函数)
构建投影滤镜图的核心函数,参数:
- `offset`: 阴影偏移向量
- `sigma`: 模糊半径
- `color`: 阴影颜色(支持 SkColor4f 和色彩空间)
- `shadowOnly`: 是否仅显示阴影(不叠加原图)

### `legacy_drop_shadow_create_proc()` (内部函数)
旧版 SKP 的反序列化支持。新版 SKP 直接序列化组合滤镜图。

## 公共 API 函数

### `SkImageFilters::DropShadow(dx, dy, sigmaX, sigmaY, color, colorSpace, input, cropRect)`
创建投影+前景滤镜。

### `SkImageFilters::DropShadowOnly(dx, dy, sigmaX, sigmaY, color, colorSpace, input, cropRect)`
创建仅投影滤镜(不叠加原图)。

## 内部实现细节

### 滤镜图构建
1. **模糊**: `SkImageFilters::Blur(sigma.fWidth, sigma.fHeight, input)`
2. **着色**: `SkImageFilters::ColorFilter(SkColorFilters::Blend(color, cs, kSrcIn), ...)`
   - 使用 `kSrcIn` 混合模式保留模糊后的 alpha 轮廓,填充阴影颜色
3. **偏移**: `SkImageFilters::MatrixTransform(Translate(dx,dy), kLinear, ...)`
   - 使用线性采样而非最近邻,隐藏模糊后分数偏移产生的锯齿
4. **合并**: `SkImageFilters::Merge(shadow, input)` (非 shadowOnly 时)
   - 使用 Merge 而非 Blend(kSrcOver),因为阴影和原图的边界通常不同
   - Merge 让每个子滤镜独立绘制,避免 Blend 的统一边界求值带来的瓦片边缘问题

### Merge vs Blend 的选择
代码注释详细说明了为什么使用 `Merge` 而非 `Blend(kSrcOver)`:
- Blend 用单个着色器求值两个子输入的并集区域
- 当阴影和原图边界不一致时,Blend 会对超出范围的像素求值瓦片边缘条件
- Merge 让每个子输入独立绘制到各自的边界范围,性能更优

### 遗留序列化支持
- 旧版 SKP 存储独立的 DropShadow flattenable,包含偏移、sigma、颜色和模式
- 新版 SKP 直接存储组合滤镜图,无需专门的 flattenable
- `legacy_drop_shadow_create_proc` 检查版本号,仅处理旧版数据

### SkColor4f 支持
颜色参数使用 `SkColor4f` 和 `sk_sp<SkColorSpace>`,支持广色域阴影。遗留代码使用 `SkColor`(`nullptr` 色彩空间)。

## 依赖关系

- `include/effects/SkImageFilters.h` - 子滤镜工厂方法
- `include/core/SkBlendMode.h` - `kSrcIn` 混合模式
- `include/core/SkColorFilter.h` / `SkColorSpace.h` - 颜色处理
- `src/core/SkImageFilter_Base.h` - `Unflatten` 工具函数
- `src/core/SkPicturePriv.h` - SKP 版本常量

## 设计模式与设计决策

### 组合优于继承
投影效果不再是独立的滤镜子类,而是组合现有滤镜构建。这体现了 "偏好组合优于继承" 的设计原则:
- 减少了代码重复(模糊、偏移、裁剪等逻辑复用现有实现)
- 序列化由组合滤镜各自处理,无需专门的序列化代码
- 每个子滤镜的优化自动应用于投影效果

### 渐进式迁移
通过注册旧名称的反序列化回调,实现了从独立 flattenable 到组合滤镜的平滑迁移。新版 SKP 不再需要专门的投影 flattenable。

## 性能考量

- 组合式实现让每个子步骤共享 FilterResult 的延迟求值优化
- Merge 的使用避免了 Blend 在不一致边界上的额外求值开销
- 线性采样的偏移确保模糊效果的视觉平滑性
- 若整个投影在期望输出之外,模糊和着色步骤会自然跳过

## DropShadow 与 DropShadowOnly 的差异

| 特性 | DropShadow | DropShadowOnly |
|------|-----------|---------------|
| 输出内容 | 阴影 + 原图叠加 | 仅阴影 |
| 滤镜图尾部 | Merge(shadow, input) | 无 Merge |
| 输出边界 | 阴影和原图的并集 | 仅阴影范围 |
| SVG 对应 | flood-opacity="1" 的完整效果 | 可用于后续自定义合成 |

## 滤镜图构建细节

完整的 DropShadow 滤镜图等价于:
```
crop(
  merge(
    matrixTransform(Translate(dx,dy), Linear,
      colorFilter(Blend(color, SrcIn),
        blur(sigmaX, sigmaY,
          input))),
    input),
  cropRect)
```

每个子步骤的作用:
1. `blur`: 将输入的轮廓扩散,产生柔和的阴影形状
2. `colorFilter(SrcIn)`: 保留模糊后的 alpha 通道,填充阴影颜色
3. `matrixTransform`: 将着色后的阴影偏移到指定位置
4. `merge`: 将阴影和原图按 src-over 合并

使用 `kLinear` 采样而非 `kNearest` 的偏移是一个重要的设计选择:
- Blur 后的输出可能包含非整数像素偏移的有效信息
- 最近邻采样会在偏移时产生锯齿状伪影
- 线性采样确保偏移后的输出平滑

## 色彩空间支持

DropShadow 支持 `SkColor4f` + `sk_sp<SkColorSpace>` 的颜色参数:
- 允许在广色域(如 Display P3)中指定阴影颜色
- 颜色空间传递给 `SkColorFilters::Blend`,确保颜色在正确的空间中混合
- 遗留 API 使用 `SkColor`(sRGB 8-bit),内部转换为 `SkColor4f` + nullptr colorSpace

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/effects/imagefilters/SkBlurImageFilter.cpp` - 模糊子步骤
- `src/effects/imagefilters/SkColorFilterImageFilter.cpp` - 着色子步骤
- `src/effects/imagefilters/SkMatrixTransformImageFilter.cpp` - 偏移子步骤
- `src/effects/imagefilters/SkMergeImageFilter.cpp` - 合并子步骤
- `src/effects/imagefilters/SkCropImageFilter.cpp` - 裁剪子步骤
