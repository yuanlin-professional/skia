# SkHdrAgtmPriv - AGTM 辅助函数私有接口

> 源文件: `src/codec/SkHdrAgtmPriv.h`

## 概述

`SkHdrAgtmPriv.h` 声明了 SMPTE ST 2094-50 自适应全局色调映射（AGTM）的内部辅助函数集合。这些函数位于 `skhdr::AgtmHelpers` 命名空间中，提供了 AGTM 色调映射的核心计算功能，包括颜色增益函数评估、分量混合函数评估、增益曲线评估、PCHIP 斜率计算、头部余量自适应权重计算、参考白色调映射算子（RWTMO）填充、色彩滤镜创建等。这些函数供 `SkHdrAgtm.cpp` 和 `SkHdrAgtmParse.cpp` 内部使用。

## 架构位置

该文件位于 `src/codec/` 目录下，是 AGTM 处理管线的私有接口层。它连接了 AGTM 二进制解析（`SkHdrAgtmParse.cpp`）和色调映射应用（`SkHdrAgtm.cpp`），定义了两者共享的函数接口。所有函数都在 `skhdr::AgtmHelpers` 命名空间中，不作为公共 API 暴露。

## 主要类与结构体

### `AgtmHelpers::Weighting`
头部余量自适应权重结构体，用于在两个备选图像之间进行插值：
- `fAlternateImageIndex[2]`: 两个参与插值的备选图像索引（`kInvalidIndex = 255` 表示未使用）
- `fWeight[2]`: 对应的权重值（和为 1.0，第一个权重始终较大）

## 公共 API 函数

### 函数评估

#### `EvaluateColorGainFunction(ColorGainFunction, SkColor4f)`
评估颜色增益函数（SMPTE ST 2094-50 Clause 6.3.2），对输入颜色计算增益值。

#### `EvaluateComponentMixingFunction(ComponentMixingFunction, SkColor4f)`
评估分量混合函数（Clause 6.4.3），将 RGB 颜色混合为增益曲线的输入值。

#### `EvaluateGainCurve(GainCurve, float)`
评估增益曲线（Clause 6.5.3），通过分段三次 Hermite 插值计算增益值。

### 数据填充

#### `PopulateSlopeFromPCHIP(GainCurve&)`
使用 PCHIP（Piecewise Cubic Hermite Interpolation Package）算法（Clause C.3.9）计算控制点的斜率值（fM），避免在序列化时存储显式斜率。

#### `PopulateUsingRwtmo(HeadroomAdaptiveToneMap&)`
使用参考白色调映射算子（RWTMO）填充自适应色调映射参数。基于 `fBaselineHdrHeadroom` 值计算默认的两个备选图像及其增益曲线。

#### `PopulateToneMapAgtmParams(Metadata, SkColorSpace*, AdaptiveGlobalToneMap*, float*)`
根据元数据和输入色彩空间确定色调映射参数。处理 PQ/HLG 输入的参考白电平转换，无 AGTM 元数据时使用 RWTMO 默认值。

### 色调映射应用

#### `ApplyGain(HeadroomAdaptiveToneMap, SkSpan<SkColor4f>, float)`
对增益应用色彩空间中的颜色数组应用色调映射。

#### `MakeColorFilter(HeadroomAdaptiveToneMap, float targetedHdrHeadroom, float scaleFactor)`
创建 `SkColorFilter`，实现 GPU 加速的色调映射。先缩放再映射。

### 辅助函数

#### `MakeGainCurveXYMImage(HeadroomAdaptiveToneMap)`
创建包含控制点 X/Y/M 值的 `SkImage`，供着色器纹理采样使用。

#### `GetGainApplicationSpace(HeadroomAdaptiveToneMap)`
返回增益应用色彩空间（线性传输函数 + 指定色度坐标的 `SkColorSpace`）。

#### `Validate(AdaptiveGlobalToneMap)` / `Validate(HeadroomAdaptiveToneMap)`
验证 AGTM 或 HATM 是否满足所有规范约束（Clause 6.2.2, 6.2.3, 6.4.2, 6.5.2）。

## 内部实现细节

1. **命名空间嵌套**: 函数位于 `skhdr::AgtmHelpers` 双层命名空间中，表明这些是 HDR 子系统的内部辅助工具。

2. **前向声明**: `SkData` 和 `SkString` 通过前向声明引入，减少头文件依赖。

3. **规范条款引用**: 每个函数的文档注释引用了对应的 SMPTE ST 2094-50 条款号，便于规范追溯。

## 依赖关系

- `include/core/SkColor.h`: `SkColor4f` 颜色类型
- `include/core/SkColorSpace.h`: 色彩空间
- `include/core/SkImage.h`: 图像接口
- `include/core/SkSpan.h`: 数组视图
- `include/private/SkHdrMetadata.h`: AGTM 和 Metadata 类型定义

## 设计模式与设计决策

1. **工具命名空间模式**: 使用 `AgtmHelpers` 命名空间组织相关的无状态函数，而非类的静态方法。

2. **规范驱动设计**: 函数划分严格对应 SMPTE 规范的条款结构。

3. **公私分离**: 这些函数位于私有头文件中，不对外暴露，公共接口通过 `Metadata::makeToneMapColorFilter` 提供。

## 性能考量

- **GPU 加速**: `MakeColorFilter` 生成 `SkColorFilter`，可在 GPU 着色器中执行
- **纹理查找**: 控制点通过纹理图像传递给 GPU，利用硬件纹理采样
- **权重预计算**: `ComputeWeighting` 在应用增益前预计算插值权重

## 相关文件

- `src/codec/SkHdrAgtm.cpp`: 函数实现和着色器代码
- `src/codec/SkHdrAgtmParse.cpp`: AGTM 解析和序列化
- `include/private/SkHdrMetadata.h`: 公共类型定义
- `src/codec/SkHdrMetadata.cpp`: HDR 元数据管理
