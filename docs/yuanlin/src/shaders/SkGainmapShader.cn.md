# SkGainmapShader — HDR 增益图着色器

> 源文件: `src/shaders/SkGainmapShader.cpp`

## 概述

`SkGainmapShader.cpp` 实现了 Skia 中用于 HDR 增益图（Gainmap）渲染的着色器。增益图是一种将 SDR（标准动态范围）图像和 HDR（高动态范围）元数据结合在一起的技术，广泛应用于 Android 的 Ultra HDR 格式和 Apple 的 HDR 照片格式。

该模块的核心功能是将一幅基础图像（base image）和一幅增益图图像（gainmap image）组合在一起，根据目标显示设备的 HDR 能力（`dstHdrRatio`）动态生成最终的 HDR 或 SDR 输出。增益图的数学运算通过 SkSL 运行时着色器（Runtime Effect）实现，可以在 GPU 上高效执行。

## 架构位置

```
Skia
├── include/private/
│   ├── SkGainmapShader.h       // API 声明
│   └── SkGainmapInfo.h         // 增益图元数据定义
├── src/shaders/
│   └── SkGainmapShader.cpp     // 本文件
└── include/effects/
    └── SkRuntimeEffect.h       // 运行时着色器效果
```

`SkGainmapShader` 依赖于 Skia 的运行时着色器系统（`SkRuntimeEffect`），通过内嵌的 SkSL 代码在 GPU 或 CPU 上执行增益图合成。

## 主要类与结构体

### SkSL 着色器 (`gGainmapSKSL`)

内嵌的 SkSL 代码定义了增益图应用的数学公式：

**Uniform 输入**:

| Uniform | 类型 | 说明 |
|---------|------|------|
| `base` | `shader` | 基础图像着色器 |
| `gainmap` | `shader` | 增益图图像着色器 |
| `logRatioMin` | `half4` | 增益比率最小值的对数 |
| `logRatioMax` | `half4` | 增益比率最大值的对数 |
| `gainmapGamma` | `half4` | 增益图 gamma 校正值 |
| `epsilonBase` | `half4` | 基础图像的 epsilon 偏移 |
| `epsilonOther` | `half4` | 目标图像的 epsilon 偏移 |
| `W` | `half` | 混合权重 |
| `gainmapIsAlpha` | `int` | 增益图是否为 alpha 格式 |
| `gainmapIsRed` | `int` | 增益图是否为单红通道格式 |
| `singleChannel` | `int` | 是否为单通道增益图 |
| `noGamma` | `int` | 是否跳过 gamma 校正 |
| `isApple` | `int` | 是否为 Apple 增益图格式 |
| `appleG` / `appleH` | `half` | Apple 格式专用参数 |

## 公共 API 函数

### `sk_sp<SkShader> SkGainmapShader::Make(...)` (2 个重载)

- **功能**: 创建增益图合成着色器
- **参数**:
  - `baseImage` / `baseRect`: 基础图像及其源矩形
  - `gainmapImage` / `gainmapRect`: 增益图图像及其源矩形
  - `baseSamplingOptions` / `gainmapSamplingOptions`: 采样选项
  - `gainmapInfo`: 增益图元数据（比率、gamma、epsilon 等）
  - `dstRect`: 目标矩形
  - `dstHdrRatio`: 目标显示设备的 HDR 亮度比率
  - `dstColorSpace` (可选): 目标色彩空间（当前未使用）
- **返回值**: 组合后的着色器；如果权重 W=0（无需增益），直接返回基础图像着色器

## 内部实现细节

### 权重计算 (W)

权重 W 基于目标设备的 HDR 能力在 SDR 和 HDR 比率之间进行对数插值：

```
W = (log(dstHdrRatio) - log(displayRatioSdr)) / (log(displayRatioHdr) - log(displayRatioSdr))
```

- `W = 0`: 输出 SDR（基础图像原样输出）
- `W = 1`: 输出完整 HDR
- `0 < W < 1`: 部分 HDR

如果基础图像是 HDR 格式，W 减 1（变为负值范围 `[-1, 0]`），表示从 HDR 基础回退到 SDR。

### 增益图数学公式

核心公式（标准模式）：
```
L = mix(logRatioMin, logRatioMax, pow(G, gainmapGamma))
H = (S + epsilonBase) * exp(L * W) - epsilonOther
```

其中 S 是基础像素，G 是增益图像素，H 是输出像素。

### Apple 增益图格式

Apple 格式使用不同的映射函数：
```
L = log(1.0 + (appleH - 1.0) * pow(G, appleG))
```

其中 `appleG = 1.961`（固定值），`appleH` 为显示 HDR 比率。

### 单通道优化

当增益图为灰度/alpha/红色单通道且所有通道参数相等时，启用单通道路径。此时只计算一个标量 L 值并应用到所有 RGB 通道，减少计算量。

### 色彩空间处理

- 基础图像着色器使用 `makeShader`（自动色彩空间转换）
- 增益图着色器使用 `makeRawShader`（忽略色彩空间，因为增益图的值不是颜色）
- 最终结果通过 `makeWithWorkingColorSpace` 在线性 gamma 色彩空间中执行运算

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkGainmapShader.h` | API 声明 |
| `SkGainmapInfo.h` | 增益图元数据结构 |
| `SkRuntimeEffect.h` | 运行时着色器编译与执行 |
| `SkImage.h` | 图像接口（着色器创建） |
| `SkShader.h` | 着色器基类 |
| `SkColorSpace.h` | 色彩空间管理 |
| `SkMatrix.h` | 变换矩阵（矩形映射） |
| `<cmath>` | `std::log`、`std::pow` |

## 设计模式与设计决策

1. **运行时着色器**: 使用 SkSL 运行时效果而非硬编码的 C++ 着色器，允许增益图数学在 GPU 上高效执行
2. **惰性编译**: `gainmap_apply_effect()` 使用 `static` 局部变量缓存编译后的着色器，仅在首次调用时编译
3. **快速路径**: 当 W=0 时直接返回基础图像着色器，完全跳过增益图处理
4. **多格式支持**: 通过 uniform 标志（`isApple`、`singleChannel`、`noGamma`）在同一个着色器中处理多种增益图格式
5. **线性色彩空间**: 增益图数学运算在线性 gamma 色彩空间中执行，确保物理正确性
6. **原始着色器**: 增益图使用 `makeRawShader` 忽略色彩空间，因为增益图的值表示乘法因子而非颜色

## 性能考量

- **GPU 加速**: SkSL 着色器可以在 GPU 上并行执行，适合全屏 HDR 渲染
- **着色器缓存**: `static const SkRuntimeEffect*` 确保 SkSL 只编译一次
- **单通道优化**: 灰度增益图只需要 1/3 的数学运算
- **noGamma 优化**: 当 gamma 为 1.0 时跳过 `pow` 运算（`pow` 是较昂贵的 GPU 操作）
- **W=0 短路**: 完全跳过增益图处理，对于 SDR 显示设备零额外开销
- **对数预计算**: `logRatioMin` 和 `logRatioMax` 在 CPU 端预计算，避免 GPU 端的 `log` 调用

## 相关文件

- `include/private/SkGainmapShader.h` — API 声明
- `include/private/SkGainmapInfo.h` — 增益图元数据
- `include/effects/SkRuntimeEffect.h` — 运行时着色器
- `src/codec/SkJpegGainmapEncoder.cpp` — JPEG 增益图编码
- `include/core/SkImage.h` — 图像接口
