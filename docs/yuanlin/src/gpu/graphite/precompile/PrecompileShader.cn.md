# PrecompileShader

> 源文件
> - include/gpu/graphite/precompile/PrecompileShader.h
> - src/gpu/graphite/precompile/PrecompileShader.cpp

## 概述

`PrecompileShader` 是 Skia Graphite 图形管线预编译系统的核心组件，对应于主 API 中的 `SkShader` 类。该类提供了一个抽象接口，用于在实际绘制前预编译着色器管线，从而显著减少首帧渲染延迟。通过预先生成各种着色器组合，应用可以避免运行时编译导致的卡顿。

PrecompileShader 支持几乎所有 Skia 着色器类型的预编译，包括颜色着色器、图像着色器、渐变着色器、混合着色器、噪声着色器等，并提供了丰富的工厂方法来生成不同的着色器组合。

## 架构位置

```
skgpu::graphite
├── precompile/
│   ├── PrecompileBase (基类)
│   ├── PrecompileShader (当前组件)
│   ├── PrecompileColorFilter
│   ├── PrecompileBlender
│   ├── PrecompileMaskFilter
│   └── PrecompileImageFilter
├── KeyContext (密钥上下文)
├── PaintParams (绘制参数)
└── PaintParamsKey (绘制参数密钥)
```

PrecompileShader 是 Graphite 预编译架构的关键层，位于 PrecompileBase 基类和具体绘制系统之间，负责将着色器配置转换为可编译的管线密钥。

## 主要类与结构体

### PrecompileShader

**继承关系**
- 基类: `PrecompileBase`
- 派生类: 各种具体着色器实现类（PrecompileEmptyShader、PrecompileColorShader、PrecompileImageShader 等）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| N/A | N/A | 基类主要通过虚函数实现多态，不包含特定成员变量 |

### PrecompileEmptyShader

**继承关系**: `PrecompileShader`

空着色器实现，对应 `SkShader` 的空状态。

### PrecompileColorShader

**继承关系**: `PrecompileShader`

纯色着色器，用于生成单一颜色的着色器管线。

### PrecompileBlendShader

**继承关系**: `PrecompileShader`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fBlenderOptions | PrecompileBlenderList | 混合器选项列表 |
| fDstOptions | std::vector&lt;sk_sp&lt;PrecompileShader&gt;&gt; | 目标着色器选项 |
| fSrcOptions | std::vector&lt;sk_sp&lt;PrecompileShader&gt;&gt; | 源着色器选项 |
| fNumDstCombos | int | 目标着色器组合数 |
| fNumSrcCombos | int | 源着色器组合数 |

### PrecompileImageShader

**继承关系**: `PrecompileShader`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fNumExtraSamplingTilingCombos | int | 额外采样平铺组合数（立方采样） |
| fColorInfos | std::vector&lt;SkColorInfo&gt; | 颜色信息列表 |
| fTileModes | std::vector&lt;SkTileMode&gt; | 平铺模式列表 |
| fUseDstColorInfo | bool | 是否使用目标颜色信息 |
| fRaw | bool | 是否为原始图像着色器 |
| fImmutableSamplerInfo | ImmutableSamplerInfo | 不可变采样器信息 |

### PrecompileYUVImageShader

**继承关系**: `PrecompileShader`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fColorInfos | std::vector&lt;SkColorInfo&gt; | 颜色信息列表 |
| fUseDstColorSpace | bool | 是否使用目标颜色空间 |
| fNumTilingModes | int | 平铺模式数量 |
| fTilingModes | int[kMaxTilingModes] | 平铺模式数组 |

### PrecompileGradientShader

**继承关系**: `PrecompileShader`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fType | SkShaderBase::GradientType | 渐变类型 |
| fInterpolation | SkGradient::Interpolation | 插值方式 |
| fNumStopVariants | int | 色阶变体数量 |
| fStopVariants | int[kMaxStopVariants] | 色阶变体数组 |

### PrecompileLocalMatrixShader

**继承关系**: `PrecompileShader`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fWrapped | std::vector&lt;sk_sp&lt;PrecompileShader&gt;&gt; | 被包装的着色器列表 |
| fNumWrappedCombos | int | 被包装着色器组合数 |
| fFlags | SkEnumBitMask&lt;Flags&gt; | 标志位（透视、包含无变换变体） |

## 公共 API 函数

### PrecompileShader 核心方法

```cpp
sk_sp<PrecompileShader> makeWithLocalMatrix(bool isPerspective) const;
```
创建带局部矩阵变换的着色器变体，isPerspective 指定是否需要透视除法。

```cpp
sk_sp<PrecompileShader> makeWithColorFilter(sk_sp<PrecompileColorFilter>) const;
```
创建带颜色滤镜的着色器变体。

```cpp
sk_sp<PrecompileShader> makeWithWorkingColorSpace(
    sk_sp<SkColorSpace> inputCS,
    sk_sp<SkColorSpace> outputCS=nullptr) const;
```
创建带工作颜色空间转换的着色器变体。

### PrecompileShaders 命名空间工厂函数

**基础着色器**

```cpp
sk_sp<PrecompileShader> Empty();
sk_sp<PrecompileShader> Color();
sk_sp<PrecompileShader> Color(sk_sp<SkColorSpace>);
```

**混合着色器**

```cpp
sk_sp<PrecompileShader> Blend(
    SkSpan<const SkBlendMode> blendModes,
    SkSpan<const sk_sp<PrecompileShader>> dsts,
    SkSpan<const sk_sp<PrecompileShader>> srcs);

sk_sp<PrecompileShader> Blend(
    SkSpan<const sk_sp<PrecompileBlender>> blenders,
    SkSpan<const sk_sp<PrecompileShader>> dsts,
    SkSpan<const sk_sp<PrecompileShader>> srcs);
```

**图像着色器**

```cpp
sk_sp<PrecompileShader> Image(
    ImageShaderFlags = ImageShaderFlags::kAll,
    SkSpan<const SkColorInfo> = {},
    SkSpan<const SkTileMode> = { kAllTileModes });

sk_sp<PrecompileShader> YUVImage(
    YUVImageShaderFlags = YUVImageShaderFlags::kExcludeCubic,
    SkSpan<const SkColorInfo> = {});

sk_sp<PrecompileShader> RawImage(
    ImageShaderFlags = ImageShaderFlags::kExcludeCubic,
    SkSpan<const SkColorInfo> = {},
    SkSpan<const SkTileMode> = { kAllTileModes });
```

**渐变着色器**

```cpp
sk_sp<PrecompileShader> LinearGradient(
    GradientShaderFlags = GradientShaderFlags::kAll,
    SkGradient::Interpolation = SkGradient::Interpolation());

sk_sp<PrecompileShader> RadialGradient(...);
sk_sp<PrecompileShader> TwoPointConicalGradient(...);
sk_sp<PrecompileShader> SweepGradient(...);
```

**特殊着色器**

```cpp
sk_sp<PrecompileShader> MakeFractalNoise();
sk_sp<PrecompileShader> MakeTurbulence();
sk_sp<PrecompileShader> Picture();
sk_sp<PrecompileShader> CoordClamp(SkSpan<const sk_sp<PrecompileShader>>);
```

**包装器着色器**

```cpp
sk_sp<PrecompileShader> LocalMatrix(
    SkSpan<const sk_sp<PrecompileShader>> wrapped,
    bool isPerspective = false);

sk_sp<PrecompileShader> ColorFilter(
    SkSpan<const sk_sp<PrecompileShader>> shaders,
    SkSpan<const sk_sp<PrecompileColorFilter>> colorFilters);

sk_sp<PrecompileShader> WorkingColorSpace(
    SkSpan<const sk_sp<PrecompileShader>> shaders,
    SkSpan<const sk_sp<SkColorSpace>> inputSpaces,
    SkSpan<const sk_sp<SkColorSpace>> outputSpaces = {});
```

## 内部实现细节

### 组合计算机制

每个 PrecompileShader 实现都需要计算其可能生成的组合数量。总组合数 = 固有组合数 × 子组合数。

**PrecompileBlendShader 组合计算示例**:
```cpp
int numChildCombinations() const override {
    return fBlenderOptions.numCombinations() * fNumDstCombos * fNumSrcCombos;
}
```

### 密钥生成流程

`addToKey` 方法负责将着色器配置转换为 PaintParamsKey：

1. 解析 desiredCombination 计算出具体的子选项组合
2. 调用对应的 Block::BeginBlock 开始代码片段
3. 递归为子着色器添加密钥
4. 调用 endBlock 完成代码片段

**PrecompileImageShader 密钥添加示例**:
```cpp
void addToKey(const KeyContext& keyContext, int desiredCombination) const override {
    // 计算采样/平铺组合和颜色信息索引
    const int desiredSamplingTilingCombo = desiredCombination % numSamplingTilingCombos;
    const int desiredColorInfo = desiredCombination / numSamplingTilingCombos;

    // 构造 ImageData 和 ColorSpaceTransformData
    ImageShaderBlock::ImageData imgData(...);
    ColorSpaceTransformBlock::ColorSpaceTransformData colorXformData(...);

    // 组合添加到密钥
    Compose(keyContext,
        [&]() { ImageShaderBlock::AddBlock(keyContext, imgData); },
        [&]() { ColorSpaceTransformBlock::AddBlock(keyContext, colorXformData); });
}
```

### LocalMatrix 着色器优化

LocalMatrixShader 有两个固有变体：带矩阵变换和不带变换。这对应于运行时 SkShader 当局部矩阵为单位矩阵时的优化。

```cpp
int numIntrinsicCombinations() const override {
    if (!(fFlags & Flags::kIncludeWithOutVariant)) {
        return 1;   // 仅 kWithLocalMatrix
    }
    return kNumIntrinsicCombinations;  // 两种变体
}
```

### 图像着色器的采样策略

PrecompileImageShader 支持多种采样和平铺组合：
- **硬件平铺**: 当子集覆盖整个图像时使用
- **着色器平铺**: 当子集小于图像时使用
- **立方采样**: 可选的高质量采样模式

### 渐变着色器的中间色彩空间

渐变着色器需要处理颜色插值，使用 `get_gradient_intermediate_cs` 函数计算中间色彩空间：

```cpp
sk_sp<SkColorSpace> get_gradient_intermediate_cs(
    SkColorSpace* dstColorSpace,
    SkGradient::Interpolation interpolation) {
    // 创建临时渐变着色器以获取中间色彩空间
    SkLinearGradient shader(pts, {{colors, pos, tileMode, nullptr}, interpolation});
    SkColor4fXformer xformedColors(&shader, dstColorSpace);
    return xformedColors.fIntermediateColorSpace;
}
```

### 特殊着色器实现

**PrecompileBlurShader**: 预编译 12 种模糊着色器（6 种 1D + 6 种 2D），对应不同的核大小。

**PrecompileMatrixConvolutionShader**: 生成 3 种变体（1 个基于 uniform + 2 个基于纹理），并自动包含 RawImage 着色器。

**PrecompileMorphologyShader**: 支持线性和稀疏形态学运算。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| PrecompileBase | 基类，提供通用预编译接口 |
| PrecompileColorFilter | 颜色滤镜预编译支持 |
| PrecompileBlender | 混合器预编译支持 |
| KeyContext | 提供密钥生成上下文 |
| PaintParamsKey | 管线参数密钥表示 |
| KeyHelpers | 密钥构建辅助函数 |
| BuiltInCodeSnippetID | 内置代码片段标识 |
| TextureFormat | 纹理格式支持 |
| Swizzle | 颜色通道重排 |
| SkColorSpace | 颜色空间转换 |
| SkRuntimeEffect | 运行时效果支持 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| PaintOptions | 使用 PrecompileShader 构建绘制选项 |
| PrecompileMaskFilter | 内部使用着色器生成遮罩管线 |
| PrecompileImageFilter | 内部使用着色器生成图像滤镜管线 |
| PrecompileColorFilterShader | 组合着色器和颜色滤镜 |
| PrecompileWorkingColorSpaceShader | 颜色空间转换着色器 |

## 设计模式与设计决策

### 组合模式 (Composite Pattern)

PrecompileShader 采用组合模式构建着色器树：
- 简单着色器（Empty、Color）作为叶节点
- 复杂着色器（Blend、LocalMatrix）作为组合节点，包含子着色器

### 工厂方法模式 (Factory Method Pattern)

通过 PrecompileShaders 命名空间提供统一的工厂接口，隐藏具体实现类。

### 策略模式 (Strategy Pattern)

通过虚函数 `addToKey` 和 `numChildCombinations` 实现不同着色器的具体策略。

### 设计决策

1. **组合爆炸控制**: 通过标志位（ImageShaderFlags、GradientShaderFlags）让用户精确控制需要预编译的变体数量，避免生成过多无用管线。

2. **懒惰求值**: PrecompileShader 本身不立即编译，而是生成描述信息，实际编译在 buildCombinations 时发生。

3. **默认值优化**: 提供合理的默认颜色信息列表（DefaultColorInfos、NonAlphaOnlyDefaultColorInfos、RawImageDefaultColorInfos），减少用户配置负担。

4. **链式优化**: LocalMatrixShader 会自动折叠连续的局部矩阵变换，模拟运行时行为。

5. **选项组合 API**: 提供批量工厂函数（如 ColorFilter、WorkingColorSpace）支持笛卡尔积组合，简化批量预编译场景。

## 性能考量

### 组合数量优化

- 默认图像着色器组合数: 24 (2 种颜色类型 × 12 种采样/平铺组合)
- 渐变着色器最多 3 种色阶变体（Small、Medium、Large）
- YUV 图像着色器最多 4 种平铺模式

### 内存占用

PrecompileShader 对象本身轻量，主要开销在子着色器引用。使用 `std::vector` 存储子选项，避免小对象分配开销。

### 编译时间

- 通过 `kExcludeCubic`、`kNoAlphaNoCubic` 标志排除不常用的立方采样变体
- `fUseDstColorInfo` 标志避免不必要的目标颜色空间组合

### 缓存友好性

PaintParamsKey 生成是深度优先遍历，利用栈局部性。

### 特殊优化

- 常量着色器（Color）标记为 `isConstant`，允许渲染器优化
- Picture 着色器包装 Image 着色器，复用已有管线
- 空着色器使用 `kPriorOutput` 片段，零开销传递

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/gpu/graphite/precompile/PrecompileShader.h | 公共头文件 |
| src/gpu/graphite/precompile/PrecompileShader.cpp | 实现文件 |
| src/gpu/graphite/precompile/PrecompileShaderPriv.h | 私有接口 |
| src/gpu/graphite/precompile/PrecompileImageShader.h | 图像着色器接口 |
| src/gpu/graphite/precompile/PrecompileShadersPriv.h | 内部着色器工厂 |
| src/gpu/graphite/KeyHelpers.h | 密钥构建辅助 |
| src/gpu/graphite/BuiltInCodeSnippetID.h | 内置代码片段 ID |
| include/core/SkShader.h | 对应的运行时 API |
| include/effects/SkGradient.h | 渐变着色器 API |
| include/effects/SkRuntimeEffect.h | 运行时效果 |
