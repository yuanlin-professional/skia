# SkBlurImageFilter

> 源文件: `src/effects/imagefilters/SkBlurImageFilter.cpp`

## 概述

`SkBlurImageFilter` 实现了高斯模糊图像滤镜,对应 SVG 的 `feGaussianBlur` 滤镜。该滤镜使用高斯核对输入图像进行卷积,通过 sigma 参数控制 X 和 Y 方向的模糊半径。它是 Skia 中使用最广泛的图像滤镜之一,被投影效果、发光效果和各种 UI 模糊场景所依赖。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkBlurImageFilter (本文件)
            └─ 输入[0]: 待模糊的子滤镜
            └─ 委托给 SkBlurEngine (后端特定实现)

工厂方法: SkImageFilters::Blur(sigmaX, sigmaY, tileMode, input, cropRect)
```

模糊的实际执行委托给 `SkBlurEngine`，不同的 GPU 后端提供各自的实现。

## 主要类与结构体

### `SkBlurImageFilter`
- 继承自 `SkImageFilter_Base`，接收一个子滤镜输入
- **成员变量**:
  - `fSigma` (`skif::ParameterSpace<SkSize>`): X/Y 方向的模糊 sigma 值
  - `fLegacyTileMode` (`SkTileMode`): 遗留平铺模式(kDecal 表示无遗留平铺)
- 两个构造函数: 标准版和遗留平铺版

## 公共 API 函数

### `SkImageFilters::Blur(sigmaX, sigmaY, tileMode, input, cropRect)`
创建模糊滤镜。复杂的平铺处理逻辑:
- sigma 必须非负且有限
- **无 cropRect + 非 Decal 模式**: 使用遗留构造函数(临时支持)
- **有 cropRect + 非 Decal 模式**: 先用 `Crop(cropRect, tileMode, input)` 限制输入,再模糊,再用 `Crop(cropRect, kDecal)` 限制输出
- **Decal 模式**: 创建模糊滤镜,若有 cropRect 则外包 Crop

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 的工作流程:
1. 扩展期望输出 3*sigma 像素(核范围)获取子滤镜输出
2. 映射 sigma 到图层空间并校验
3. 若两个方向的 sigma 都为 0，直接返回子输出
4. 处理遗留平铺模式(将子输出的边界作为裁剪区域)
5. 使用 `FilterResult::Builder::blur(sigma)` 执行模糊

### Sigma 映射和裁剪
`mapSigma()` 方法:
- 将参数空间 sigma 映射到图层空间
- 裁剪到最大值 `kMaxSigma = 532.f`(对应约 1000 像素的 box blur 核)
- 禁用非有限或过小的 sigma 轴(`SkBlurEngine::IsEffectivelyIdentity`)

### 核边界计算
`kernelBounds()`: 输入需要在每个方向扩展 `ceil(3 * sigma)` 像素。3 sigma 覆盖了高斯核约 99.7% 的能量。

### 遗留平铺支持
当 `fLegacyTileMode != kDecal` 时(无 cropRect 的旧 API 调用):
- 使用子输出的实际边界作为虚拟裁剪区域
- 通过 `applyCrop(bounds, tileMode)` 设置边缘平铺行为
- 输出范围为核扩展后的子输出边界(与期望输出取交集)

### WebKit/Firefox 兼容性
`kMaxSigma = 532.f` 这个值确保光栅路径的 box blur 核不超过 1000 像素,与 WebKit 和 Firefox 的实现匹配。GPU 路径不使用 box blur,但限制 sigma 确保两种路径的行为一致。

## 依赖关系

- `src/core/SkBlurEngine.h` - 模糊引擎抽象接口
- `include/core/SkTileMode.h` - 平铺模式
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类

## 设计模式与设计决策

### 分离的平铺处理
新 API 将平铺通过外部 Crop 滤镜处理:输入裁剪(非 Decal 平铺)和输出裁剪(Decal)分别由两个 Crop 节点完成。这使得模糊滤镜本身只需关注模糊逻辑。

### 遗留兼容层
`fLegacyTileMode` 保持了无 cropRect 时旧 API 的行为,避免破坏现有客户端代码。注释明确标注这是临时方案,应在客户端迁移后删除。

### 引擎抽象
实际的模糊算法由 `SkBlurEngine` 实现,不同后端(CPU/GPU)提供各自的优化实现。滤镜层仅负责参数管理和边界计算。

## 性能考量

- 3 sigma 截断在能量损失(0.3%)和性能之间取得了良好平衡
- sigma 上限 532 防止极大核导致的性能退化
- 有效恒等 sigma 检测(`IsEffectivelyIdentity`)避免不必要的模糊操作
- `FilterResult::Builder::blur()` 可以自动优化输出区域
- 遗留平铺的 `applyCrop` 延迟到模糊前执行,可能与模糊操作合并

## 模糊核大小与 Sigma 的关系

高斯核在 3*sigma 处的能量覆盖约 99.7%。`kernelBounds()` 使用 ceil(3*sigma) 作为扩展量:

| sigma | 核扩展(像素) | 核直径 | 采样次数(box blur) |
|-------|-------------|--------|-------------------|
| 1.0 | 3 | 7 | 7 |
| 5.0 | 15 | 31 | 31 |
| 50.0 | 150 | 301 | 301 |
| 532.0 | 1596 | ~3193 | ~1000 (实际 box blur 限制) |

最大 sigma 532 对应的 box blur 核约 1000 像素,与 WebKit 和 Firefox 的实现匹配。

## 平铺模式处理流程

新 API 的平铺处理分为三种情况:

**情况 1: kDecal + 无 cropRect** (最简单)
```
Blur(sigma, input)
```

**情况 2: kDecal + 有 cropRect**
```
Crop(cropRect, Decal, Blur(sigma, input))
```

**情况 3: 非 Decal + 有 cropRect** (最复杂)
```
Crop(cropRect, Decal,
  Blur(sigma,
    Crop(cropRect, tileMode, input)))
```
内层 Crop 将输入限制到 cropRect 并设置边缘平铺,外层 Crop 确保输出不超过 cropRect。

**遗留情况: 非 Decal + 无 cropRect**
```
SkBlurImageFilter(sigma, legacyTileMode, input)
```
使用遗留构造函数,在 `onFilterImage` 中使用子输出的实际边界作为虚拟裁剪矩形。

## Sigma 映射与裁剪

`mapSigma()` 的完整处理流程:
1. 将参数空间 sigma 映射到图层空间: `sigma_layer = mapping.paramToLayer(sigma)`
2. 裁剪到最大值: `min(sigma_layer, kMaxSigma)` (每个轴独立)
3. 有效恒等检测: 若 sigma < 某阈值,视为 0(无模糊)
4. 非有限值检测: 非有限 sigma 设为 0

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkBlurEngine.h` - 模糊引擎接口
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/effects/imagefilters/SkCropImageFilter.cpp` - 平铺处理
- `src/effects/imagefilters/SkDropShadowImageFilter.cpp` - 依赖模糊的投影效果
