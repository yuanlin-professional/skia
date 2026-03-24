# PrecompileMaskFilter

> 源文件
> - include/gpu/graphite/precompile/PrecompileMaskFilter.h
> - src/gpu/graphite/precompile/PrecompileMaskFilter.cpp

## 概述

`PrecompileMaskFilter` 是 Skia Graphite 预编译系统中用于遮罩滤镜的抽象基类，对应于主 API 中的 `SkMaskFilter` 类。与其他预编译组件不同，PrecompileMaskFilter 不直接参与着色器密钥生成，而是通过 `createPipelines` 方法创建完整的独立渲染管线。

目前主要支持模糊遮罩滤镜（Blur Mask Filter）的预编译，这是实际应用中最常用的遮罩效果。模糊遮罩滤镜通常用于实现阴影、发光等视觉效果。

## 架构位置

```
skgpu::graphite
├── precompile/
│   ├── PrecompileBase (基类)
│   ├── PrecompileMaskFilter (当前组件)
│   ├── PrecompileShader
│   ├── PrecompileColorFilter
│   ├── PrecompileImageFilter
│   └── PaintOptions (使用方)
├── RenderPassDesc (渲染通道描述)
├── KeyContext (密钥上下文)
└── Renderer (渲染器)
```

PrecompileMaskFilter 是 PaintOptions 的重要组成部分，在 PaintOptions 构建管线组合时被调用，负责生成遮罩滤镜相关的所有渲染管线。

## 主要类与结构体

### PrecompileMaskFilter

**继承关系**
- 基类: `PrecompileBase`
- 派生类: `PrecompileBlurMaskFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| N/A | N/A | 抽象基类，无具体成员变量 |

PrecompileMaskFilter 主要通过纯虚函数 `createPipelines` 定义接口。

### PrecompileBlurMaskFilter

**继承关系**: `PrecompileMaskFilter`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| N/A | N/A | 无状态实现类 |

PrecompileBlurMaskFilter 是无状态的，因为模糊参数（半径、样式等）不影响生成的着色器代码，只影响运行时的 uniform 值。

## 公共 API 函数

### PrecompileMaskFilter 核心方法

```cpp
virtual void createPipelines(
    const KeyContext& keyContext,
    const PaintOptions& paintOptions,
    const RenderPassDesc& renderPassDesc,
    const PaintOptions::ProcessCombination& processCombination) const = 0;
```
纯虚函数，派生类实现该方法以创建所有必要的渲染管线。参数说明：
- `keyContext`: 包含 Caps、目标颜色信息等上下文
- `paintOptions`: 原始绘制选项，包含着色器、颜色滤镜等配置
- `renderPassDesc`: 目标渲染通道描述
- `processCombination`: 管线处理回调函数

### PrecompileMaskFilters 命名空间工厂函数

```cpp
sk_sp<PrecompileMaskFilter> Blur();
```
创建模糊遮罩滤镜的预编译对象。对应主 API 中的 `SkMaskFilter::MakeBlur` 工厂函数。

注意：该函数不接受模糊参数（半径、样式等），因为这些参数在预编译阶段是不确定的，且不影响生成的着色器代码。

## 内部实现细节

### PrecompileBlurMaskFilter 的管线创建策略

模糊遮罩滤镜的实现涉及三个主要管线组：

#### 1. 模糊图像滤镜管线

```cpp
PrecompileImageFiltersPriv::CreateBlurImageFilterPipelines(
    keyContext,
    coverageRenderPassDesc,
    processCombination);
```

这部分管线负责实际的模糊计算。使用 Alpha8 覆盖率纹理作为目标，执行多遍模糊操作。

**覆盖率渲染通道配置**:
```cpp
TextureInfo info = caps->getDefaultSampledTextureInfo(
    kAlpha_8_SkColorType,    // 单通道 Alpha
    Mipmapped::kNo,
    Protected::kNo,
    Renderable::kYes);

RenderPassDesc coverageRenderPassDesc = RenderPassDesc::Make(
    caps, info,
    LoadOp::kClear,              // 清除为透明
    StoreOp::kStore,             // 保存结果
    DepthStencilFlags::kDepth,
    { 0.0f, 0.0f, 0.0f, 0.0f },  // 清除颜色（透明）
    /* requiresMSAA= */ false,
    skgpu::Swizzle("a000"),      // Alpha 通道映射
    caps->getDstReadStrategy());
```

#### 2. 恢复绘制管线

```cpp
PaintOptions restoreOptions = paintOptions;
restoreOptions.setMaskFilters({});  // 移除遮罩滤镜，避免递归
restoreOptions.priv().buildCombinations(
    keyContext,
    static_cast<DrawTypeFlags>(InternalDrawTypeFlags::kCoverageMask),
    /* withPrimitiveBlender= */ false,
    Coverage::kSingleChannel,
    renderPassDescIn,
    processCombination);
```

这部分管线负责将模糊后的覆盖率纹理应用到最终图像。使用原始 PaintOptions 的着色器、颜色滤镜等配置，但用模糊结果作为覆盖率遮罩。

对应于 `AutoLayerForImageFilter::addMaskFilterLayer` 中的恢复绘制逻辑。

#### 3. 覆盖率初始绘制管线

```cpp
PaintOptions coverageOptions;
coverageOptions.setShaders({{ PrecompileShaders::Color() }});
coverageOptions.setBlendModes(SKSPAN_INIT_ONE(SkBlendMode::kSrcOver));

coverageOptions.priv().buildCombinations(
    keyContext,
    DrawTypeFlags::kAnalyticRRect,  // 仅解析圆角矩形
    /* withPrimitiveBlender= */ false,
    Coverage::kSingleChannel,
    coverageRenderPassDesc,
    processCombination);
```

这部分管线负责将原始形状绘制到覆盖率纹理。使用纯白色（固定颜色）和 SrcOver 混合模式。

**设计注释**: 代码中有 TODO 注释表明这部分管线可能过度生成，因为它会为所有简单绘制类型创建，而实际上只在绘制类型为 kSimple 且有模糊遮罩时才需要。

### addToKey 方法的特殊处理

```cpp
void PrecompileMaskFilter::addToKey(const KeyContext& keyContext, int desiredCombination) const {
    SkASSERT(false);  // 永远不应该被调用
}
```

PrecompileMaskFilter 覆盖了 `addToKey` 方法并断言失败。这是因为遮罩滤镜不像着色器或颜色滤镜那样作为管线的一部分，而是创建完全独立的绘制通道和管线。

这种设计反映了遮罩滤镜在 Skia 中的特殊地位：它们通常需要离屏渲染和多遍绘制，无法简单地嵌入到单个着色器中。

### 与图像滤镜的关联

模糊遮罩滤镜的实现重用了模糊图像滤镜的基础设施：

```cpp
#include "src/gpu/graphite/precompile/PrecompileImageFiltersPriv.h"

PrecompileImageFiltersPriv::CreateBlurImageFilterPipelines(...);
```

这种设计避免了代码重复，因为从技术角度看，模糊遮罩和模糊图像滤镜使用相同的底层模糊算法。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| PrecompileBase | 基类，提供预编译接口 |
| PaintOptions | 构建完整的绘制选项组合 |
| PrecompileShader | 创建覆盖率绘制和恢复绘制的着色器 |
| PrecompileColorFilter | 恢复绘制时可能使用颜色滤镜 |
| PrecompileImageFiltersPriv | 重用模糊图像滤镜的管线生成逻辑 |
| KeyContext | 提供 Caps 和目标颜色信息 |
| RenderPassDesc | 描述渲染通道配置 |
| Caps | 查询硬件能力，创建纹理信息 |
| InternalDrawTypeFlags | 使用 kCoverageMask 绘制类型标志 |
| Renderer | 底层渲染器（间接依赖） |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| PaintOptions | 通过 setMaskFilters 接受 PrecompileMaskFilter 列表 |
| PaintOptionsPriv | 在 buildCombinations 中调用 createPipelines |

## 设计模式与设计决策

### 模板方法模式 (Template Method Pattern)

PrecompileMaskFilter 定义了抽象接口 `createPipelines`，具体实现由派生类完成。基类提供了框架（通过 PrecompileBase），派生类填充具体行为。

### 策略模式 (Strategy Pattern)

通过函数指针 `ProcessCombination` 回调，允许调用者自定义管线处理策略。这使得同一个遮罩滤镜可以用于不同的场景（预编译、运行时编译等）。

### 设计决策

1. **无参数工厂**: `PrecompileMaskFilters::Blur()` 不接受参数，因为模糊半径、样式等参数不影响着色器代码，只影响 uniform 值。这简化了 API 并减少了预编译组合数量。

2. **独立管线创建**: 不使用 `addToKey` 而是 `createPipelines`，反映了遮罩滤镜需要多遍渲染的本质。这种设计比强行将遮罩滤镜嵌入单个着色器更清晰。

3. **重用图像滤镜基础设施**: 模糊遮罩和模糊图像滤镜共享底层实现，避免代码重复。这是合理的抽象，因为两者在技术上执行相同的操作，只是应用场景不同。

4. **覆盖率纹理格式**: 使用 kAlpha_8 单通道格式存储覆盖率，节省内存带宽。Swizzle 设置为 "a000" 确保 Alpha 通道正确映射。

5. **显式层管理**: 通过 `AutoLayerForImageFilter::addMaskFilterLayer` 的逻辑模型，明确了遮罩滤镜需要创建显式图层的情况。这避免了在不需要时创建额外的渲染目标。

## 性能考量

### 管线数量控制

模糊遮罩滤镜的管线数量 = 模糊图像滤镜管线数 + 恢复绘制选项组合数 + 覆盖率绘制组合数。

其中恢复绘制组合数可能很大，因为它包含了原始 PaintOptions 的所有着色器、颜色滤镜组合。

### 覆盖率绘制优化

覆盖率初始绘制使用 `DrawTypeFlags::kAnalyticRRect`，仅为解析圆角矩形生成管线。这是常见的模糊遮罩应用场景（如圆角卡片阴影）。

TODO 注释指出应进一步限制为 `DrawTypeFlags::kSimple` 的子集，避免过度生成。

### 内存占用

使用 Alpha8 格式的覆盖率纹理，相比 RGBA8 节省 75% 内存。

### 多遍渲染开销

模糊遮罩滤镜本质上需要至少 3 次渲染：
1. 绘制形状到覆盖率纹理
2. 对覆盖率纹理应用模糊（可能多遍）
3. 使用模糊覆盖率绘制最终结果

这是算法本质决定的，无法避免。预编译可以减少每次渲染的编译延迟，但不能减少渲染次数。

### 硬件依赖

覆盖率渲染通道配置依赖于硬件能力（通过 Caps 查询）：
- 纹理格式支持（kAlpha_8）
- 深度/模板缓冲区支持
- 目标读取策略

不同硬件可能生成不同的管线变体。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/gpu/graphite/precompile/PrecompileMaskFilter.h | 公共头文件 |
| src/gpu/graphite/precompile/PrecompileMaskFilter.cpp | 实现文件 |
| include/core/SkMaskFilter.h | 对应的运行时 API |
| src/core/SkMaskFilterBase.h | 运行时遮罩滤镜基类 |
| src/gpu/graphite/precompile/PrecompileImageFiltersPriv.h | 重用的模糊图像滤镜实现 |
| include/gpu/graphite/precompile/PaintOptions.h | 使用 PrecompileMaskFilter 的接口 |
| src/gpu/graphite/RenderPassDesc.h | 渲染通道描述 |
| src/gpu/graphite/InternalDrawTypeFlags.h | kCoverageMask 标志定义 |
