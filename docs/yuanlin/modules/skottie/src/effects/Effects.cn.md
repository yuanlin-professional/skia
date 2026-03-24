# Effects - Skottie 特效系统

> 源文件: [`modules/skottie/src/effects/Effects.h`](../../../../modules/skottie/src/effects/Effects.h), [`modules/skottie/src/effects/Effects.cpp`](../../../../modules/skottie/src/effects/Effects.cpp)

## 概述

Effects 模块实现了 Skottie 的图层特效系统，支持超过 25 种 After Effects 特效（模糊、阴影、色调、色相饱和度、渐变、变形等）以及图层样式（投影、内阴影、外发光、内发光）。EffectBuilder 是特效系统的入口，负责根据 JSON 中的特效类型派发到对应的构建函数。

## 架构位置

位于 Skottie 内部实现层的特效子系统：

- **调用者**: LayerBuilder::buildRenderTree（附加特效到图层渲染树）
- **输入**: JSON 特效/样式数组 + 图层渲染节点
- **输出**: 包装了特效的 sksg::RenderNode

## 主要类与结构体

### `EffectBuilder` 类
特效构建器，根据特效名称派发到对应构建函数。

```cpp
class EffectBuilder final : SkNoncopyable {
public:
    EffectBuilder(const AnimationBuilder*, const SkSize&, CompositionBuilder*);
    sk_sp<sksg::RenderNode> attachEffects(const ArrayValue&, sk_sp<sksg::RenderNode>) const;
    sk_sp<sksg::RenderNode> attachStyles(const ArrayValue&, sk_sp<sksg::RenderNode>) const;
    static const Value& GetPropValue(const ArrayValue& jprops, size_t prop_index);
};
```

### `EffectBinder` 辅助类
语法糖，简化特效属性的绑定：
```cpp
EffectBinder(jprops, abuilder, acontainer)
    .bind(0, prop0)
    .bind(1, prop1);
```

### `MaskShaderEffectBase` 基类
遮罩着色器特效的抽象基类，派生类实现 `onMakeMask()` 返回遮罩着色器。

### `LayerContent` 结构体
图层内容引用，用于位移映射等跨图层特效。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `attachEffects(jeffects, layer)` | 遍历特效数组，逐个附加到图层 |
| `attachStyles(jstyles, layer)` | 遍历样式数组，逐个附加到图层 |
| `GetPropValue(jprops, index)` | 按索引获取特效属性值 |
| `getLayerContent(layer_index)` | 获取指定图层的内容（跨图层特效用） |

## 内部实现细节

### 特效派发机制
`findBuilder()` 使用两级查找：
1. **名称匹配**（主路径）：按字母序排列的 `gBuilderInfo[]` 数组，使用 `std::lower_bound` 二分查找 "mn" 字段
2. **类型回退**（兼容路径）：对缺少有效 "mn" 的旧式 JSON，根据 "ty" 数字类型匹配少量常用特效

### 支持的特效列表（29种）

| 特效名称 | 构建函数 |
|----------|----------|
| ADBE Black&White | attachBlackAndWhiteEffect |
| ADBE Brightness & Contrast 2 | attachBrightnessContrastEffect |
| ADBE Bulge | attachBulgeEffect |
| ADBE Corner Pin | attachCornerPinEffect |
| ADBE Displacement Map | attachDisplacementMapEffect |
| ADBE Drop Shadow | attachDropShadowEffect |
| ADBE Fill | attachFillEffect |
| ADBE Fractal Noise | attachFractalNoiseEffect |
| ADBE Gaussian Blur 2 | attachGaussianBlurEffect |
| ADBE HUE SATURATION | attachHueSaturationEffect |
| ADBE Invert | attachInvertEffect |
| ADBE Linear Wipe | attachLinearWipeEffect |
| ADBE Motion Blur | attachDirectionalBlurEffect |
| ADBE Ramp | attachGradientEffect |
| ADBE Sharpen | attachSharpenEffect |
| CC Sphere | attachSphereEffect |
| SkSL Color Filter / Shader | 自定义 SkSL 特效 |
| ... | （共 29 种） |

### 支持的样式
- 类型 1: 投影 (Drop Shadow)
- 类型 2: 内阴影 (Inner Shadow)
- 类型 3: 外发光 (Outer Glow)
- 类型 4: 内发光 (Inner Glow)

### 特效链式应用
`attachEffects` 对特效数组进行线性遍历，每个特效包装前一个结果，形成链式处理管道。

## 依赖关系

- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder
- `modules/skottie/src/Composition.h` - CompositionBuilder（跨图层引用）
- `modules/skottie/src/Layer.h` - LayerBuilder（获取图层内容）
- `modules/sksg/include/SkSGRenderEffect.h` - 场景图特效节点
- `modules/skottie/src/animator/Animator.h` - AnimatablePropertyContainer

## 设计模式与设计决策

### 工厂方法模式
每个特效类型对应一个独立的 attach 方法，通过函数指针表实现派发。

### 二分查找优化
特效名称表按字母序排列，使用 lower_bound 实现 O(log n) 查找。

### 条件编译
样式功能可通过 `SKOTTIE_DISABLE_STYLES` 宏禁用，用于减小二进制大小。

### EffectBinder 辅助
简化了特效属性的索引式绑定，避免重复的 GetPropValue + bind 调用。

## 性能考量

- 二分查找特效名称，避免线性扫描
- 特效按需应用，跳过 null 或无效条目
- MaskShaderEffectBase 在 onSync 时仅在可见时更新着色器

## 相关文件

- `modules/skottie/src/effects/` 目录下的各特效实现文件
- `modules/skottie/src/Layer.cpp` - 特效附加调用点
- `modules/sksg/include/SkSGRenderEffect.h` - 特效渲染节点
