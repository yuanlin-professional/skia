# Layer - Skottie 图层系统

> 源文件: [`modules/skottie/src/Layer.h`](../../../modules/skottie/src/Layer.h), [`modules/skottie/src/Layer.cpp`](../../../modules/skottie/src/Layer.cpp)

## 概述

Layer 模块实现了 Skottie 的图层构建系统，负责将 Lottie JSON 中的图层定义解析为场景图渲染树。它处理所有 AE 图层类型（预合成、纯色、图片、null、形状、文本、音频、相机等），管理图层变换链、遮罩、蒙版、混合模式和时间控制。

LayerBuilder 是图层构建的核心类，通过两阶段构建（先变换链，后内容树）解决了图层父子关系和 3D 变换依赖。

## 架构位置

位于 Skottie 内部实现层的核心位置：

- **调用者**: CompositionBuilder::build()
- **协作组件**: CompositionBuilder（合成）、TransformAdapter（变换）、CameraAdaper（相机）
- **输出**: sksg 场景图节点（RenderNode、Transform）
- **子系统**: Effects（特效）、Masks（遮罩）、Animator（动画）

## 主要类与结构体

### `LayerBuilder` 类
图层构建器，负责从 JSON 创建完整的图层渲染树。

```cpp
class LayerBuilder final {
public:
    LayerBuilder(const ObjectValue& jlayer, const SkSize& comp_size);
    int index() const;
    bool isCamera() const;
    sk_sp<sksg::Transform> buildTransform(const AnimationBuilder&, CompositionBuilder*);
    sk_sp<sksg::RenderNode> buildRenderTree(const AnimationBuilder&, CompositionBuilder*, int prev_layer_index);
};
```

### `LayerController` 内部类
动画控制器，管理图层的入点/出点（in/out）时间和可见性。非活跃图层仅更新变换动画（供活跃子图层使用）。

### `MaskAdapter` 内部类
遮罩适配器，处理遮罩路径的不透明度、羽化（feather）和混合模式。

### `MaskInfo` 结构体
遮罩类型信息，映射 AE 遮罩模式字符（'a'=加、'i'=交、's'=减、'f'=异或）到混合模式和合并模式。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `buildTransform(abuilder, cbuilder)` | 构建图层变换链（包含父级链） |
| `buildRenderTree(abuilder, cbuilder, prev_layer_index)` | 构建完整渲染树（内容+遮罩+蒙版+混合） |
| `getContentTree(abuilder, cbuilder)` | 获取（惰性构建的）内容树 |
| `isCamera()` | 是否为相机层（类型 13） |

## 内部实现细节

### 图层类型派发表
使用 `gLayerBuildInfo[]` 静态数组将图层类型映射到构建函数：
- 类型 0: 预合成层 (attachPrecompLayer, kTransformEffects)
- 类型 1: 纯色层 (attachSolidLayer, kTransformEffects)
- 类型 2: 图片层 (attachFootageLayer, kTransformEffects)
- 类型 3: Null 层 (attachNullLayer)
- 类型 4: 形状层 (attachShapeLayer)
- 类型 5: 文本层 (attachTextLayer)
- 类型 6: 音频层 (attachAudioLayer, kForceSeek)
- 类型 13: 相机层 (attachNullLayer)

### 变换链构建
`getTransform()` 递归构建变换链，处理父层关系。使用缓存和循环检测标记（`cache_valid_mask`）防止无限递归。

### 遮罩系统（AttachMask）
AE 遮罩处理有两种路径：
1. **裁剪路径**: 完全不透明的遮罩使用 ClipEffect，多个路径使用 Merge 合并
2. **遮罩节点**: 半透明或羽化的遮罩使用 MaskEffect，支持模糊滤镜

### 图层控制器（LayerController）
管理图层的时间活跃性。非活跃图层隐藏渲染节点但仍更新变换动画器（fTransformAnimatorsCount 个），确保子图层变换正确。

### 效果与变换的交互
不同图层类型的效果应用顺序不同：
- 预渲染类型（预合成、纯色、图片）: 效果受变换影响 (kTransformEffects)
- 其他类型（形状、文本）: 变换不影响效果

## 依赖关系

- `modules/skottie/src/Composition.h` - CompositionBuilder
- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder
- `modules/skottie/src/effects/Effects.h` - 特效处理
- `modules/sksg/` - 场景图节点（Group、ClipEffect、MaskEffect、Transform 等）

## 设计模式与设计决策

### 两阶段构建
先构建所有变换链（第一遍），再构建内容树（第二遍），确保父层变换在子层构建时已就绪。

### 缓存机制
变换链使用 `fTransformCache[2]` 分别缓存 2D 和 3D 版本，避免递归调用中的重复构建。

### 惰性内容树
内容树通过 `getContentTree()` 惰性构建并缓存于 `fContentTree`，支持蒙版引用其他图层内容。

## 性能考量

- 静态图层优化：不产生动画器的变换直接求值
- 恒等变换丢弃：identity 变换不创建节点
- 非活跃图层仅更新变换子集

## 相关文件

- `modules/skottie/src/Composition.h` - 合成构建
- `modules/skottie/src/Transform.h` - 变换适配器
- `modules/skottie/src/Camera.h` - 相机
- `modules/skottie/src/effects/Effects.h` - 特效
