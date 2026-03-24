# SkSVGFeColorMatrix

> 源文件: [modules/svg/src/SkSVGFeColorMatrix.cpp](../../../../modules/svg/src/SkSVGFeColorMatrix.cpp)

## 概述

`SkSVGFeColorMatrix` 实现了 SVG `<feColorMatrix>` 滤镜基元，用于对图像进行颜色变换。它支持四种颜色矩阵操作类型：自定义矩阵（matrix）、饱和度调整（saturate）、色相旋转（hueRotate）和亮度到 Alpha 转换（luminanceToAlpha）。

该类将 SVG 颜色矩阵参数转换为 Skia 的 `SkColorMatrix`，然后通过 `SkImageFilters::ColorFilter` 应用到图像滤镜链中。

## 架构位置

```
SkSVGNode
  └── SkSVGFe                         （滤镜基元基类）
        └── SkSVGFeColorMatrix         ← 本文件
```

## 主要类与结构体

### `SkSVGFeColorMatrix`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fType` | `SkSVGFeColorMatrixType` | 矩阵操作类型 |
| `fValues` | `SkSVGFeColorMatrixValues` | 矩阵数据值数组 |

### `SkSVGFeColorMatrixType` 枚举

| 值 | 说明 |
|----|------|
| `kMatrix` | 自定义 5x4 颜色矩阵 |
| `kSaturate` | 饱和度调整（单值参数） |
| `kHueRotate` | 色相旋转（角度参数，单位：度） |
| `kLuminanceToAlpha` | 亮度到 Alpha 通道转换（无参数） |

## 公共 API 函数

### `parseAndSetAttribute(const char* name, const char* value)`
解析 `type` 和 `values` 属性。

## 内部实现细节

### 矩阵构建 (`makeMatrixForType`)

根据操作类型构建对应的 `SkColorMatrix`：

**matrix 类型:**
- 需要 20 个浮点值（5x4 行主序矩阵）
- 值不足 20 个时返回单位矩阵

**saturate 类型:**
- 调用 `MakeSaturate()`，委托给 `SkColorMatrix::setSaturation()`
- 参数为饱和度值（0 = 灰度，1 = 原色）
- 无值时默认为 1（保持原色）

**hueRotate 类型:**
- 调用 `MakeHueRotate()`，实现色相旋转矩阵
- 使用三角函数计算旋转后的 RGB 分量混合系数
- 基于 ITU-R BT.601 亮度系数（0.213, 0.715, 0.072）
- 无值时默认为 0 度（无旋转）

**luminanceToAlpha 类型:**
- 调用 `MakeLuminanceToAlpha()`
- RGB 通道置零，Alpha 通道使用亮度系数（`SK_LUM_COEFF_R/G/B`）加权求和
- 不需要参数值

### 色相旋转矩阵详解

`MakeHueRotate` 构建的 5x4 矩阵实现了 HSL 色彩空间中的色相旋转：

```
[ 0.213+c*0.787+s*(-0.213)  0.715+c*(-0.715)+s*(-0.715)  0.072+c*(-0.072)+s*0.928  0  0 ]
[ 0.213+c*(-0.213)+s*0.143  0.715+c*0.285+s*0.140        0.072+c*(-0.072)+s*(-0.283) 0  0 ]
[ 0.213+c*(-0.213)+s*(-0.787) 0.715+c*(-0.715)+s*0.715   0.072+c*0.928+s*0.072     0  0 ]
[ 0                          0                             0                          1  0 ]
```

其中 `c = cos(theta)`，`s = sin(theta)`。

### 图像滤镜生成 (`onMakeImageFilter`)

1. 调用 `makeMatrixForType()` 构建颜色矩阵
2. 使用 `SkColorFilters::Matrix()` 创建颜色滤镜
3. 包装为 `SkImageFilters::ColorFilter()`
4. 从 FilterContext 解析输入（`fctx.resolveInput`）并应用色彩空间转换到目标色彩空间
5. 传入 `resolveFilterSubregion()` 返回的滤镜子区域作为裁剪边界

### 颜色矩阵的数学基础

5x4 颜色矩阵将输入的 RGBA 值映射到输出的 RGBA 值：
```
| R' |   | m0  m1  m2  m3  m4  |   | R |
| G' | = | m5  m6  m7  m8  m9  | x | G |
| B' |   | m10 m11 m12 m13 m14 |   | B |
| A' |   | m15 m16 m17 m18 m19 |   | A |
                                    | 1 |
```
其中 m4、m9、m14、m19 列对应偏移量（常数项）。

### 类型解析

通过特化 `SkSVGAttributeParser::parse<SkSVGFeColorMatrixType>` 实现字符串到枚举的映射：
- "matrix" -> `kMatrix`
- "saturate" -> `kSaturate`
- "hueRotate" -> `kHueRotate`
- "luminanceToAlpha" -> `kLuminanceToAlpha`

## 依赖关系

- **Skia Core**: `SkColorFilter`, `SkScalar`
- **Skia Effects**: `SkImageFilters`
- **Skia Internal**: `SkColorData`（亮度系数宏 `SK_LUM_COEFF_*`）
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGFilterContext`

## 设计模式与设计决策

1. **策略模式**: 四种矩阵类型通过 switch-case 分发，每种类型有独立的静态构建方法（MakeSaturate、MakeHueRotate、MakeLuminanceToAlpha）。这种设计使得添加新的矩阵类型（如果 SVG 规范扩展）非常简单。

2. **安全降级**: 当值数组为空或数量不足时，返回单位矩阵而非产生错误，确保即使 SVG 输入不完整也能正常渲染。对于 saturate 和 hueRotate，缺少值时分别使用 1（原色）和 0（无旋转）作为默认值。

3. **色彩空间感知**: 通过 `resolveColorspace()` 和 `resolveInput()` 确保颜色矩阵在正确的色彩空间中应用。这对于 hueRotate 和 saturate 操作尤为重要，因为它们的数学基础假设了特定的色彩空间。

4. **枚举映射表**: 使用 `std::tuple` 数组定义字符串到枚举的映射，通过 `parseEnumMap` 统一处理。这种声明式的映射方式比 if-else 链更易于维护和扩展。

5. **亮度系数选择**: `MakeLuminanceToAlpha` 使用 `SK_LUM_COEFF_R/G/B` 宏定义的亮度系数，这些系数来源于 ITU-R BT.601 标准，与 SVG 规范中定义的亮度权重一致。

6. **SkColorMatrix 委托**: saturate 操作直接委托给 `SkColorMatrix::setSaturation()`，复用了 Skia 核心的实现，避免了重复编写饱和度矩阵的数学公式。

## 性能考量

- 颜色矩阵构建仅涉及少量浮点运算，开销极小
- `hueRotate` 需要计算 sin/cos，但仅执行一次
- `SkColorFilters::Matrix()` 创建的颜色滤镜通常由 GPU 高效执行，每个像素进行一次矩阵乘法
- 矩阵在每次滤镜 DAG 构建时重新计算，但不涉及图像数据处理
- `saturate` 类型委托给 `SkColorMatrix::setSaturation()`，该方法内部使用优化的系数计算
- `luminanceToAlpha` 生成的矩阵大部分元素为零，GPU 实现可能优化跳过零乘法
- 颜色空间转换（通过 `resolveInput` 的第三个参数）可能在矩阵滤镜前后插入额外的颜色滤镜节点
- 对于 `matrix` 类型，20 个浮点值直接传入 `SkColorMatrix`，无需额外计算
- 所有矩阵类型的构建都是纯函数式的（无副作用），理论上可以缓存但当前未实现
- 枚举映射表使用 `std::tuple` 数组，`parseEnumMap` 进行线性扫描，对于 4 个枚举值性能足够

## 相关文件

- `modules/svg/include/SkSVGFeColorMatrix.h` - 头文件定义，声明类接口和属性
- `modules/svg/include/SkSVGFe.h` - 滤镜基元基类，提供通用的输入/输出解析
- `modules/svg/src/SkSVGFilter.cpp` - 滤镜容器，构建滤镜 DAG
- `modules/svg/src/SkSVGFilterContext.cpp` - 滤镜上下文，管理输入解析和色彩空间转换
- `include/effects/SkColorMatrix.h` - Skia 颜色矩阵类，提供 setSaturation 等方法
- `src/core/SkColorData.h` - 提供 SK_LUM_COEFF_R/G/B 亮度系数宏定义
