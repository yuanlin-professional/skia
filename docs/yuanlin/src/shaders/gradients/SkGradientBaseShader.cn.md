# SkGradientBaseShader - 渐变着色器基类

> 源文件: `src/shaders/gradients/SkGradientBaseShader.h`, `src/shaders/gradients/SkGradientBaseShader.cpp`

## 概述

SkGradientBaseShader 是 Skia 中所有渐变着色器（线性、径向、扫描、锥形）的公共基类。它提供了颜色停靠点管理、颜色插值（包括多种色彩空间）、平铺模式处理、以及光栅化管线阶段生成等通用功能。此外还包含渐变序列化/反序列化的公共逻辑，以及在退化情况下的降级处理。

本文件还定义了 SkColor4fXformer 类用于将渐变颜色转换到中间色彩空间，支持 CSS Color Level 4 中定义的多种色彩空间插值方式（Lab、OKLab、HSL、HWB、LCH 等）。

## 架构位置

```
SkShaderBase
  └── SkGradientBaseShader (渐变基类)
        ├── SkLinearGradient
        ├── SkRadialGradient
        ├── SkSweepGradient
        └── SkConicalGradient
```

- **ShaderType**: 所有渐变子类统一返回 `ShaderType::kGradientBase`
- **模板方法模式**: 基类 `appendStages` 调用子类的 `appendGradientStages` 纯虚方法

## 主要类与结构体

### SkGradientBaseShader
**关键成员变量**:
- `fPtsToUnit` (SkMatrix): 点坐标到单位空间的变换矩阵
- `fColors` / `fPositions` — 颜色数组和位置数组（存储在 fStorage 中）
- `fColorSpace` — 渐变停靠颜色的色彩空间（默认 sRGB）
- `fInterpolation` — 插值设置（色彩空间、预乘、色相方法）
- `fTileMode` — 平铺模式
- `fColorCount` — 颜色数量（可能包含隐式首尾停靠点）
- `fFirstStopIsImplicit / fLastStopIsImplicit` — 是否自动添加了首/尾停靠点
- `fColorsAreOpaque` — 所有颜色是否不透明
- `fColorsAndOffsetsBitmap` — Graphite 后端用的缓存位图

**内联存储优化**: 使用 `AutoSTMalloc` 预留 4 个停靠点的内联空间，避免小渐变的堆分配。

### SkGradientScope
辅助类，用于渐变反序列化时临时存储颜色和位置数组。

### SkColor4fXformer
负责将渐变颜色从源色彩空间转换到插值色彩空间，并处理：
- 特殊色彩空间转换（Lab、OKLab、HSL、HWB、LCH 等）
- 无力色相（powerless hue）的处理（色度为零时色相无意义）
- 色相方法调整（Shorter、Longer、Increasing、Decreasing）
- 预乘 alpha（极坐标空间下色相不预乘）

### GradientSerializationFlags
序列化标志位枚举，用位掩码编码平铺模式、插值色彩空间、色相方法、预乘等信息。

## 公共 API 函数

### 静态方法
```cpp
static bool ValidGradient(SkSpan<const SkColor4f>, SkTileMode, const Interpolation&);
```
验证渐变参数是否合法。

```cpp
static sk_sp<SkShader> MakeDegenerateGradient(const SkGradient::Colors&);
```
创建退化渐变：Decal 返回空着色器，Repeat/Mirror 返回平均色，Clamp 返回最后一个颜色。

```cpp
static void AppendGradientFillStages(SkRasterPipeline*, SkArenaAlloc*,
                                     const SkPMColor4f*, const SkScalar*, int);
```
向管线追加渐变颜色填充阶段。支持三种情况：
- 2-stop 均匀分布（最快路径）
- N-stop 均匀分布
- 任意位置停靠点

```cpp
static void AppendInterpolatedToDstStages(SkRasterPipeline*, SkArenaAlloc*,
                                          bool colorsAreOpaque, const Interpolation&,
                                          const SkColorSpace* intermediate, const SkColorSpace* dst);
```
追加从插值色彩空间到目标色彩空间的转换阶段。

### 查询方法
- `getGradientMatrix()` — 获取 ptsToUnit 矩阵
- `getColorCount()` / `getPositions()` — 颜色数量和位置
- `getInterpolation()` — 插值参数
- `colors()` / `positions()` — 颜色和位置的 span
- `getTileMode()` — 平铺模式
- `isOpaque()` — 是否不透明
- `colorsAreOpaque()` — 所有颜色是否不透明

## 内部实现细节

### 停靠点规范化
构造函数处理以下情况：
1. 自动添加隐式首尾停靠点（pos[0]>0 或 pos[n-1]<1）
2. 位置单调递增保证（通过 SkTPin）
3. 均匀分布停靠点检测（均匀时设置 fPositions=nullptr 走快速路径）
4. 重复停靠点去重（保留最左和最右颜色，非 Clamp 模式下忽略边界重复）

### 渐变颜色填充
`AppendGradientFillStages` 将停靠点转化为线性方程组 `color = factor * t + bias`：
- **均匀 2-stop**: 使用 `evenly_spaced_2_stop_gradient` 单阶段
- **均匀 N-stop**: 使用 `evenly_spaced_gradient` 带预计算的 factor/bias 数组
- **任意停靠点**: 使用 `gradient` 阶段，包含搜索 t 值对应区间的逻辑

### appendStages 管线组装
1. 应用 ptsToUnit 矩阵变换
2. 调用子类 `appendGradientStages`（如 xy_to_radius）
3. 追加平铺模式阶段（mirror_x_1、repeat_x_1、decal_x、clamp_x_1）
4. 颜色转换和填充
5. 从插值空间转换到目标色彩空间
6. Decal 掩码检查
7. 子类的 postPipeline 阶段

### 色彩空间转换
支持 CSS Color Level 4 定义的所有插值色彩空间：
- 矩形空间: sRGB、sRGB-linear、Display P3、Rec.2020、ProPhoto RGB、A98 RGB、Destination
- 实验室空间: Lab、OKLab、OKLab (gamut-map)
- 极坐标空间: LCH、OKLCH、OKLCH (gamut-map)、HSL、HWB

极坐标空间中色相存储在第一个分量以简化色相方法处理和预乘逻辑。

### 色相方法
四种色相插值策略（CSS Color Level 4）：
- **Shorter**: 选择较短弧
- **Longer**: 选择较长弧（隐式停靠点处跳过以避免产生完整旋转）
- **Increasing**: 色相仅递增
- **Decreasing**: 色相仅递减

## 依赖关系

- `SkShaderBase` — 着色器基类
- `SkRasterPipeline` — 光栅化管线
- `SkColorSpaceXformSteps` — 色彩空间转换
- `SkConvertPixels` — 像素格式转换
- `skcms` — 色彩管理
- `SkVx` / `skvx::float4` — SIMD 向量运算

## 设计模式与设计决策

1. **模板方法模式**: `appendStages` 定义算法骨架，子类实现 `appendGradientStages`
2. **预计算线性方程**: 将颜色插值转化为 factor*t+bias 形式，避免运行时除法
3. **AVX2 对齐**: GradientCtx 中数组至少分配 8 个 float 以支持 YMM 寄存器的 gather 操作
4. **GRADIENT_FACTORY_EARLY_EXIT 宏**: 所有渐变工厂共享的参数验证和单色优化
5. **缓存位图**: 当停靠点数量超过 Graphite uniform 限制时使用位图存储

## 性能考量

- 2-stop 均匀渐变使用最优化的单阶段管线
- 均匀分布停靠点自动检测，避免不必要的 t 值搜索
- 不透明渐变跳过 alpha 相关的预乘/反预乘步骤
- 均匀分布时 clamp 可在管线中提前执行
- 重复停靠点去重减少运行时区间搜索的次数

## 相关文件

- `include/effects/SkGradient.h` — 渐变公共 API（SkGradient 描述符）
- `src/shaders/gradients/SkLinearGradient.h` — 线性渐变
- `src/shaders/gradients/SkRadialGradient.h` — 径向渐变
- `src/shaders/gradients/SkSweepGradient.h` — 扫描渐变
- `src/shaders/gradients/SkConicalGradient.h` — 锥形渐变
- `src/core/SkRasterPipelineOpContexts.h` — GradientCtx 等上下文定义
- `src/core/SkColorSpaceXformSteps.h` — 色彩空间转换

### 附录: 色彩空间到中间空间映射

| 插值色彩空间 | 中间 SkColorSpace | 特殊转换函数 |
|-------------|-------------------|-------------|
| Destination | dst 色彩空间 | 无 |
| sRGBLinear | sRGB Linear | 无 |
| sRGB | sRGB | 无 |
| HSL | sRGB | srgb_to_hsl |
| HWB | sRGB | srgb_to_hwb |
| Lab | XYZD50 Linear | xyzd50_to_lab |
| LCH | XYZD50 Linear | xyzd50_to_hcl |
| OKLab | sRGB Linear | lin_srgb_to_oklab |
| OKLabGamutMap | sRGB Linear | lin_srgb_to_oklab |
| OKLCH | sRGB Linear | lin_srgb_to_okhcl |
| OKLCHGamutMap | sRGB Linear | lin_srgb_to_okhcl |
| DisplayP3 | Display P3 (sRGB TF) | 无 |
| Rec2020 | Rec.2020 (Rec.2020 TF) | 无 |
| ProPhotoRGB | ProPhoto RGB | 无 |
| A98RGB | Adobe RGB (A98 TF) | 无 |

### 附录: 管线阶段顺序

完整的渐变管线阶段顺序如下：
1. 矩阵变换（mRec.apply + ptsToUnit）
2. 子类特定阶段（如 xy_to_radius、xy_to_unit_angle）
3. 平铺阶段（mirror_x_1 / repeat_x_1 / decal_x / clamp_x_1）
4. 颜色填充阶段（evenly_spaced_2_stop_gradient / evenly_spaced_gradient / gradient）
5. 插值空间到目标空间转换（特殊空间逆转换 + SkColorSpaceXformSteps）
6. Decal 掩码检查（check_decal_mask）
7. 子类后处理阶段（postPipeline）

### 附录: 序列化标志位布局

```
Bit 31:    kHasPosition_GSF
Bit 30:    kHasLegacyLocalMatrix_GSF
Bit 29:    kHasColorSpace_GSF
Bits 12-28: 未使用
Bits 8-11:  fTileMode
Bits 4-7:   fInterpolation.fColorSpace
Bits 1-3:   fInterpolation.fHueMethod
Bit 0:      fInterpolation.fInPremul
```
