# effects - 视觉效果 API

## 概述

`include/effects` 目录定义了 Skia 丰富的视觉效果 API，包含路径效果（PathEffect）、
图像滤镜（ImageFilter）、颜色滤镜（ColorFilter）、遮罩滤镜（MaskFilter）、着色器
（Shader）和混合器（Blender）等多种效果类型。这些效果可以单独使用，也可以组合成
复杂的视觉效果管线。

路径效果模块提供了一系列变换路径几何形状的工具：`SkDashPathEffect` 创建虚线效果；
`Sk1DPathEffect` / `Sk2DPathEffect` 沿路径复制图案；`SkCornerPathEffect` 将尖角
转换为圆角；`SkDiscretePathEffect` 对路径进行随机扰动；`SkTrimPathEffect` 截取
路径的子段。这些效果可以通过 `SkPathEffect::MakeCompose` 进行链式组合。

图像滤镜模块（`SkImageFilters`）是该目录中最为庞大的部分，提供了超过30种滤镜效果，
包括模糊、阴影、光照（漫反射和镜面反射，支持远光、点光和聚光灯三种光源）、形态学
操作（膨胀和腐蚀）、颜色过滤、位移映射、矩阵卷积、仿射变换等。所有这些滤镜都可以
通过 `Compose` 和 `Merge` 操作组合成有向无环图（DAG）形式的复杂效果。

`SkRuntimeEffect` 是 Skia 最强大的扩展机制之一，允许开发者使用 SkSL 着色语言编写
自定义的着色器、颜色滤镜和混合器。通过 `SkRuntimeEffectBuilder` 构建器模式，可以
方便地设置 uniform 变量和子着色器，创建高度定制化的渲染效果。

渐变着色器（`SkGradient`）支持线性渐变、径向渐变、双圆锥渐变和扇形渐变四种类型，
并提供了丰富的颜色空间插值选项，包括 sRGB、OKLab、OKLCH、HSL 等多种色彩空间。

## 架构图

```
+------------------------------------------------------------------+
|                       SkPaint 绘制属性                             |
|  PathEffect / Shader / ColorFilter / MaskFilter / Blender         |
+------------------------------------------------------------------+
         |              |              |             |
         v              v              v             v
+-------------+  +-------------+  +----------+  +-----------+
| PathEffect  |  |   Shader    |  | Color    |  | Mask      |
| 路径效果     |  |  着色器     |  | Filter   |  | Filter    |
+-------------+  +-------------+  | 颜色滤镜 |  | 遮罩滤镜  |
| Dash        |  | Gradient   |  +----------+  +-----------+
| 1D/2D Path  |  | - Linear   |  | ColorMat |  | Blur      |
| Corner      |  | - Radial   |  | LumaCF   |  | Shader    |
| Discrete    |  | - Conical  |  | Overdraw |  | Table     |
| Trim        |  | - Sweep    |  | HighContr|  +-----------+
+-------------+  | Perlin     |  +----------+
                 | Runtime    |
                 +-------------+      +-------------------+
                                      |   ImageFilter     |
+------------------+                  |  图像滤镜          |
| SkRuntimeEffect  |                  +-------------------+
| SkSL 运行时效果   |<--------------->| Blur / DropShadow |
| - makeShader()   |                  | Lighting (6种)    |
| - makeColorFilter|                  | Morphology        |
| - makeBlender()  |                  | DisplacementMap   |
+------------------+                  | MatrixConvolution |
                                      | Blend / Compose   |
+------------------+                  | Crop / Offset     |
|   SkBlenders     |                  | RuntimeShader     |
|  算术混合器       |                  +-------------------+
+------------------+
```

## 目录结构

```
include/effects/
  BUILD.bazel                # Bazel 构建配置
  Sk1DPathEffect.h           # 沿路径复制1D图案的路径效果
  Sk2DPathEffect.h           # 2D路径效果：线条网格和路径网格
  SkBlenders.h               # 自定义混合器（算术混合）
  SkBlurMaskFilter.h         # 模糊遮罩滤镜（含浮雕效果，已部分弃用）
  SkColorMatrix.h            # 5x4 颜色矩阵类
  SkColorMatrixFilter.h      # 基于颜色矩阵的颜色滤镜
  SkCornerPathEffect.h       # 圆角路径效果
  SkDashPathEffect.h         # 虚线路径效果
  SkDiscretePathEffect.h     # 离散化随机扰动路径效果
  SkGradient.h               # 渐变着色器（线性/径向/锥形/扇形）
  SkHighContrastFilter.h     # 高对比度颜色滤镜（辅助功能）
  SkImageFilters.h           # 图像滤镜工厂类（30+种滤镜）
  SkLumaColorFilter.h        # 亮度颜色滤镜
  SkOverdrawColorFilter.h    # 过度绘制可视化颜色滤镜
  SkPerlinNoiseShader.h      # Perlin 噪声着色器
  SkRuntimeEffect.h          # SkSL 运行时效果（自定义着色器/滤镜/混合器）
  SkShaderMaskFilter.h       # 基于着色器的遮罩滤镜
  SkTableMaskFilter.h        # 查找表遮罩滤镜
  SkTrimPathEffect.h         # 路径截取效果
```

## 关键类与函数

### SkImageFilters - 图像滤镜工厂

提供丰富的静态工厂方法创建图像滤镜：

- **模糊与阴影**：`Blur()`, `DropShadow()`, `DropShadowOnly()`
- **颜色处理**：`ColorFilter()`, `Blend()`, `Arithmetic()`
- **几何变换**：`MatrixTransform()`, `Offset()`, `Crop()`, `Tile()`
- **形态学操作**：`Dilate()`, `Erode()`
- **光照效果**（漫反射和镜面反射，各支持三种光源）：
  - `DistantLitDiffuse()`, `PointLitDiffuse()`, `SpotLitDiffuse()`
  - `DistantLitSpecular()`, `PointLitSpecular()`, `SpotLitSpecular()`
- **高级功能**：`DisplacementMap()`, `MatrixConvolution()`, `Magnifier()`
- **组合操作**：`Compose()`, `Merge()`, `RuntimeShader()`
- **输入源**：`Image()`, `Picture()`, `Shader()`, `Empty()`

### SkRuntimeEffect - SkSL 运行时效果

允许使用 SkSL 编写自定义效果：
- `MakeForShader()` - 入口：`vec4 main(vec2 inCoords)`
- `MakeForColorFilter()` - 入口：`vec4 main(vec4 inColor)`
- `MakeForBlender()` - 入口：`vec4 main(vec4 srcColor, vec4 dstColor)`
- `SkRuntimeEffectBuilder` - uniform 和子着色器绑定的构建器

### SkGradient - 渐变着色器

- `SkShaders::LinearGradient()` - 线性渐变
- `SkShaders::RadialGradient()` - 径向渐变
- `SkShaders::TwoPointConicalGradient()` - 双圆锥渐变
- `SkShaders::SweepGradient()` - 扇形渐变
- `SkGradient::Interpolation` - 插值配置（色彩空间、预乘、色相方法）

### 路径效果

- `SkDashPathEffect::Make()` - 创建虚线效果
- `SkPath1DPathEffect::Make()` - 沿路径复制图案
- `SkCornerPathEffect::Make()` - 圆角化
- `SkDiscretePathEffect::Make()` - 随机扰动
- `SkTrimPathEffect::Make()` - 截取路径子段

### SkColorMatrix - 颜色矩阵

5x4 浮点矩阵，用于颜色空间变换：
- `setSaturation()` - 设置饱和度
- `setScale()` - 设置 RGBA 缩放
- `RGBtoYUV()` / `YUVtoRGB()` - RGB 与 YUV 互转

### SkHighContrastFilter - 高对比度滤镜

辅助功能滤镜，支持灰度转换、亮度/明度反转和对比度调节。

## 依赖关系

- **内部依赖**：`include/core`（SkShader、SkColorFilter、SkPathEffect、SkBlender、SkImageFilter 等基类）
- **内部依赖**：`include/sksl`（SkSL 版本和调试追踪）
- **被依赖**：应用层通过 SkPaint 使用各种效果

## 相关文档与参考

- SVG 滤镜规范（图像滤镜的设计灵感）：https://www.w3.org/TR/SVG/filters.html
- CSS Color Level 4（渐变插值色彩空间）：https://www.w3.org/TR/css-color-4/
- Perlin 噪声算法：https://www.w3.org/TR/SVG/filters.html#feTurbulenceElement
- SkSL 着色语言文档
- 源码实现位于 `src/effects/` 和 `src/core/` 目录
