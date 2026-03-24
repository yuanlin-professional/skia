# CornerPinEffect - Skottie 四角定位效果

> 源文件: `modules/skottie/src/effects/CornerPinEffect.cpp`

## 概述

CornerPinEffect 实现了 After Effects 中的"四角定位"（Corner Pin）效果。该效果允许通过指定图层四个角的目标位置来对图层进行透视变换，常用于将图像"钉"到三维表面上（如将视频画面映射到建筑物墙面）。实现核心是通过 `SkMatrix::PolyToPoly` 计算从源矩形到目标四边形的透视变换矩阵。

## 架构位置

该文件属于 Skottie 效果子系统，位于 `skottie::internal` 命名空间。与颜色滤镜类效果不同，Corner Pin 效果产生的是几何变换节点（`sksg::TransformEffect`），它包装一个 `sksg::Matrix<SkMatrix>` 节点来承载透视矩阵。

```
AnimationBuilder
  └── EffectBuilder::attachCornerPinEffect()
        ├── CornerPinAdapter (AnimatablePropertyContainer)
        │     └── sksg::Matrix<SkMatrix>
        └── sksg::TransformEffect(layer, matrix_node)
```

## 主要类与结构体

### `CornerPinAdapter`
- 继承自 `AnimatablePropertyContainer`（而非 DiscardableAdapterBase）
- 通过工厂方法 `Make()` 创建，接收 JSON 属性、动画构建器和图层尺寸
- 持有 `fMatrixNode`（`sksg::Matrix<SkMatrix>`）和 `fLayerSize`（`SkSize`）
- 管理四个二维向量动画属性：`fUL`（左上）、`fUR`（右上）、`fLL`（左下）、`fLR`（右下）

### 属性索引枚举
- `kUpperLeft_Index = 0`
- `kUpperRight_Index = 1`
- `kLowerLeft_Index = 2`
- `kLowerRight_Index = 3`

## 公共 API 函数

### `EffectBuilder::attachCornerPinEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachCornerPinEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- **功能**：将四角定位变换效果附加到指定图层
- **返回值**：经 `sksg::TransformEffect::Make()` 包装的渲染节点

## 内部实现细节

### onSync 方法

每次动画属性更新时调用，执行以下操作：

1. **构建源点数组**：以图层尺寸为基础，四个角依次为 (0,0)、(width,0)、(width,height)、(0,height)
2. **构建目标点数组**：从四个 `Vec2Value` 属性中获取用户指定的角位置
3. **计算透视矩阵**：调用 `SkMatrix::PolyToPoly(src, dst)` 计算从源矩形到目标四边形的变换
4. **应用矩阵**：若计算成功，将结果设置到 `fMatrixNode` 上

```cpp
if (auto m = SkMatrix::PolyToPoly(src, dst)) {
    fMatrixNode->setMatrix(*m);
}
```

注意：`PolyToPoly` 对 4 个点会计算一个完整的透视变换（3x3 射影矩阵），这是唯一能正确映射任意四边形的变换类型。

### 节点暴露

`node()` 访问器返回内部的 `fMatrixNode`，由 `attachCornerPinEffect` 用于构建 `TransformEffect`。

## 依赖关系

- **Skia 核心**：`SkMatrix`（透视矩阵计算）、`SkPoint`、`SkSize`
- **Skottie 内部**：`SkottiePriv.h`、`SkottieValue.h`（`Vec2Value`）、`Effects.h`（`EffectBinder`）、`Animator.h`（`AnimatablePropertyContainer`）
- **SkSG（场景图）**：`SkSGTransform.h`（`sksg::Matrix`、`sksg::TransformEffect`）

## 设计模式与设计决策

1. **属性容器模式**：使用 `AnimatablePropertyContainer` 而非 `DiscardableAdapterBase`，因为该效果不直接拥有渲染节点，而是产生一个矩阵节点供外部 TransformEffect 使用。

2. **工厂方法**：`Make()` 静态方法封装了私有构造函数，确保对象始终通过引用计数管理。

3. **几何变换与颜色效果分离**：Corner Pin 产生的是变换节点而非滤镜节点，体现了 Skottie 效果系统中几何变换与颜色处理的架构分离。

4. **静态断言**：`static_assert(std::size(src) == std::size(dst))` 确保源点与目标点数组大小一致。

## 性能考量

- `SkMatrix::PolyToPoly` 对 4 点的计算涉及求解 8 个未知数的线性方程组，但作为非频繁操作（仅在属性变化时触发），性能开销可以接受
- 变换矩阵缓存在 `fMatrixNode` 中，渲染时直接使用，无需重复计算
- 当 `PolyToPoly` 返回空值（退化情况）时，矩阵保持上一次的有效值，避免异常渲染

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBuilder 与 EffectBinder 定义
- `modules/skottie/src/animator/Animator.h` - AnimatablePropertyContainer 基类
- `modules/sksg/include/SkSGTransform.h` - 场景图变换节点
- `include/core/SkMatrix.h` - SkMatrix::PolyToPoly 实现
- `modules/skottie/src/SkottieValue.h` - Vec2Value 类型定义
