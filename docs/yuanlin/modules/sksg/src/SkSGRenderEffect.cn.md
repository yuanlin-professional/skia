# SkSGRenderEffect

> 源文件: modules/sksg/src/SkSGRenderEffect.cpp

## 概述

SkSGRenderEffect 是 Skia Scene Graph 模块中负责渲染效果的核心实现文件，提供了多种视觉效果节点，包括着色器效果、遮罩效果、图像滤镜效果、混合效果和图层效果。该文件包含 252 行代码，实现了场景图渲染管线中的关键效果系统，允许开发者将复杂的视觉效果以节点的形式组合到渲染树中。

主要功能包括：
- **Shader** 基类：为所有着色器节点提供通用框架
- **ShaderEffect**：将着色器附加到渲染节点
- **MaskShaderEffect**：应用遮罩着色器
- **ImageFilter** 基类和具体实现（DropShadow、Blur）
- **ImageFilterEffect**：将图像滤镜链应用到渲染树
- **BlenderEffect**：应用自定义混合模式
- **LayerEffect**：创建独立图层并应用混合模式

## 架构位置

SkSGRenderEffect 在 Scene Graph 渲染管线中处于效果层：

```
应用层 (Skottie/Lottie 动画)
    ↓
Scene Graph 构建
    ├── GeometryNode (几何)
    ├── PaintNode (绘制属性)
    └── EffectNode (效果节点) ← 当前模块
        ├── ShaderEffect (着色器效果)
        ├── MaskShaderEffect (遮罩效果)
        ├── ImageFilterEffect (滤镜效果)
        ├── BlenderEffect (混合效果)
        └── LayerEffect (图层效果)
    ↓
渲染上下文 (RenderContext)
    ↓
Skia Canvas 绘制
```

模块依赖关系：

```
include/core (Skia 核心)
    ├── SkShader
    ├── SkImageFilter
    ├── SkBlender
    └── SkCanvas
         ↓
modules/sksg/include
    ├── SkSGNode
    ├── SkSGEffectNode
    └── SkSGRenderNode
         ↓
SkSGRenderEffect.cpp (当前文件)
```

## 主要类与结构体

### Shader (基类)

着色器节点的抽象基类：

```cpp
class Shader : public Node {
public:
    ~Shader() override;
    const sk_sp<SkShader>& getShader() const;

protected:
    Shader();
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) final;
    virtual sk_sp<SkShader> onRevalidateShader() = 0;

private:
    sk_sp<SkShader> fShader;  // 缓存的 Skia 着色器
};
```

**特点**：
- 使用 `kBubbleDamage_Trait` 损坏传播策略
- 通过 `onRevalidateShader()` 钩子让子类生成具体着色器
- 缓存生成的 `SkShader` 对象以提高性能

### MaskShaderEffect

将遮罩着色器应用到子节点：

```cpp
class MaskShaderEffect final : public EffectNode {
public:
    static sk_sp<MaskShaderEffect> Make(sk_sp<RenderNode>, sk_sp<SkShader> = nullptr);
    SG_ATTRIBUTE(Shader, sk_sp<SkShader>, fShader)

protected:
    void onRender(SkCanvas*, const RenderContext*) const override;

private:
    MaskShaderEffect(sk_sp<RenderNode>, sk_sp<SkShader>);
    sk_sp<SkShader> fShader;
};
```

### ShaderEffect

将 Scene Graph Shader 节点附加到渲染树：

```cpp
class ShaderEffect final : public EffectNode {
public:
    static sk_sp<ShaderEffect> Make(sk_sp<RenderNode> child, sk_sp<Shader> shader = nullptr);
    void setShader(sk_sp<Shader>);

protected:
    void onRender(SkCanvas*, const RenderContext*) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    sk_sp<Shader> fShader;  // Scene Graph Shader 节点
};
```

### ImageFilter (基类)

图像滤镜节点的抽象基类：

```cpp
class ImageFilter : public Node {
public:
    ~ImageFilter() override;
    const sk_sp<SkImageFilter>& getFilter() const;
    SG_ATTRIBUTE(CropRect, SkImageFilters::CropRect, fCropRect)

protected:
    ImageFilter();
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) final;
    virtual sk_sp<SkImageFilter> onRevalidateFilter() = 0;

private:
    sk_sp<SkImageFilter> fFilter;           // 缓存的滤镜
    SkImageFilters::CropRect fCropRect;     // 裁剪区域
};
```

### DropShadowImageFilter

投影滤镜实现：

```cpp
class DropShadowImageFilter final : public ImageFilter {
public:
    static sk_sp<DropShadowImageFilter> Make();
    enum class Mode { kShadowAndForeground, kShadowOnly };

    SG_ATTRIBUTE(Offset, SkVector, fOffset)
    SG_ATTRIBUTE(Sigma, SkVector, fSigma)
    SG_ATTRIBUTE(Color, SkColor, fColor)
    SG_ATTRIBUTE(Mode, Mode, fMode)

protected:
    sk_sp<SkImageFilter> onRevalidateFilter() override;

private:
    SkVector fOffset = {0, 0};  // 阴影偏移
    SkVector fSigma = {0, 0};   // 模糊半径
    SkColor fColor = SK_ColorBLACK;
    Mode fMode = Mode::kShadowAndForeground;
};
```

### BlurImageFilter

模糊滤镜实现：

```cpp
class BlurImageFilter final : public ImageFilter {
public:
    static sk_sp<BlurImageFilter> Make();

    SG_ATTRIBUTE(Sigma, SkVector, fSigma)
    SG_ATTRIBUTE(TileMode, SkTileMode, fTileMode)

protected:
    sk_sp<SkImageFilter> onRevalidateFilter() override;

private:
    SkVector fSigma = {0, 0};            // 模糊半径
    SkTileMode fTileMode = SkTileMode::kDecal;
};
```

### ImageFilterEffect

将图像滤镜附加到渲染节点：

```cpp
class ImageFilterEffect final : public EffectNode {
public:
    static sk_sp<RenderNode> Make(sk_sp<RenderNode> child, sk_sp<ImageFilter> filter);
    enum class Cropping { kNone, kContent };
    SG_ATTRIBUTE(Cropping, Cropping, fCropping)

protected:
    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    sk_sp<ImageFilter> fImageFilter;
    Cropping fCropping = Cropping::kNone;
};
```

**关键特性**：
- 使用 `kOverrideDamage_Trait` 覆盖后代损坏
- 支持内容裁剪和无裁剪两种模式

### BlenderEffect

应用自定义混合器：

```cpp
class BlenderEffect final : public EffectNode {
public:
    static sk_sp<BlenderEffect> Make(sk_sp<RenderNode> child, sk_sp<SkBlender> = nullptr);
    SG_ATTRIBUTE(Blender, sk_sp<SkBlender>, fBlender)

protected:
    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;

private:
    sk_sp<SkBlender> fBlender;
};
```

### LayerEffect

创建独立图层并应用混合模式：

```cpp
class LayerEffect final : public EffectNode {
public:
    static sk_sp<LayerEffect> Make(sk_sp<RenderNode> child, SkBlendMode mode = SkBlendMode::kSrcOver);
    SG_ATTRIBUTE(Mode, SkBlendMode, fMode)

protected:
    void onRender(SkCanvas*, const RenderContext*) const override;

private:
    SkBlendMode fMode;
};
```

## 公共 API 函数

### Shader::getShader()

```cpp
const sk_sp<SkShader>& getShader() const;
```

获取缓存的 Skia 着色器对象。要求节点已经过验证（断言检查 `!this->hasInval()`）。

### MaskShaderEffect::Make()

```cpp
static sk_sp<MaskShaderEffect> Make(sk_sp<RenderNode> child, sk_sp<SkShader> sh = nullptr);
```

创建遮罩着色器效果。如果 `child` 为空，返回 `nullptr`。

**使用示例**：
```cpp
auto mask_shader = SkShader::MakeFractalNoise(...);
auto masked_content = MaskShaderEffect::Make(content_node, mask_shader);
```

### ShaderEffect::Make()

```cpp
static sk_sp<ShaderEffect> Make(sk_sp<RenderNode> child, sk_sp<Shader> shader = nullptr);
```

创建着色器效果节点，将 Scene Graph Shader 附加到渲染树。

### ImageFilterEffect::Make()

```cpp
static sk_sp<RenderNode> Make(sk_sp<RenderNode> child, sk_sp<ImageFilter> filter);
```

创建图像滤镜效果。如果 `filter` 为空，直接返回 `child` 节点（优化）。

### DropShadowImageFilter::Make()

```cpp
static sk_sp<DropShadowImageFilter> Make();
```

创建投影滤镜节点。需要通过 setter 方法配置参数：

```cpp
auto shadow = DropShadowImageFilter::Make();
shadow->setOffset({5, 5});
shadow->setSigma({3, 3});
shadow->setColor(SK_ColorBLACK);
shadow->setMode(Mode::kShadowOnly);
```

### BlurImageFilter::Make()

```cpp
static sk_sp<BlurImageFilter> Make();
```

创建模糊滤镜节点。

### BlenderEffect::Make()

```cpp
static sk_sp<BlenderEffect> Make(sk_sp<RenderNode> child, sk_sp<SkBlender> blender = nullptr);
```

创建混合效果节点。

### LayerEffect::Make()

```cpp
static sk_sp<LayerEffect> Make(sk_sp<RenderNode> child, SkBlendMode mode = SkBlendMode::kSrcOver);
```

创建图层效果节点，自动处理图层隔离。

## 内部实现细节

### Shader 验证流程

```cpp
SkRect Shader::onRevalidate(InvalidationController*, const SkMatrix&) {
    SkASSERT(this->hasInval());
    fShader = this->onRevalidateShader();  // 调用子类钩子生成着色器
    return SkRect::MakeEmpty();  // 着色器不占用空间
}
```

### MaskShaderEffect 渲染

```cpp
void MaskShaderEffect::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    const auto local_ctx = ScopedRenderContext(canvas, ctx)
            .modulateMaskShader(fShader, canvas->getTotalMatrix());
    this->INHERITED::onRender(canvas, local_ctx);
}
```

**关键点**：
- 使用 `ScopedRenderContext` 管理渲染上下文生命周期
- `modulateMaskShader()` 将遮罩着色器应用到绘制操作
- 传入当前变换矩阵以正确映射着色器坐标

### ShaderEffect 观察者管理

```cpp
ShaderEffect::ShaderEffect(sk_sp<Shader> shader) : fShader(std::move(shader)) {
    if (fShader) {
        this->observeInval(fShader);  // 注册为观察者
    }
}

ShaderEffect::~ShaderEffect() {
    if (fShader) {
        this->unobserveInval(fShader);  // 注销观察者
    }
}

void ShaderEffect::setShader(sk_sp<Shader> sh) {
    if (fShader) {
        this->unobserveInval(fShader);
    }
    fShader = std::move(sh);
    if (fShader) {
        this->observeInval(fShader);
    }
}
```

动态更换着色器时需要正确管理观察者关系。

### ImageFilterEffect 边界计算

```cpp
SkRect ImageFilterEffect::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    const auto content_bounds = this->INHERITED::onRevalidate(ic, ctm);

    // 根据裁剪模式设置滤镜裁剪区域
    if (fCropping == Cropping::kContent) {
        fImageFilter->setCropRect(content_bounds);
    } else {
        fImageFilter->setCropRect(std::nullopt);
    }

    fImageFilter->revalidate(ic, ctm);
    const auto& filter = fImageFilter->getFilter();

    // 计算滤镜影响后的边界
    return filter ? filter->computeFastBounds(content_bounds) : content_bounds;
}
```

**边界扩展逻辑**：
- 滤镜可能扩大渲染区域（如模糊、阴影）
- 使用 `computeFastBounds()` 快速估算扩展后的边界
- 用于优化裁剪和脏区管理

### DropShadowImageFilter 滤镜生成

```cpp
sk_sp<SkImageFilter> DropShadowImageFilter::onRevalidateFilter() {
    if (fMode == Mode::kShadowOnly) {
        return SkImageFilters::DropShadowOnly(
            fOffset.x(), fOffset.y(),
            fSigma.x(), fSigma.y(),
            fColor, nullptr, this->getCropRect());
    } else {
        return SkImageFilters::DropShadow(
            fOffset.x(), fOffset.y(),
            fSigma.x(), fSigma.y(),
            fColor, nullptr, this->getCropRect());
    }
}
```

**两种模式**：
- `kShadowAndForeground`：绘制阴影和原图
- `kShadowOnly`：仅绘制阴影

### BlurImageFilter 滤镜生成

```cpp
sk_sp<SkImageFilter> BlurImageFilter::onRevalidateFilter() {
    // Tile modes other than kDecal require an explicit crop rect.
    SkASSERT(fTileMode == SkTileMode::kDecal || this->getCropRect().has_value());
    return SkImageFilters::Blur(fSigma.x(), fSigma.y(), fTileMode, nullptr, this->getCropRect());
}
```

**平铺模式处理**：
- `kDecal` 模式：边缘透明，无需裁剪矩形
- 其他模式：必须提供裁剪矩形以定义平铺边界

### ImageFilterEffect 渲染隔离

```cpp
void ImageFilterEffect::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    const auto filter_ctx = ScopedRenderContext(canvas, ctx)
        .setFilterIsolation(this->getChild()->bounds(),
                           canvas->getTotalMatrix(),
                           fImageFilter->getFilter());
    this->INHERITED::onRender(canvas, filter_ctx);
}
```

**隔离策略**：
- 使用子节点的边界作为 `saveLayer` 区域（优化）
- 将滤镜应用到独立图层
- 避免滤镜影响到非后代节点

### LayerEffect 渲染实现

```cpp
void LayerEffect::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    SkAutoCanvasRestore acr(canvas, false);

    // 提交任何挂起的绘制效果到独立图层
    const auto local_ctx = ScopedRenderContext(canvas, ctx)
        .setIsolation(this->bounds(), canvas->getTotalMatrix(), true);

    SkPaint layer_paint;
    if (ctx) {
        ctx->modulatePaint(canvas->getTotalMatrix(), &layer_paint);
    }
    layer_paint.setBlendMode(fMode);

    canvas->saveLayer(nullptr, &layer_paint);
    this->INHERITED::onRender(canvas, nullptr);  // 清除上下文，强制隔离
}
```

**关键设计**：
- 使用 `saveLayer` 创建独立图层
- 混合模式应用到图层整体而非单个绘制操作
- 传递 `nullptr` 作为子节点的上下文，确保完全隔离

## 依赖关系

### 头文件依赖

```cpp
#include "include/core/SkBlender.h"          // 混合器
#include "include/core/SkCanvas.h"           // 画布
#include "include/core/SkPaint.h"            // 绘制属性
#include "include/core/SkShader.h"           // 着色器
#include "include/core/SkTileMode.h"         // 平铺模式
#include "include/effects/SkImageFilters.h"  // 图像滤镜工厂
#include "modules/sksg/include/SkSGRenderNode.h"       // 渲染节点
#include "modules/sksg/include/SkSGRenderEffect.h"    // 本文件头文件
```

### 依赖链

```
Skia 核心效果 (include/effects)
    ├── SkImageFilters (滤镜工厂)
    └── SkBlender (混合器)
         ↓
Scene Graph 基础 (modules/sksg)
    ├── Node (节点基类)
    ├── EffectNode (效果节点基类)
    └── RenderNode (渲染节点基类)
         ↓
SkSGRenderEffect (当前文件)
    ├── Shader 系统
    ├── ImageFilter 系统
    └── Blend/Layer 系统
         ↓
上层应用 (Skottie)
```

## 设计模式与设计决策

### 模板方法模式

基类定义验证流程，子类实现具体生成：

```cpp
// 基类模板方法
SkRect Shader::onRevalidate(...) {
    fShader = this->onRevalidateShader();  // 调用子类钩子
    return SkRect::MakeEmpty();
}

// 子类实现具体逻辑
class LinearGradientShader : public Shader {
    sk_sp<SkShader> onRevalidateShader() override {
        return SkGradientShader::MakeLinear(...);
    }
};
```

### 装饰器模式

效果节点装饰渲染节点，添加视觉效果：

```cpp
auto content = DrawNode::Make(...);
auto blurred = ImageFilterEffect::Make(content, blur_filter);
auto shadowed = ImageFilterEffect::Make(blurred, shadow_filter);
```

### 空对象模式优化

```cpp
static sk_sp<RenderNode> Make(sk_sp<RenderNode> child, sk_sp<ImageFilter> filter) {
    return filter ? sk_sp<RenderNode>(new ImageFilterEffect(std::move(child), std::move(filter)))
                  : child;  // 无滤镜时直接返回子节点
}
```

避免创建无效的包装节点。

### Scoped Context 模式

使用 RAII 管理渲染上下文：

```cpp
void onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    const auto local_ctx = ScopedRenderContext(canvas, ctx)
            .modulateShader(fShader, canvas->getTotalMatrix());
    // local_ctx 在作用域结束时自动恢复
    this->INHERITED::onRender(canvas, local_ctx);
}
```

确保上下文修改不泄漏到外部。

### 损坏覆盖策略

```cpp
ImageFilterEffect::ImageFilterEffect(...)
    : INHERITED(std::move(child), kOverrideDamage_Trait) { }
```

**理由**：图像滤镜改变整个渲染结果，必须覆盖后代的损坏区域，重新计算影响范围。

## 性能考量

### 着色器缓存

```cpp
private:
    sk_sp<SkShader> fShader;  // 缓存生成的着色器
```

避免每帧重新创建 `SkShader` 对象，减少内存分配和对象构造开销。

### 快速边界计算

```cpp
return filter->computeFastBounds(content_bounds);
```

使用快速边界估算而非精确计算，平衡精度和性能。

### 条件滤镜应用

```cpp
return filter ? sk_sp<RenderNode>(new ImageFilterEffect(...)) : child;
```

无滤镜时避免创建额外的节点层次，减少遍历开销。

### saveLayer 区域优化

```cpp
.setFilterIsolation(this->getChild()->bounds(), ...);
```

使用子节点的实际边界作为 `saveLayer` 区域，而非整个画布，减少离屏渲染的纹理大小。

### Tile Mode 断言

```cpp
SkASSERT(fTileMode == SkTileMode::kDecal || this->getCropRect().has_value());
```

在调试模式下验证配置正确性，避免运行时错误和性能陷阱。

## 相关文件

### 头文件

- **modules/sksg/include/SkSGRenderEffect.h** - 本文件的公共接口声明
- **modules/sksg/include/SkSGEffectNode.h** - 效果节点基类定义
- **modules/sksg/include/SkSGNode.h** - 所有节点的基类

### 实现文件

- **modules/sksg/src/SkSGColorFilter.cpp** - 颜色滤镜效果实现
- **modules/sksg/src/SkSGMaskEffect.cpp** - 遮罩效果实现
- **modules/sksg/src/SkSGOpacityEffect.cpp** - 不透明度效果实现
- **modules/sksg/src/SkSGGradient.cpp** - 渐变着色器实现

### 核心依赖

- **include/core/SkShader.h** - Skia 着色器接口
- **include/core/SkImageFilter.h** - Skia 图像滤镜接口
- **include/effects/SkImageFilters.h** - 滤镜工厂函数
- **include/core/SkBlender.h** - Skia 混合器接口

### 使用者

- **modules/skottie/src/Skottie.cpp** - Lottie 动画系统使用各种效果
- **modules/sksg/src/SkSGRenderNode.cpp** - 渲染节点协调效果应用
- **tests/SkSGTest.cpp** - 单元测试验证效果正确性
