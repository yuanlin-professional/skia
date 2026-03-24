# TextShadow

> 源文件: [modules/skparagraph/include/TextShadow.h](../../../../modules/skparagraph/include/TextShadow.h)

## 概述

`TextShadow` 定义了文本阴影效果的数据结构，用于描述文本段落中的阴影参数。每个文本阴影由颜色、偏移量和模糊半径三个属性组成。该类是 `TextStyle` 的组成部分，一个文本样式可以拥有多个阴影效果（存储在 `std::vector<TextShadow>` 中），支持叠加显示。该设计与 CSS 的 `text-shadow` 属性语义对齐，同时也满足了 Flutter 框架中 `Shadow` 类的数据需求。

## 架构位置

```
skia::textlayout 命名空间
  TextStyle
    └── fTextShadows: std::vector<TextShadow>  ← 本文件定义的阴影数据
          └── 在渲染阶段通过 ParagraphPainter::drawTextShadow() 逐一绘制
```

`TextShadow` 是文本样式系统中的值类型，在布局阶段附加到文本运行（text run），在渲染阶段由 `ParagraphPainter` 的 `drawTextShadow` 方法绘制。多个阴影按照数组顺序依次绘制，后面的阴影覆盖在前面的阴影之上。

## 主要类与结构体

### TextShadow
- 值类型类，描述单个文本阴影效果
- 成员变量：
  - `fColor`（`SkColor`，32 位 ARGB）: 阴影颜色，默认黑色 `SK_ColorBLACK`
  - `fOffset`（`SkPoint`，两个 float）: 阴影偏移量（x, y），正 x 向右，正 y 向下
  - `fBlurSigma`（`double`，64 位浮点）: 高斯模糊的 sigma 值，默认 0.0（无模糊），值越大模糊越强

## 公共 API 函数

### 构造函数
```cpp
TextShadow();
TextShadow(SkColor color, SkPoint offset, double blurSigma);
```
默认构造函数创建一个不产生视觉效果的阴影（黑色、零偏移、零模糊）。参数化构造函数允许指定所有属性。

### 比较运算符
```cpp
bool operator==(const TextShadow& other) const;
bool operator!=(const TextShadow& other) const;
```
支持相等性比较，用于文本样式匹配和段落缓存判断。两个阴影相等当且仅当颜色、偏移和模糊 sigma 完全相同。

### `hasShadow`
```cpp
bool hasShadow() const;
```
检查是否实际存在视觉上可见的阴影效果。该方法检查颜色是否非透明、偏移是否非零、模糊是否非零等条件，用于在渲染路径中快速跳过不可见的阴影。

## 内部实现细节

- 使用 `double` 而非 `SkScalar`（即 `float`）存储 `fBlurSigma`，这提供了更高的精度。这一设计选择可能源于与 Flutter/Dart 的兼容需求，因为 Dart 语言中的 `double` 类型为 64 位 IEEE 754 浮点数。在 Skia 内部绘制时，该值会被截断为 `SkScalar`（float）。
- `fOffset` 使用 `SkPoint` 类型（两个 float），天然支持浮点精度的亚像素偏移。
- `hasShadow()` 提供快速检测，避免在无阴影（默认构造或完全透明）时执行不必要的模糊和绘制操作。
- 所有成员变量均为公开（`public`），这在 Skia 的数据传输类型中是常见做法，简化了直接访问。

## 依赖关系

- **Skia 核心**: `SkColor`（`include/core/SkColor.h`，32 位 ARGB 颜色类型）、`SkPoint`（`include/core/SkPoint.h`，二维浮点点）

## 设计模式与设计决策

1. **值语义设计**: `TextShadow` 作为简单的数据容器，使用值类型设计，支持拷贝和比较，适合存储在 `std::vector` 中。整个对象大小约 24 字节（4 + 8 + 8 + padding），拷贝开销极低。

2. **默认值策略**: 成员变量提供合理的默认值（黑色、零偏移、零模糊），使得默认构造的 `TextShadow` 不产生视觉效果。这避免了未初始化对象导致意外渲染结果。

3. **阴影检测**: `hasShadow()` 方法封装了阴影存在性的判断逻辑，避免调用方自行检查各个属性。这是一个关键的性能优化入口。

4. **与 CSS/Flutter 对齐**: 三个属性（颜色、偏移、模糊）直接对应 CSS `text-shadow` 属性的三个参数，以及 Flutter `Shadow` 类的字段。

## 性能考量

- 作为轻量级值类型（约 24 字节），拷贝开销极低，适合在 vector 中按值存储。
- `hasShadow()` 可用于跳过无阴影文本的阴影绘制路径，避免不必要的高斯模糊计算。
- 多阴影场景下，每个阴影需要单独的 `drawTextShadow` 调用，每次调用都涉及高斯模糊（当 `fBlurSigma > 0` 时），因此阴影数量应保持较少。
- 比较运算符用于缓存键匹配，直接比较基本类型值，效率很高。

## 相关文件

- `modules/skparagraph/include/TextStyle.h` - 使用 `TextShadow` 的文本样式类（`addShadow`/`getShadows`/`resetShadows` 方法）
- `modules/skparagraph/include/ParagraphPainter.h` - `drawTextShadow` 绘制方法声明
- `modules/skparagraph/src/TextShadow.cpp` - 构造函数、比较运算符和 `hasShadow` 的实现
- `include/core/SkColor.h` - `SkColor` 类型和颜色常量
- `include/core/SkPoint.h` - `SkPoint` 二维点类型
