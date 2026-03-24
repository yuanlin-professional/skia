# src/effects/imagefilters - 图像滤镜实现

## 概述

`src/effects/imagefilters` 目录实现了 Skia 图形库中全部**图像滤镜**（Image Filter）的具体子类。与颜色滤镜逐像素处理不同，图像滤镜在**图像区域**级别操作，能够读取和变换整个像素区域，实现模糊、光照、形态学运算等复杂的视觉效果。所有图像滤镜均继承自 `SkImageFilter_Base`（定义于 `src/core`），后者是公共接口 `SkImageFilter` 的内部扩展。

本目录包含 **17 个图像滤镜实现文件**，覆盖了 SVG 滤镜规范中的大部分效果以及 Skia 专有的扩展效果。这些滤镜可分为几大类别：基础变换类（裁剪、合并、组合、矩阵变换）、模糊与形态学类（高斯模糊、腐蚀/膨胀）、光照类（远距离光、点光源、聚光灯的漫反射和镜面反射）、颜色处理类（颜色滤镜适配、混合）、位移与卷积类（位移映射、矩阵卷积），以及特殊效果类（放大镜、投影阴影、运行时自定义效果）。

图像滤镜的执行建立在 `skif`（Skia Image Filter Types）命名空间定义的**坐标空间类型系统**之上。该系统严格区分了参数空间（`ParameterSpace`）、图层空间（`LayerSpace`）和设备空间，通过 `skif::Mapping` 进行坐标变换。每个滤镜必须实现三个核心虚函数：`onFilterImage()`（执行滤镜）、`onGetInputLayerBounds()`（计算所需输入区域）和 `onGetOutputLayerBounds()`（计算输出区域范围）。这种显式的边界计算机制使得 Skia 能够精确控制每个滤镜阶段的像素读写范围，避免不必要的大面积处理。

图像滤镜支持**有向无环图**（DAG）组合。通过输入数组（`inputs[]`）机制，一个滤镜可以接收多个子滤镜的输出作为输入。例如 `SkBlendImageFilter` 接收背景和前景两个输入，`SkMergeImageFilter` 可以合并任意数量的输入。`SkComposeImageFilter` 则将外部滤镜的输入重定向到内部滤镜的输出，实现串行组合。

许多图像滤镜的像素处理逻辑通过 **SkSL 运行时效果**实现。光照、位移映射、放大镜、形态学运算和矩阵卷积等复杂效果都使用预编译的 SkSL 着色器（通过 `SkKnownRuntimeEffects` 获取），确保在光栅和 GPU 后端都能高效执行。

## 架构图

```
                    +-------------------------+
                    |    SkImageFilter         |
                    | (include/core 公共接口)   |
                    +-----------+-------------+
                                |
                    +-----------v-------------+
                    |  SkImageFilter_Base      |
                    |  (src/core 内部基类)      |
                    |  - onFilterImage() = 0   |
                    |  - onGetInputLayer       |
                    |    Bounds() = 0          |
                    |  - onGetOutputLayer      |
                    |    Bounds() = 0          |
                    +-----------+-------------+
                                |
     +------+------+------+----+----+------+------+------+
     |      |      |      |        |      |      |      |
  +--v--+ +-v--+ +-v--+ +-v--+ +--v--+ +-v--+ +-v--+ +-v--+
  |Blur | |Crop| |Blend| |Comp| |Morph| |Light| |Disp| |更多|
  |Image| |    | |Image| |ose | |ology| |ing  | |lace| |... |
  |Fltr | |    | |Fltr | |    | |     | |     | |Map | |    |
  +--+--+ +----+ +--+--+ +----+ +-----+ +-----+ +----+ +----+
     |              |
     v              v
  +--+--------------+---+     +-------------------+
  | skif::FilterResult  |     | SkKnownRuntime    |
  | (滤镜结果封装)       |     | Effects           |
  +----------+----------+     | (SkSL预编译效果)   |
             |                +--------+----------+
             v                         |
  +----------+----------+    +---------v----------+
  | skif::Context       |    | SkRuntimeEffect    |
  | (滤镜执行上下文)     |    | (SkSL运行时引擎)   |
  +---------------------+    +--------------------+
             |                         |
             v                         v
  +----------+-------------------------+--+
  |        SkBlurEngine / GPU Backend     |
  |        (模糊引擎 / GPU 渲染后端)       |
  +---------------------------------------+
```

## 目录结构

```
src/effects/imagefilters/
|-- BUILD.bazel                              # Bazel 构建配置
|-- SkBlendImageFilter.cpp                   # 混合图像滤镜（两个输入按混合模式合成）
|-- SkBlurImageFilter.cpp                    # 高斯模糊图像滤镜
|-- SkColorFilterImageFilter.cpp             # 颜色滤镜适配为图像滤镜
|-- SkComposeImageFilter.cpp                 # 组合图像滤镜（串联两个滤镜）
|-- SkCropImageFilter.cpp                    # 裁剪图像滤镜（限制输出区域）
|-- SkDisplacementMapImageFilter.cpp         # 位移映射图像滤镜
|-- SkDropShadowImageFilter.cpp              # 投影阴影图像滤镜
|-- SkImageImageFilter.cpp                   # 图片源图像滤镜
|-- SkLightingImageFilter.cpp                # 光照图像滤镜（漫反射/镜面反射）
|-- SkMagnifierImageFilter.cpp               # 放大镜图像滤镜
|-- SkMatrixConvolutionImageFilter.cpp       # 矩阵卷积图像滤镜
|-- SkMatrixConvolutionImageFilter.h         # 矩阵卷积内部头文件（常量定义）
|-- SkMatrixTransformImageFilter.cpp         # 矩阵变换图像滤镜
|-- SkMergeImageFilter.cpp                   # 合并图像滤镜（多个输入叠加）
|-- SkMorphologyImageFilter.cpp              # 形态学图像滤镜（腐蚀/膨胀）
|-- SkPictureImageFilter.cpp                 # 图片录制源图像滤镜
|-- SkRuntimeImageFilter.cpp                 # 运行时自定义图像滤镜
|-- SkShaderImageFilter.cpp                  # 着色器源图像滤镜
```

## 关键类与函数

### SkBlurImageFilter - 高斯模糊滤镜

对输入图像应用高斯模糊效果，是最常用的图像滤镜之一：

```cpp
class SkBlurImageFilter final : public SkImageFilter_Base {
    skif::ParameterSpace<SkSize> fSigma;              // 模糊半径（参数空间）
    SkTileMode fLegacyTileMode = SkTileMode::kDecal;  // 旧版平铺模式
};
```

核心特性：
- 模糊核范围为 3 倍 sigma（`kernelBounds` 方法）
- 通过 `SkBlurEngine` 执行实际模糊运算，支持 CPU 和 GPU 后端
- `fLegacyTileMode` 用于向后兼容，新代码应使用 `SkCropImageFilter` 控制边界行为
- sigma 通过 `skif::Mapping` 从参数空间映射到图层空间

### SkBlendImageFilter - 混合图像滤镜

将背景和前景两个输入按照指定的混合模式进行合成：

```cpp
class SkBlendImageFilter : public SkImageFilter_Base {
    static constexpr int kBackground = 0;     // 背景输入索引
    static constexpr int kForeground = 1;     // 前景输入索引

    sk_sp<SkBlender> fBlender;                             // 混合器
    std::optional<SkV4> fArithmeticCoefficients;           // 算术混合系数 (k1,k2,k3,k4)
    bool fEnforcePremul;                                   // 是否强制预乘
};
```

支持标准 `SkBlendMode` 和自定义 `SkBlender`（包括算术混合）。当 k3 != 0 时会影响透明黑色。

### SkColorFilterImageFilter - 颜色滤镜适配器

将 `SkColorFilter` 包装为 `SkImageFilter`，在图像滤镜链中应用颜色变换：

```cpp
class SkColorFilterImageFilter final : public SkImageFilter_Base {
    sk_sp<SkColorFilter> fColorFilter;  // 被包装的颜色滤镜
};
```

构造时会优化连续的颜色滤镜节点：如果输入也是颜色滤镜图像滤镜，会将两个颜色滤镜组合为一个。支持 `onIsColorFilterNode()` 查询，使上层可以提取和优化颜色滤镜节点。

### SkComposeImageFilter - 组合图像滤镜

将两个图像滤镜串联执行（外部滤镜处理内部滤镜的输出）：

```cpp
class SkComposeImageFilter final : public SkImageFilter_Base {
    static constexpr int kOuter = 0;  // 外部滤镜（后执行）
    static constexpr int kInner = 1;  // 内部滤镜（先执行）
};
```

外部滤镜的源图像输入被重定向到内部滤镜的输出，`usesSource()` 仅取决于内部滤镜是否使用源图像。

### SkCropImageFilter - 裁剪图像滤镜

限制滤镜输出的空间范围，并支持多种平铺模式：

```cpp
class SkCropImageFilter final : public SkImageFilter_Base {
    skif::ParameterSpace<SkRect> fCropRect;  // 裁剪矩形（浮点，参数空间）
    SkTileMode fTileMode;                     // 平铺模式（Decal/Clamp/Repeat/Mirror）
};
```

裁剪矩形使用浮点数以支持亚像素精度。非 `kDecal` 平铺模式会影响透明黑色。`ignoreInputsAffectsTransparentBlack()` 返回 `true` 以阻止透明黑色影响的向上传播。

### SkLightingImageFilter - 光照图像滤镜

实现基于 SVG 规范的光照效果，支持漫反射（Diffuse）和镜面反射（Specular）两种光照模型：

```cpp
struct Light {
    enum class Type { kDistant, kPoint, kSpot };
    Type fType;
    SkColor fLightColor;
    skif::ParameterSpace<SkPoint> fLocationXY;    // 点光源/聚光灯位置
    skif::ParameterSpace<ZValue>  fLocationZ;
    skif::ParameterSpace<skif::Vector> fDirectionXY;  // 平行光/聚光灯方向
    skif::ParameterSpace<ZValue>       fDirectionZ;
    float fFalloffExponent;    // 聚光灯衰减指数
    float fCosCutoffAngle;     // 聚光灯截止角余弦
};
```

光源的 X/Y 坐标按 `ParameterSpace` 处理，Z 坐标使用自定义的 `ZValue` 类型，映射到图层空间时按 X/Y 缩放因子的平均值进行缩放。光照计算通过 `SkKnownRuntimeEffects` 中的预编译 SkSL 着色器执行。

### SkMorphologyImageFilter - 形态学图像滤镜

实现腐蚀（Erode）和膨胀（Dilate）两种形态学运算：

```cpp
class SkMorphologyImageFilter final : public SkImageFilter_Base {
    MorphType fType;                          // kErode 或 kDilate
    skif::ParameterSpace<SkSize> fRadii;      // 运算半径（参数空间）
};
```

半径被限制为最大 256 像素以避免性能问题。形态学运算通过分离式（先水平后垂直）的 SkSL 运行时效果执行。

### SkDisplacementMapImageFilter - 位移映射图像滤镜

使用位移图像的颜色通道值对颜色图像进行像素偏移：

```cpp
class SkDisplacementMapImageFilter final : public SkImageFilter_Base {
    static constexpr int kDisplacement = 0;   // 位移图输入索引
    static constexpr int kColor = 1;          // 颜色图输入索引

    SkColorChannel fXChannel;                 // X 方向使用的颜色通道
    SkColorChannel fYChannel;                 // Y 方向使用的颜通道
    SkScalar fScale;                          // 位移缩放因子
};
```

通道值 [0,1] 映射到偏移量 [-scale/2, scale/2]。采样目前使用最近邻模式。

### SkMatrixConvolutionImageFilter - 矩阵卷积图像滤镜

使用自定义卷积核对图像进行卷积运算：

```cpp
class SkMatrixConvolutionImageFilter final : public SkImageFilter_Base {
    TArray<float> fKernel;            // 卷积核数据
    SkISize fKernelSize;              // 卷积核尺寸
    skif::ParameterSpace<SkIPoint> fKernelOffset;  // 核偏移
    float fGain;                      // 增益因子
    float fBias;                      // 偏置值
    bool fConvolveAlpha;              // 是否对 alpha 通道进行卷积
};
```

核大小有两个阈值：`kSmallKernelSize` 和 `kLargeKernelSize`。小核使用 uniform 数组传递，大核编码为 A8 位图纹理。核数据以 `half4` 打包以避免 std140 对齐浪费。

### SkDropShadowImageFilter - 投影阴影图像滤镜

通过组合多个基础图像滤镜来实现投影阴影效果（组合模式）：

```cpp
// 不再作为独立的 SkImageFilter_Base 子类实现，而是组合以下滤镜：
// 1. Blur(sigma) -> 模糊输入
// 2. ColorFilter(Blend(color, kSrcIn)) -> 将模糊结果着色
// 3. MatrixTransform(offset) -> 偏移阴影位置
// 4. Merge(shadow, input) 或仅 shadow（shadowOnly 模式）
// 5. Crop(cropRect) -> 可选裁剪
```

新版序列化直接存储组合滤镜图，旧版通过 `legacy_drop_shadow_create_proc()` 兼容读取。

### SkRuntimeImageFilter - 运行时自定义图像滤镜

允许用户通过 SkSL 着色器创建自定义图像滤镜：

```cpp
class SkRuntimeImageFilter final : public SkImageFilter_Base {
    SkRuntimeShaderBuilder fRuntimeEffectBuilder;  // SkSL 效果构建器
    float fMaxSampleRadius;                         // 最大采样半径
    TArray<SkString> fChildShaderNames;             // 子着色器名称
};
```

`fMaxSampleRadius` 控制输出边界相对于输入边界的扩展量。由于无法自动推断几何 uniform 的语义，当前限制为仅平移变换。

### 其他滤镜

| 类名 | 功能 |
|------|------|
| `SkImageImageFilter` | 将 `SkImage` 作为滤镜源，支持源/目标矩形映射 |
| `SkMergeImageFilter` | 将多个输入滤镜的结果按顺序叠加（src-over） |
| `SkMatrixTransformImageFilter` | 对输入图像应用仿射/透视矩阵变换 |
| `SkPictureImageFilter` | 将 `SkPicture` 录制内容作为滤镜源 |
| `SkShaderImageFilter` | 将 `SkShader` 作为滤镜源，支持抖动 |
| `SkMagnifierImageFilter` | 对指定区域进行放大，带有平滑过渡的边缘 |

## 依赖关系

### 向上依赖（被以下模块使用）

- `include/effects/SkImageFilters.h` - 公共工厂函数命名空间
- `src/core/SkCanvas` - 画布绘制时执行图像滤镜
- `src/core/SkPaint` - 绘制属性中引用图像滤镜
- `src/core/SkDevice` - 设备层处理图像滤镜的实际渲染
- `src/gpu/ganesh/` - Ganesh GPU 后端执行图像滤镜
- `src/gpu/graphite/` - Graphite GPU 后端执行图像滤镜

### 向下依赖（依赖以下模块）

- `src/core/SkImageFilter_Base` - 图像滤镜基类
- `src/core/SkImageFilterTypes.h` - `skif` 命名空间的坐标空间类型系统
- `src/core/SkBlurEngine` - 高斯模糊执行引擎
- `src/core/SkKnownRuntimeEffects` - 预编译 SkSL 运行时效果
- `include/effects/SkRuntimeEffect.h` - SkSL 运行时效果框架
- `src/core/SkReadBuffer` / `SkWriteBuffer` - 序列化/反序列化
- `src/core/SkPicturePriv.h` - 序列化版本兼容性常量
- `src/core/SkRectPriv.h` - 矩形辅助工具
- `src/effects/colorfilters/SkColorFilterBase.h` - 颜色滤镜基类（颜色滤镜适配器使用）
- `include/core/SkBlender` / `SkBlendMode` - 混合接口（混合滤镜使用）
- `include/effects/SkBlenders.h` - 算术混合器（混合滤镜使用）

## 设计模式分析

### 坐标空间类型安全系统

`skif` 命名空间通过模板包装（`ParameterSpace<T>` 和 `LayerSpace<T>`）实现了**编译期坐标空间安全**。这是一种**幻影类型**（Phantom Type）模式的应用：

```cpp
skif::ParameterSpace<SkSize> fSigma;          // 参数空间中的模糊半径
skif::LayerSpace<SkIRect> outputBounds;       // 图层空间中的输出边界
skif::LayerSpace<SkSize> layerSigma = mapping.paramToLayer(fSigma);  // 安全转换
```

这种设计在编译时防止了不同坐标空间之间的错误混用，同时 `skif::Mapping` 提供了安全的空间转换方法。

### 组合图像滤镜图（DAG 模式）

图像滤镜通过输入数组形成有向无环图。每个滤镜的 `inputs[]` 可以指向其他滤镜或为 null（表示使用源图像）：

```
DropShadow 示例（组合模式）：
    Merge
    |-- MatrixTransform(offset)
    |   |-- ColorFilter(Blend(color, kSrcIn))
    |       |-- Blur(sigma)
    |           |-- [Source]
    |-- [Source]
```

这种模式使得复杂效果可以由简单效果组合而成，`SkDropShadowImageFilter` 就是典型示例。

### FilterResult 封装

`skif::FilterResult` 封装了图像滤镜的中间结果，包含图像数据和元信息（采样选项、颜色滤镜等）。滤镜之间通过 `FilterResult` 传递数据，而非裸指针。这种封装支持了延迟评估和批量优化。

### 运行时效果委托

复杂的像素处理逻辑通过 SkSL 运行时效果实现。滤镜类负责参数管理和边界计算，实际像素操作委托给预编译的 SkSL 程序：

- 光照效果 -> `SkKnownRuntimeEffects::StableKey` 中的光照着色器
- 形态学运算 -> 分离式腐蚀/膨胀着色器
- 位移映射 -> 位移采样着色器
- 放大镜 -> 放大镜着色器
- 矩阵卷积 -> 小核/大核两种卷积着色器

### 旧版兼容性策略

多个滤镜实现了旧版序列化格式的兼容读取：

- `SkDropShadowImageFilter` 通过 `legacy_drop_shadow_create_proc` 读取旧格式，新格式直接序列化组合滤镜图
- `SkMatrixTransformImageFilter` 通过 `LegacyOffsetCreateProc` 兼容旧版 `SkOffsetImageFilter`
- `SkCropImageFilter` 通过 `LegacyTileCreateProc` 兼容旧版 `SkTileImageFilter`
- 版本判断通过 `SkPicturePriv::Version` 枚举进行

### MatrixCapability 分级

每个滤镜声明自己对变换矩阵的支持级别：

```cpp
enum class MatrixCapability {
    kTranslate,  // 仅支持平移
    kScaleTranslate,  // 支持缩放和平移
    kComplex  // 支持任意仿射/透视变换
};
```

大多数滤镜返回 `kComplex`，但 `SkRuntimeImageFilter` 由于无法推断 uniform 语义而限制为 `kTranslate`。

## 数据流

### 图像滤镜总体执行流程

```
SkCanvas::drawX(paint)  // paint 包含 SkImageFilter
    |
    v
SkDevice::drawDevice()
    |
    v
SkImageFilter_Base::filterImage(skif::Context)
    |
    +-- 1. 计算输出边界
    |       onGetOutputLayerBounds(mapping, contentBounds)
    |
    +-- 2. 计算所需输入边界
    |       onGetInputLayerBounds(mapping, desiredOutput, contentBounds)
    |
    +-- 3. 递归处理输入滤镜
    |       filterInput(index, context) -> skif::FilterResult
    |
    +-- 4. 执行本滤镜
    |       onFilterImage(context) -> skif::FilterResult
    |
    v
最终 FilterResult -> 设备渲染
```

### 高斯模糊执行流程

```
SkBlurImageFilter::onFilterImage(context)
    |
    v
1. 获取输入滤镜结果
   filterInput(0, context) -> inputResult
    |
    v
2. 计算图层空间的 sigma
   mapSigma(mapping) -> layerSigma
    |
    v
3. 委托给模糊引擎
   context.blurEngine()->blur(layerSigma, inputResult, ...)
    |
    +-- CPU: SkRasterPipeline 模糊实现
    +-- GPU: 硬件加速模糊（分离式两遍高斯）
    |
    v
4. 返回模糊后的 FilterResult
```

### 光照滤镜执行流程

```
SkLightingImageFilter::onFilterImage(context)
    |
    v
1. 获取输入并转为着色器
   filterInput(0, context) -> inputResult
   inputResult.asShaderWithLayerPosition() -> inputShader
    |
    v
2. 构建光源参数
   Light 从 ParameterSpace 映射到 LayerSpace
    |
    v
3. 选择 SkSL 光照着色器
   GetKnownRuntimeEffect(StableKey::kLighting_*)
    |
    v
4. 设置 uniform 参数
   (光源类型、位置、方向、颜色、表面缩放、反射系数...)
    |
    v
5. 绑定子着色器（输入图像、法线计算）
    |
    v
6. 构建 SkRuntimeShaderBuilder 并执行
   -> FilterResult
```

### 位移映射执行流程

```
SkDisplacementMapImageFilter::onFilterImage(context)
    |
    v
1. 获取两个输入
   filterInput(kDisplacement) -> 位移图
   filterInput(kColor)        -> 颜色图
    |
    v
2. 转为着色器
   displacementResult.asShaderWithLayerPosition()
   colorResult.asShaderWithLayerPosition()
    |
    v
3. 加载位移映射 SkSL 着色器
   GetKnownRuntimeEffect(StableKey::kDisplacementMap)
    |
    v
4. 设置参数 (xChannel, yChannel, scale)
    |
    v
5. 对每个输出像素：
   a. 读取位移图对应像素的通道值
   b. 计算偏移量 = (channelValue - 0.5) * scale
   c. 从颜色图的偏移位置采样
    |
    v
6. 返回 FilterResult
```

### 矩阵卷积执行流程

```
SkMatrixConvolutionImageFilter::onFilterImage(context)
    |
    v
1. 获取输入
   filterInput(0, context) -> inputResult
    |
    v
2. 选择卷积 SkSL 着色器
   kernelSize <= kSmallKernelSize?
   +-- 是: 使用 uniform 数组传递核（StableKey::kMatrixConvSmall）
   +-- 否: 使用位图纹理传递核（StableKey::kMatrixConvLarge）
    |
    v
3. 打包核数据
   小核: float[] -> uniform half4[]（4个一组打包）
   大核: float[] -> A8 SkBitmap -> 纹理采样
    |
    v
4. 设置 uniform (kernelSize, offset, gain, bias, convolveAlpha)
    |
    v
5. 对每个输出像素执行卷积运算
   result = sum(kernel[i][j] * sample(x+i, y+j)) * gain + bias
    |
    v
6. 返回 FilterResult
```

## 相关文档与参考

### 公共 API 工厂函数

| 函数 | 对应滤镜类 | 描述 |
|------|-----------|------|
| `SkImageFilters::Blur(sigmaX, sigmaY, input)` | `SkBlurImageFilter` | 高斯模糊 |
| `SkImageFilters::Blend(mode, bg, fg)` | `SkBlendImageFilter` | 混合两个输入 |
| `SkImageFilters::ColorFilter(cf, input)` | `SkColorFilterImageFilter` | 应用颜色滤镜 |
| `SkImageFilters::Compose(outer, inner)` | `SkComposeImageFilter` | 串联组合 |
| `SkImageFilters::Crop(rect, tileMode, input)` | `SkCropImageFilter` | 裁剪/平铺 |
| `SkImageFilters::DisplacementMap(...)` | `SkDisplacementMapImageFilter` | 位移映射 |
| `SkImageFilters::DropShadow(...)` | (组合滤镜) | 投影阴影 |
| `SkImageFilters::DropShadowOnly(...)` | (组合滤镜) | 仅阴影 |
| `SkImageFilters::Image(image, ...)` | `SkImageImageFilter` | 图片源 |
| `SkImageFilters::DistantLitDiffuse(...)` | `SkLightingImageFilter` | 远光漫反射 |
| `SkImageFilters::PointLitDiffuse(...)` | `SkLightingImageFilter` | 点光漫反射 |
| `SkImageFilters::SpotLitDiffuse(...)` | `SkLightingImageFilter` | 聚光漫反射 |
| `SkImageFilters::DistantLitSpecular(...)` | `SkLightingImageFilter` | 远光镜面 |
| `SkImageFilters::PointLitSpecular(...)` | `SkLightingImageFilter` | 点光镜面 |
| `SkImageFilters::SpotLitSpecular(...)` | `SkLightingImageFilter` | 聚光镜面 |
| `SkImageFilters::Magnifier(...)` | `SkMagnifierImageFilter` | 放大镜 |
| `SkImageFilters::MatrixConvolution(...)` | `SkMatrixConvolutionImageFilter` | 矩阵卷积 |
| `SkImageFilters::MatrixTransform(...)` | `SkMatrixTransformImageFilter` | 矩阵变换 |
| `SkImageFilters::Merge(filters[], count)` | `SkMergeImageFilter` | 多层合并 |
| `SkImageFilters::Dilate(rx, ry, input)` | `SkMorphologyImageFilter` | 膨胀 |
| `SkImageFilters::Erode(rx, ry, input)` | `SkMorphologyImageFilter` | 腐蚀 |
| `SkImageFilters::Picture(picture, rect)` | `SkPictureImageFilter` | 录制源 |
| `SkImageFilters::RuntimeShader(...)` | `SkRuntimeImageFilter` | 自定义 SkSL |
| `SkImageFilters::Shader(shader, dither)` | `SkShaderImageFilter` | 着色器源 |

### 相关核心模块

| 模块 | 描述 |
|------|------|
| `src/core/SkImageFilter_Base.h` | 图像滤镜内部基类 |
| `src/core/SkImageFilterTypes.h` | `skif` 坐标空间类型系统 |
| `src/core/SkBlurEngine.h` | 模糊引擎抽象接口 |
| `src/core/SkKnownRuntimeEffects.h` | 预编译 SkSL 效果注册表 |
| `src/effects/colorfilters/` | 颜色滤镜实现（被 `SkColorFilterImageFilter` 使用） |
| `src/effects/SkEmbossMaskFilter.h` | 浮雕遮罩滤镜（光照相关，`LegacySpecular` 定义于光照滤镜中） |
| `include/effects/SkImageFilters.h` | 图像滤镜公共工厂函数 |
| `include/effects/SkRuntimeEffect.h` | SkSL 运行时效果框架 |
