# PrecompileColorFilter

> 源文件: include/gpu/graphite/precompile/PrecompileColorFilter.h, src/gpu/graphite/precompile/PrecompileColorFilter.cpp

## 概述

`PrecompileColorFilter` 是 Skia Graphite 预编译系统中表示颜色滤镜（ColorFilter）的抽象类，对应运行时 API 中的 `SkColorFilter` 类。它封装了各种颜色变换操作的预编译变体，包括混合模式颜色滤镜、矩阵变换、色彩空间转换、组合滤镜等。该模块支持复杂的颜色处理管线预编译，是图像处理和效果系统的核心组件。

主要功能：
- 提供颜色滤镜的抽象表示
- 支持 Blend、Matrix、HSLAMatrix、Table 等多种滤镜类型
- 支持滤镜组合（Compose）
- 支持色彩空间转换（LinearToSRGBGamma、SRGBToLinearGamma）
- 支持特殊效果（HighContrast、Luma、Overdraw、Gaussian）
- 支持工作格式颜色滤镜（WithWorkingFormat）

## 架构位置

`PrecompileColorFilter` 在预编译系统中的位置：

```
预编译层次：
PrecompileBase (基类)
    ├── PrecompileShader
    ├── PrecompileColorFilter (本模块)
    ├── PrecompileBlender
    └── PrecompileImageFilter

滤镜组合结构：
PrecompileColorFilter
    ├── PrecompileComposeColorFilter (组合滤镜)
    ├── PrecompileBlendModeColorFilter (混合模式滤镜)
    ├── PrecompileMatrixColorFilter (矩阵滤镜)
    ├── PrecompileColorSpaceXformColorFilter (色彩空间转换)
    ├── PrecompileTableColorFilter (查找表滤镜)
    ├── PrecompileGaussianColorFilter (高斯滤镜)
    └── PrecompileWithWorkingFormatColorFilter (工作格式滤镜)

使用流程：
Client → PrecompileColorFilters::Blend/Matrix/... → PrecompileColorFilter
                                                           ↓
                                                  PaintOptions::setColorFilters
                                                           ↓
                                                  buildCombinations
                                                           ↓
                                                  MatrixColorFilterBlock::AddBlock
```

## 主要类与结构体

### PrecompileColorFilter

颜色滤镜预编译抽象基类。

**继承关系**
```
PrecompileBase (基类)
    ↑
PrecompileColorFilter (本模块)
    ↑
├── PrecompileComposeColorFilter
├── PrecompileBlendModeColorFilter
├── PrecompileMatrixColorFilter
├── PrecompileColorSpaceXformColorFilter
├── PrecompileTableColorFilter
├── PrecompileGaussianColorFilter
└── PrecompileWithWorkingFormatColorFilter
```

### PrecompileComposeColorFilter

实现滤镜组合的类。

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fOuterOptions` | `std::vector<sk_sp<PrecompileColorFilter>>` | 外层滤镜选项 |
| `fInnerOptions` | `std::vector<sk_sp<PrecompileColorFilter>>` | 内层滤镜选项 |
| `fNumOuterCombos` | `int` | 外层组合数 |
| `fNumInnerCombos` | `int` | 内层组合数 |

### PrecompileBlendModeColorFilter

实现混合模式颜色滤镜的类。

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBlendOptions` | `PrecompileBlenderList` | 混合选项列表 |

### PrecompileMatrixColorFilter

实现矩阵变换颜色滤镜的类。

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fInHSLA` | `bool` | 是否在 HSLA 空间操作 |

### PrecompileColorSpaceXformColorFilter

实现色彩空间转换的类。

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fSrc` | `std::vector<sk_sp<SkColorSpace>>` | 源色彩空间列表 |
| `fDst` | `std::vector<sk_sp<SkColorSpace>>` | 目标色彩空间列表 |
| `fNumCombinations` | `int` | 组合数（src.size * dst.size） |

### PrecompileWithWorkingFormatColorFilter

在特定工作格式中执行颜色滤镜的包装类。

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fChildOptions` | `std::vector<sk_sp<PrecompileColorFilter>>` | 子滤镜选项 |
| `fNumChildCombos` | `int` | 子滤镜组合数 |
| `fWorkingFormatCalculator` | `SkWorkingFormatCalculator` | 工作格式计算器 |

## 公共 API 函数

### PrecompileColorFilter 类

**滤镜组合**
```cpp
sk_sp<PrecompileColorFilter> makeComposed(sk_sp<PrecompileColorFilter> inner) const;
```
创建由当前滤镜和内层滤镜组合的新滤镜。

### PrecompileColorFilters 命名空间

**组合滤镜**
```cpp
sk_sp<PrecompileColorFilter> Compose(
    SkSpan<const sk_sp<PrecompileColorFilter>> outer,
    SkSpan<const sk_sp<PrecompileColorFilter>> inner);
```

**混合模式滤镜**
```cpp
sk_sp<PrecompileColorFilter> Blend(SkSpan<const SkBlendMode> blendModes);
sk_sp<PrecompileColorFilter> Blend(); // 包含所有混合模式
```

**矩阵变换**
```cpp
sk_sp<PrecompileColorFilter> Matrix();
sk_sp<PrecompileColorFilter> HSLAMatrix();
```

**色彩空间转换**
```cpp
sk_sp<PrecompileColorFilter> LinearToSRGBGamma();
sk_sp<PrecompileColorFilter> SRGBToLinearGamma();
```

**插值滤镜**
```cpp
sk_sp<PrecompileColorFilter> Lerp(
    SkSpan<const sk_sp<PrecompileColorFilter>> dstOptions,
    SkSpan<const sk_sp<PrecompileColorFilter>> srcOptions);
```

**查找表滤镜**
```cpp
sk_sp<PrecompileColorFilter> Table();
```

**其他滤镜**
```cpp
sk_sp<PrecompileColorFilter> Lighting();      // 等价于 Matrix
sk_sp<PrecompileColorFilter> HighContrast();
sk_sp<PrecompileColorFilter> Luma();
sk_sp<PrecompileColorFilter> Overdraw();
```

## 内部实现细节

### 组合滤镜实现

**构造函数**：
```cpp
PrecompileComposeColorFilter(SkSpan<const sk_sp<PrecompileColorFilter>> outerOptions,
                             SkSpan<const sk_sp<PrecompileColorFilter>> innerOptions)
        : fOuterOptions(outerOptions.begin(), outerOptions.end())
        , fInnerOptions(innerOptions.begin(), innerOptions.end()) {

    fNumOuterCombos = 0;
    for (const auto& outerOption : fOuterOptions) {
        fNumOuterCombos += outerOption ? outerOption->priv().numCombinations() : 1;
    }

    fNumInnerCombos = 0;
    for (const auto& innerOption : fInnerOptions) {
        fNumInnerCombos += innerOption ? innerOption->priv().numCombinations() : 1;
    }
}
```

**Key 生成**：
```cpp
void addToKey(const KeyContext& keyContext, int desiredCombination) const override {
    // 解码组合索引
    const int desiredOuterCombination = desiredCombination % fNumOuterCombos;
    int remainingCombinations = desiredCombination / fNumOuterCombos;
    const int desiredInnerCombination = remainingCombinations % fNumInnerCombos;

    // 选择具体选项
    auto [outer, outerChildOptions] = SelectOption<PrecompileColorFilter>(
            fOuterOptions, desiredOuterCombination);
    auto [inner, innerChildOptions] = SelectOption<PrecompileColorFilter>(
            fInnerOptions, desiredInnerCombination);

    // 处理特殊情况
    if (!inner && !outer) {
        // 直通滤镜
        keyContext.paintParamsKeyBuilder()->addBlock(BuiltInCodeSnippetID::kPriorOutput);
    } else if (!inner) {
        outer->priv().addToKey(keyContext, outerChildOptions);
    } else if (!outer) {
        inner->priv().addToKey(keyContext, innerChildOptions);
    } else {
        // 组合两个滤镜
        Compose(keyContext,
                [&]() { inner->priv().addToKey(keyContext, innerChildOptions); },
                [&]() { outer->priv().addToKey(keyContext, outerChildOptions); });
    }
}
```

### 混合模式颜色滤镜

**Key 生成**：
```cpp
void addToKey(const KeyContext& keyContext, int desiredCombination) const override {
    auto [blender, option] = fBlendOptions.selectOption(desiredCombination);
    SkASSERT(option == 0 && blender->priv().asBlendMode().has_value());
    SkBlendMode representativeBlendMode = *blender->priv().asBlendMode();

    // 使用占位颜色
    AddBlendModeColorFilter(keyContext, representativeBlendMode, SK_PMColor4fWHITE);
}
```

**所有混合模式工厂**：
```cpp
sk_sp<PrecompileColorFilter> PrecompileColorFilters::Blend() {
    static constexpr SkBlendMode kAllBlendOptions[15] = {
        SkBlendMode::kSrcOver,  // 触发 Porter-Duff 混合
        SkBlendMode::kHue,      // 触发 HSLC 混合
        // 所有剩余固定混合模式
        SkBlendMode::kPlus, SkBlendMode::kModulate, SkBlendMode::kScreen,
        SkBlendMode::kOverlay, SkBlendMode::kDarken, SkBlendMode::kLighten,
        // ...
    };
    return Blend(kAllBlendOptions);
}
```

### 矩阵颜色滤镜

**Key 生成**：
```cpp
void addToKey(const KeyContext& keyContext, int desiredCombination) const override {
    SkASSERT(desiredCombination == 0);
    static constexpr float kIdentity[20] = { 1, 0, 0, 0, 0,
                                             0, 1, 0, 0, 0,
                                             0, 0, 1, 0, 0,
                                             0, 0, 0, 1, 0 };
    MatrixColorFilterBlock::MatrixColorFilterData matrixCFData(kIdentity, fInHSLA, true);
    MatrixColorFilterBlock::AddBlock(keyContext, matrixCFData);
}
```

### 色彩空间转换

**组合数计算**：
```cpp
int numIntrinsicCombinations() const override {
    return fSrc.size() * fDst.size();
}
```

**Key 生成**：
```cpp
void addToKey(const KeyContext& keyContext, int desiredCombination) const override {
    const int srcCombination = desiredCombination % fSrc.size();
    const int dstCombination = desiredCombination / fSrc.size();

    constexpr SkAlphaType kAlphaType = kPremul_SkAlphaType;

    ColorSpaceTransformBlock::ColorSpaceTransformData csData(
            fSrc[srcCombination].get(), kAlphaType,
            fDst[dstCombination].get(), kAlphaType);

    ColorSpaceTransformBlock::AddBlock(keyContext, csData);
}
```

### Lerp 滤镜实现

使用内置运行时效果：
```cpp
sk_sp<PrecompileColorFilter> PrecompileColorFilters::Lerp(
        SkSpan<const sk_sp<PrecompileColorFilter>> dstOptions,
        SkSpan<const sk_sp<PrecompileColorFilter>> srcOptions) {

    const SkRuntimeEffect* lerpEffect =
            GetKnownRuntimeEffect(SkKnownRuntimeEffects::StableKey::kLerp);

    skia_private::TArray<sk_sp<PrecompileBase>> dsts, srcs;
    for (const sk_sp<PrecompileColorFilter>& d : dstOptions) {
        dsts.push_back(d);
    }
    for (const sk_sp<PrecompileColorFilter>& s : srcOptions) {
        srcs.push_back(s);
    }

    return PrecompileRuntimeEffects::MakePrecompileColorFilter(
            sk_ref_sp(lerpEffect), {{ dsts, srcs }});
}
```

### HighContrast 滤镜

带工作格式包装：
```cpp
sk_sp<PrecompileColorFilter> PrecompileColorFilters::HighContrast() {
    const SkRuntimeEffect* highContrastEffect =
            GetKnownRuntimeEffect(SkKnownRuntimeEffects::StableKey::kHighContrast);

    sk_sp<PrecompileColorFilter> cf =
            PrecompileRuntimeEffects::MakePrecompileColorFilter(sk_ref_sp(highContrastEffect));

    // 匹配 src/effects/SkHighContrastFilter.cpp 的工作格式参数
    const skcms_TransferFunction kTF = SkNamedTransferFn::kLinear;
    const SkAlphaType kUnpremul = kUnpremul_SkAlphaType;
    return PrecompileColorFiltersPriv::WithWorkingFormat(
            {{std::move(cf)}}, &kTF, nullptr, &kUnpremul);
}
```

### WithWorkingFormat 实现

**Key 生成（嵌套 Compose）**：
```cpp
void addToKey(const KeyContext& keyContext, int desiredCombination) const override {
    const SkColorInfo& dstInfo = keyContext.dstColorInfo();
    const SkAlphaType dstAT = dstInfo.alphaType();
    sk_sp<SkColorSpace> dstCS = dstInfo.colorSpace()
                                    ? dstInfo.refColorSpace()
                                    : SkColorSpace::MakeSRGB();

    SkAlphaType workingAT;
    sk_sp<SkColorSpace> workingCS = fWorkingFormatCalculator.workingFormat(dstCS, &workingAT);
    KeyContext workingContext = keyContext.withColorInfo({...});

    // 使用两层嵌套 compose：(dst→working), child, (working→dst)
    Compose(keyContext,
            /* addInnerToKey= */ [&]() {
                Compose(keyContext,
                        /* addInnerToKey= */ [&]() {
                            // dst → working 转换
                            ColorSpaceTransformBlock::AddBlock(keyContext, data1);
                        },
                        /* addOuterToKey= */ [&]() {
                            // 子滤镜
                            AddToKey<PrecompileColorFilter>(workingContext, fChildOptions, ...);
                        });
            },
            /* addOuterToKey= */ [&]() {
                // working → dst 转换
                ColorSpaceTransformBlock::AddBlock(keyContext, data2);
            });
}
```

### 空选项处理

**辅助函数**：
```cpp
bool is_empty(SkSpan<const sk_sp<PrecompileColorFilter>> options) {
    if (options.empty()) return true;

    for (const auto& o : options) {
        if (o) return false;
    }
    return true;
}
```

**Compose 工厂使用**：
```cpp
sk_sp<PrecompileColorFilter> PrecompileColorFilters::Compose(
        SkSpan<const sk_sp<PrecompileColorFilter>> outerOptions,
        SkSpan<const sk_sp<PrecompileColorFilter>> innerOptions) {
    if (is_empty(outerOptions) && is_empty(innerOptions)) {
        return nullptr; // 返回 null 表示无滤镜
    }
    return sk_make_sp<PrecompileComposeColorFilter>(outerOptions, innerOptions);
}
```

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `PrecompileBase` | 预编译基类 |
| `PrecompileRuntimeEffect` | 运行时效果预编译 |
| `SkRuntimeEffect` | 运行时效果基础 |
| `SkKnownRuntimeEffects` | 内置运行时效果 |
| `KeyHelpers` | Key 生成辅助函数 |
| `BuiltInCodeSnippetID` | 内置代码片段 ID |
| `PrecompileBlender` | 混合器（用于 Blend 滤镜） |
| `SkColorSpace` | 色彩空间 |
| `SkWorkingFormatColorFilter` | 工作格式计算 |

**被依赖的模块**

- `PaintOptions`：管理颜色滤镜选项
- `PrecompileShader`：某些着色器可能包含颜色滤镜
- `PrecompileImageFilter`：图像滤镜可能包含颜色滤镜

## 设计模式与设计决策

### 策略模式

`PrecompileColorFilter` 作为抽象策略，多个子类实现不同的颜色变换策略。

### 装饰器模式

`PrecompileComposeColorFilter` 和 `PrecompileWithWorkingFormatColorFilter` 包装其他滤镜，添加额外行为。

### 工厂模式

`PrecompileColorFilters` 命名空间提供多个工厂函数，隐藏具体实现类。

### 组合模式

`PrecompileComposeColorFilter` 将多个滤镜组合成树状结构。

### 空对象模式

`nullptr` 被解释为直通滤镜（no-op），简化组合逻辑。

### 笛卡尔积组合

组合滤镜和色彩空间转换都使用笛卡尔积生成所有可能组合。

### 嵌套 Compose 模式

`WithWorkingFormat` 使用两层嵌套 Compose 将色彩空间转换和子滤镜串联。

### 运行时效果复用

多个滤镜（Lerp、HighContrast、Luma、Overdraw）复用内置运行时效果，避免重复实现。

## 性能考量

### 矩阵滤镜优化

使用单位矩阵作为占位，因为具体矩阵值不影响着色器代码生成。

### 混合模式合并

通过 `PrecompileBlenderList` 合并相似混合模式，减少滤镜变体。

### 空选项快速路径

`is_empty` 快速检查避免创建无用的空组合对象。

### 色彩空间转换批处理

`PrecompileColorSpaceXformColorFilter` 预先计算组合数，避免重复计算。

### 直通滤镜优化

空 inner 和 outer 组合时，直接添加 `kPriorOutput` 块，避免无用的滤镜代码。

### 工作格式计算缓存

`SkWorkingFormatCalculator` 内部缓存计算结果，避免重复计算。

### 智能指针优化

使用 `sk_sp` 和移动语义减少引用计数操作。

### 向量预留

构造时预留向量空间，减少动态扩容。

### 编译时常量

内置矩阵和 alpha 类型使用编译时常量，允许编译器优化。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/gpu/graphite/precompile/PrecompileBase.h` | 基类 | 预编译基类定义 |
| `src/gpu/graphite/precompile/PrecompileColorFiltersPriv.h` | 相关 | 私有工具函数 |
| `include/gpu/graphite/precompile/PrecompileRuntimeEffect.h` | 依赖 | 运行时效果预编译 |
| `src/core/SkKnownRuntimeEffects.h` | 依赖 | 内置运行时效果 |
| `src/gpu/graphite/KeyHelpers.h` | 依赖 | Key 生成辅助 |
| `src/gpu/graphite/BuiltInCodeSnippetID.h` | 依赖 | 内置代码片段 |
| `include/core/SkColorSpace.h` | 依赖 | 色彩空间 |
| `src/effects/colorfilters/SkWorkingFormatColorFilter.h` | 依赖 | 工作格式计算 |
| `include/gpu/graphite/precompile/PaintOptions.h` | 使用方 | 绘制选项管理 |
