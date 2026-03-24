# TextAnimator - Skottie 文本动画器

> 源文件: [`modules/skottie/src/text/TextAnimator.h`](../../../../modules/skottie/src/text/TextAnimator.h), [`modules/skottie/src/text/TextAnimator.cpp`](../../../../modules/skottie/src/text/TextAnimator.cpp)

## 概述

TextAnimator 实现了 AE 文本层的属性动画器系统。每个文本动画器包含一组可动画的属性（位置、缩放、旋转、颜色、不透明度等）和一组范围选择器（RangeSelector）。范围选择器为每个字形生成覆盖值 [0..1]，动画器使用该覆盖值作为插值权重来调制属性值。

## 架构位置

位于 Skottie 文本子系统中：

- **调用者**: TextAdapter（在 onSync 时调用 modulateProps）
- **协作组件**: RangeSelector（范围选择器）
- **数据结构**: AnimatedProps -> ResolvedProps 映射

## 主要类与结构体

### `TextAnimator` 类

### `AnimatedProps` 结构体
直接映射 AE 属性的动画值：位置、缩放、旋转、颜色、不透明度、模糊、字间距、描边宽度、行间距。

### `ResolvedProps` 结构体
解析后的属性值，使用最终渲染所需的格式（SkV3、SkColor、float 等）。

### `AnimatedPropsModulator` 结构体
每个字形的调制状态：累积的属性值（props）和当前动画器的覆盖值（coverage）。

### `DomainSpan` / `DomainMap` / `DomainMaps`
域映射描述索引域（字符、单词、行）如何映射到片段索引范围，用于范围选择器的域感知选择。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Make(janimator, abuilder, acontainer)` | 从 JSON 创建文本动画器 |
| `modulateProps(maps, buf)` | 对调制缓冲区中的每个片段应用属性调制 |
| `hasBlur()` | 是否包含模糊属性 |
| `requiresAnchorPoint()` | 是否需要锚点信息（缩放/旋转） |
| `requiresLineAdjustments()` | 是否需要行级调整（字间距/行间距） |

## 内部实现细节

### 属性调制流程
1. 初始化覆盖值（无选择器时为 1，有选择器时为 0）
2. 各选择器累加覆盖值
3. 使用覆盖值调制属性：
   - **组合型属性**（位置、旋转、缩放、字间距、模糊、行间距、描边宽度）: `value += animated_value * amount`
   - **插值型属性**（颜色、不透明度）: `value = lerp(value, animated_value, clamped_amount)`

### 颜色插值
使用 `Sk4f` 向量化 RGBA 线性插值。不透明度使用 clamped_amount（>= 0），避免负值产生无效颜色。

### 缩放组合
缩放使用乘法组合：`scale *= 1 + (animated_scale/100 - 1) * amount`，确保 amount=0 时无效果。

## 依赖关系

- `modules/skottie/src/text/RangeSelector.h` - 范围选择器
- `modules/skottie/src/animator/Animator.h` - AnimatablePropertyContainer
- `modules/skottie/src/SkottieValue.h` - 值类型

## 设计模式与设计决策

### 覆盖-调制分离
将范围选择（生成覆盖值）和属性调制（应用覆盖值）分为两个阶段，允许多个选择器和动画器灵活组合。

### 位标记优化
使用位字段（fHasFillColor、fHasStrokeColor 等）跟踪哪些属性被实际绑定，跳过未使用属性的调制。

## 性能考量

- 仅调制已绑定的属性
- 覆盖值计算使用向量化操作
- 线性复杂度：O(fragments * selectors)

## 相关文件

- `modules/skottie/src/text/TextAdapter.h` - 文本适配器（调用方）
- `modules/skottie/src/text/RangeSelector.h` - 范围选择器实现
