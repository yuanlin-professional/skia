# skottie/src - 核心实现

## 概述

`src/` 目录包含 Skottie 模块的核心实现代码。这里是 Lottie JSON 被解析、场景图被构建、动画系统被组装的地方。该目录定义了从 JSON 到渲染树的完整转换管线,是 Skottie 模块中代码量最大、逻辑最复杂的部分。

核心流程由 `AnimationBuilder` 类驱动:它接收 JSON DOM 对象,递归解析合成、图层、形状、文本、特效等元素,为每个可动画属性创建关键帧动画器,并将所有内容组装为一棵 sksg 场景图。最终输出的 `Animation` 对象持有场景图根节点和动画器集合,客户端通过 `seek/render` 方法驱动动画播放。

该目录还包含多个重要的子目录:`animator/`(动画系统)、`layers/`(图层类型)、`text/`(文本系统)和 `effects/`(特效系统),各自负责 Lottie 规范的不同方面。

## 架构图

```
+--------------------------------------------------------------+
|                    AnimationBuilder                           |
|                                                              |
|  parse(jsonRoot)                                             |
|    |                                                         |
|    +---> parseAssets()    -> fAssets 资产表                   |
|    +---> parseFonts()     -> fFonts 字体表                   |
|    +---> dispatchMarkers() -> MarkerObserver                 |
|    +---> CompositionBuilder::build()                         |
|           |                                                  |
|           +---> LayerBuilder[0..N]                           |
|           |      +---> buildTransform() -> sksg::Transform   |
|           |      +---> buildRenderTree()                     |
|           |      |      |                                    |
|           |      |      +---> attachShapeLayer()             |
|           |      |      +---> attachTextLayer()              |
|           |      |      +---> attachFootageLayer()           |
|           |      |      +---> attachPrecompLayer()           |
|           |      |      +---> attachSolidLayer()             |
|           |      |      +---> attachNullLayer()              |
|           |      |      +---> attachAudioLayer()             |
|           |      |      |                                    |
|           |      |      +---> EffectBuilder::attachEffects() |
|           |      |      +---> attachOpacity()                |
|           |      |      +---> attachBlendMode()              |
|           |      +---> sksg::RenderNode (图层渲染树)         |
|           |                                                  |
|           +---> sksg::RenderNode (合成渲染树)                |
|                                                              |
+--------------------------------------------------------------+
        |                              |
        v                              v
  AnimatorScope                  sksg::RenderNode
  [Animator, Animator, ...]       (场景图根节点)
```

## 目录结构

```
src/
├── Skottie.cpp              # Animation 构建主入口,Builder::make() 实现
├── SkottiePriv.h            # AnimationBuilder 核心定义 (内部头文件)
├── SkottieJson.h/cpp        # JSON 辅助: ParseDefault, ParseSlotID 等
├── SkottieValue.h           # 值类型定义: ScalarValue, Vec2Value, VectorValue, ColorValue
├── SkottieProperty.cpp      # PropertyHandle, PropertyObserver 实现
├── SkottieTest.cpp          # Animation 级别内部测试
├── Layer.h/cpp              # LayerBuilder: 单图层构建与变换链
├── Composition.h/cpp        # CompositionBuilder: 合成/图层集合管理
├── Camera.h/cpp             # 3D 相机变换
├── Transform.h/cpp          # TransformAdapter2D/3D: AE变换到sksg变换
├── Adapter.h                # DiscardableAdaptorBase 基类
├── BlendModes.cpp           # AE混合模式 -> SkBlendMode 映射
├── Path.cpp                 # SkPath 动画绑定
├── SlotManager.cpp          # SlotManager 实现: 插槽追踪和值分发
├── BUILD.bazel              # Bazel 构建配置
├── animator/                # 关键帧动画系统 (子目录)
├── layers/                  # 图层构建 (子目录)
│   ├── shapelayer/          # 形状图层 (子子目录)
│   └── ...
├── text/                    # 文本排版与动画 (子目录)
└── effects/                 # AE特效实现 (子目录)
```

## 关键类与函数

### AnimationBuilder (SkottiePriv.h)

这是 Skottie 的核心内部类,负责整个构建流程:

```cpp
class AnimationBuilder final : public SkNoncopyable {
    // 核心构建
    AnimationInfo parse(const skjson::ObjectValue&);

    // 变换构建
    sk_sp<sksg::Transform> attachMatrix2D(jobj, parent, auto_orient);
    sk_sp<sksg::Transform> attachMatrix3D(jobj, parent, auto_orient);
    sk_sp<sksg::Transform> attachCamera(jlayer, jtransform, parent, size);

    // 图层构建 (由 LayerBuilder 调用)
    sk_sp<sksg::RenderNode> attachFootageLayer(jobj, layerInfo);
    sk_sp<sksg::RenderNode> attachNullLayer(jobj, layerInfo);
    sk_sp<sksg::RenderNode> attachPrecompLayer(jobj, layerInfo);
    sk_sp<sksg::RenderNode> attachShapeLayer(jobj, layerInfo);
    sk_sp<sksg::RenderNode> attachSolidLayer(jobj, layerInfo);
    sk_sp<sksg::RenderNode> attachTextLayer(jobj, layerInfo);
    sk_sp<sksg::RenderNode> attachAudioLayer(jobj, layerInfo);

    // 属性分发
    bool dispatchColorProperty(color_node);
    bool dispatchOpacityProperty(opacity_node);
    bool dispatchTextProperty(text_adapter, jtext);
    bool dispatchTransformProperty(transform_adapter);

    // 适配器附加
    template<typename T> void attachDiscardableAdapter(adapter);
};
```

### 值类型 (SkottieValue.h)

```cpp
using ScalarValue  = float;           // 标量
using Vec2Value    = SkV2;            // 二维向量
using VectorValue  = std::vector<float>; // 动态数组
using ColorValue   = VectorValue;     // 颜色 (RGBA 数组)
using ShapeValue   = SkPath;          // 形状/路径
```

### LayerBuilder (Layer.h)

```cpp
class LayerBuilder final {
    int index() const;
    bool isCamera() const;

    // 构建变换链 (处理父图层继承)
    sk_sp<sksg::Transform> buildTransform(abuilder, comp);

    // 构建渲染树 (内容 + 遮罩 + 混合模式)
    sk_sp<sksg::RenderNode> buildRenderTree(abuilder, comp, prev_layer_index);
};
```

### CompositionBuilder (Composition.h)

```cpp
class CompositionBuilder final {
    // 构建合成渲染树
    sk_sp<sksg::RenderNode> build(const AnimationBuilder&);

    // 查找图层
    LayerBuilder* layerBuilder(int layer_index);
};
```

### AutoScope / AutoPropertyTracker

```cpp
// 动画器作用域管理
class AutoScope {
    AutoScope(builder);             // 创建新作用域
    AnimatorScope release();        // 释放并返回收集的动画器
};

// 属性观察器跟踪
class AutoPropertyTracker {
    AutoPropertyTracker(builder, jobj, node_type);
    // 构造时调用 onEnterNode, 析构时调用 onLeavingNode
};
```

## 依赖关系

```
src/ 内部依赖:
  Skottie.cpp
    ├── SkottiePriv.h (AnimationBuilder)
    ├── SkottieJson.h (JSON 工具)
    ├── Composition.h (CompositionBuilder)
    └── animator/Animator.h

  Layer.cpp
    ├── SkottiePriv.h
    ├── Composition.h
    ├── effects/Effects.h
    └── sksg (Transform, RenderNode, Group)

  SlotManager.cpp
    ├── SkottieValue.h
    ├── text/TextAdapter.h
    └── skresources/ImageAsset
```

## 设计模式分析

- **RAII 作用域管理**: `AutoScope` 确保动画器被正确收集到作用域栈中。`AutoPropertyTracker` 确保属性观察器的进入/离开调用配对。
- **循环检测**: `ScopedAssetRef` 使用 `fIsAttaching` 标志防止资产之间的循环引用。
- **惰性求值**: `attachDiscardableAdapter` 对静态属性(无动画器)执行一次性同步后丢弃,只有动态属性才保留动画器。
- **缓存**: `LayerBuilder` 缓存变换链 (`fTransformCache[2D/3D]`) 和内容树 (`fContentTree`),避免重复构建。

## 相关文档与参考

- **动画系统**: `docs/yuanlin/modules/skottie/src/animator/README.md`
- **图层系统**: `docs/yuanlin/modules/skottie/src/layers/README.md`
- **文本系统**: `docs/yuanlin/modules/skottie/src/text/README.md`
- **特效系统**: `docs/yuanlin/modules/skottie/src/effects/README.md`
- **sksg 模块**: `docs/yuanlin/modules/sksg/README.md`
