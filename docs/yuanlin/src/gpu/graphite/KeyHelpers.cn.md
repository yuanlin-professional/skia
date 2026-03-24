# KeyHelpers

> 源文件
> - src/gpu/graphite/KeyHelpers.h
> - src/gpu/graphite/KeyHelpers.cpp

## 概述

`KeyHelpers` 是 Skia Graphite 渲染引擎中用于手动构建着色器参数键（`PaintParamsKey`）的工具集合。该模块定义了一系列"块"（Block）结构体和辅助函数，每个块对应一种着色器效果类型（如纯色、渐变、图像采样、混合模式、颜色滤镜等），负责将高层绘制参数转换为底层着色器键和管线数据。

这是 Graphite 着色器编译系统的核心组件之一，支持两种操作模式：
1. **预编译模式**：在没有具体绘制参数时生成着色器变体
2. **运行时模式**：从实际 `PaintParams` 提取完整的键和uniform数据

文件规模庞大（超过3000行），包含了 Skia 几乎所有着色器和颜色滤镜的键生成逻辑。

## 架构位置

```
PaintParams (绘制参数)
  └── KeyContext (键生成上下文)
      └── KeyHelpers (块添加器)
          ├── PaintParamsKeyBuilder (键构建)
          ├── PipelineDataGatherer (uniform数据收集)
          └── ShaderCodeDictionary (代码字典)
```

`KeyHelpers` 位于绘制参数和着色器代码生成之间的桥接层，负责将抽象的绘制意图翻译成具体的着色器配置。

## 主要类与结构体

### Block 结构体概览

所有 Block 结构体遵循统一的设计模式：

```cpp
struct SomeBlock {
    struct SomeData { /* 数据成员 */ };
    static void AddBlock(const KeyContext&, const SomeData&);
    // 或 static void BeginBlock(...) 用于容器块
};
```

### 1. 着色器块（Shader Blocks）

#### SolidColorShaderBlock

```cpp
struct SolidColorShaderBlock {
    static void AddBlock(const KeyContext&, const SkPMColor4f&);
};
```

**用途**：纯色着色器

**数据**：预乘颜色（`SkPMColor4f`）

#### RGBPaintColorBlock

```cpp
struct RGBPaintColorBlock {
    static void AddBlock(const KeyContext&);
};
```

**用途**：使用画笔的 RGB 颜色（从 `KeyContext::paintColor()` 获取）

#### AlphaOnlyPaintColorBlock

```cpp
struct AlphaOnlyPaintColorBlock {
    static void AddBlock(const KeyContext&);
};
```

**用途**：仅使用画笔的 alpha 通道

#### GradientShaderBlocks

```cpp
struct GradientShaderBlocks {
    struct GradientData {
        static constexpr int kNumInternalStorageStops = 8;

        SkShaderBase::GradientType fType;
        SkPoint fPoints[2];
        float fRadii[2];
        float fBias, fScale;
        SkTileMode fTM;
        int fNumStops;
        bool fUseStorageBuffer;

        // 内部存储（≤8 stops）
        SkPMColor4f fColors[kNumInternalStorageStops];
        SkV4 fOffsets[kNumInternalStorageStops / 4];

        // 外部存储（>8 stops）
        sk_sp<TextureProxy> fColorsAndOffsetsProxy;  // 纹理方式
        const SkPMColor4f* fSrcColors;                // 缓冲区方式
        const float* fSrcOffsets;

        SkGradient::Interpolation fInterpolation;
    };

    static void AddBlock(const KeyContext&, const GradientData&);
};
```

**渐变类型支持**：
- 线性渐变（Linear）
- 径向渐变（Radial）
- 扫描渐变（Sweep）
- 锥形渐变（Conical）

**存储策略**：
- **≤8 stops**：直接存储在 uniform 中（`fColors` 和 `fOffsets`）
- **>8 stops**：
  - 优先使用存储缓冲区（storage buffer）
  - 备选使用纹理（`fColorsAndOffsetsProxy`）

**offset 打包优化**：
- 8 个 offset 值打包成 2 个 `SkV4`（float4），节省 std140 布局的填充空间

#### ImageShaderBlock

```cpp
struct ImageShaderBlock {
    struct ImageData {
        SkSamplingOptions fSampling;
        std::pair<SkTileMode, SkTileMode> fTileModes;
        SkISize fImgSize;
        SkRect fSubset;

        sk_sp<TextureProxy> fTextureProxy;          // 运行时
        ImmutableSamplerInfo fImmutableSamplerInfo; // 预编译
    };

    static void AddBlock(const KeyContext&, const ImageData&);
};
```

**用途**：普通 RGBA 图像采样

**采样选项**：
- 最近邻 / 线性 / 立方采样
- Mipmap 支持
- 各种平铺模式（Clamp、Repeat、Mirror、Decal）

#### YUVImageShaderBlock

```cpp
struct YUVImageShaderBlock {
    struct ImageData {
        SkSamplingOptions fSampling;
        SkSamplingOptions fSamplingUV;
        SkISize fImgSize;
        SkISize fImgSizeUV;
        SkRect fSubset;
        SkPoint fLinearFilterUVInset;
        SkV4 fChannelSelect[4];
        float fAlphaParam;
        SkMatrix fYUVtoRGBMatrix;
        SkPoint3 fYUVtoRGBTranslate;
        sk_sp<TextureProxy> fTextureProxies[4];
    };

    static void AddBlock(const KeyContext&, const ImageData&);
};
```

**用途**：YUVA 格式图像采样

**关键特性**：
- 分别处理 Y 和 UV 平面的采样
- UV 平面尺寸可能与 Y 平面不同（子采样）
- YUV 到 RGB 色彩空间转换矩阵

#### LocalMatrixShaderBlock

```cpp
struct LocalMatrixShaderBlock {
    struct LMShaderData {
        const SkMatrix fLocalMatrix;
    };

    static void BeginBlock(const KeyContext&, const LMShaderData&);
};
```

**用途**：为子着色器应用局部矩阵变换

**优化**：4x4 矩阵扁平化为 3x3（坐标为 `xy01`，不需要透视）

#### PerlinNoiseShaderBlock

```cpp
struct PerlinNoiseShaderBlock {
    enum class Type { kFractalNoise, kTurbulence };

    struct PerlinNoiseData {
        Type fType;
        SkVector fBaseFrequency;
        int fNumOctaves;
        SkVector fStitchData;
        sk_sp<TextureProxy> fPermutationsProxy;
        sk_sp<TextureProxy> fNoiseProxy;
    };

    static void AddBlock(const KeyContext&, const PerlinNoiseData&);
};
```

**用途**：Perlin 噪声着色器（分形噪声 / 湍流）

### 2. 混合和组合块（Blend & Compose Blocks）

#### BlendComposeBlock

```cpp
struct BlendComposeBlock {
    static void BeginBlock(const KeyContext&);
};
```

**用途**：混合两个着色器（src 和 dst）

**结构**：容器块，包含三个子块（src、dst、blend mode）

#### ComposeBlock

```cpp
struct ComposeBlock {
    static void BeginBlock(const KeyContext&);
};
```

**用途**：组合两个着色器（inner 和 outer）

**语义**：`outer(inner(coords))`

#### PorterDuffBlenderBlock

```cpp
struct PorterDuffBlenderBlock {
    static void AddBlock(const KeyContext&, SkSpan<const float> coeffs);
};
```

**用途**：Porter-Duff 混合模式（通过系数表示）

**系数格式**：`[srcCoeff, dstCoeff, ...]`

#### HSLCBlenderBlock

```cpp
struct HSLCBlenderBlock {
    static void AddBlock(const KeyContext&, SkSpan<const float> coeffs);
};
```

**用途**：HSLC（色相-饱和度-亮度-颜色）混合模式

### 3. 颜色滤镜块（Color Filter Blocks）

#### MatrixColorFilterBlock

```cpp
struct MatrixColorFilterBlock {
    struct MatrixColorFilterData {
        SkM44 fMatrix;      // 4x4 矩阵（从 20 元素数组提取）
        SkV4 fTranslate;    // 平移向量
        bool fInHSLA;       // 是否在 HSLA 空间操作
        bool fClamp;        // 是否钳位结果
    };

    static void AddBlock(const KeyContext&, const MatrixColorFilterData&);
};
```

**用途**：矩阵颜色变换（如色调调整、饱和度调整）

**矩阵提取**：从 20 元素数组中提取 4x4 矩阵和 4 元素平移向量

#### TableColorFilterBlock

```cpp
struct TableColorFilterBlock {
    struct TableColorFilterData {
        sk_sp<TextureProxy> fTextureProxy;
    };

    static void AddBlock(const KeyContext&, const TableColorFilterData&);
};
```

**用途**：查表颜色映射（通过纹理存储映射表）

#### ColorSpaceTransformBlock

```cpp
struct ColorSpaceTransformBlock {
    struct ColorSpaceTransformData {
        SkColorSpaceXformSteps fSteps;
        Swizzle fReadSwizzle = Swizzle::RGBA();
    };

    static void AddBlock(const KeyContext&, const ColorSpaceTransformData&);
};
```

**用途**：色彩空间转换（如 sRGB ↔ Display P3）

**转换步骤**：解码、转换、编码（由 `SkColorSpaceXformSteps` 封装）

### 4. 坐标变换块（Coordinate Transform Blocks）

#### CoordNormalizeShaderBlock

```cpp
struct CoordNormalizeShaderBlock {
    struct CoordNormalizeData {
        SkSize fInvDimensions;  // 1.0 / width, 1.0 / height
    };

    static void BeginBlock(const KeyContext&, const CoordNormalizeData&);
};
```

**用途**：将像素坐标归一化到 [0, 1] 范围

#### CoordClampShaderBlock

```cpp
struct CoordClampShaderBlock {
    struct CoordClampData {
        SkRect fSubset;
    };

    static void BeginBlock(const KeyContext&, const CoordClampData&);
};
```

**用途**：限制坐标在指定子集内（用于图像子集采样）

### 5. 运行时效果块（Runtime Effect Blocks）

#### RuntimeEffectBlock

```cpp
struct RuntimeEffectBlock {
    struct ShaderData {
        sk_sp<const SkRuntimeEffect> fEffect;
        sk_sp<const SkData> fUniforms;  // 可选，预编译时为空
    };

    static bool BeginBlock(const KeyContext&, const ShaderData&);
    static void AddNoOpEffect(const KeyContext&, SkRuntimeEffect*);
    static void HandleIntrinsics(const KeyContext&, const SkRuntimeEffect*);
};
```

**用途**：用户定义的着色器（SkSL）

**特殊处理**：
- `toLinearSrgb` / `fromLinearSrgb` 内置函数
- 子效果（child shaders/blenders）

### 6. 抗锯齿和裁剪块

#### DitherShaderBlock

```cpp
struct DitherShaderBlock {
    struct DitherData {
        float fRange;
        sk_sp<TextureProxy> fLUTProxy;  // 查找表纹理
    };

    static void AddBlock(const KeyContext&, const DitherData&);
};
```

**用途**：抖动（dithering），减少色带效应

#### NonMSAAClipBlock

```cpp
struct NonMSAAClipBlock {
    struct NonMSAAClipData {
        // 解析裁剪
        SkRect fRect;
        SkPoint fRadiusPlusHalf;
        SkRect fEdgeSelect;

        // 图集裁剪
        SkPoint fTexCoordOffset;
        SkRect fMaskBounds;
        sk_sp<TextureProxy> fAtlasTexture;
    };

    static void AddBlock(const KeyContext&, const NonMSAAClipData&);
};
```

**用途**：非多重采样抗锯齿的裁剪（解析圆角矩形或图集遮罩）

## 公共 API 函数

### 全局辅助函数

#### AddToKey (SkShader*)

```cpp
void AddToKey(const KeyContext& keyContext, const SkShader* shader);
```

**功能**：自动识别着色器类型并添加相应的块

**支持的着色器类型**：
- 纯色着色器（`SkColorShader`）
- 图像着色器（`SkImageShader`）
- 渐变着色器（线性、径向、扫描、锥形）
- 混合着色器（`SkBlendShader`）
- 局部矩阵着色器（`SkLocalMatrixShader`）
- 运行时着色器（`SkRuntimeShader`）
- Perlin 噪声着色器
- 等等...

#### AddToKey (SkColorFilter*)

```cpp
void AddToKey(const KeyContext& keyContext, const SkColorFilter* filter);
```

**功能**：识别并添加颜色滤镜块

**支持的滤镜类型**：
- 矩阵颜色滤镜
- 混合模式颜色滤镜
- 表格颜色滤镜
- 色彩空间转换滤镜
- 组合颜色滤镜（`SkComposeColorFilter`）
- 运行时颜色滤镜
- 高斯滤镜

#### AddToKey (SkBlender*)

```cpp
void AddToKey(const KeyContext&, const SkBlender*);
```

**功能**：添加混合器块

**支持的混合器**：
- `SkBlendModeBlender`（标准混合模式）
- `SkRuntimeBlender`（运行时混合器）

#### AddToKey (SimpleImage)

```cpp
void AddToKey(const KeyContext& keyContext, const PaintParams::SimpleImage& imageShader);
```

**功能**：添加简化的图像着色器（避免创建 `SkShader` 对象和矩阵求逆）

**等价操作**：
```cpp
SkMatrix localMatrix = SkMatrix::Rect2Rect(srcRect, dstRect);
sk_sp<SkShader> shader = SkImageShader::MakeSubset(
    image, subset, SkTileMode::kClamp, SkTileMode::kClamp, sampling, localMatrix);
AddToKey(keyContext, shader.get());
```

### 混合模式辅助函数

#### AddBlendMode

```cpp
void AddBlendMode(const KeyContext&, SkBlendMode);
```

**功能**：添加可变混合模式块（运行时确定）

#### AddFixedBlendMode

```cpp
void AddFixedBlendMode(const KeyContext&, SkBlendMode);
```

**功能**：添加固定混合模式块（编译时确定，可能优化）

### 其他辅助函数

#### AddPrimitiveColor

```cpp
void AddPrimitiveColor(const KeyContext&, bool skipColorXform);
```

**功能**：引用 `RenderStep` 产生的原始颜色，并考虑色彩空间转换

#### AddBlendModeColorFilter

```cpp
void AddBlendModeColorFilter(const KeyContext&, SkBlendMode, const SkPMColor4f& srcColor);
```

**功能**：添加混合模式颜色滤镜（输入作为 dst，固定颜色作为 src）

#### AddDitherBlock

```cpp
void AddDitherBlock(const KeyContext&, SkColorType);
```

**功能**：根据目标颜色类型添加抖动块

### 模板辅助函数

#### Blend

```cpp
template <typename AddBlendToKeyT, typename AddSrcToKeyT, typename AddDstToKeyT>
void Blend(const KeyContext& keyContext,
           AddBlendToKeyT addBlendToKey,
           AddSrcToKeyT addSrcToKey,
           AddDstToKeyT addDstToKey);
```

**功能**：通用混合模式辅助，接受三个 lambda：

```cpp
Blend(keyContext,
      []() { AddBlendMode(keyContext, SkBlendMode::kSrcOver); },
      []() { AddToKey(keyContext, srcShader); },
      []() { AddToKey(keyContext, dstShader); });
```

**结构**：
```
BlendComposeBlock {
    src block
    dst block
    blend mode block
}
```

#### Compose

```cpp
template <typename AddInnerToKeyT, typename AddOuterToKeyT>
void Compose(const KeyContext& keyContext,
             AddInnerToKeyT addInnerToKey,
             AddOuterToKeyT addOuterToKey);
```

**功能**：通用组合辅助

**语义**：`outer(inner(coords))`

## 内部实现细节

### ScopedUniformWriter

```cpp
class ScopedUniformWriter {
public:
    ScopedUniformWriter(const KeyContext&, BuiltInCodeSnippetID);
    ~ScopedUniformWriter();
};
```

**用途**：RAII 管理 uniform 结构体的开始和结束

**功能**：
- 构造时调用 `gatherer->beginStruct(snippet->fRequiredAlignment)`
- 析构时调用 `gatherer->endStruct()`
- Debug 模式下验证 uniform 写入的正确性

**使用方式**：
```cpp
#define BEGIN_WRITE_UNIFORMS(keyContext, codeSnippetID) \
    ScopedUniformWriter scope{keyContext, codeSnippetID};

void add_some_uniform_data(const KeyContext& keyContext) {
    BEGIN_WRITE_UNIFORMS(keyContext, BuiltInCodeSnippetID::kSomeShader)
    keyContext.pipelineDataGatherer()->write(...);
}
```

### 渐变数据存储策略

#### 内部存储（≤8 stops）

```cpp
gatherer->writeArray(SkSpan{gradData.fColors, 8});
gatherer->writeArray(SkSpan{gradData.fOffsets, 2});  // 8 个 float 打包成 2 个 float4
```

**优化**：
- 颜色和偏移量直接作为 uniform 上传
- 偏移量打包减少 std140 布局的填充浪费
- 未使用的 stop 填充为最后一个有效 stop（支持二分搜索）

#### 外部存储（>8 stops）

**存储缓冲区方式**：
```cpp
int bufferOffset = write_color_and_offset_bufdata(...);
gatherer->write(gradData.fNumStops);
gatherer->write(bufferOffset);
```

**数据布局**：
```
[offset0, offset1, ..., offsetN, r0, g0, b0, a0, r1, g1, b1, a1, ...]
```

**优点**：缓存友好（二分搜索时偏移量连续存储）

**纹理方式**：
```cpp
gatherer->add(gradData.fColorsAndOffsetsProxy, {SkFilterMode::kNearest, SkTileMode::kClamp});
```

### 锥形渐变的特殊计算

```cpp
float a = 1 - dRadius * dRadius;
float invA = (std::abs(a) > SK_ScalarNearlyZero) ? 1.0 / (2.0 * a) : 0;
```

**目的**：处理退化情况（径向渐变、线性边缘）

**判断逻辑**：
- 如果两点距离接近零，视为径向渐变
- 如果 `a ≈ 0`，视为线性边缘

### 矩阵颜色滤镜的打包

```cpp
MatrixColorFilterData(const float matrix[20], bool inHSLA, bool clamp)
    : fMatrix(matrix[ 0], matrix[ 1], matrix[ 2], matrix[ 3],
              matrix[ 5], matrix[ 6], matrix[ 7], matrix[ 8],
              matrix[10], matrix[11], matrix[12], matrix[13],
              matrix[15], matrix[16], matrix[17], matrix[18])
    , fTranslate{matrix[4], matrix[9], matrix[14], matrix[19]}
```

**输入格式**：5x4 矩阵（20 个元素，行主序）

**提取策略**：
- 跳过索引 4、9、14、19（第 5 列，平移部分）→ 4x4 矩阵
- 提取索引 4、9、14、19 → 4 元素平移向量

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `KeyContext` | 提供上下文信息和构建器访问 |
| `PaintParamsKeyBuilder` | 构建着色器键 |
| `PipelineDataGatherer` | 收集 uniform 和纹理数据 |
| `ShaderCodeDictionary` | 查询代码片段定义 |
| `RuntimeEffectDictionary` | 管理运行时效果 |

### 着色器和滤镜依赖

| 类型 | 头文件 |
|------|--------|
| 渐变着色器 | `SkLinearGradient.h`, `SkRadialGradient.h`, `SkSweepGradient.h`, `SkConicalGradient.h` |
| 图像着色器 | `SkImageShader.h` |
| 颜色滤镜 | `SkMatrixColorFilter.h`, `SkTableColorFilter.h`, `SkBlendModeColorFilter.h` |
| 运行时效果 | `SkRuntimeEffect.h`, `SkRuntimeShader.h`, `SkRuntimeColorFilter.h` |
| 混合器 | `SkBlendShader.h`, `SkBlendModeBlender.h` |

## 设计模式与设计决策

### 1. 静态工具类模式

所有 Block 结构体都是静态的（只有静态方法），无需实例化：

```cpp
SolidColorShaderBlock::AddBlock(keyContext, color);  // 直接调用
```

**好处**：
- 清晰的命名空间
- 零运行时开销
- 方便分组相关功能

### 2. 数据与逻辑分离

每个 Block 包含内嵌的 Data 结构体，分离数据表示和键生成逻辑：

```cpp
struct SomeBlock {
    struct SomeData { /* 纯数据 */ };
    static void AddBlock(const KeyContext&, const SomeData&);
};
```

### 3. RAII 资源管理

`ScopedUniformWriter` 使用 RAII 确保 uniform 结构体的开始/结束配对：

```cpp
{
    ScopedUniformWriter scope{keyContext, id};
    // write uniforms
}  // 自动调用 endStruct()
```

### 4. 模板 Lambda 辅助

`Blend` 和 `Compose` 使用模板接受 lambda，实现灵活的组合：

```cpp
Blend(keyContext,
      [&]() { /* blend mode */ },
      [&]() { /* src */ },
      [&]() { /* dst */ });
```

### 5. 两阶段构造

许多 Data 结构体提供两个构造函数：
- **预编译构造函数**：仅提供键生成所需的最少信息
- **运行时构造函数**：提供完整的 uniform 数据

```cpp
GradientData(SkShaderBase::GradientType, int numStops, bool useStorageBuffer);  // 预编译
GradientData(..., const SkPMColor4f* colors, const float* offsets, ...);       // 运行时
```

### 6. 策略模式（存储策略）

渐变数据根据 stop 数量和设备能力选择存储策略：
- 内部 uniform 存储
- 存储缓冲区
- 纹理存储

### 7. 宏简化

使用宏简化重复代码：

```cpp
#define BEGIN_WRITE_UNIFORMS(keyContext, codeSnippetID) \
    ScopedUniformWriter scope{keyContext, codeSnippetID};
```

## 性能考量

### Uniform 打包优化

1. **渐变偏移量打包**：8 个 float 打包成 2 个 float4，减少 std140 填充
2. **矩阵扁平化**：局部矩阵从 4x4 简化为 3x3（9 个 float → 36 字节）
3. **数据对齐**：`ScopedUniformWriter` 自动处理对齐要求

### 存储策略优化

1. **小渐变内联**：≤8 stops 直接在 uniform 中，避免缓冲区/纹理开销
2. **缓冲区去重**：`FloatStorageManager::allocateGradientData` 检测重复数据
3. **缓存友好布局**：偏移量连续存储，支持高效二分搜索

### 键生成效率

1. **单次遍历**：每个着色器/滤镜只遍历一次
2. **早期退出**：空着色器/滤镜立即返回，无额外开销
3. **内联小函数**：大量小函数易于内联优化

### 预编译优化

预编译构造函数避免不必要的数据准备：

```cpp
GradientData(type, numStops, useStorageBuffer);  // 不处理颜色/偏移量
```

这允许在不知道具体颜色的情况下生成着色器变体。

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/KeyContext.h` | 键生成上下文 |
| `src/gpu/graphite/PaintParamsKey.h` | 着色器参数键 |
| `src/gpu/graphite/PipelineData.h` | 管线数据（uniform、纹理） |
| `src/gpu/graphite/ShaderCodeDictionary.h` | 着色器代码字典 |
| `src/gpu/graphite/RuntimeEffectDictionary.h` | 运行时效果字典 |
| `src/gpu/graphite/UniformManager.h` | Uniform 管理 |
| `src/gpu/graphite/FloatStorageManager.h` | 浮点数存储管理 |
| `src/gpu/graphite/PaintParams.h` | 绘制参数 |
| `include/core/SkShader.h` | 着色器公共接口 |
| `include/core/SkColorFilter.h` | 颜色滤镜公共接口 |
| `include/core/SkBlendMode.h` | 混合模式定义 |
| `include/effects/SkRuntimeEffect.h` | 运行时效果 |
