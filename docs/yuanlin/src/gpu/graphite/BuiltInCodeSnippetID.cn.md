# BuiltInCodeSnippetID

> 源文件
> - src/gpu/graphite/BuiltInCodeSnippetID.h

## 概述

`BuiltInCodeSnippetID` 是 Graphite 渲染系统中用于标识内置着色器代码片段的枚举类型。它为 Skia 的各种渲染效果（如着色器、颜色滤镜、混合模式等）提供唯一标识符，支持动态着色器组合和管线缓存。

该枚举是 Graphite 着色器编译系统的核心，通过代码片段组合实现灵活的渲染管线构建，避免预编译所有可能的着色器排列组合。

## 架构位置

```
Graphite Shader System
├── PaintParamsKey (使用 CodeSnippetID 构建键)
├── ShaderCodeDictionary (ID 到代码映射)
├── PipelineDataGatherer (收集 uniform 数据)
└── BuiltInCodeSnippetID (本枚举) ← 定义所有内置代码片段
```

## 主要类与结构体

### BuiltInCodeSnippetID 枚举

```cpp
enum class BuiltInCodeSnippetID : int32_t
```

**设计原则**：
- 32 位整型，支持大量代码片段
- 按功能分组（着色器、颜色滤镜、混合器）
- 固定混合模式 ID 与 `SkBlendMode` 枚举对齐

## 枚举值分类

### 1. 特殊/控制片段

| ID | 说明 |
|---|------|
| `kError` | 错误片段，实现默认错误处理行为 |
| `kPriorOutput` | 透传前一阶段的输出 |

### 2. 着色器片段（SkShader）

#### 纯色着色器

| ID | 说明 |
|---|------|
| `kSolidColorShader` | 纯色填充 |
| `kRGBPaintColor` | RGB 绘制颜色 |
| `kAlphaOnlyPaintColor` | 仅 Alpha 通道绘制颜色 |

#### 渐变着色器（4 种类型 × 4 种实现）

**渐变类型**：
- Linear（线性）
- Radial（径向）
- Sweep（扫描）
- Conical（锥形）

**实现方式**：
- `*4`：4 色插值（小渐变）
- `*8`：8 色插值（中等渐变）
- `*Texture`：纹理查找（复杂渐变）
- `*Buffer`：缓冲区查找（动态渐变）

**示例**：
```
kLinearGradientShader4,
kLinearGradientShader8,
kLinearGradientShaderTexture,
kLinearGradientShaderBuffer,
```

#### 图像着色器

| ID | 说明 |
|---|------|
| `kImageShader` | 标准图像采样 |
| `kImageShaderClamp` | Clamp 模式图像采样 |
| `kCubicImageShader` | 三次插值图像采样 |
| `kHWImageShader` | 硬件加速图像采样 |
| `kYUVImageShader` | YUV 图像采样 |
| `kCubicYUVImageShader` | 三次插值 YUV 图像 |
| `kHWYUVImageShader` | 硬件加速 YUV 图像 |
| `kHWYUVNoSwizzleImageShader` | 无通道交换的 YUV 图像 |

#### 变换和辅助着色器

| ID | 说明 |
|---|------|
| `kLocalMatrixShader` | 局部矩阵变换（仿射） |
| `kLocalMatrixShaderPersp` | 局部矩阵变换（透视） |
| `kCoordNormalizeShader` | 坐标归一化 |
| `kCoordClampShader` | 坐标钳位 |
| `kDitherShader` | 抖动效果 |
| `kPerlinNoiseShader` | Perlin 噪声生成 |

### 3. 颜色滤镜片段（SkColorFilter）

| ID | 说明 |
|---|------|
| `kMatrixColorFilter` | 颜色矩阵变换 |
| `kHSLMatrixColorFilter` | HSL 颜色空间矩阵 |
| `kTableColorFilter` | 查找表颜色映射 |
| `kGaussianColorFilter` | 高斯模糊滤镜 |
| `kColorSpaceXformColorFilter` | 色彩空间转换（通用） |
| `kColorSpaceXformPremul` | 预乘 Alpha 色彩空间转换 |
| `kColorSpaceXformSRGB` | sRGB 色彩空间转换 |

### 4. 特殊片段

| ID | 说明 |
|---|------|
| `kPrimitiveColor` | 访问 RenderStep 的图元颜色 |
| `kAnalyticClip` | 解析裁剪（圆角矩形、抗锯齿矩形） |
| `kAnalyticAndAtlasClip` | 解析 + 图集裁剪 |
| `kCompose` | 组合两个子片段 |
| `kBlendCompose` | 混合组合三个子片段 |

### 5. 混合器片段（SkBlender）

#### 可编程混合

| ID | 说明 |
|---|------|
| `kPorterDuffBlender` | Porter-Duff 混合模式（处理所有 PD 模式） |
| `kHSLCBlender` | HSLC 混合（色相、饱和度、亮度、颜色） |

#### 固定功能混合（按 SkBlendMode 顺序排列）

**Porter-Duff 模式**：
```
kFixedBlend_Clear,      // 清空
kFixedBlend_Src,        // 源
kFixedBlend_Dst,        // 目标
kFixedBlend_SrcOver,    // 源覆盖
kFixedBlend_DstOver,    // 目标覆盖
kFixedBlend_SrcIn,      // 源在内
kFixedBlend_DstIn,      // 目标在内
kFixedBlend_SrcOut,     // 源在外
kFixedBlend_DstOut,     // 目标在外
kFixedBlend_SrcATop,    // 源在上
kFixedBlend_DstATop,    // 目标在上
kFixedBlend_Xor,        // 异或
```

**可分离混合模式**：
```
kFixedBlend_Plus,       // 加法（带钳位）
kFixedBlend_Modulate,   // 调制
kFixedBlend_Screen,     // 屏幕
```

**高级混合模式**：
```
kFixedBlend_Overlay,    // 叠加
kFixedBlend_Darken,     // 变暗
kFixedBlend_Lighten,    // 变亮
kFixedBlend_ColorDodge, // 颜色减淡
kFixedBlend_ColorBurn,  // 颜色加深
kFixedBlend_HardLight,  // 强光
kFixedBlend_SoftLight,  // 柔光
kFixedBlend_Difference, // 差值
kFixedBlend_Exclusion,  // 排除
kFixedBlend_Multiply,   // 正片叠底
```

**非可分离混合模式**：
```
kFixedBlend_Hue,        // 色相
kFixedBlend_Saturation, // 饱和度
kFixedBlend_Color,      // 颜色
kFixedBlend_Luminosity, // 亮度
```

## 常量定义

```cpp
static constexpr int kBuiltInCodeSnippetIDCount =
    static_cast<int>(BuiltInCodeSnippetID::kLast) + 1;
```
内置代码片段总数。

```cpp
static constexpr int kFixedBlendIDOffset =
    static_cast<int>(BuiltInCodeSnippetID::kFirstFixedBlend);
```
固定混合模式 ID 的偏移量，用于转换为 `SkBlendMode`。

```cpp
kFirstFixedBlend = kFixedBlend_Clear
kLast = kFixedBlend_Luminosity
```
固定混合模式的范围标记。

## 设计模式与设计决策

### 1. ID 与 SkBlendMode 对齐

```cpp
(id - kFirstFixedBlend) == SkBlendMode
```

**目的**：
- 简化混合模式到 ID 的转换
- 支持固定功能硬件混合
- 确保不同混合模式产生不同的管线键

### 2. 分层实现策略

渐变着色器提供 4 种实现，根据颜色数量选择最优方案：
- **4 色**：内联常量，最快
- **8 色**：展开循环，次优
- **纹理**：适用于任意色数
- **缓冲区**：支持动态更新

### 3. 代码片段组合

通过 `kCompose` 和 `kBlendCompose` 支持树状着色器组合：
```
kCompose(kSolidColorShader, kMatrixColorFilter)
```

### 4. 错误处理内置

`kError` 不仅是错误信号，还实现默认绘制行为（虽然 `Device` 会丢弃此类绘制）。

### 5. 硬件加速标记

`kHW*` 前缀标识使用硬件特定优化的片段，如硬件纹理采样。

## 性能考量

### 1. 固定混合的内联优化

固定混合模式硬编码到着色器树中：
- 编译器可内联常量
- 支持固定功能 GPU 混合
- 减少动态分支

### 2. 渐变实现选择

根据渐变复杂度选择实现：
- 简单渐变：寄存器常量（最快）
- 中等渐变：展开循环
- 复杂渐变：纹理查找（避免寄存器压力）

### 3. 代码复用 vs. 变体数量

**权衡**：
- 更多代码片段 → 更多着色器变体 → 更大缓存
- 更少代码片段 → 更多动态分支 → 运行时开销

Graphite 选择：为常用效果提供专用片段。

### 4. 管线键唯一性

每个 ID 确保产生唯一的 `PaintParamsKey`：
- 高效管线缓存
- 避免意外着色器复用
- 支持快速相等性比较

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/ShaderCodeDictionary.h` | 使用者 | ID 到着色器代码的映射 |
| `src/gpu/graphite/PaintParamsKey.h` | 使用者 | 使用 ID 构建管线键 |
| `src/gpu/graphite/KeyContext.h` | 使用者 | 构建代码片段的上下文 |
| `src/gpu/graphite/PipelineData.h` | 使用者 | 代码片段的 uniform 数据 |
| `include/core/SkBlendMode.h` | 对齐 | 混合模式枚举 |
| `src/gpu/graphite/Renderer.h` | 使用者 | 渲染器使用代码片段 |
