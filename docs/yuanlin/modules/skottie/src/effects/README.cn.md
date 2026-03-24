# skottie/src/effects - 特效系统

## 概述

`effects/` 目录实现了 Skottie 对 After Effects 图层特效 (Layer Effects) 和图层样式 (Layer Styles) 的支持。该目录包含 30 多种特效的具体实现,涵盖颜色校正、模糊、扭曲、过渡和自定义着色器等类别。所有特效通过 `EffectBuilder` 类统一调度和构建。

特效系统的设计核心是将 AE 的特效参数 (通过 `EffectBinder` 绑定到动画属性) 转换为 sksg 渲染节点上的视觉效果,通常使用 `SkImageFilter`、`SkColorFilter`、`SkShader` 或自定义 SkSL 着色器来实现。

## 目录结构

```
effects/
├── BUILD.bazel                    # Bazel 构建配置
├── Effects.h                      # EffectBuilder, EffectBinder, MaskShaderEffectBase
├── Effects.cpp                    # 效果分发表和主逻辑
├── BrightnessContrastEffect.cpp   # 亮度对比度
├── BulgeEffect.cpp                # 膨胀扭曲
├── CCTonerEffect.cpp              # CC Toner 色调
├── CornerPinEffect.cpp            # 角落钉变形
├── DisplacementMapEffect.cpp      # 置换贴图
├── DropShadowEffect.cpp           # 投影
├── FillEffect.cpp                 # 颜色填充
├── FractalNoiseEffect.cpp         # 分形噪点
├── GaussianBlurEffect.cpp         # 高斯模糊
├── GlowStyles.cpp                 # 内/外发光样式
├── GradientEffect.cpp             # 渐变叠加
├── HueSaturationEffect.cpp        # 色相饱和度
├── InvertEffect.cpp               # 反转
├── LevelsEffect.cpp               # 色阶 (Easy/Pro)
├── LinearWipeEffect.cpp           # 线性擦除
├── MotionTileEffect.cpp           # 动态瓦片
├── RadialWipeEffect.cpp           # 径向擦除
├── ShadowStyles.cpp               # 投影/内阴影样式
├── SharpenEffect.cpp              # 锐化
├── ShiftChannelsEffect.cpp        # 通道偏移
├── SkSLEffect.cpp                 # SkSL 自定义着色器
├── SphereEffect.cpp               # 球面化
├── ThresholdEffect.cpp            # 阈值
├── TintEffect.cpp                 # 色调 (双色)
├── TransformEffect.cpp            # 变换效果
├── TritoneEffect.cpp              # 三色调
└── VenetianBlindsEffect.cpp       # 百叶窗
```

## 关键类与函数

### EffectBuilder - 特效构建器

```cpp
class EffectBuilder final : public SkNoncopyable {
    EffectBuilder(const AnimationBuilder*, const SkSize&, CompositionBuilder*);

    // 附加图层特效 (数组)
    sk_sp<sksg::RenderNode> attachEffects(const skjson::ArrayValue&,
                                          sk_sp<sksg::RenderNode>) const;

    // 附加图层样式
    sk_sp<sksg::RenderNode> attachStyles(const skjson::ArrayValue&,
                                         sk_sp<sksg::RenderNode>) const;

    // 获取指定索引的效果属性值
    static const skjson::Value& GetPropValue(jprops, prop_index);

    // 获取指定图层的内容 (用于置换贴图等跨图层效果)
    LayerContent getLayerContent(int layer_index) const;
};
```

### EffectBinder - 属性绑定辅助

```cpp
class EffectBinder {
    EffectBinder(jprops, abuilder, container);

    // 链式绑定效果属性
    template <typename T>
    const EffectBinder& bind(size_t prop_index, T& value) const;
};

// 使用示例:
EffectBinder(jprops, abuilder, this)
    .bind(0, fBlurriness)
    .bind(1, fDirection)
    .bind(2, fRepeatEdge);
```

### MaskShaderEffectBase - 遮罩着色器基类

```cpp
class MaskShaderEffectBase : public AnimatablePropertyContainer {
    const sk_sp<sksg::MaskShaderEffect>& node() const;

protected:
    struct MaskInfo {
        sk_sp<SkShader> fMaskShader;
        bool            fVisible;
    };
    virtual MaskInfo onMakeMask() const = 0;
};
```

多种擦除/过渡效果 (LinearWipe, RadialWipe, VenetianBlinds) 继承此基类。

### 特效分类

**颜色校正类:**
| 特效 | 文件 | 实现方式 |
|------|------|---------|
| 亮度对比度 | BrightnessContrastEffect.cpp | SkSL ColorFilter |
| 色相饱和度 | HueSaturationEffect.cpp | SkSL ColorFilter |
| 色调 | TintEffect.cpp | GradientColorFilter |
| 三色调 | TritoneEffect.cpp | GradientColorFilter |
| CC Toner | CCTonerEffect.cpp | GradientColorFilter |
| 色阶 | LevelsEffect.cpp | SkSL ColorFilter |
| 反转 | InvertEffect.cpp | ExternalColorFilter |
| 填充 | FillEffect.cpp | ModeColorFilter |
| 通道偏移 | ShiftChannelsEffect.cpp | SkSL ColorFilter |
| 阈值 | ThresholdEffect.cpp | SkSL ColorFilter |

**模糊/锐化类:**
| 特效 | 文件 | 实现方式 |
|------|------|---------|
| 高斯模糊 | GaussianBlurEffect.cpp | BlurImageFilter |
| 投影 | DropShadowEffect.cpp | DropShadowImageFilter |
| 锐化 | SharpenEffect.cpp | SkSL ColorFilter |

**扭曲/变形类:**
| 特效 | 文件 | 实现方式 |
|------|------|---------|
| 球面化 | SphereEffect.cpp | SkSL Shader |
| 膨胀 | BulgeEffect.cpp | SkSL Shader |
| 角落钉 | CornerPinEffect.cpp | Matrix Transform |
| 置换贴图 | DisplacementMapEffect.cpp | SkSL Shader |
| 变换 | TransformEffect.cpp | TransformEffect |

**过渡/擦除类:**
| 特效 | 文件 | 实现方式 |
|------|------|---------|
| 线性擦除 | LinearWipeEffect.cpp | MaskShaderEffect |
| 径向擦除 | RadialWipeEffect.cpp | MaskShaderEffect |
| 百叶窗 | VenetianBlindsEffect.cpp | MaskShaderEffect |

**生成类:**
| 特效 | 文件 | 实现方式 |
|------|------|---------|
| 分形噪点 | FractalNoiseEffect.cpp | SkSL Shader |
| 渐变 | GradientEffect.cpp | ShaderEffect |
| 动态瓦片 | MotionTileEffect.cpp | SkSL Shader |

**图层样式:**
| 样式 | 文件 | 实现方式 |
|------|------|---------|
| 投影样式 | ShadowStyles.cpp | DropShadowImageFilter |
| 内阴影 | ShadowStyles.cpp | 自定义 ImageFilter |
| 外发光 | GlowStyles.cpp | BlurImageFilter |
| 内发光 | GlowStyles.cpp | 自定义 ImageFilter |

**自定义着色器:**
| 特效 | 文件 | 说明 |
|------|------|------|
| SkSL ColorFilter | SkSLEffect.cpp | 通过 JSON 内嵌 SkSL 代码实现自定义颜色滤镜 |
| SkSL Shader | SkSLEffect.cpp | 通过 JSON 内嵌 SkSL 代码实现自定义着色器 |

## 数据流

```
图层 JSON -> "ef" (effects) 数组
    |
    v
EffectBuilder::attachEffects(jeffects, content_node)
    |
    遍历每个效果:
    +---> findBuilder(jeffect) 根据 "ty"/"nm" 查表
    |       -> EffectBuilderT 函数指针
    |
    +---> (this->*builder)(jprops, child)
    |       |
    |       v
    |     创建 AnimatablePropertyContainer 派生类
    |     通过 EffectBinder 绑定效果参数
    |     创建对应的 sksg 效果节点
    |     返回包装后的 sksg::RenderNode
    |
    +---> 链式包装: 每个效果包装前一个的结果
    |
    v
最终 sk_sp<sksg::RenderNode> (带完整效果链)
```

## 依赖关系

```
effects/
  ├── sksg (RenderEffect, ColorFilter, ImageFilter, Shader, MaskShaderEffect)
  ├── SkImageFilters (DropShadow, Blur)
  ├── SkColorFilter (Blend, Compose)
  ├── SkRuntimeEffect (SkSL 编译和执行)
  ├── animator/Animator.h (AnimatablePropertyContainer)
  └── Composition.h (getLayerContent 跨图层访问)
```

## 相关文档与参考

- **父目录**: `docs/yuanlin/modules/skottie/src/README.md`
- **sksg 渲染效果**: `modules/sksg/include/SkSGRenderEffect.h`
- **sksg 颜色滤镜**: `modules/sksg/include/SkSGColorFilter.h`
- **SkSL 文档**: Skia 着色器语言,用于自定义效果
