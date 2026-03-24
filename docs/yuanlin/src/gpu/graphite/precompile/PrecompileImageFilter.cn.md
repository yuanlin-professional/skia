# PrecompileImageFilter

> 源文件
> - include/gpu/graphite/precompile/PrecompileImageFilter.h
> - src/gpu/graphite/precompile/PrecompileImageFilter.cpp

## 概述

`PrecompileImageFilter` 是 Skia Graphite 预编译系统中用于图像滤镜的抽象基类，对应于主 API 中的 `SkImageFilter` 类。图像滤镜用于对整个图像进行各种特效处理，如模糊、颜色调整、形态学操作、光照效果等。

与 PrecompileMaskFilter 类似，PrecompileImageFilter 也不直接参与着色器密钥生成，而是通过 `onCreatePipelines` 方法创建完整的渲染管线。图像滤镜支持构建有向无环图（DAG）结构，允许多个滤镜组合使用，实现复杂的图像处理效果。

## 架构位置

```
skgpu::graphite
├── precompile/
│   ├── PrecompileBase (基类)
│   ├── PrecompileImageFilter (当前组件)
│   │   ├── PrecompileBlendFilterImageFilter
│   │   ├── PrecompileBlurImageFilter
│   │   ├── PrecompileColorFilterImageFilter
│   │   ├── PrecompileDisplacementMapImageFilter
│   │   ├── PrecompileLightingImageFilter
│   │   ├── PrecompileMatrixConvolutionImageFilter
│   │   └── PrecompileMorphologyImageFilter
│   ├── PrecompileShader
│   ├── PrecompileColorFilter
│   ├── PrecompileBlender
│   └── PaintOptions (使用方)
├── RenderPassDesc (渲染通道描述)
└── Renderer (渲染器)
```

PrecompileImageFilter 形成一个继承层次结构，每个具体滤镜类型都有对应的实现类。这些滤镜可以组合成树形或 DAG 结构，实现复杂的图像处理管线。

## 主要类与结构体

### PrecompileImageFilter

**继承关系**
- 基类: `PrecompileBase`
- 派生类: PrecompileBlendFilterImageFilter、PrecompileBlurImageFilter、PrecompileColorFilterImageFilter 等

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fInputs | AutoSTArray&lt;2, sk_sp&lt;PrecompileImageFilter&gt;&gt; | 输入滤镜列表（DAG 结构） |

PrecompileImageFilter 使用 AutoSTArray 优化小规模输入（大多数滤镜有 0-2 个输入），避免堆分配。

### PrecompileBlendFilterImageFilter

**继承关系**: `PrecompileImageFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fBlender | sk_sp&lt;PrecompileBlender&gt; | 混合器配置 |

混合滤镜接受两个输入图像（背景和前景），使用指定的混合器组合它们。

### PrecompileBlurImageFilter

**继承关系**: `PrecompileImageFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| N/A | N/A | 无状态实现 |

模糊滤镜是最常用的图像滤镜，重用 PrecompileImageFiltersPriv 中的共享实现。

### PrecompileColorFilterImageFilter

**继承关系**: `PrecompileImageFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fColorFilter | sk_sp&lt;PrecompileColorFilter&gt; | 颜色滤镜配置 |

颜色滤镜图像滤镜将颜色滤镜应用于整个图像。支持作为 ColorFilterNode 优化。

### PrecompileDisplacementMapImageFilter

**继承关系**: `PrecompileImageFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| N/A | N/A | 无状态实现 |

位移贴图滤镜使用一个输入图像的颜色通道偏移另一个输入图像的像素位置。

### PrecompileLightingImageFilter

**继承关系**: `PrecompileImageFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| N/A | N/A | 无状态实现 |

光照滤镜模拟各种光源效果（距离光、点光、聚光，漫反射、镜面反射）。

### PrecompileMatrixConvolutionImageFilter

**继承关系**: `PrecompileImageFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| N/A | N/A | 无状态实现 |

矩阵卷积滤镜对图像应用卷积核，用于实现锐化、边缘检测等效果。

### PrecompileMorphologyImageFilter

**继承关系**: `PrecompileImageFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| N/A | N/A | 无状态实现 |

形态学滤镜实现腐蚀（Erode）和膨胀（Dilate）操作。

## 公共 API 函数

### PrecompileImageFilter 核心方法

```cpp
PrecompileImageFilter(SkSpan<sk_sp<PrecompileImageFilter>> inputs);
```
构造函数，接受输入滤镜列表。大多数滤镜有 0-1 个输入，混合类滤镜有 2 个输入。

### PrecompileImageFilters 命名空间工厂函数

**混合滤镜**

```cpp
sk_sp<PrecompileImageFilter> Arithmetic(
    sk_sp<PrecompileImageFilter> background,
    sk_sp<PrecompileImageFilter> foreground);
```
创建算术混合滤镜，使用固定的算术混合公式。

```cpp
sk_sp<PrecompileImageFilter> Blend(
    SkBlendMode bm,
    sk_sp<PrecompileImageFilter> background,
    sk_sp<PrecompileImageFilter> foreground);
```
创建混合模式滤镜，使用指定的 SkBlendMode。

```cpp
sk_sp<PrecompileImageFilter> Blend(
    sk_sp<PrecompileBlender> blender,
    sk_sp<PrecompileImageFilter> background,
    sk_sp<PrecompileImageFilter> foreground);
```
创建自定义混合器滤镜，支持运行时效果混合器。

**常用滤镜**

```cpp
sk_sp<PrecompileImageFilter> Blur(sk_sp<PrecompileImageFilter> input);
```
创建模糊滤镜，对应 SkImageFilters::Blur 的两个工厂函数。

```cpp
sk_sp<PrecompileImageFilter> ColorFilter(
    sk_sp<PrecompileColorFilter> colorFilter,
    sk_sp<PrecompileImageFilter> input);
```
创建颜色滤镜图像滤镜，将颜色滤镜应用于图像。

**高级滤镜**

```cpp
sk_sp<PrecompileImageFilter> DisplacementMap(
    sk_sp<PrecompileImageFilter> input);
```
创建位移贴图滤镜，实现像素偏移效果。

```cpp
sk_sp<PrecompileImageFilter> Lighting(
    sk_sp<PrecompileImageFilter> input);
```
创建光照滤镜，涵盖所有 6 种光照类型（DistantLitDiffuse、PointLitDiffuse、SpotLitDiffuse、DistantLitSpecular、PointLitSpecular、SpotLitSpecular）。

```cpp
sk_sp<PrecompileImageFilter> MatrixConvolution(
    sk_sp<PrecompileImageFilter> input);
```
创建矩阵卷积滤镜，支持任意卷积核。

```cpp
sk_sp<PrecompileImageFilter> Morphology(
    sk_sp<PrecompileImageFilter> input);
```
创建形态学滤镜，涵盖腐蚀和膨胀操作。

## 内部实现细节

### DAG 遍历与管线创建

PrecompileImageFilter 的核心方法是 `createPipelines`，它递归遍历滤镜 DAG 并为每个节点创建管线：

```cpp
void PrecompileImageFilter::createPipelines(
        const KeyContext& keyContext,
        const RenderPassDesc& renderPassDesc,
        const PaintOptions::ProcessCombination& processCombination) {
    // 创建当前节点的管线
    this->onCreatePipelines(keyContext, renderPassDesc, processCombination);

    // 递归处理所有输入节点
    for (const sk_sp<PrecompileImageFilter>& input : fInputs) {
        if (input) {
            input->createPipelines(keyContext, renderPassDesc, processCombination);
        }
    }
}
```

**设计注意**: 代码注释指出未来需要添加访问标记以防止 DAG 中的循环，并跟踪已创建的管线以避免重复生成（例如，多个分支都使用模糊时）。

### ColorFilterNode 优化

```cpp
sk_sp<PrecompileColorFilter> PrecompileImageFilter::asAColorFilter() const {
    sk_sp<PrecompileColorFilter> tmp = this->isColorFilterNode();
    if (!tmp) {
        return nullptr;
    }
    SkASSERT(this->countInputs() == 1);
    if (this->getInput(0)) {
        return nullptr;  // 有输入时不能优化
    }
    // TODO: 处理 affectsTransparentBlack 特殊情况
    return tmp;
}
```

当 ColorFilterImageFilter 没有输入时，可以优化为纯 ColorFilter，避免创建额外的离屏渲染目标。

### 具体滤镜实现模式

#### 模糊图像滤镜

```cpp
void PrecompileBlurImageFilter::onCreatePipelines(...) const {
    PrecompileImageFiltersPriv::CreateBlurImageFilterPipelines(
        keyContext, renderPassDesc, processCombination);
}
```

重用共享的模糊管线生成函数，该函数创建：
- 使用 PrecompileShadersPriv::Blur 包装的图像着色器
- SkBlendMode::kSrc 混合模式
- DrawTypeFlags::kSimpleShape 绘制类型
- Coverage::kSingleChannel 覆盖率

#### 混合滤镜图像滤镜

```cpp
void PrecompileBlendFilterImageFilter::onCreatePipelines(...) const {
    sk_sp<PrecompileShader> imageShader = PrecompileShaders::Image(
        ImageShaderFlags::kNoAlphaNoCubic);

    sk_sp<PrecompileShader> blendShader = PrecompileShaders::Blend(
        SkSpan(&fBlender, 1),
        {{ imageShader }},  // 目标
        {{ imageShader }});  // 源

    paintOptions.setShaders({{ std::move(blendShader) }});
    paintOptions.priv().buildCombinations(...);
}
```

创建混合着色器，两个输入都使用图像着色器（对应输入图像滤镜的输出）。

#### 颜色滤镜图像滤镜

```cpp
void PrecompileColorFilterImageFilter::onCreatePipelines(...) const {
    PaintOptions paintOptions;
    sk_sp<PrecompileShader> imageShader = PrecompileShaders::Image(
        ImageShaderFlags::kNoAlphaNoCubic);

    static const SkBlendMode kBlendModes[] = { SkBlendMode::kDstOut };
    paintOptions.setShaders({{ std::move(imageShader) }});
    paintOptions.setColorFilters({{ fColorFilter }});
    paintOptions.setBlendModes(kBlendModes);

    paintOptions.priv().buildCombinations(...);
}
```

使用 kDstOut 混合模式是特殊的实现细节，可能与颜色滤镜的 Alpha 处理有关。

#### 位移贴图滤镜

```cpp
void PrecompileDisplacementMapImageFilter::onCreatePipelines(...) const {
    sk_sp<PrecompileShader> imageShader = PrecompileShaders::Image(
        ImageShaderFlags::kNoAlphaNoCubic);

    displacement.setShaders({{
        PrecompileShadersPriv::Displacement(imageShader, imageShader)
    }});

    displacement.priv().buildCombinations(...);
}
```

使用专门的 Displacement 着色器，接受两个图像输入（位移贴图和颜色图）。

#### 光照滤镜

```cpp
void PrecompileLightingImageFilter::onCreatePipelines(...) const {
    sk_sp<PrecompileShader> imageShader = PrecompileShaders::Image(
        ImageShaderFlags::kNoAlphaNoCubic);

    lighting.setShaders({{
        PrecompileShadersPriv::Lighting(std::move(imageShader))
    }});

    lighting.priv().buildCombinations(...);
}
```

使用嵌套的 Lighting 和 Normal 运行时效果着色器。

#### 形态学滤镜

```cpp
void PrecompileMorphologyImageFilter::onCreatePipelines(...) const {
    // 稀疏形态学
    PaintOptions sparse;
    sparse.setShaders({{ PrecompileShadersPriv::SparseMorphology(imageShader) }});
    sparse.setBlendModes({{ SkBlendMode::kSrc }});
    sparse.priv().buildCombinations(...);

    // 线性形态学
    PaintOptions linear;
    linear.setShaders({{ PrecompileShadersPriv::LinearMorphology(imageShader) }});
    linear.setBlendModes({{ SkBlendMode::kSrcOver }});
    linear.priv().buildCombinations(...);
}
```

生成两种形态学算法的管线：稀疏（小核）和线性（大核），使用不同的混合模式。

### 混合模式优化

Blend 滤镜工厂对某些混合模式进行了优化：

```cpp
if (std::optional<SkBlendMode> bm = blender->priv().asBlendMode()) {
    if (bm == SkBlendMode::kSrc) {
        return foreground;  // 只需要前景
    } else if (bm == SkBlendMode::kDst) {
        return background;  // 只需要背景
    } else if (bm == SkBlendMode::kClear) {
        return nullptr;  // TODO: 返回 Empty 滤镜
    }
}
```

这些优化减少了不必要的管线创建。

### 颜色滤镜组合

ColorFilter 工厂会尝试组合连续的颜色滤镜节点：

```cpp
if (colorFilter && input) {
    sk_sp<PrecompileColorFilter> inputCF = input->priv().isColorFilterNode();
    if (inputCF) {
        colorFilter = colorFilter->makeComposed(std::move(inputCF));
        input = sk_ref_sp(input->priv().getInput(0));
    }
}
```

这种优化合并多个颜色滤镜为单个，减少渲染通道数量。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| PrecompileBase | 基类，提供预编译接口 |
| PrecompileShader | 创建图像着色器和特殊效果着色器 |
| PrecompileColorFilter | 颜色滤镜图像滤镜使用 |
| PrecompileBlender | 混合滤镜使用 |
| PrecompileShadersPriv | 访问内部着色器（Blur、Displacement、Lighting 等） |
| PrecompileImageFiltersPriv | 共享的图像滤镜管线生成函数 |
| PaintOptions | 构建绘制选项组合 |
| KeyContext | 提供上下文信息 |
| RenderPassDesc | 渲染通道配置 |
| Renderer | 底层渲染器（间接依赖） |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| PaintOptions | 通过 setImageFilters 接受 PrecompileImageFilter 列表 |
| PrecompileMaskFilter | 模糊遮罩滤镜重用模糊图像滤镜的实现 |

## 设计模式与设计决策

### 组合模式 (Composite Pattern)

PrecompileImageFilter 完美实现了组合模式：
- Component: PrecompileImageFilter 抽象基类
- Leaf: PrecompileBlurImageFilter 等无输入或单输入滤镜
- Composite: PrecompileBlendFilterImageFilter 等多输入滤镜
- 统一接口: createPipelines 递归遍历整个树/DAG

### 模板方法模式 (Template Method Pattern)

```cpp
void createPipelines(...) {
    this->onCreatePipelines(...);  // 子类实现
    for (input : fInputs) {
        input->createPipelines(...);  // 递归
    }
}
```

基类定义遍历框架，子类实现具体的管线创建逻辑。

### 工厂方法模式 (Factory Method Pattern)

PrecompileImageFilters 命名空间提供统一的工厂接口，隐藏具体实现类。

### 设计决策

1. **简化的 API**: 不允许为图像滤镜内部和 DAG 结构指定选项。代码注释明确说明："为了使预编译分析更易处理，我们不允许为 PrecompileImageFilter 的内部指定选项，也不允许为 DAG 结构指定选项。"这大大减少了组合爆炸。

2. **统一的图像着色器**: 所有图像滤镜都使用 `PrecompileShaders::Image(ImageShaderFlags::kNoAlphaNoCubic)`，因为图像滤镜处理的是完整的 RGBA 图像，不需要 alpha-only 纹理或立方采样。

3. **统一的绘制类型**: 大多数图像滤镜使用 `DrawTypeFlags::kSimpleShape`，因为它们通常在全屏四边形上执行。

4. **统一的覆盖率**: 使用 `Coverage::kSingleChannel`，因为图像滤镜通常在离屏纹理上工作。

5. **无参数工厂**: 工厂函数不接受滤镜参数（如模糊半径、卷积核大小等），因为这些参数不影响着色器代码结构。

6. **DAG 支持但有限制**: 支持 DAG 结构以匹配运行时 API，但预编译时不尝试检测和优化 DAG 中的共享子树（TODO 注释中提到）。

7. **重用着色器基础设施**: 图像滤镜实现为特殊的着色器（Blur、Displacement、Lighting 等），这些着色器在 PrecompileShadersPriv 中定义。这种设计统一了着色器和图像滤镜的预编译路径。

## 性能考量

### 管线数量

图像滤镜的管线数量通常不大，因为：
- 使用统一的图像着色器配置
- 不支持内部选项组合
- 大多数滤镜只有 1-2 个变体

### 特殊情况

- 形态学滤镜生成 2 组管线（稀疏 + 线性）
- 矩阵卷积滤镜生成 3 个变体（uniform 基础 + 2 个纹理基础大小）

### 内存占用

使用 AutoSTArray<2> 优化小规模输入列表，避免大多数情况下的堆分配。

### DAG 遍历开销

当前实现简单递归遍历整个 DAG，对于复杂的 DAG 可能导致重复工作。TODO 注释提到需要添加访问标记优化。

### 着色器复用

通过重用 PrecompileImageFiltersPriv 和 PrecompileShadersPriv 中的共享实现，避免代码和编译开销重复。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/gpu/graphite/precompile/PrecompileImageFilter.h | 公共头文件 |
| src/gpu/graphite/precompile/PrecompileImageFilter.cpp | 实现文件 |
| src/gpu/graphite/precompile/PrecompileImageFilterPriv.h | 私有接口 |
| src/gpu/graphite/precompile/PrecompileImageFiltersPriv.h | 共享管线生成函数 |
| include/core/SkImageFilter.h | 对应的运行时 API |
| src/core/SkImageFilter_Base.h | 运行时图像滤镜基类 |
| src/gpu/graphite/precompile/PrecompileShadersPriv.h | 图像滤镜使用的特殊着色器 |
