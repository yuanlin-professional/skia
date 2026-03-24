# SkSVGFeTurbulence

> 源文件: [modules/svg/src/SkSVGFeTurbulence.cpp](../../../../modules/svg/src/SkSVGFeTurbulence.cpp)

## 概述

`SkSVGFeTurbulence` 实现了 SVG `<feTurbulence>` 滤镜基元，用于生成 Perlin 噪声纹理。它支持两种噪声类型：`turbulence`（湍流）和 `fractalNoise`（分形噪声），可以通过基频、八度数和种子值来控制噪声的外观特征。

该滤镜基元常用于生成自然纹理效果（如云彩、大理石、木纹等），也可与其他滤镜组合产生更复杂的视觉效果。

## 架构位置

```
SkSVGNode
  └── SkSVGFe                    （滤镜基元基类）
        └── SkSVGFeTurbulence     ← 本文件
```

`SkSVGFeTurbulence` 作为滤镜效果基元，由 `SkSVGFilter` 在构建滤镜 DAG 时调用其 `makeImageFilter()` 方法。

## 主要类与结构体

### `SkSVGFeTurbulence`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fBaseFrequency` | `SkSVGFeTurbulenceBaseFrequency` | 噪声基频（X 和 Y 方向可独立设置） |
| `fNumOctaves` | `SkSVGIntegerType` | 噪声八度数，控制细节层次 |
| `fSeed` | `SkSVGNumberType` | 随机种子值 |
| `fTurbulenceType` | `SkSVGFeTurbulenceType` | 噪声类型（turbulence 或 fractalNoise） |

### `SkSVGFeTurbulenceBaseFrequency`

表示基频参数，包含 `freqX()` 和 `freqY()` 两个分量。解析时如果只提供一个值，则 X 和 Y 使用相同的频率。

### `SkSVGFeTurbulenceType`

枚举类型：
- `kTurbulence` - 湍流噪声
- `kFractalNoise` - 分形噪声

## 公共 API 函数

### `parseAndSetAttribute(const char* name, const char* value)`
解析 `<feTurbulence>` 元素的属性：
- `numOctaves` - 噪声八度数
- `seed` - 随机种子
- `baseFrequency` - 基频率（可接受单值或双值）
- `type` - 噪声类型

## 内部实现细节

### baseFrequency 解析
`SkSVGFeTurbulenceBaseFrequency` 的自定义解析器支持两种格式：
- 单值格式：`baseFrequency="0.05"` -> X 和 Y 使用相同频率
- 双值格式：`baseFrequency="0.05, 0.1"` -> X 和 Y 使用不同频率
解析器先解析第一个值，然后尝试解析可选的逗号分隔符和第二个值。

### 图像滤镜生成 (`onMakeImageFilter`)
根据噪声类型选择不同的 Skia Perlin 噪声着色器：
- `kTurbulence` -> `SkShaders::MakeTurbulence()`
- `kFractalNoise` -> `SkShaders::MakeFractalNoise()`

然后通过 `SkImageFilters::Shader()` 将着色器包装为图像滤镜，并限定在滤镜子区域内。

### turbulenceType 解析
使用字符串匹配将 "fractalNoise" 和 "turbulence" 映射到对应枚举值。

## 依赖关系

- **Skia Core**: `SkShader`
- **Skia Effects**: `SkImageFilters`, `SkPerlinNoiseShader`
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGFilterContext`, `SkSVGRenderContext`

## 设计模式与设计决策

1. **模板特化**: 通过特化 `SkSVGAttributeParser::parse` 模板函数，为 `SkSVGFeTurbulenceBaseFrequency` 和 `SkSVGFeTurbulenceType` 提供自定义解析逻辑。

2. **委托到 Skia 核心**: 噪声生成完全委托给 Skia 的 `SkPerlinNoiseShader`，SVG 层仅负责参数解析和映射。

3. **TODO 标注**: `tileSize` 参数目前为 `nullptr`，表示尚未实现基于滤镜子区域属性的平铺功能。

## 性能考量

- Perlin 噪声的计算复杂度随 `numOctaves` 增大而线性增长
- 高频率 (`baseFrequency`) 噪声需要更精细的采样
- 噪声着色器被包装为 `SkImageFilter`，支持 Skia 的延迟求值和缓存机制
- `tileSize` 为 nullptr 表示噪声不会被平铺，可能影响大面积区域的渲染性能

## 相关文件

- `modules/svg/include/SkSVGFeTurbulence.h` - 头文件，定义属性和类接口
- `modules/svg/include/SkSVGFe.h` - 滤镜基元基类
- `modules/svg/src/SkSVGFilter.cpp` - 滤镜容器，构建滤镜 DAG
- `modules/svg/src/SkSVGFilterContext.cpp` - 滤镜上下文管理
- `include/effects/SkPerlinNoiseShader.h` - Skia Perlin 噪声着色器
