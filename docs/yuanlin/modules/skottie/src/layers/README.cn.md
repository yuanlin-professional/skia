# skottie/src/layers - 图层类型实现

## 概述

`layers/` 目录实现了 Lottie 规范定义的所有图层类型。在 After Effects 和 Lottie 中,图层 (Layer) 是动画的基本构建单元,每个图层具有独立的变换、时间范围、遮罩和特效。Skottie 在构建阶段将每种图层类型转换为对应的 sksg 渲染节点子树。

该目录还包含 `shapelayer/` 子目录,用于实现形状图层中的各种几何体、绘制和几何效果。

## 目录结构

```
layers/
├── BUILD.bazel              # Bazel 构建配置
├── AudioLayer.cpp           # 音频图层 (类型 6)
├── FootageLayer.cpp         # 图像/视频图层 (类型 2)
├── NullLayer.cpp            # 空图层 (类型 3)
├── PrecompLayer.cpp         # 预合成图层 (类型 0)
├── SolidLayer.cpp           # 纯色图层 (类型 1)
├── TextLayer.cpp            # 文本图层 (类型 5)
└── shapelayer/              # 形状图层 (类型 4) 子目录
```

## 关键类与函数

### 图层类型映射

Lottie 通过 `ty` 字段标识图层类型,由 `AnimationBuilder` 分发到对应的 `attach*Layer` 方法:

| Lottie `ty` | 图层类型 | 方法 | 产出场景图节点 |
|:---:|------|------|------|
| 0 | 预合成 (Precomp) | `attachPrecompLayer()` | Group + TransformEffect (递归合成) |
| 1 | 纯色 (Solid) | `attachSolidLayer()` | Draw(Rect, Color) |
| 2 | 图像 (Footage/Image) | `attachFootageLayer()` | Image + TransformEffect |
| 3 | 空 (Null) | `attachNullLayer()` | nullptr (仅变换) |
| 4 | 形状 (Shape) | `attachShapeLayer()` | 复杂场景子树 (见 shapelayer/) |
| 5 | 文本 (Text) | `attachTextLayer()` | TextAdapter (Group) |
| 6 | 音频 (Audio) | `attachAudioLayer()` | nullptr (事件触发) |

### PrecompLayer.cpp

预合成图层是最复杂的图层类型:
- 递归构建内嵌合成 (`CompositionBuilder`)
- 支持时间重映射 (`tm` 属性)
- 支持外部图层替换 (`PrecompInterceptor`)
- 通过 `ScopedAssetRef` 进行循环依赖检测

### FootageLayer.cpp

图像图层:
- 通过 `ResourceProvider` 加载 `ImageAsset`
- 支持延迟加载 (`kDeferImageLoading` 标志)
- 缓存已加载的图像资源 (`fImageAssetCache`)
- 创建 `sksg::Image` 节点用于渲染

### TextLayer.cpp

文本图层:
- 创建 `TextAdapter` 来管理文本内容和动画
- 支持文本动画器 (逐字符/逐词/逐行)
- 通过 `SlotManager` 支持运行时文本替换

### SolidLayer.cpp

纯色图层: 创建 `sksg::Rect` + `sksg::Color` 组合的 `sksg::Draw` 节点。

### NullLayer.cpp

空图层: 不产生渲染内容,仅提供变换节点作为其他图层的父级。

### AudioLayer.cpp

音频图层: 通过 `ResourceProvider` 触发音频事件,不产生渲染内容。

## 图层渲染树构建流程

```
LayerBuilder::buildRenderTree()
    |
    +---> buildContentTree()
    |       调用对应的 attach*Layer() 方法
    |       -> sk_sp<sksg::RenderNode> (图层内容)
    |
    +---> EffectBuilder::attachEffects()
    |       附加图层特效
    |
    +---> attachOpacity()
    |       包装不透明度
    |
    +---> TransformEffect
    |       包装图层变换
    |
    +---> MaskEffect (如有遮罩)
    |       应用图层遮罩
    |
    +---> attachBlendMode()
    |       应用混合模式
    |
    +---> Matte 处理 (如有遮片)
            应用轨道遮片
```

## 依赖关系

```
layers/*.cpp
  ├── SkottiePriv.h     (AnimationBuilder)
  ├── Layer.h           (LayerBuilder)
  ├── Composition.h     (CompositionBuilder)
  ├── text/TextAdapter.h
  ├── effects/Effects.h
  └── sksg (RenderNode, Draw, Rect, Color, Image, Group)
```

## 相关文档与参考

- **形状图层**: `docs/yuanlin/modules/skottie/src/layers/shapelayer/README.md`
- **特效系统**: `docs/yuanlin/modules/skottie/src/effects/README.md`
- **文本系统**: `docs/yuanlin/modules/skottie/src/text/README.md`
- **父目录**: `docs/yuanlin/modules/skottie/src/README.md`
