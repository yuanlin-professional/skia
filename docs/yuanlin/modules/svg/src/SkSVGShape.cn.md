# SkSVGShape

> 源文件: [modules/svg/src/SkSVGShape.cpp](../../../../modules/svg/src/SkSVGShape.cpp)

## 概述

`SkSVGShape` 是所有 SVG 形状元素（如 `<circle>`、`<rect>`、`<path>`、`<ellipse>` 等）的抽象基类。它继承自 `SkSVGTransformableNode`，为所有图形形状提供了统一的渲染流程：分别使用填充画笔和描边画笔绘制形状。

该类的实现非常精简（39 行），体现了 SVG 形状渲染的核心逻辑——填充和描边是 SVG 形状绘制的两个独立步骤。

## 架构位置

```
SkSVGNode
  └── SkSVGTransformableNode
        └── SkSVGShape              ← 本文件（形状基类）
              ├── SkSVGCircle
              ├── SkSVGEllipse
              ├── SkSVGRect
              ├── SkSVGPath
              ├── SkSVGLine
              └── SkSVGPoly
```

`SkSVGShape` 位于形状继承体系的中间层，向上继承变换能力，向下为具体形状提供统一的渲染接口。

## 主要类与结构体

### `SkSVGShape`

抽象基类，使用 `final` 关键字标记 `onRender()` 为不可覆盖，确保所有形状使用统一的渲染流程。子类需实现 `onDraw()` 纯虚函数来定义具体的绘制行为。

## 公共 API 函数

### `appendChild(sk_sp<SkSVGNode>)`
覆盖基类方法，禁止向形状节点添加子节点。调用时仅输出调试信息 "cannot append child nodes to an SVG shape"。

## 内部实现细节

### 渲染流程 (`onRender`)

`onRender` 实现了 SVG 形状的标准渲染流程：

1. 从渲染上下文获取当前的 `fill-rule`
2. 分别获取填充画笔 (`fillPaint`) 和描边画笔 (`strokePaint`)
3. 如果填充画笔有值，调用 `onDraw()` 执行填充绘制
4. 如果描边画笔有值，调用 `onDraw()` 执行描边绘制

注意：代码中的 TODO 注释指出，当前实现会在填充和描边两次调用中重复解析几何数据，后续应重构以避免冗余计算。

### 叶子节点特性

形状节点是 SVG DOM 树的叶子节点，不能包含子节点。`appendChild()` 方法通过调试断言阻止此操作。

## 依赖关系

- **Skia Core**: `SkPaint`
- **SVG 模块**: `SkSVGAttribute`, `SkSVGRenderContext`, `SkSVGTypes`, `SkSVGTransformableNode`

## 设计模式与设计决策

1. **模板方法模式**: `onRender()` 定义了固定的渲染算法骨架（获取画笔 -> 填充绘制 -> 描边绘制），子类通过 `onDraw()` 实现具体绘制。

2. **`final` 修饰**: `onRender()` 被声明为 `final`，防止子类改变渲染流程，确保所有形状遵循相同的填充/描边模式。

3. **填充/描边分离**: 严格遵循 SVG 规范，填充和描边是独立的绘制操作，各自有独立的画笔属性。

4. **叶子节点约束**: 通过覆盖 `appendChild` 并输出调试信息，在运行时防止错误的 DOM 结构。

## 性能考量

- 代码中注明了当前实现的性能缺陷：`onDraw()` 被调用两次（一次填充、一次描边），导致几何解析重复执行
- 对于仅有填充或仅有描边的形状（通过 `has_value()` 检查），可以跳过一次绘制调用
- 该类本身开销极小，性能主要取决于子类的 `onDraw()` 实现

## 相关文件

- `modules/svg/include/SkSVGShape.h` - 头文件，定义纯虚接口 `onDraw()`
- `modules/svg/include/SkSVGTransformableNode.h` - 可变换节点基类
- `modules/svg/src/SkSVGCircle.cpp` - 圆形形状实现
- `modules/svg/src/SkSVGRect.cpp` - 矩形形状实现
- `modules/svg/src/SkSVGPath.cpp` - 路径形状实现
- `modules/svg/src/SkSVGEllipse.cpp` - 椭圆形状实现
