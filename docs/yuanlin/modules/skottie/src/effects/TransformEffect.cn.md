# TransformEffect - Skottie 变换效果

> 源文件: `modules/skottie/src/effects/TransformEffect.cpp`

## 概述

TransformEffect 实现了 After Effects 中的变换效果（Transform Effect），允许在效果级别对图层进行额外的几何变换和不透明度调整。与图层自身的变换不同，该效果作为后处理效果应用，支持锚点、位置、缩放（统一/非统一）、旋转、斜切和不透明度参数。该效果通过组合 `TransformAdapter2D` 和 `OpacityEffect` 实现。

## 架构位置

TransformEffect 位于 Skottie 效果子系统中，组合了变换和不透明度两个子系统。

```
EffectBuilder::attachTransformEffect()
  |
  +-> TransformAdapter2D [几何变换适配器]
  |     +-> anchor, position, rotation, skew, skewAxis
  |     +-> sksg::TransformEffect [变换渲染节点]
  |
  +-> TransformEffectAdapter [不透明度 + 缩放适配器]
        +-> DiscardableAdapterBase<..., sksg::OpacityEffect>
        +-> opacity, uniformScale, scaleWidth, scaleHeight
        +-> 同步缩放到 TransformAdapter2D
```

## 主要类与结构体

### TransformEffectAdapter
- 继承自 `DiscardableAdapterBase<TransformEffectAdapter, sksg::OpacityEffect>`
- 包装 `sksg::OpacityEffect` 节点管理不透明度
- 持有 `TransformAdapter2D` 实例管理几何变换
- 属性：
  - `fOpacity` (100) - 不透明度百分比
  - `fUniformScale` (0) - 布尔标志：是否使用统一缩放
  - `fScaleWidth` (100) - X 轴缩放百分比
  - `fScaleHeight` (100) - Y 轴缩放百分比

## 公共 API 函数

### `EffectBuilder::attachTransformEffect`
```cpp
sk_sp<sksg::RenderNode> attachTransformEffect(const skjson::ArrayValue& jprops,
                                               sk_sp<sksg::RenderNode> layer) const;
```
- 从 JSON props 提取各变换参数
- 创建 `TransformAdapter2D`（处理锚点、位置、旋转、斜切）
- 创建 `sksg::TransformEffect` 应用几何变换
- 创建 `TransformEffectAdapter` 处理不透明度和缩放
- 缩放由外部处理（`nullptr` 传给 TransformAdapter2D 的 scale 参数）

## 内部实现细节

### 参数索引映射
```
kAnchorPoint_Index  = 0    // 锚点
kPosition_Index     = 1    // 位置
kUniformScale_Index = 2    // 统一缩放开关
kScaleHeight_Index  = 3    // 高度缩放
kScaleWidth_Index   = 4    // 宽度缩放
kSkew_Index         = 5    // 斜切
kSkewAxis_Index     = 6    // 斜切轴
kRotation_Index     = 7    // 旋转
kOpacity_Index      = 8    // 不透明度
```

### 缩放处理
```cpp
void onSync() override {
    this->node()->setOpacity(fOpacity * 0.01f);
    const auto scale = SkVector::Make(
        SkScalarRoundToInt(fUniformScale) ? fScaleHeight : fScaleWidth,
        fScaleHeight);
    fTransformAdapter->setScale(scale);
}
```
- 统一缩放模式：X 和 Y 都使用 `fScaleHeight`
- 非统一缩放模式：X 使用 `fScaleWidth`，Y 使用 `fScaleHeight`
- `SkScalarRoundToInt(fUniformScale)` 将浮点值当作布尔使用

### 渲染节点链
```
OpacityEffect [不透明度控制]
  |
  +-> TransformEffect [几何变换]
        |
        +-> 原始图层
```

### 适配器嵌套
- `TransformEffectAdapter` 通过 `attachDiscardableAdapter(fTransformAdapter)` 将变换适配器的生命周期绑定到自身
- 当效果适配器被丢弃时，变换适配器也会被清理

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `Transform.h` | TransformAdapter2D 二维变换适配器 |
| `Adapter.h` | DiscardableAdapterBase 基类 |
| `SkSGOpacityEffect.h` | OpacityEffect 不透明度节点 |
| `SkSGTransform.h` | TransformEffect 变换节点 |
| `Animator.h` | AnimatablePropertyContainer |
| `Effects.h` | EffectBinder、GetPropValue |
| `SkottieValue.h` | ScalarValue 类型 |

## 设计模式与设计决策

- **组合模式**：变换效果由 TransformAdapter2D（几何）和 TransformEffectAdapter（不透明度+缩放）组合实现，职责清晰分离。
- **缩放外部化**：缩放不传递给 TransformAdapter2D，而是由 TransformEffectAdapter 在 onSync 中手动设置。这是因为缩放需要根据统一/非统一模式动态选择来源。
- **适配器嵌套**：通过 `attachDiscardableAdapter` 建立适配器间的所有权关系，确保生命周期正确管理。
- **效果级变换**：区别于图层变换，效果变换在效果栈中处理，可以与其他效果组合。

## 性能考量

- `OpacityEffect` 在不透明度为 100% 时可优化为透传。
- `TransformEffect` 使用矩阵变换，GPU 原生支持。
- `onSync` 仅执行简单的条件判断和赋值，开销极小。
- 缩放通过 `setScale` 触发变换适配器的同步，间接更新 Scene Graph 矩阵节点。

### 效果变换与图层变换的区别

在 After Effects 中，图层变换和变换效果虽然参数相似，但在渲染管线中的位置不同：

1. **图层变换**：在所有效果之前应用，决定图层在合成中的基本位置和尺寸。在 Skottie 中通过图层附加管线的变换阶段处理。

2. **变换效果**：作为效果栈中的一个效果应用，在其他效果之后或之间执行。可以叠加多个变换效果，每个效果独立控制。在 Skottie 中通过 EffectBuilder 管线处理。

这种区别意味着变换效果可以与其他效果（如模糊、色彩校正等）交叉使用，产生图层变换无法实现的效果组合。

### GetPropValue 辅助函数

`GetPropValue(jprops, index)` 从 JSON 属性数组中提取指定索引的属性值对象。它返回 `const skjson::ObjectValue*`，可能为 nullptr（当索引越界或属性缺失时）。各参数通过该函数从 jprops 数组中按索引提取，然后分别传递给 TransformAdapter2D 和 TransformEffectAdapter。

### 未使用的参数

JSON 属性中存在但当前未绑定的参数：
- `kUseCompShutterAngle_Index = 9` - 使用合成快门角度
- `kShutterAngle_Index = 10` - 快门角度
- `kSampling_Index = 11` - 采样模式

这些参数与运动模糊相关，Skottie 当前不支持变换效果的运动模糊功能。

### 缩放参数的特殊处理

缩放参数没有传递给 TransformAdapter2D（传入 nullptr），而是由 TransformEffectAdapter 在 onSync 中手动调用 `fTransformAdapter->setScale()`。这样做的原因是缩放需要根据 `fUniformScale` 标志动态决定使用 `fScaleHeight`（统一模式）还是 `fScaleWidth/fScaleHeight`（非统一模式），这种逻辑无法通过简单的属性绑定实现。

## 相关文件

- `modules/skottie/src/Transform.h` - TransformAdapter2D
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase
- `modules/skottie/src/effects/Effects.h` - EffectBinder、GetPropValue
- `modules/sksg/include/SkSGOpacityEffect.h` - OpacityEffect
- `modules/sksg/include/SkSGTransform.h` - TransformEffect
