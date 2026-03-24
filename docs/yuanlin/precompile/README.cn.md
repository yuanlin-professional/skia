# precompile - GPU 管线预编译系统

## 概述

`src/gpu/graphite/precompile/` 目录实现了 Skia Graphite 后端的管线预编译（Pipeline Precompilation）子系统。管线预编译是 Graphite 架构中一项关键的性能优化机制，允许客户端在实际绘制操作发生之前，提前创建和编译 GPU 渲染管线。这种方式有效消除了渲染期间因即时编译（JIT compilation）导致的性能卡顿问题。

预编译的核心思想是通过 `PaintOptions` 类将 `SkPaint` 的各种配置选项抽象化。`PaintOptions` 是 `SkPaint` 在预编译场景下的对应物，它封装了着色器（Shader）、颜色滤镜（ColorFilter）、混合模式（Blender）、图像滤镜（ImageFilter）和遮罩滤镜（MaskFilter）等选项的组合集合。当这些选项被传递给 `Precompile()` 函数时，系统会枚举所有可能的组合，并为每种组合预编译对应的 GPU 管线。

该子系统的设计采用了组合爆发（combinatorial explosion）管理策略。每个 `PrecompileBase` 派生类都能报告其支持的组合数量（通过 `numIntrinsicCombinations()` 和 `numChildCombinations()`），系统通过笛卡尔积的方式计算总组合数，并利用整数索引在组合空间中高效导航。这使得即使面对大量选项组合，预编译过程也能系统化地遍历所有可能性。

预编译系统还支持混合模式的智能合并优化。`PrecompileBlenderList` 类将 Porter-Duff 混合模式和 HSLC 混合模式分别合并为单一代表性选项，从而大幅减少需要预编译的管线数量。例如，所有 Porter-Duff 混合模式（如 kSrcOver、kDstOver 等）都共享同一个管线着色器片段，因此只需预编译一次。

最终，预编译生成的管线密钥（`PaintParamsKey`）通过 `ShaderCodeDictionary` 查找或创建唯一标识（`UniquePaintParamsID`），然后配合绘制类型（`DrawTypeFlags`）和渲染通道描述（`RenderPassDesc`）来创建完整的图形管线。

## 架构图

```
                    +-------------------+
                    |   Precompile()    |  <-- 公共 API 入口
                    +--------+----------+
                             |
                             v
                    +-------------------+
                    |   PaintOptions    |  <-- SkPaint 的预编译抽象
                    |  - fShaderOptions |
                    |  - fColorFilter.. |
                    |  - fBlendMode..   |
                    |  - fImageFilter.. |
                    |  - fMaskFilter..  |
                    +--------+----------+
                             |
                    buildCombinations()
                             |
                             v
              +------------------------------+
              | 组合枚举与索引计算              |
              |  numCombinations() =          |
              |    shader * colorFilter *     |
              |    blend * clipShader         |
              +------------------------------+
                             |
                    createKey()
                             |
                             v
                    +-------------------+
                    |   PaintOption     |  <-- 单一组合的具体化
                    |  - toKey()        |
                    +--------+----------+
                             |
        +--------+-----------+-----------+--------+
        |        |           |           |        |
        v        v           v           v        v
   handleDither  handleColor  handlePaint  handle  handleClip
   ing()         Filter()     Alpha()      Primit  ping()
                                          iveColor
                             |
                             v
              +------------------------------+
              |    PaintParamsKeyBuilder      |
              |  -> PaintParamsKey            |
              |  -> UniquePaintParamsID       |
              +------------------------------+
                             |
                             v
              +------------------------------+
              |    ProcessCombination 回调    |
              |  -> 创建 GraphicsPipeline    |
              +------------------------------+

  PrecompileBase 类继承体系:
  +-------------------+
  |  PrecompileBase   |
  +-------------------+
       |    |    |    |    |
       v    v    v    v    v
   Shader Blender CF  IF  MF
       |
       +-- PrecompileColorShader
       +-- PrecompileBlendShader
       +-- PrecompileImageShader
       +-- PrecompileGradientShader
       +-- PrecompileLocalMatrixShader
       +-- PrecompileBlurShader
       +-- PrecompilePerlinNoiseShader
       +-- ... (更多着色器类型)
```

## 目录结构

```
src/gpu/graphite/precompile/
|-- BUILD.bazel                      # Bazel 构建配置
|-- PaintOption.h                    # 单一绘制选项组合类
|-- PaintOption.cpp                  # PaintOption 实现，管线密钥生成逻辑
|-- PaintOptions.cpp                 # PaintOptions 组合枚举与构建
|-- PaintOptionsPriv.h               # PaintOptions 内部接口（友元模式）
|-- PrecompileBaseComplete.h         # PrecompileBase 模板方法的完整实现
|-- PrecompileBasePriv.h             # PrecompileBase 内部特权接口
|-- PrecompileBlender.cpp            # 混合器预编译实现
|-- PrecompileBlenderPriv.h          # 混合器内部接口与 PrecompileBlenderList
|-- PrecompileColorFilter.cpp        # 颜色滤镜预编译实现
|-- PrecompileColorFiltersPriv.h     # 颜色滤镜内部接口
|-- PrecompileImageFilter.cpp        # 图像滤镜预编译实现
|-- PrecompileImageFilterPriv.h      # 图像滤镜内部接口
|-- PrecompileImageFiltersPriv.h     # 图像滤镜工厂内部接口
|-- PrecompileImageShader.h          # 图像着色器预编译头文件
|-- PrecompileMaskFilter.cpp         # 遮罩滤镜预编译实现
|-- PrecompileRuntimeEffect.cpp      # 运行时效果预编译实现
|-- PrecompileShader.cpp             # 着色器预编译实现（核心，55KB+）
|-- PrecompileShaderPriv.h           # 着色器内部接口
|-- PrecompileShadersPriv.h          # 着色器工厂内部接口
```

## 关键类与函数

### PaintOptions
预编译系统的主要公共接口。对应于 `SkPaint`，封装了所有绘制效果的选项集合。

```cpp
class PaintOptions {
public:
    void setShaders(SkSpan<const sk_sp<PrecompileShader>> shaders);
    void setColorFilters(SkSpan<const sk_sp<PrecompileColorFilter>> colorFilters);
    void setBlendModes(SkSpan<const SkBlendMode> blendModes);
    void setBlenders(SkSpan<const sk_sp<PrecompileBlender>> blenders);
    void setImageFilters(SkSpan<const sk_sp<PrecompileImageFilter>> imageFilters);
    void setMaskFilters(SkSpan<const sk_sp<PrecompileMaskFilter>> maskFilters);
    void setDither(bool dither);
    int numCombinations() const;
};
```

### PaintOption
表示一个具体的绘制选项组合实例，负责将该组合转换为管线密钥。

```cpp
class PaintOption {
public:
    void toKey(const KeyContext&) const;
private:
    void addPaintColorToKey(const KeyContext&) const;
    void handlePrimitiveColor(const KeyContext&) const;
    void handlePaintAlpha(const KeyContext&) const;
    void handleColorFilter(const KeyContext&) const;
    void handleDithering(const KeyContext&) const;
    void handleClipping(const KeyContext&) const;
};
```

### PrecompileBase
所有预编译对象的基类，定义了组合计数和密钥生成的虚函数接口。

```cpp
class PrecompileBase : public SkRefCnt {
public:
    enum class Type { kBlender, kColorFilter, kImageFilter, kMaskFilter, kShader };
protected:
    virtual int numIntrinsicCombinations() const;
    virtual int numChildCombinations() const;
    int numCombinations() const;
    virtual void addToKey(const KeyContext&, int desiredCombination) const = 0;
    template<typename T>
    static std::pair<sk_sp<T>, int> SelectOption(SkSpan<const sk_sp<T>> options, int desiredOption);
};
```

### PrecompileBlenderList
管理混合器选项列表，实现 Porter-Duff 和 HSLC 混合模式的智能合并。

```cpp
class PrecompileBlenderList {
public:
    PrecompileBlenderList(SkSpan<const sk_sp<PrecompileBlender>> blenders);
    PrecompileBlenderList(SkSpan<const SkBlendMode> blendModes);
    int numCombinations() const;
    std::pair<sk_sp<PrecompileBlender>, int> selectOption(int desiredCombination) const;
};
```

### 关键工厂函数

- `PrecompileShaders::Image()` - 创建图像着色器预编译选项
- `PrecompileShaders::LinearGradient()` / `RadialGradient()` / `SweepGradient()` / `TwoPointConicalGradient()` - 梯度着色器
- `PrecompileShaders::Blend()` - 混合着色器
- `PrecompileShaders::Color()` - 纯色着色器
- `PrecompileShaders::LocalMatrix()` - 局部矩阵着色器包装
- `PrecompileColorFilters::Blend()` / `Matrix()` / `Table()` / `Compose()` - 颜色滤镜
- `PrecompileBlenders::Mode()` / `Arithmetic()` - 混合器
- `PrecompileImageFilters::Blur()` / `ColorFilter()` / `Blend()` / `Morphology()` - 图像滤镜
- `PrecompileMaskFilters::Blur()` - 遮罩滤镜
- `PrecompileRuntimeEffects::MakePrecompileShader()` / `MakePrecompileColorFilter()` / `MakePrecompileBlender()` - SkRuntimeEffect 封装

## 依赖关系

### 上游依赖（本目录依赖的模块）

| 模块 | 说明 |
|------|------|
| `src/gpu/graphite/KeyContext.h` | 密钥构建上下文，包含 Caps、目标颜色信息等 |
| `src/gpu/graphite/KeyHelpers.h` | 密钥构建辅助函数，如 `AddBlendMode()`、`Compose()` 等 |
| `src/gpu/graphite/PaintParamsKey.h` | 管线参数密钥的核心数据结构 |
| `src/gpu/graphite/ShaderCodeDictionary.h` | 着色器代码字典，管理密钥到 ID 的映射 |
| `src/gpu/graphite/Caps.h` | GPU 能力查询，决定硬件混合支持等 |
| `src/gpu/graphite/Renderer.h` | 渲染器定义，包含 Coverage 和 DrawTypeFlags |
| `src/gpu/graphite/RenderPassDesc.h` | 渲染通道描述信息 |
| `src/gpu/graphite/BuiltInCodeSnippetID.h` | 内置代码片段标识 |
| `src/core/SkKnownRuntimeEffects.h` | 已知运行时效果的稳定键 |
| `include/effects/SkRuntimeEffect.h` | 运行时效果公共接口 |

### 下游依赖（依赖本目录的模块）

| 模块 | 说明 |
|------|------|
| `include/gpu/graphite/precompile/Precompile.h` | 公共 `Precompile()` 函数入口 |
| `src/gpu/graphite/PrecompileInternal.h` | 内部预编译协调模块 |
| 各后端管线创建逻辑 | Vulkan、Metal、Dawn 等后端的管线编译 |

## 设计模式分析

### 1. 组合模式（Combinatorial Pattern）
整个预编译系统基于组合思想设计。`PaintOptions` 中的每个选项槽（shader、colorFilter、blender 等）可以设置多个选项，系统通过笛卡尔积计算所有可能的组合。`numCombinations()` 的计算公式为：

```
总组合数 = numShaderCombinations * numColorFilterCombinations *
           numBlendCombinations * numClipShaderCombinations
```

每个组合通过整数索引唯一标识，可以通过取模和除法操作反向解码出每个槽的具体选项。

### 2. Priv 模式（Friend-based Access Control）
Skia 广泛使用 Priv 模式来控制内部 API 的访问。每个主要类（如 `PrecompileBase`、`PaintOptions`、`PrecompileBlender`）都有对应的 `*Priv` 类，通过 `priv()` 方法访问。这些 Priv 类是纯粹的"特权窗口"，没有额外的数据成员或虚函数，仅暴露内部方法。

### 3. 工厂方法模式（Factory Method Pattern）
`PrecompileShaders`、`PrecompileColorFilters`、`PrecompileBlenders` 等命名空间中的静态工厂函数（如 `Image()`、`Blend()`、`Mode()`）隐藏了具体实现类（如 `PrecompileImageShader`、`PrecompileBlendShader`），客户端仅通过基类指针交互。

### 4. 策略模式（Strategy Pattern）
`PaintOption::toKey()` 方法中的渲染管线构建采用策略模式。根据是否存在自定义混合器、是否需要目标读取（dst read）、是否需要抖动等条件，动态选择不同的密钥构建策略。

### 5. 模板方法模式（Template Method Pattern）
`PrecompileBase::addToKey()` 是纯虚方法，定义了密钥添加的接口。`PrecompileBase::numCombinations()` 是非虚方法，组合了 `numIntrinsicCombinations()` 和 `numChildCombinations()` 两个虚方法的结果，形成模板方法。

## 数据流

```
1. 客户端设置阶段:
   PaintOptions.setShaders({shader1, shader2})
   PaintOptions.setBlendModes({kSrcOver, kMultiply})
   PaintOptions.setColorFilters({cf1})

2. 组合枚举阶段:
   PaintOptions.buildCombinations()
     for i in 0..numCombinations():
       |
       v
3. 密钥创建阶段:
   PaintOptions.createKey(keyContext, targetFormat, i, ...)
     |-- 解码组合索引 -> desiredShader, desiredBlend, desiredCF, desiredClip
     |-- 构造 PaintOption 实例
     |
     v
4. 密钥序列化阶段:
   PaintOption.toKey(keyContext)
     |-- handleDithering()
     |     |-- handleColorFilter()
     |           |-- handlePaintAlpha()
     |                 |-- handlePrimitiveColor()
     |                       |-- addPaintColorToKey()
     |-- AddBlendMode() 或 fFinalBlender.addToKey()
     |-- handleClipping()
     |
     v
5. 管线创建阶段:
   ShaderCodeDictionary.findOrCreate(key)
     -> UniquePaintParamsID
       -> ProcessCombination 回调
         -> 后端管线编译 (Vulkan/Metal/Dawn)
```

## 相关文档与参考

- `include/gpu/graphite/precompile/Precompile.h` - 公共预编译 API 定义
- `include/gpu/graphite/precompile/PaintOptions.h` - PaintOptions 公共接口
- `include/gpu/graphite/precompile/PrecompileBase.h` - PrecompileBase 公共基类
- `include/gpu/graphite/precompile/PrecompileShader.h` - PrecompileShader 公共接口
- `include/gpu/graphite/precompile/PrecompileColorFilter.h` - PrecompileColorFilter 公共接口
- `include/gpu/graphite/precompile/PrecompileBlender.h` - PrecompileBlender 公共接口
- `include/gpu/graphite/precompile/PrecompileImageFilter.h` - PrecompileImageFilter 公共接口
- `include/gpu/graphite/precompile/PrecompileMaskFilter.h` - PrecompileMaskFilter 公共接口
- `include/gpu/graphite/precompile/PrecompileRuntimeEffect.h` - 运行时效果预编译接口
- `src/gpu/graphite/KeyContext.h` - 密钥构建上下文
- `src/gpu/graphite/KeyHelpers.h` - 密钥构建辅助函数
- `src/gpu/graphite/PaintParamsKey.h` - 管线参数密钥
- `src/gpu/graphite/ShaderCodeDictionary.h` - 着色器代码字典
- `src/gpu/graphite/PrecompileInternal.h` - 内部预编译协调
