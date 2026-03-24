# SkHdrAgtm - AGTM 色调映射算法实现

> 源文件: `src/codec/SkHdrAgtm.cpp`

## 概述

`SkHdrAgtm.cpp` 实现了 SMPTE ST 2094-50 标准中定义的自适应全局色调映射（Adaptive Global Tone Map, AGTM）的核心算法。该文件包含增益曲线评估、分量混合函数计算、PCHIP 斜率生成、参考白色调映射算子（RWTMO）构建、头部余量自适应权重计算、GPU 着色器色调映射滤镜创建以及规范约束验证等全套功能。文件分为 CPU 路径（逐像素评估）和 GPU 路径（SkSL 运行时着色器），为 HDR 图像提供了完整的色调映射管线。

## 架构位置

该文件位于 `src/codec/` 目录下，是 Skia HDR 处理管线的核心计算引擎。它实现了 `SkHdrAgtmPriv.h` 中声明的所有 `AgtmHelpers` 函数，被 `SkHdrMetadata.cpp` 的 `makeToneMapColorFilter` 方法调用。GPU 着色器通过 `SkRuntimeEffect` 框架实现，与 Skia 的 GPU 渲染管线无缝集成。

## 主要类与结构体

### `AgtmSyntax`（来自匿名命名空间）
虽然 `AgtmSyntax` 的完整定义在 `SkHdrAgtmParse.cpp` 中，但本文件使用了相关的常量约束值。

### 匿名命名空间常量
- `kMinHdrHeadroom = 0.f` / `kMaxHdrHeadroom = 6.f`: HDR 头部余量范围（log2 域）
- `kMaxLinearHdrHeadroom = 64.f`: 线性域的最大头部余量（`exp2(6) = 64`）

## 公共 API 函数

### 函数评估

#### `AgtmHelpers::EvaluateComponentMixingFunction(mix, color)`
实现 SMPTE 公式 (9) 和 (10)：
- 计算 `common = R*fRed + G*fGreen + B*fBlue + max(R,G,B)*fMax + min(R,G,B)*fMin`
- 当 `fComponent == 0` 时返回 `{common, common, common}`（优化：所有通道相同）
- 否则返回 `{fComponent*R + common, fComponent*G + common, fComponent*B + common}`

#### `AgtmHelpers::EvaluateGainCurve(gainCurve, x)`
实现公式 (11) 的分段三次 Hermite 插值：
- 左端点外：返回 `cp[0].fY`（常数外推）
- 右端点外：返回 `cp[N-1].fY + log2(cp[N-1].fX / x)`（对数衰减）
- 区间内：二分查找定位区间，计算三次多项式系数并求值

#### `AgtmHelpers::EvaluateColorGainFunction(gain, color)`
组合分量混合和增益曲线评估。当所有混合输出相同时（`m.R == m.G == m.B`），仅评估一次曲线。

### PCHIP 斜率计算

#### `AgtmHelpers::PopulateSlopeFromPCHIP(gainCurve)`
实现 SMPTE Annex C.3.9 的 PCHIP 算法：
1. 计算区间宽度 `h[i]` 和分段线性斜率 `s[i]`
2. 端点斜率使用公式 (C.7)/(C.8)（N>=3 时），或线性斜率（N=2）
3. 内部点使用公式 (C.9)：如果相邻斜率异号则为 0，否则为加权调和平均

### RWTMO 构建

#### `AgtmHelpers::PopulateUsingRwtmo(hatm)`
使用参考白色调映射算子填充色调映射参数：
- 色彩空间设为 Rec2020
- 两个备选图像：headroom=0（SDR）和 headroom 由公式 (C.1) 计算
- 每个备选图像的增益曲线通过 Bezier 控制点（公式 C.3-C.6）生成 8 个控制点
- 使用 kappa=0.65 作为 Bezier 参数

### 权重计算

#### `AgtmHelpers::ComputeWeighting(hatm, targetedHdrHeadroom)`
实现 Clause 6.2.5 的头部余量自适应权重计算：
1. 构建排序的头部余量列表 H[]（包含基线和所有备选图像）
2. 如果目标在左端点左侧或右端点右侧：权重为 1.0（公式 2）
3. 否则：二分查找并线性插值（公式 3）
4. 基线图像的权重始终为 0（增益为 0）
5. 按权重降序排列

### 色调映射应用

#### `AgtmHelpers::ApplyGain(hatm, colors, targetedHdrHeadroom)`
CPU 路径的增益应用（公式 4）：
- 权重全 0：不修改颜色
- 仅一个权重非 0：`C *= exp2(w * G)`
- 两个权重非 0：`C *= exp2(w0*G0 + w1*G1)`

### GPU 着色器

#### `AgtmHelpers::MakeColorFilter(hatm, targetedHdrHeadroom, scaleFactor)`
创建 GPU 色调映射颜色滤镜：
1. 计算权重
2. 配置 SkSL uniform 变量（权重、混合系数、曲线参数）
3. 创建增益曲线纹理（`MakeGainCurveXYMImage`）
4. 构建 `SkRuntimeShaderBuilder` 并创建 `SkColorFilter`
5. 通过 `makeWithWorkingColorSpace` 设置增益应用色彩空间

#### GPU 着色器代码（`gAgtmSKSL`）
SkSL 运行时着色器实现了与 CPU 路径等价的色调映射：
- `EvalComponentMixing`: 分量混合
- `EvalGainCurve`: 增益曲线评估（纹理采样 + 二分查找 + 三次插值）
- `EvalColorGainFunction`: 组合评估
- `main`: 缩放 + 增益应用（支持 alpha 预乘处理）

### 辅助函数

#### `AgtmHelpers::MakeGainCurveXYMImage(hatm)`
创建控制点纹理：
- 宽度 = 最大控制点数（32），高度 = 备选图像数
- 每个像素存储 (X, Y, M, 1) 四个浮点值
- 先用 F32 格式填充，再转换为 F16 格式供 GPU 使用

#### `AgtmHelpers::GetGainApplicationSpace(hatm)`
返回增益应用色彩空间（线性传输函数 + 指定色度坐标）。

#### `AgtmHelpers::PopulateToneMapAgtmParams(metadata, inputColorSpace, outAgtm, outScaleFactor)`
确定色调映射参数：
- 检测输入是否为 PQ 或 HLG
- 无 AGTM 时，PQ/HLG 使用 RWTMO + CLLI/MDCV 计算的头部余量
- SDR 输入无 AGTM 时不进行色调映射
- 计算缩放因子：`inputPqOrHlgWhite / agtm.fHdrReferenceWhite`

### 验证

#### `AgtmHelpers::Validate(AdaptiveGlobalToneMap)` / `Validate(HeadroomAdaptiveToneMap)`
验证规范约束（Clause 6.2.2, 6.2.3, 6.4.2, 6.5.2）：
- 头部余量范围 [0, 6]
- 备选图像数量 [0, 4]
- 备选头部余量严格递增且不等于基线
- 色度坐标在 [0, 1] 范围内
- 增益曲线 Y 值符号正确（正增益或负衰减）
- 混合系数在 [0, 1] 且和为 1
- 控制点数量 [1, 32]，X 值非递减，X 相等时 Y 也相等

### toString

#### `AdaptiveGlobalToneMap::toString() const`
返回人类可读的 AGTM 摘要字符串。

## 依赖关系

- `include/core/SkBitmap.h`: 控制点纹理
- `include/core/SkColorFilter.h`: 色调映射滤镜
- `include/effects/SkRuntimeEffect.h`: SkSL 运行时着色器
- `include/private/SkHdrMetadata.h`: AGTM 类型定义
- `src/codec/SkCodecPriv.h`: 调试输出
- `src/codec/SkHdrAgtmPriv.h`: 函数声明

## 设计模式与设计决策

1. **CPU/GPU 双路径**: CPU 路径用于测试和回退，GPU 路径通过 SkSL 着色器实现高性能渲染。

2. **纹理化控制点**: 将控制点存储为纹理图像，利用 GPU 纹理采样硬件进行高效查找。

3. **二分查找优化**: GPU 着色器中限制二分查找为最多 5 步（`log2(32) = 5`），匹配最大控制点数。

4. **RWTMO 默认行为**: 无 AGTM 元数据的 HDR 内容使用 RWTMO 提供合理的默认色调映射。

5. **规范严格验证**: 所有操作前后都通过 `Validate` 确保数据满足 SMPTE 规范约束。

6. **延迟着色器编译**: `agtm_runtime_effect()` 使用静态局部变量模式，SkSL 着色器仅编译一次。

## 性能考量

- **GPU 着色器加速**: 主要色调映射路径在 GPU 上执行
- **F16 纹理格式**: 控制点纹理使用 F16 格式，节省 GPU 内存和带宽
- **提前短路**: 权重为 0 时跳过增益计算
- **单通道优化**: 所有混合输出相同时仅评估一次增益曲线
- **最近邻采样**: 控制点纹理使用 `kNearest` 采样，避免插值开销
- **工作色彩空间**: 通过 `makeWithWorkingColorSpace` 在正确的色彩空间中执行色调映射

## 相关文件

- `src/codec/SkHdrAgtmPriv.h`: 函数声明
- `src/codec/SkHdrAgtmParse.cpp`: AGTM 二进制解析/序列化
- `src/codec/SkHdrMetadata.cpp`: HDR 元数据容器
- `include/private/SkHdrMetadata.h`: 类型定义
- `include/effects/SkRuntimeEffect.h`: SkSL 运行时效果框架
