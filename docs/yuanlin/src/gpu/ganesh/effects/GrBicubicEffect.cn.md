# GrBicubicEffect

> 源文件
> - src/gpu/ganesh/effects/GrBicubicEffect.h
> - src/gpu/ganesh/effects/GrBicubicEffect.cpp

## 概述

`GrBicubicEffect` 是实现双三次（Bicubic）纹理采样的片段处理器，提供高质量的图像缩放和插值。该效果使用 Catmull-Rom 或 Mitchell-Netravali 滤波器内核，对纹理进行 4x4 邻域采样并加权混合，生成平滑的放大/缩小结果。相比双线性采样，双三次采样质量更高但计算成本更大，适用于高质量图像处理、媒体播放、UI 缩放等场景。

## 架构位置

- **模块层级**：`src/gpu/ganesh/effects/` - Ganesh 效果层
- **继承关系**：`GrBicubicEffect` -> `GrFragmentProcessor`
- **使用者**：图像绘制、纹理缩放、高质量采样
- **滤波器**：Catmull-Rom、Mitchell-Netravali

## 主要类与结构体

### GrBicubicEffect

**静态工厂**：
```cpp
static std::unique_ptr<GrFragmentProcessor> Make(
    GrSurfaceProxyView view,
    SkAlphaType alphaType,
    const SkMatrix& matrix,
    SkCubicResampler resampler);
```

**内核类型**：
- `SkCubicResampler::CatmullRom()` - Catmull-Rom 样条
- `SkCubicResampler::Mitchell(B, C)` - Mitchell-Netravali 滤波器

## 内部实现细节

### 双三次插值算法

**采样布局**：
```
[p00] [p01] [p02] [p03]
[p10] [p11] [p12] [p13]
[p20] [p21] [p22] [p23]
[p30] [p31] [p32] [p33]
```

**权重计算**：
- 根据样本点到中心的距离计算权重
- 使用三次多项式内核函数
- X 和 Y 方向分别计算权重

**混合公式**：
```
result = Σ(i=0..3, j=0..3) weight_x[i] * weight_y[j] * sample[i][j]
```

### 内核函数

**Catmull-Rom**：
```cpp
w(x) = {
    (2 - |x|) * |x|^2 - 1   if |x| < 1
    4 - 8|x| + 5|x|^2 - |x|^3   if 1 <= |x| < 2
    0   if |x| >= 2
}
```

**Mitchell-Netravali**：
```cpp
w(x; B, C) = {
    (12 - 9B - 6C)|x|^3 + (-18 + 12B + 6C)|x|^2 + (6 - 2B)   if |x| < 1
    (-B - 6C)|x|^3 + (6B + 30C)|x|^2 + (-12B - 48C)|x| + (8B + 24C)   if 1 <= |x| < 2
    0   if |x| >= 2
}
```

### 着色器实现

**SkSL 伪代码**：
```sksl
half4 bicubic_sample(texture2D tex, float2 coord) {
    float2 texelSize = 1.0 / textureSize(tex);
    float2 f = fract(coord * textureSize(tex) - 0.5);

    half4 result = half4(0);
    for (int y = 0; y < 4; y++) {
        half weight_y = cubic_weight(f.y - y + 1);
        for (int x = 0; x < 4; x++) {
            half weight_x = cubic_weight(f.x - x + 1);
            float2 offset = (float2(x, y) - 1.5) * texelSize;
            result += weight_x * weight_y * sample(tex, coord + offset);
        }
    }
    return result;
}
```

### 优化策略

**分离采样**：
- X 方向先采样 4 次并混合
- Y 方向再对中间结果采样 4 次
- 减少纹理采样次数（从 16 次到 8 次）

**查找表**：
- 预计算权重查找表
- 减少着色器算术运算

## 设计模式与设计决策

### 参数化内核

通过 `SkCubicResampler` 参数化不同滤波器，支持灵活配置。

### 质量-性能权衡

双三次采样比双线性慢 8-16 倍，但质量显著提升。

### 分离计算优化

X/Y 分离减少采样次数，利用纹理缓存。

## 性能考量

### 纹理采样开销

16 次纹理采样是性能瓶颈，需要高带宽内存。

### 权重计算

三次多项式计算需要多条 GPU 指令，可通过查找表优化。

### 缓存友好

4x4 邻域采样利用纹理缓存，减少内存访问延迟。

## 相关文件

- `include/core/SkSamplingOptions.h` - 采样选项（包含 `SkCubicResampler`）
- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
- `src/gpu/ganesh/effects/GrTextureEffect.h` - 基础纹理效果
