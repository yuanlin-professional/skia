# SkLightingImageFilter

> 源文件: `src/effects/imagefilters/SkLightingImageFilter.cpp`

## 概述

`SkLightingImageFilter` 实现了基于法线贴图的光照图像滤镜效果,对应 SVG 的 `feDiffuseLighting` 和 `feSpecularLighting` 滤镜。它通过输入图像的 alpha 通道构建表面法线(使用 Sobel 核),然后应用漫反射或镜面反射光照模型,支持远光(Distant)、点光(Point)和聚光灯(Spot)三种光源类型。该滤镜是 Skia 中最复杂的图像滤镜之一,涉及 3D 光照数学、法线贴图生成和多种光源模型。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkLightingImageFilter (本文件)
            ├─ 输入[0]: alpha 源图像
            ├─ Light 结构体 (三种光源)
            ├─ Material 结构体 (三种材质)
            ├─ SkSL 法线着色器 (kNormal StableKey)
            └─ SkSL 光照着色器 (kLighting StableKey)

工厂方法:
  SkImageFilters::DistantLitDiffuse / PointLitDiffuse / SpotLitDiffuse
  SkImageFilters::DistantLitSpecular / PointLitSpecular / SpotLitSpecular
```

## 主要类与结构体

### `ZValue` 结构体
表示 3D 空间中的 Z 坐标值。X/Y 坐标使用标准的 `ParameterSpace`/`LayerSpace` 类型,而 Z 坐标按 X/Y 缩放因子的平均值进行变换。提供了 `skif::LayerSpace<ZValue>` 特化。

### `Light` 结构体
光源参数,包含:
- `Type` 枚举: `kDistant`(远光)、`kPoint`(点光)、`kSpot`(聚光灯)
- 位置(`fLocationXY`/`fLocationZ`): 点光和聚光灯使用
- 方向(`fDirectionXY`/`fDirectionZ`): 远光和聚光灯使用
- 聚光灯参数: `fFalloffExponent`、`fCosCutoffAngle`
- 静态工厂方法: `Point()`, `Distant()`, `Spot()`

### `Material` 结构体
材质参数,包含:
- `Type` 枚举: `kDiffuse`(漫反射)、`kSpecular`(镜面反射)、`kEmbossSpecular`(浮雕)
- `fSurfaceDepth`: 表面深度(alpha 值到高度的缩放)
- `fK`: 反射系数
- `fShininess`: 光泽度(仅镜面反射)
- 静态工厂方法: `Diffuse()`, `Specular()`, `EmbossSpecular()`

### `SkLightingImageFilter`
- 继承自 `SkImageFilter_Base`,接收一个子滤镜输入
- 成员: `fLight` 和 `fMaterial`

## 公共 API 函数

六个工厂方法覆盖 3 种光源 x 2 种材质的组合:
- `DistantLitDiffuse`, `PointLitDiffuse`, `SpotLitDiffuse`
- `DistantLitSpecular`, `PointLitSpecular`, `SpotLitSpecular`

聚光灯工厂方法自动计算方向向量(`target - location`)和余弦截止角。

### `SkEmbossMaskFilter::LegacySpecular()`
私有工厂方法,用于 `SkEmbossMaskFilter` 的遗留支持。

## 内部实现细节

### 两阶段着色器管线
1. **法线生成** (`make_normal_shader()`):
   - 使用 Sobel 核对 alpha 通道进行卷积,生成表面法线
   - `edgeBounds` 控制边缘处的核权重修正
   - `negSurfaceDepth` 控制 alpha 到高度的映射深度

2. **光照计算** (`make_lighting_shader()`):
   - 接收法线贴图着色器作为子着色器
   - 根据光源类型和材质类型计算最终颜色
   - 预归一化光照方向向量,处理零向量的安全情况

### 法线贴图边界处理
`onFilterImage()` 中的边界处理策略:
- 请求 1 像素扩展作为 Sobel 核的边界数据
- 当子输出完全覆盖所需区域时:使用 clamp 平铺(近似 SVG 规范的修正 Sobel 核)
- 当子输出远小于期望输出时:使用 decal 平铺(在图像边缘产生视觉斜面)
- 边缘自适应:逐边判断是使用 clamp 还是 decal(`edgeClamp` lambda)

### 3D 坐标变换
3D 点/向量的 X、Y 坐标作为 `ParameterSpace<SkPoint/Vector>` 处理,Z 坐标使用 X/Y 缩放因子的平均值进行变换。这遵循最小惊讶原则:均匀缩放时 Z 也均匀缩放。

### 光照颜色不进行色彩空间变换
注释详细说明了不变换光照颜色的理由:
- 历史行为:Skia 和 Chromium 都不进行变换
- SVG 规范未明确规定
- 颜色系数 K 在着色器中预乘(K / 255)

### 序列化
新格式统一序列化所有光源和材质字段。旧格式通过 `LegacyDeserializeLight` 和 `LegacyDiffuseCreateProc`/`LegacySpecularCreateProc` 处理,它们分别解析旧版的光源和材质数据。

## 依赖关系

- `include/core/SkPoint3.h` - 3D 点和向量
- `include/effects/SkRuntimeEffect.h` - 运行时着色器
- `src/core/SkKnownRuntimeEffects.h` - 内置 SkSL 效果
- `src/effects/SkEmbossMaskFilter.h` - 浮雕效果支持
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型

## 设计模式与设计决策

### 统一的光照/材质模型
将所有光源类型和材质类型统一到单一的 `SkLightingImageFilter` 类中,通过枚举区分行为。着色器通过 uniform 选择光源和材质类型,避免为每种组合创建不同的着色器。

### 裁剪矩形的双重应用
当提供 cropRect 时,同时作用于输入(限制法线贴图范围)和输出(限制光照输出范围),更好地匹配 SVG 的边界条件规范。

### Z 轴变换策略
使用 X/Y 缩放平均值处理 Z 坐标,在非均匀缩放时可能不完美,但提供了合理的默认行为。

## 性能考量

- 法线着色器和光照着色器分为两层,但通过着色器组合在单次 Pass 中执行
- 注释提到未来可将法线贴图作为独立滤镜,支持多光源共享同一法线贴图的自动缓存
- Sobel 核仅需 3x3 窗口(1 像素扩展),输入需求增长有限
- 光源方向预归一化避免着色器内的重复计算
- 输出声明为无界(`Unbounded()`)因为光照方程在整个平面上定义

## 光照计算详解

### 漫反射 (Diffuse)
```
L = normalize(lightPos - surfacePos)  // 或直接使用远光方向
N = normalFromSobel(alpha_image)
result = kd * lightColor * max(dot(N, L), 0)
```

### 镜面反射 (Specular)
```
L = normalize(lightPos - surfacePos)
N = normalFromSobel(alpha_image)
H = normalize(L + V)                 // V 为视线方向 (0, 0, 1)
result = ks * lightColor * pow(max(dot(N, H), 0), shininess)
```

### 聚光灯衰减
```
spotDirection = normalize(lightDir)
spotFactor = max(dot(-L, spotDirection), 0)^falloffExponent
if (spotFactor < cosCutoffAngle) spotFactor = 0
finalLight = lightColor * spotFactor
```

### Sobel 核
法线贴图通过 3x3 Sobel 算子计算:
```
Gx = [-1 0 1; -2 0 2; -1 0 1]  // 水平梯度
Gy = [-1 -2 -1; 0 0 0; 1 2 1]  // 垂直梯度
N = normalize(-surfaceDepth * Gx, -surfaceDepth * Gy, 1)
```

## 三种光源的参数空间变换

| 参数 | 远光 | 点光 | 聚光灯 |
|------|------|------|--------|
| 位置 XY | 不使用 | ParameterSpace<SkPoint> -> LayerSpace | ParameterSpace<SkPoint> -> LayerSpace |
| 位置 Z | 不使用 | ParameterSpace<ZValue> -> 平均缩放 | ParameterSpace<ZValue> -> 平均缩放 |
| 方向 XY | ParameterSpace<Vector> -> LayerSpace | 不使用 | ParameterSpace<Vector> -> LayerSpace |
| 方向 Z | ParameterSpace<ZValue> -> 平均缩放 | 不使用 | ParameterSpace<ZValue> -> 平均缩放 |
| 衰减指数 | - | - | 不变换(标量) |
| 余弦截止角 | - | - | 不变换(标量) |

## 边界处理策略

法线贴图的边缘处理是光照滤镜中最微妙的部分:

1. **理想情况** (子输出 >= 所需输入): 使用 clamp 平铺
   - 所有 4 条边和 4 个角使用 clamp 求值
   - 近似 SVG 规范的修正 Sobel 核(仅角点略有差异)

2. **子输出不完整**: 逐边判断
   - 若边缘处子输出匹配期望输出: 该边使用 clamp(SVG 行为)
   - 否则: 使用 decal(产生斜面效果,避免拉伸伪影)

## 材质类型的 EmbossSpecular 变体

`Material::EmbossSpecular` 是一个特殊类型,仅通过 `SkEmbossMaskFilter::LegacySpecular()` 创建。它与标准 Specular 的区别在着色器内部处理(可能使用不同的法线计算或光照公式)。这是为了支持旧版 SkEmbossMaskFilter 的视觉效果。

## 版本兼容性

该滤镜经历了显著的架构重构:
- 旧版: 独立的 `SkDiffuseLightingImageFilter` 和 `SkSpecularLightingImageFilter`
- 新版: 统一为 `SkLightingImageFilter`,通过 Material::Type 区分
- 旧版光源数据格式(浮点 RGB,类型特定字段)在 `LegacyDeserializeLight` 中处理
- 旧版的 `surfaceScale * 255` 序列化约定在 `LegacyDiffuseCreateProc` 中自动处理

新版序列化格式:
```
基类数据 + Light(type, color, pos, dir, falloff, cutoff) + Material(type, depth, K, shininess)
```

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkKnownRuntimeEffects.h` - 内置 SkSL 效果
- `src/sksl/sksl_rt_shader.sksl` - 法线和光照着色器的 SkSL 源码
- `src/effects/SkEmbossMaskFilter.h` - 浮雕效果的遗留支持
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
