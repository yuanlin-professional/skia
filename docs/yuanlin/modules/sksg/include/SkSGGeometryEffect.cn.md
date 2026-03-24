# SkSGGeometryEffect -- 几何效果节点

> 源文件: `modules/sksg/include/SkSGGeometryEffect.h`

## 概述

`SkSGGeometryEffect.h` 定义了 Skia Scene Graph 中的几何效果体系。`GeometryEffect` 是一个抽象基类，对子几何节点的路径进行变换或修改，产生新的几何形状。该文件包含六个具体的几何效果实现：`TrimEffect`（路径裁剪）、`GeometryTransform`（几何变换）、`FillTypeOverride`（填充类型覆盖）、`DashEffect`（虚线效果）、`RoundEffect`（圆角效果）和 `OffsetEffect`（偏移效果）。这些效果广泛用于 Lottie 动画和 SVG 渲染中的路径操作。

## 架构位置

几何效果节点在 sksg 节点层次中的位置：

```
Node
└── GeometryNode (几何节点基类)
    ├── Path, Rect, RRect, Plane, Text (叶几何节点)
    └── GeometryEffect (几何效果基类)
        ├── TrimEffect
        ├── GeometryTransform
        ├── FillTypeOverride
        ├── DashEffect
        ├── RoundEffect
        └── OffsetEffect
```

几何效果节点是装饰器模式的应用：它们包装一个子 `GeometryNode`，在其基础上应用路径变换。变换结果缓存为 `SkPath`，提供给上层的 `Draw` 节点用于实际绘制。

## 主要类与结构体

### `GeometryEffect` (抽象基类)
```cpp
class GeometryEffect : public GeometryNode {
protected:
    explicit GeometryEffect(sk_sp<GeometryNode>);
    virtual SkPath onRevalidateEffect(const sk_sp<GeometryNode>&, const SkMatrix&) = 0;
private:
    const sk_sp<GeometryNode> fChild;
    SkPath fPath; // 变换后的路径缓存
};
```
所有几何效果的基类。子类只需实现 `onRevalidateEffect` 返回变换后的 `SkPath`。基类处理裁剪、绘制、包含测试和路径缓存。

### `TrimEffect`
```cpp
class TrimEffect final : public GeometryEffect {
    SG_ATTRIBUTE(Start, SkScalar, fStart)   // 起始位置 [0, 1]
    SG_ATTRIBUTE(Stop,  SkScalar, fStop)    // 结束位置 [0, 1]
    SG_ATTRIBUTE(Mode,  SkTrimPathEffect::Mode, fMode) // Normal 或 Inverted
};
```
路径裁剪效果，提取路径的一部分。`Start` 和 `Stop` 定义裁剪范围（归一化到 [0,1]），`Mode` 控制是保留还是反转选中的部分。常用于 Lottie 的 Trim Path 动画。

### `GeometryTransform`
```cpp
class GeometryTransform final : public GeometryEffect {
    const sk_sp<Transform> fTransform;
public:
    const sk_sp<Transform>& getTransform() const;
};
```
将 `Transform` 节点应用到子几何体上。与 `TransformEffect`（作用于渲染子树）不同，这里直接变换路径数据本身。

### `FillTypeOverride`
```cpp
class FillTypeOverride final : public GeometryEffect {
    SG_ATTRIBUTE(FillType, SkPathFillType, fFillType)
};
```
覆盖子几何体的路径填充类型（如 `kWinding`、`kEvenOdd`），不改变路径形状。

### `DashEffect`
```cpp
class DashEffect final : public GeometryEffect {
    SG_ATTRIBUTE(Intervals, std::vector<float>, fIntervals)
    SG_ATTRIBUTE(Phase, float, fPhase)
};
```
虚线效果，语义与 `SkDashPathEffect` 相同。当间隔数为奇数时，自动重复一次以获得偶数序列（遵循 SVG stroke-dasharray 规范）。

### `RoundEffect`
```cpp
class RoundEffect final : public GeometryEffect {
    SG_ATTRIBUTE(Radius, SkScalar, fRadius)
};
```
将路径的尖角转换为指定半径的圆角。

### `OffsetEffect`
```cpp
class OffsetEffect final : public GeometryEffect {
    SG_ATTRIBUTE(Offset, SkScalar, fOffset)
    SG_ATTRIBUTE(MiterLimit, SkScalar, fMiterLimit)
    SG_ATTRIBUTE(Join, SkPaint::Join, fJoin)
};
```
路径偏移效果，将路径沿法线方向偏移指定距离。支持设置斜接限制和连接类型（Miter/Round/Bevel）。

## 公共 API 函数

所有具体效果类都遵循统一的模式：

### `Make(child, ...)` 工厂方法
每个效果类都有静态 `Make` 方法，接受子 `GeometryNode`（必须非空），返回效果节点的 `sk_sp`。

### `SG_ATTRIBUTE` 生成的属性访问器
每个效果通过 `SG_ATTRIBUTE` 宏生成 `get*()` 和 `set*()` 方法，设值时自动调用 `invalidate()` 触发失效传播。

## 内部实现细节

- `GeometryEffect` 的 `onClip`、`onDraw`、`onContains`、`onAsPath` 和 `onRevalidate` 全部声明为 `final`，子类不能覆盖这些方法。子类只能覆盖 `onRevalidateEffect`，简化了扩展点。
- `fPath` 成员缓存了变换后的路径，避免每次渲染时重复计算。只有在节点失效后的 `onRevalidate` 中才会调用 `onRevalidateEffect` 更新缓存。
- `GeometryTransform` 额外持有 `sk_sp<Transform>` 并监听其失效，当变换矩阵改变时自动重新计算。
- `DashEffect` 的 `fIntervals` 使用 `std::vector<float>` 支持可变长度的间隔数组。
- `OffsetEffect` 的默认斜接限制为 4，默认连接类型为 `kMiter_Join`。

## 依赖关系

- `include/core/SkPath.h` -- 路径类型，效果的输入和输出
- `include/core/SkPaint.h` -- `SkPaint::Join` 枚举（OffsetEffect 使用）
- `include/effects/SkTrimPathEffect.h` -- `TrimEffect::Mode` 枚举
- `modules/sksg/include/SkSGGeometryNode.h` -- 基类
- `modules/sksg/include/SkSGTransform.h` -- GeometryTransform 使用的变换类型

## 设计模式与设计决策

1. **装饰器模式**：每个 GeometryEffect 包装一个子 GeometryNode，在其路径输出上叠加效果。效果可以嵌套组合。

2. **模板方法模式**：基类 GeometryEffect 定义了 `onRevalidate` 的完整流程（revalidate 子节点 -> 调用 `onRevalidateEffect` -> 缓存结果），子类只需实现 `onRevalidateEffect` 这一个扩展点。

3. **final 继承控制**：基类的 `onClip`/`onDraw`/`onContains`/`onAsPath`/`onRevalidate` 全部为 `final`，防止子类绕过缓存机制。

4. **SG_ATTRIBUTE 统一属性管理**：所有效果参数通过 SG_ATTRIBUTE 宏定义，自动处理值比较（避免无变化的失效）和失效触发。

5. **SVG 兼容性**：DashEffect 的奇数间隔重复策略遵循 SVG 规范，确保与 SVG/Lottie 内容的兼容性。

## 性能考量

- 路径缓存 (`fPath`) 避免了每帧重新计算路径变换，只在参数变化时更新。
- `GeometryTransform` 监听 Transform 节点的失效，实现精确的增量更新。
- DashEffect 的 `std::vector<float>` 间隔在堆上分配，频繁更新间隔数组可能产生分配开销。
- 效果链的嵌套深度影响 revalidation 的递归深度和路径复杂度。
- TrimEffect 和 DashEffect 产生的路径可能比原始路径复杂得多（更多的段和控制点），影响后续的渲染性能。

## 相关文件

- `modules/sksg/src/SkSGGeometryEffect.cpp` -- 各效果的 `onRevalidateEffect` 实现
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 基类
- `modules/sksg/include/SkSGPath.h` -- Path 叶节点（常作为效果链的起始节点）
- `modules/sksg/include/SkSGTransform.h` -- Transform 类（GeometryTransform 使用）
- `modules/sksg/include/SkSGDraw.h` -- Draw 节点（将几何效果的结果绘制到 Canvas）
