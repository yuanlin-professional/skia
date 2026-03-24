# skottie - Lottie 动画播放器模块

## 概述

Skottie 是 Skia 图形库中的 Lottie 动画播放器模块,负责解析和渲染由 Adobe After Effects (AE) 通过 Bodymovin 插件导出的 JSON 动画格式。该模块自 2017 年起由 Google 开发和维护,是 Skia 生态系统中最复杂、功能最丰富的模块之一。

Skottie 的核心职责是将 Lottie JSON 描述文件转换为 Skia 场景图 (Scene Graph, 即 `sksg` 模块),并通过关键帧动画系统驱动场景图节点的属性变化,从而实现流畅的矢量动画渲染。它支持 Lottie 规范中的绝大多数特性,包括形状图层、预合成图层、文本图层、图像图层、遮罩、混合模式以及丰富的 After Effects 特效。

该模块被广泛应用于 Android (通过 Skia 后端)、Chrome、Flutter 以及其他基于 Skia 的平台。Skottie 采用构建器模式 (Builder Pattern) 来创建动画实例,允许客户端自定义资源加载、字体管理、属性观察和表达式求值等行为。

Skottie 不仅仅是一个简单的 JSON 解析和渲染引擎,它还提供了强大的运行时属性操控能力。通过 `PropertyObserver` 和 `SlotManager` 接口,嵌入方可以在运行时动态修改动画中的颜色、不透明度、变换和文本属性,这对于需要动态内容的应用场景(如个性化动画模板)尤为重要。

此外,Skottie 支持 AE 表达式求值(`ExpressionManager`)、外部图层注入(`PrecompInterceptor` / `ExternalLayer`)和自定义文本渲染修饰(`GlyphDecorator`),使其具备高度的可扩展性和灵活性。

## 架构图

```
+------------------------------------------------------------------+
|                    Animation::Builder (入口)                       |
|   setResourceProvider / setFontManager / setPropertyObserver     |
|   setLogger / setMarkerObserver / setExpressionManager           |
|   setPrecompInterceptor / setTextShapingFactory                  |
+---------------------------+--------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|                  AnimationBuilder (内部核心)                       |
|                                                                  |
|   +-------------------+  +------------------+  +--------------+  |
|   | JSON 解析 (skjson)|  | 资源管理         |  | 字体解析     |  |
|   | ObjectValue       |  | ResourceProvider |  | FontInfo     |  |
|   | ArrayValue        |  | ImageAsset       |  | CustomFont   |  |
|   +-------------------+  +------------------+  +--------------+  |
|                                                                  |
|   +-------------------+  +------------------+  +--------------+  |
|   | 图层构建           |  | 效果构建         |  | 文本构建     |  |
|   | LayerBuilder      |  | EffectBuilder    |  | TextAdapter  |  |
|   | CompositionBuilder|  | 30+ 效果类型     |  | TextAnimator |  |
|   +-------------------+  +------------------+  +--------------+  |
|                                                                  |
+---------------------------+--------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|                  场景图 (sksg 模块)                                |
|                                                                  |
|   RenderNode -> Group -> Draw -> [GeometryNode + PaintNode]      |
|   TransformEffect / OpacityEffect / ClipEffect / MaskEffect      |
|   ColorFilter / ImageFilterEffect / BlenderEffect                |
+---------------------------+--------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|                  动画系统 (animator/)                              |
|                                                                  |
|   Animator -> AnimatablePropertyContainer                        |
|      -> KeyframeAnimator (Scalar/Vec2/Vector/Shape/Text)         |
|      -> 贝塞尔插值 (SkCubicMap)                                  |
|      -> LERPInfo { weight, vrec0, vrec1 }                        |
+------------------------------------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|                  Animation 实例                                   |
|   seekFrame(t) / seekFrameTime(t) -> 驱动所有 Animator           |
|   render(canvas, dst, flags) -> 渲染场景图到 SkCanvas            |
+------------------------------------------------------------------+
```

## 目录结构

```
modules/skottie/
├── BUILD.gn                     # GN 构建配置
├── BUILD.bazel                  # Bazel 构建配置
├── skottie.gni                  # GN 导入配置
├── include/                     # 公开头文件
│   ├── Skottie.h                # 核心 API: Animation, Builder, Logger
│   ├── SkottieProperty.h        # 属性系统: PropertyObserver, PropertyHandle
│   ├── ExternalLayer.h          # 外部图层接口: ExternalLayer, PrecompInterceptor
│   ├── SlotManager.h            # 插槽管理: 运行时属性替换
│   └── TextShaper.h             # 文本排版: Shaper, VAlign, ResizePolicy
├── src/                         # 核心实现
│   ├── Skottie.cpp              # Animation 构建主流程
│   ├── SkottiePriv.h            # 内部核心: AnimationBuilder, SceneGraphRevalidator
│   ├── SkottieJson.h/cpp        # JSON 辅助工具
│   ├── SkottieValue.h           # 值类型定义: ScalarValue, Vec2Value, ColorValue
│   ├── SkottieProperty.cpp      # 属性绑定实现
│   ├── SkottieTest.cpp          # 内部测试
│   ├── Layer.h/cpp              # LayerBuilder: 图层构建
│   ├── Composition.h/cpp        # CompositionBuilder: 合成构建
│   ├── Camera.h/cpp             # 3D 相机支持
│   ├── Transform.h/cpp          # 变换适配器 (2D/3D)
│   ├── Adapter.h                # 适配器基类
│   ├── BlendModes.cpp           # 混合模式映射
│   ├── Path.cpp                 # 路径动画
│   ├── SlotManager.cpp          # 插槽管理实现
│   ├── animator/                # 动画系统
│   ├── layers/                  # 图层类型
│   ├── text/                    # 文本系统
│   └── effects/                 # 特效系统
├── utils/                       # 工具类
│   ├── SkottieUtils.h/cpp       # CustomPropertyManager, ExternalAnimationPrecompInterceptor
│   ├── TextEditor.h/cpp         # WYSIWYG 文本编辑器
│   ├── TextPreshape.h/cpp       # 文本预排版
│   └── PreshapeTool.cpp         # 预排版命令行工具
├── tests/                       # 单元测试
│   ├── Image.cpp                # 图像测试
│   ├── Text.cpp                 # 文本测试
│   ├── AudioLayer.cpp           # 音频图层测试
│   ├── PropertyObserver.cpp     # 属性观察器测试
│   ├── Keyframe.cpp             # 关键帧测试
│   ├── Shaper.cpp               # 文本排版测试
│   └── Expression.cpp           # 表达式测试
├── gm/                          # GPU 测试 (Ganesh/Graphite)
│   ├── SkottieGM.cpp            # Skottie GM 测试
│   └── ExternalProperties.cpp   # 外部属性 GM 测试
└── fuzz/                        # 模糊测试
    └── FuzzSkottieJSON.cpp      # JSON 模糊测试
```

## 关键类与函数

### 公开 API 层

| 类名 | 文件 | 描述 |
|------|------|------|
| `Animation` | `include/Skottie.h` | 动画实例,持有场景图根节点和动画器集合 |
| `Animation::Builder` | `include/Skottie.h` | 构建器,配置资源加载、字体、日志等 |
| `Logger` | `include/Skottie.h` | 日志接收器,报告解析警告和错误 |
| `ExpressionManager` | `include/Skottie.h` | AE 表达式求值管理器 |
| `ExpressionEvaluator<T>` | `include/Skottie.h` | 表达式求值器模板 |
| `MarkerObserver` | `include/Skottie.h` | AE 合成标记接收器 |
| `PropertyObserver` | `include/SkottieProperty.h` | 属性回调观察器 |
| `PropertyHandle<V,N>` | `include/SkottieProperty.h` | 属性操控句柄 |
| `GlyphDecorator` | `include/SkottieProperty.h` | 文本字形修饰回调 |
| `ExternalLayer` | `include/ExternalLayer.h` | 外部渲染图层接口 |
| `PrecompInterceptor` | `include/ExternalLayer.h` | 预合成图层拦截器 |
| `SlotManager` | `include/SlotManager.h` | 运行时插槽值管理 |
| `Shaper` | `include/TextShaper.h` | 文本排版引擎 (AE 语义) |

### 内部实现层

| 类名 | 文件 | 描述 |
|------|------|------|
| `AnimationBuilder` | `src/SkottiePriv.h` | 核心构建器,解析JSON并构建场景图和动画器 |
| `SceneGraphRevalidator` | `src/SkottiePriv.h` | 场景图重新验证触发器 |
| `LayerBuilder` | `src/Layer.h` | 单个图层的构建和变换链管理 |
| `CompositionBuilder` | `src/Composition.h` | 合成构建,管理图层集合和相机 |
| `Animator` | `src/animator/Animator.h` | 动画器基类,`seek(t)` 驱动状态更新 |
| `AnimatablePropertyContainer` | `src/animator/Animator.h` | 可动画属性容器,`bind()` 绑定关键帧 |
| `KeyframeAnimator` | `src/animator/KeyframeAnimator.h` | 关键帧动画器,支持常量/线性/贝塞尔插值 |
| `TextAdapter` | `src/text/TextAdapter.h` | 文本图层适配器,处理文本排版和动画 |
| `TextAnimator` | `src/text/TextAnimator.h` | 文本动画器,处理逐字符/逐词/逐行动画 |
| `RangeSelector` | `src/text/RangeSelector.h` | 范围选择器,控制文本动画覆盖范围 |
| `EffectBuilder` | `src/effects/Effects.h` | 特效构建器,分发30+种 AE 特效 |
| `ShapeBuilder` | `src/layers/shapelayer/ShapeLayer.h` | 形状图层构建器 |
| `CustomFont` | `src/text/Font.h` | 自定义字体,支持字形路径和字形合成 |

### 关键函数

```cpp
// 创建动画 (简单方式)
sk_sp<Animation> Animation::Make(const char* data, size_t length);
sk_sp<Animation> Animation::MakeFromFile(const char path[]);

// 创建动画 (构建器方式,推荐)
Animation::Builder builder;
builder.setResourceProvider(rp)
       .setFontManager(fm)
       .setPropertyObserver(po);
auto animation = builder.make(stream);

// 播放控制
animation->seekFrame(30.0);           // 跳转到第30帧
animation->seekFrameTime(1.5);        // 跳转到1.5秒
animation->render(canvas, &dstRect);  // 渲染到画布

// 属性操控 (通过 SlotManager)
auto slotMgr = builder.getSlotManager();
slotMgr->setColorSlot("primaryColor", SK_ColorRED);
slotMgr->setTextSlot("title", textValue);

// 属性操控 (通过 PropertyObserver)
class MyObserver : public PropertyObserver {
    void onColorProperty(const char name[],
                         const LazyHandle<ColorPropertyHandle>& handle) override {
        auto h = handle();
        h->set(SK_ColorBLUE);
    }
};
```

## 依赖关系

```
skottie 模块依赖图:

skottie
  ├── sksg (场景图)             // 核心渲染树
  ├── skresources              // 资源加载框架
  ├── skshaper                 // 文本排版 (HarfBuzz)
  ├── skunicode                // Unicode 处理
  ├── skjson (jsonreader)      // JSON DOM 解析
  ├── include/core/            // Skia 核心: SkCanvas, SkPaint, SkPath 等
  ├── include/effects/         // Skia 效果: SkImageFilters, SkTrimPathEffect 等
  └── include/utils/           // Skia 工具: SkTextUtils, SkCustomTypeface
```

**模块间关系说明:**

- **sksg**: Skottie 将 Lottie JSON 转换为 sksg 场景图节点。所有的渲染最终通过 sksg 节点完成
- **skresources**: 提供 `ResourceProvider` 和 `ImageAsset` 接口,用于外部资源(图像、字体文件)的加载
- **skshaper**: 通过 `SkShapers::Factory` 提供高级文本排版能力 (依赖 HarfBuzz)
- **skunicode**: 提供 Unicode 文本处理,用于换行策略和文本方向判断
- **skjson/jsonreader**: 高性能 JSON 解析器,构建 DOM 树用于属性访问

## 设计模式分析

### 1. 构建器模式 (Builder Pattern)
`Animation::Builder` 类使用构建器模式,允许链式配置:
```cpp
auto animation = Animation::Builder()
    .setResourceProvider(rp)
    .setFontManager(fm)
    .setLogger(logger)
    .make(stream);
```

### 2. 观察者模式 (Observer Pattern)
`PropertyObserver` 在构建阶段接收属性发现回调,`MarkerObserver` 接收标记事件:
```cpp
class MyObserver : public PropertyObserver {
    void onColorProperty(const char name[],
                         const LazyHandle<ColorPropertyHandle>&) override;
    void onEnterNode(const char name[], NodeType) override;
    void onLeavingNode(const char name[], NodeType) override;
};
```

### 3. 适配器模式 (Adapter Pattern)
`AnimatablePropertyContainer` 及其派生类(如 `TextAdapter`、`TransformAdapter2D`)将 Lottie JSON 属性适配为 sksg 场景图节点属性。`PropertyHandle<V,N>` 则将内部节点类型适配为公开的值类型。

### 4. 组合模式 (Composite Pattern)
- `CompositionBuilder` 包含多个 `LayerBuilder`
- 场景图本身是组合模式: `Group` 包含多个 `RenderNode`

### 5. 策略模式 (Strategy Pattern)
- `EffectBuilder` 通过函数指针表 (`EffectBuilderT`) 分发不同的效果构建策略
- `Shaper` 中的 `VAlign`、`ResizePolicy`、`LinebreakPolicy` 等枚举控制文本排版策略

### 6. 作用域守卫 (RAII / Scope Guard)
- `AutoScope`: 管理动画器作用域栈,确保动画器正确归属
- `AutoPropertyTracker`: 管理属性观察器的节点进入/离开回调
- `ScopedAssetRef`: 管理资源引用,用于循环依赖检测

### 7. 模板方法模式 (Template Method)
- `Animator::onSeek()` 是模板方法,由 `AnimatablePropertyContainer` 和 `KeyframeAnimator` 实现
- `KeyframeAnimator` 派生类 (ScalarKeyframeAnimator 等) 实现具体的插值逻辑

## 数据流

### 构建阶段数据流

```
Lottie JSON 字符串
        |
        v
[JSON 解析] skjson::ObjectValue DOM 树
        |
        v
[AnimationBuilder::parse()]
        |
        +---> [parseAssets()] -----> fAssets (资产映射表)
        |
        +---> [parseFonts()] -----> fFonts (字体映射表)
        |
        +---> [CompositionBuilder] --+
        |                            |
        |     对每个图层:            |
        |     +---> [LayerBuilder::buildTransform()]
        |     |       构建变换链 (2D/3D), 处理父子关系
        |     |
        |     +---> [LayerBuilder::buildRenderTree()]
        |     |       |
        |     |       +---> attachShapeLayer()   -> ShapeBuilder
        |     |       +---> attachTextLayer()    -> TextAdapter
        |     |       +---> attachFootageLayer() -> ImageAsset
        |     |       +---> attachPrecompLayer() -> 递归 CompositionBuilder
        |     |       +---> attachSolidLayer()   -> 纯色矩形
        |     |       +---> attachNullLayer()    -> 空节点
        |     |       +---> attachAudioLayer()   -> 音频事件
        |     |       |
        |     |       +---> [EffectBuilder::attachEffects()]
        |     |       +---> [attachOpacity()]
        |     |       +---> [attachBlendMode()]
        |     |
        |     +---> 最终: sk_sp<sksg::RenderNode> 场景图根节点
        |
        v
Animation 实例 { fSceneRoot, fAnimators[], fDuration, fFPS, ... }
```

### 播放阶段数据流

```
seekFrame(frame) / seekFrameTime(time)
        |
        v
将时间转换为帧时间 t
        |
        v
遍历所有 fAnimators:
    Animator::seek(t)
        |
        +---> AnimatablePropertyContainer::onSeek(t)
        |       |
        |       +---> 遍历子 KeyframeAnimator
        |       |       |
        |       |       +---> find_segment(t) 定位关键帧区间
        |       |       +---> compute_weight() 计算插值权重
        |       |       +---> getLERPInfo() 返回 {weight, vrec0, vrec1}
        |       |       +---> 派生类实现具体插值 (Scalar/Vec2/Vector/Shape/Text)
        |       |
        |       +---> onSync() 将插值结果推送到 sksg 节点
        |               - 更新 sksg::Color 颜色
        |               - 更新 sksg::Transform 变换矩阵
        |               - 更新 sksg::Path 路径
        |               - 更新 sksg::OpacityEffect 不透明度
        |               - 触发 node->invalidate()
        |
        v
(可选) InvalidationController 跟踪脏区域
```

### 渲染阶段数据流

```
render(SkCanvas*, dstRect, flags)
        |
        v
fSceneRoot->revalidate(ic, ctm)
    遍历场景图 DAG:
        - 每个节点调用 onRevalidate() 重新计算边界
        - 向上冒泡失效信息
        |
        v
fSceneRoot->render(canvas, renderContext)
    遍历场景图 DAG:
        - Group: 遍历子节点
        - TransformEffect: 应用变换矩阵
        - OpacityEffect: 调制不透明度
        - ClipEffect: 应用裁剪
        - MaskEffect: 应用遮罩
        - Draw: 使用 GeometryNode + PaintNode 绘制
        - ImageFilterEffect: 应用图像滤镜
```

## 支持的 Lottie 特性

### 图层类型
| 类型 | 实现文件 | 说明 |
|------|---------|------|
| 预合成 (Precomp) | `src/layers/PrecompLayer.cpp` | 嵌套合成,支持时间重映射 |
| 纯色 (Solid) | `src/layers/SolidLayer.cpp` | 纯色填充矩形 |
| 图像 (Footage) | `src/layers/FootageLayer.cpp` | 外部图像资源 |
| 空 (Null) | `src/layers/NullLayer.cpp` | 控制点/父级 |
| 形状 (Shape) | `src/layers/shapelayer/ShapeLayer.cpp` | 矢量形状 |
| 文本 (Text) | `src/layers/TextLayer.cpp` | 文本渲染 |
| 音频 (Audio) | `src/layers/AudioLayer.cpp` | 音频事件 |

### 形状类型
| 形状 | 实现文件 |
|------|---------|
| 矩形 | `src/layers/shapelayer/Rectangle.cpp` |
| 椭圆 | `src/layers/shapelayer/Ellipse.cpp` |
| 多角星/多边形 | `src/layers/shapelayer/Polystar.cpp` |
| 填充/描边 | `src/layers/shapelayer/FillStroke.cpp` |
| 渐变 | `src/layers/shapelayer/Gradient.cpp` |
| 路径合并 | `src/layers/shapelayer/MergePaths.cpp` |
| 路径裁剪 | `src/layers/shapelayer/TrimPaths.cpp` |
| 圆角 | `src/layers/shapelayer/RoundCorners.cpp` |
| 重复器 | `src/layers/shapelayer/Repeater.cpp` |
| 膨胀/收缩 | `src/layers/shapelayer/PuckerBloat.cpp` |
| 路径偏移 | `src/layers/shapelayer/OffsetPaths.cpp` |

### 特效类型 (30+)
模糊 / 投影 / 色调 / 三色调 / 亮度对比度 / 色相饱和度 / 色阶 / 反转 / 填充 / 渐变 / CC Toner / 通道偏移 / 动态瓦片 / 分形噪点 / 线性擦除 / 径向擦除 / 百叶窗 / 角落钉 / 变换 / 锐化 / 置换贴图 / 球面 / 膨胀 / 阈值 / SkSL 自定义着色器 / 发光 / 阴影样式 等。

## 相关文档与参考

- **Lottie 官方文档**: [lottiefiles.com](https://lottiefiles.com/)
- **Lottie JSON 规范**: [lottie-animation-community](https://github.com/nicedoc/lottie-docs)
- **Skia 官方文档**: [skia.org](https://skia.org/)
- **sksg 模块文档**: `docs/yuanlin/modules/sksg/README.md`
- **skresources 模块**: `modules/skresources/` - 资源加载框架
- **skshaper 模块**: `modules/skshaper/` - 文本排版引擎
- **Bodymovin 插件**: AE 导出 Lottie JSON 的工具
- **After Effects 表达式**: Skottie 通过 `ExpressionManager` 支持 AE 表达式
