# PaintOptions

> 源文件: include/gpu/graphite/precompile/PaintOptions.h, src/gpu/graphite/precompile/PaintOptions.cpp

## 概述

`PaintOptions` 是 Skia Graphite 预编译系统中的核心类，作为 `SkPaint` 的预编译模拟对象。它封装了绘制管线各个阶段的选项集合（shader、colorFilter、blender 等），用于在实际绘制前预先编译所有可能的渲染管线组合，从而避免运行时的着色器编译卡顿。

主要功能：
- 管理各绘制阶段的选项列表（shader、imageFilter、maskFilter、colorFilter、blender）
- 计算所有可能的绘制管线组合数
- 生成 PaintParamsKey 用于管线编译
- 支持图像滤镜和蒙版滤镜的特殊处理
- 处理裁剪着色器和原始混合模式

该类是 Graphite 预编译架构的基石，通过预先生成所有可能的管线配置，显著减少首次绘制时的延迟。

## 架构位置

`PaintOptions` 在预编译系统中的位置：

```
预编译流程：
Client Code
    ↓ 创建
PaintOptions (本模块)
    ↓ 配置选项
PrecompileShader / PrecompileColorFilter / PrecompileBlender / ...
    ↓ 传递到
Context::Precompile()
    ↓ 遍历组合
PaintOptions::buildCombinations()
    ↓ 生成
PaintParamsKey
    ↓ 查询/创建
GraphicsPipeline (GPU 管线对象)
```

## 主要类与结构体

### PaintOptions

预编译绘制选项管理类。

**继承关系**
- 无继承关系，独立类

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fShaderOptions` | `TArray<sk_sp<PrecompileShader>>` | 着色器选项列表 |
| `fColorFilterOptions` | `TArray<sk_sp<PrecompileColorFilter>>` | 颜色滤镜选项列表 |
| `fBlendModeOptions` | `TArray<SkBlendMode>` | 混合模式列表 |
| `fBlenderOptions` | `TArray<sk_sp<PrecompileBlender>>` | 混合器选项列表 |
| `fClipShaderOptions` | `TArray<sk_sp<PrecompileShader>>` | 裁剪着色器选项列表 |
| `fImageFilterOptions` | `TArray<sk_sp<PrecompileImageFilter>>` | 图像滤镜选项列表 |
| `fMaskFilterOptions` | `TArray<sk_sp<PrecompileMaskFilter>>` | 蒙版滤镜选项列表 |
| `fPrimitiveBlendMode` | `SkBlendMode` | 原始图元混合模式（用于 drawVertices） |
| `fSkipColorXform` | `bool` | 是否跳过颜色空间转换 |
| `fDither` | `bool` | 是否启用抖动 |
| `fPaintColorIsOpaque` | `bool` | 绘制颜色是否不透明 |

## 公共 API 函数

**构造与赋值**
```cpp
PaintOptions();
PaintOptions(const PaintOptions&);
PaintOptions& operator=(const PaintOptions&);
~PaintOptions();
```

**配置接口**
```cpp
void setShaders(SkSpan<const sk_sp<PrecompileShader>> shaders);
void setImageFilters(SkSpan<const sk_sp<PrecompileImageFilter>> imageFilters);
void setMaskFilters(SkSpan<const sk_sp<PrecompileMaskFilter>> maskFilters);
void setColorFilters(SkSpan<const sk_sp<PrecompileColorFilter>> colorFilters);
void setBlendModes(SkSpan<const SkBlendMode> blendModes);
void setBlenders(SkSpan<const sk_sp<PrecompileBlender>> blenders);
void setDither(bool dither);
void setPaintColorIsOpaque(bool paintColorIsOpaque);
```

**查询接口**
```cpp
SkSpan<const sk_sp<PrecompileShader>> getShaders() const;
SkSpan<const sk_sp<PrecompileImageFilter>> getImageFilters() const;
SkSpan<const sk_sp<PrecompileMaskFilter>> getMaskFilters() const;
SkSpan<const sk_sp<PrecompileColorFilter>> getColorFilters() const;
SkSpan<const SkBlendMode> getBlendModes() const;
SkSpan<const sk_sp<PrecompileBlender>> getBlenders() const;
bool isDither() const;
bool isPaintColorOpaque() const;
```

**私有访问器**
```cpp
PaintOptionsPriv priv();
const PaintOptionsPriv priv() const;
```

## 内部实现细节

### 组合数计算

**着色器组合数**：
```cpp
int PaintOptions::numShaderCombinations() const {
    int numShaderCombinations = 0;
    for (const sk_sp<PrecompileShader>& s : fShaderOptions) {
        numShaderCombinations += s->numCombinations();
    }
    return numShaderCombinations ? numShaderCombinations : 1; // 默认为纯色着色器
}
```

**总组合数**：
```cpp
int PaintOptions::numCombinations() const {
    return this->numShaderCombinations() *
           this->numColorFilterCombinations() *
           this->numBlendCombinations() *
           this->numClipShaderCombinations();
}
```

### 组合构建核心算法

```cpp
void PaintOptions::buildCombinations(
        const KeyContext& keyContext,
        DrawTypeFlags drawTypes,
        bool withPrimitiveBlender,
        Coverage coverage,
        const RenderPassDesc& renderPassDesc,
        const ProcessCombination& processCombination) const {

    if (!fImageFilterOptions.empty() || !fMaskFilterOptions.empty()) {
        // 特殊处理：创建图像绘制管线和恢复绘制管线
        create_image_drawing_pipelines(keyContext, *this, renderPassDesc, processCombination);
        // ... 递归处理滤镜
    } else {
        // 标准路径：遍历所有组合
        int numCombinations = this->numCombinations();
        for (int i = 0; i < numCombinations; ++i) {
            keyContext.pipelineDataGatherer()->resetForDraw();
            this->createKey(keyContext, renderPassDesc.fColorAttachment.fFormat,
                            i, withPrimitiveBlender,
                            SkToBool(drawTypes & DrawTypeFlags::kAnalyticClip), coverage);

            UniquePaintParamsID paintID = keyContext.dict()->findOrCreate(
                    keyContext.paintParamsKeyBuilder());

            processCombination(paintID, drawTypes, withPrimitiveBlender, coverage, renderPassDesc);
        }
    }
}
```

### Key 生成逻辑

```cpp
void PaintOptions::createKey(const KeyContext& keyContext,
                             TextureFormat targetFormat,
                             int desiredCombination,
                             bool addPrimitiveBlender,
                             bool addAnalyticClip,
                             Coverage coverage) const {
    // 多维索引解码
    const int numClipShaderCombos = this->numClipShaderCombinations();
    const int numBlendModeCombos = this->numBlendCombinations();
    const int numColorFilterCombinations = this->numColorFilterCombinations();

    const int desiredClipShaderCombination = desiredCombination % numClipShaderCombos;
    int remainingCombinations = desiredCombination / numClipShaderCombos;

    const int desiredBlendCombination = remainingCombinations % numBlendModeCombos;
    remainingCombinations /= numBlendModeCombos;

    const int desiredColorFilterCombination = remainingCombinations % numColorFilterCombinations;
    remainingCombinations /= numColorFilterCombinations;

    const int desiredShaderCombination = remainingCombinations;

    // 选择具体选项
    auto clipShader = PrecompileBase::SelectOption(SkSpan(fClipShaderOptions),
                                                   desiredClipShaderCombination);
    std::pair<sk_sp<PrecompileBlender>, int> finalBlender = ...;

    // 创建 PaintOption 并转换为 Key
    PaintOption option(fPaintColorIsOpaque, finalBlender, ...);
    option.toKey(keyContext);
}
```

### 图像滤镜特殊处理

当存在图像滤镜或蒙版滤镜时：

1. **创建修改后的 PaintOptions**：
```cpp
PaintOptions tmp = *this;
tmp.setImageFilters({});
tmp.setMaskFilters({});
tmp.addBlendMode(SkBlendMode::kSrcOver); // 滤镜内部使用 SrcOver
```

2. **融合 ColorFilter-ImageFilter**：
```cpp
for (const sk_sp<PrecompileImageFilter>& o : fImageFilterOptions) {
    sk_sp<PrecompileColorFilter> imageFiltersCF = o->asAColorFilter();
    if (imageFiltersCF) {
        // 将 CFIF 融合到颜色滤镜中
        for (const sk_sp<PrecompileColorFilter>& cf : tmp.fColorFilterOptions) {
            sk_sp<PrecompileColorFilter> newCF = imageFiltersCF->makeComposed(cf);
            newCFs.push_back(std::move(newCF));
        }
    }
}
```

3. **创建图像绘制管线**：
```cpp
void create_image_drawing_pipelines(...) {
    PaintOptions imagePaintOptions;
    sk_sp<PrecompileShader> imageShader = PrecompileShaders::Image(
            PrecompileShaders::ImageShaderFlags::kNoAlphaNoCubic);
    imagePaintOptions.setShaders({{ imageShader }});
    // ... 递归构建
}
```

### 裁剪着色器处理

裁剪着色器会被自动包装：
```cpp
void PaintOptions::setClipShaders(SkSpan<const sk_sp<PrecompileShader>> clipShaders) {
    fClipShaderOptions.reserve(2 * clipShaders.size());
    for (const sk_sp<PrecompileShader>& cs : clipShaders) {
        // 包装在 CTMShader 中
        sk_sp<PrecompileShader> withCTM = cs ? PrecompileShadersPriv::CTM({{ cs }}) : nullptr;
        // 反向版本（用于 kDifference 裁剪）
        sk_sp<PrecompileShader> inverted =
                withCTM ? withCTM->makeWithColorFilter(PrecompileColorFilters::Blend())
                        : nullptr;

        fClipShaderOptions.emplace_back(std::move(withCTM));
        fClipShaderOptions.emplace_back(std::move(inverted));
    }
}
```

### Blender 选项合并

```cpp
void PaintOptions::setBlenders(SkSpan<const sk_sp<PrecompileBlender>> blenders) {
    for (const sk_sp<PrecompileBlender>& b: blenders) {
        if (b->priv().asBlendMode().has_value()) {
            // 提取简单混合模式
            fBlendModeOptions.push_back(b->priv().asBlendMode().value());
        } else {
            // 保留复杂 Blender
            fBlenderOptions.push_back(b);
        }
    }
}
```

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `PrecompileShader` | 着色器预编译选项 |
| `PrecompileColorFilter` | 颜色滤镜预编译选项 |
| `PrecompileBlender` | 混合器预编译选项 |
| `PrecompileImageFilter` | 图像滤镜预编译选项 |
| `PrecompileMaskFilter` | 蒙版滤镜预编译选项 |
| `KeyContext` | Key 生成上下文 |
| `PaintParamsKey` | 绘制参数 Key |
| `ShaderCodeDictionary` | 着色器代码字典 |
| `RenderPassDesc` | 渲染通道描述 |

**被依赖的模块**

- `Context::Precompile()`：执行预编译
- `PrecompileImageFilter`：图像滤镜使用 PaintOptions
- `PrecompileMaskFilter`：蒙版滤镜使用 PaintOptions

## 设计模式与设计决策

### 组合爆炸管理

通过笛卡尔积生成所有组合，但提供了优化策略：
- 空选项列表默认为单个默认值（如纯色着色器）
- BlendMode 和 Blender 统一管理避免重复
- 图像滤镜使用特殊路径减少无用组合

### 索引映射算法

使用多维索引解码将线性索引映射到多维组合空间：
```
linearIndex → (clipShaderIndex, blenderIndex, colorFilterIndex, shaderIndex)
```
这是一种空间高效的组合枚举方式。

### 延迟绑定模式

`ProcessCombination` 回调模式允许调用者自定义如何处理每个组合，而不是在 `PaintOptions` 中硬编码管线创建逻辑。

### 分层处理策略

对于图像滤镜和蒙版滤镜：
1. 基础绘制（使用 SrcOver 混合）
2. 图像绘制管线（用于恢复）
3. 滤镜特定管线

这种分层确保了所有滤镜路径的覆盖。

### 选项合并优化

将简单混合模式从 Blender 中提取，与 BlendMode 列表合并，减少重复的管线变体。

### 默认值策略

每个选项列表为空时都有合理的默认行为：
- 无 shader → 纯色着色器
- 无 colorFilter → 直通
- 无 blender → kSrcOver
- 无 clipShader → 无裁剪

这确保了最小配置的有效性。

## 性能考量

### 组合数预计算

`numCombinations()` 方法预先计算总数，避免在循环中重复计算。

### 批量选项设置

使用 `SkSpan` 和 `push_back_n` 批量添加选项，减少内存重分配次数。

### 智能指针复用

选项列表存储 `sk_sp`，避免重复的引用计数操作。

### Key 生成优化

Key 生成时使用栈上对象和内联函数，避免堆分配：
```cpp
PaintOption option(...); // 栈对象
option.toKey(keyContext); // 内联生成
```

### 滤镜路径分支

通过 `if (!fImageFilterOptions.empty() || !fMaskFilterOptions.empty())` 快速分支，避免常见路径的额外开销。

### 并行化潜力

`buildCombinations` 的循环是相互独立的，理论上可以并行化（当前未实现）。

### 内存局部性

使用 `TArray` 而非 `std::vector` 提供更好的内存布局控制。

### 移动语义

配置接口接受 `SkSpan`，避免不必要的拷贝。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/gpu/graphite/precompile/PrecompileShader.h` | 依赖 | 着色器预编译 |
| `include/gpu/graphite/precompile/PrecompileColorFilter.h` | 依赖 | 颜色滤镜预编译 |
| `include/gpu/graphite/precompile/PrecompileBlender.h` | 依赖 | 混合器预编译 |
| `include/gpu/graphite/precompile/PrecompileImageFilter.h` | 依赖 | 图像滤镜预编译 |
| `include/gpu/graphite/precompile/PrecompileMaskFilter.h` | 依赖 | 蒙版滤镜预编译 |
| `src/gpu/graphite/precompile/PaintOptionsPriv.h` | 相关 | 私有访问接口 |
| `src/gpu/graphite/precompile/PaintOption.h` | 相关 | 单个绘制选项 |
| `src/gpu/graphite/KeyContext.h` | 依赖 | Key 生成上下文 |
| `src/gpu/graphite/PaintParamsKey.h` | 依赖 | 绘制参数 Key |
| `src/gpu/graphite/RenderPassDesc.h` | 依赖 | 渲染通道描述 |
