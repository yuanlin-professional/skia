# NullLayer - Skottie 空图层

> 源文件: `modules/skottie/src/layers/NullLayer.cpp`

## 概述

NullLayer 实现了 Lottie 动画中空图层（Null Layer）的处理。空图层在 After Effects 中仅作为变换容器使用，用于驱动子图层的变换关系。在 Skottie 的实现中，空图层直接返回 `nullptr`，因为 Skottie 使用独立的自由浮动矩阵（free-floating `sksg::Matrix`）来处理变换依赖，而非依赖图层节点本身。

## 架构位置

NullLayer 是 Skottie `AnimationBuilder` 图层附加管线中最简单的图层类型。它在图层解析阶段被调用，但不产生任何 Scene Graph 节点。

```
Skottie AnimationBuilder
  -> attachNullLayer()
    -> return nullptr (无渲染节点)
```

变换驱动机制在图层附加之前的变换解析阶段已经处理完成。

## 主要类与结构体

本文件未定义任何类或结构体。仅包含 `AnimationBuilder::attachNullLayer` 的实现。

## 公共 API 函数

### `AnimationBuilder::attachNullLayer`
```cpp
sk_sp<sksg::RenderNode> attachNullLayer(const skjson::ObjectValue& layer,
                                         LayerInfo*) const;
```
- 参数 `layer` 和 `LayerInfo*` 均未使用
- 直接返回 `nullptr`
- 空图层的变换信息已在图层处理管线的更早阶段被提取和应用

## 内部实现细节

实现仅为单行 `return nullptr`。设计注释说明了关键的架构决策：空图层的唯一用途是驱动依赖变换，而 Skottie 通过独立的 `sksg::Matrix` 对象实现此功能，因此无需创建渲染节点。

### 空图层在 Lottie 动画中的角色

在 After Effects 工作流中，空图层（Null Object）是动画师常用的控制工具：

1. **父子变换链**：空图层作为多个可视图层的父层，统一控制一组图层的位置、旋转和缩放。例如，一个角色的所有肢体图层可以挂接到一个空图层下，通过移动空图层来移动整个角色。

2. **表达式驱动**：空图层的变换属性常被其他图层通过表达式引用，作为动画的控制点。

3. **相机/灯光控制**：在 3D 合成中，空图层可作为相机或灯光的目标点。

### Skottie 的变换处理架构

Skottie 在图层处理管线中将变换解析与图层内容创建分为两个独立阶段：

1. **变换阶段**：在 `attachLayer()` 的早期阶段，所有图层（包括空图层）的变换信息被提取并创建为独立的 `sksg::Matrix` 节点。这些矩阵节点形成变换树，通过父子关系实现变换继承。

2. **内容阶段**：之后调用具体的图层附加函数（如 `attachNullLayer`、`attachSolidLayer` 等）创建图层的可视内容。空图层在此阶段无需创建任何内容。

这种分离设计的优势在于：变换树的构建不依赖于图层是否有可视内容，使得空图层的变换能力完全保留，同时 Scene Graph 中不会出现无用的空节点。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkRefCnt.h` | `sk_sp` 智能指针 |
| `SkottiePriv.h` | `AnimationBuilder` 定义 |
| `SkSGRenderNode.h` | `RenderNode` 返回类型 |
| `skjson` (前向声明) | JSON 数据类型 |

## 设计模式与设计决策

- **空对象模式**：返回 `nullptr` 而非空的渲染节点包装，是有意为之的设计选择。这与 AudioLayer 类似，表示该图层不参与渲染管线。
- **变换外部化**：Skottie 将图层变换从图层节点中分离出来，使用独立的矩阵对象管理。这种设计使得空图层无需存在于 Scene Graph 中即可驱动子图层的变换。
- **最小化实现**：仅 27 行代码（含许可证头），是 Skottie 中最精简的图层实现。

## 性能考量

- 零运行时开销：不创建任何对象，不参与渲染管线。
- 不占用 Scene Graph 节点，减少了渲染树的遍历开销。

## 相关文件

- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder 定义及图层处理管线
- `modules/sksg/include/SkSGRenderNode.h` - RenderNode 基类
- `modules/skottie/src/layers/AudioLayer.cpp` - 同样返回 nullptr 的图层
- `modules/skottie/src/layers/SolidLayer.cpp` - 最简单的可视图层对比
