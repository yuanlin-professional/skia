# TextKeyframeAnimator

> 源文件: modules/skottie/src/animator/TextKeyframeAnimator.cpp

## 概述

`TextKeyframeAnimator.cpp` 实现了文本值的关键帧动画和表达式动画。该模块将文本值视为选择器而非插值目标,在关键帧间进行离散切换。这是 Skottie 文本属性动画的核心实现。

## 架构位置

- **模块**: `modules/skottie/src/animator/`
- **命名空间**: `skottie::internal`
- **角色**: 文本值动画器,实现关键帧选择逻辑

## 主要类与结构体

### TextKeyframeAnimator
```cpp
class TextKeyframeAnimator final : public KeyframeAnimator
```
文本关键帧动画器,使用选择器模式而非插值。

**成员变量**:
- `fValues`: 文本值向量(去重后)
- `fTarget`: 目标文本值指针

**核心方法**:
- `onSeek()`: 选择当前关键帧的文本值

### TextExpressionAnimator
```cpp
class TextExpressionAnimator final : public Animator
```
文本表达式动画器,使用字符串表达式。

**成员变量**:
- `fExpressionEvaluator`: 字符串表达式求值器
- `fTarget`: 目标文本值指针

### TextAnimatorBuilder
```cpp
class TextAnimatorBuilder final : public AnimatorBuilder
```
构建器类,解析 JSON 并去重文本值。

## 公共 API 函数

### AnimatablePropertyContainer::bind<TextValue>
```cpp
template <>
bool AnimatablePropertyContainer::bind<TextValue>(
    const AnimationBuilder& abuilder,
    const skjson::ObjectValue* jprop,
    TextValue* v)
```
将 JSON 属性绑定到文本值。

## 内部实现细节

### 选择器逻辑
```cpp
// Text value keyframes are treated as selectors, not as interpolated values.
if (*fTarget != fValues[SkToSizeT(lerp_info.vrec0.idx)]) {
    *fTarget = fValues[SkToSizeT(lerp_info.vrec0.idx)];
    return true;
}
```
使用 `vrec0.idx` 作为索引直接选择文本值,忽略插值权重。

### 去重优化
```cpp
// TODO: full deduping?
if (fValues.empty() || val != fValues.back()) {
    fValues.push_back(std::move(val));
}
v->idx = SkToU32(fValues.size() - 1);
```
相邻重复的文本值被去重,关键帧存储索引而非完整值。

### 表达式求值
```cpp
SkString old_value = fTarget->fText;
fTarget->fText = fExpressionEvaluator->evaluate(t);
```
仅更新文本字符串字段,保留其他文本属性。

### 内存优化
```cpp
fValues.reserve(jkfs.size());
// ...
fValues.shrink_to_fit();
```
预留后收缩向量容量。

## 依赖关系

- **Skia 核心**: `SkString`, `SkCubicMap`
- **Skottie**: `KeyframeAnimator`, `Animator`, `TextValue`, `ExpressionEvaluator`

## 设计模式

- **选择器模式**: 关键帧作为选择器,非插值器
- **模板方法**: 继承 `KeyframeAnimator` 实现特定逻辑
- **去重策略**: 基于相邻比较的简单去重

## 性能考量

- **去重**: 减少内存占用和比较开销
- **索引存储**: 关键帧存储 32 位索引而非完整文本
- **内存收缩**: `shrink_to_fit()` 释放多余容量
- **状态检测**: 仅在文本改变时返回 `true`

## 相关文件

- `modules/skottie/src/animator/KeyframeAnimator.h`: 基类
- `modules/skottie/src/text/TextValue.h`: `TextValue` 定义
- `modules/skottie/src/animator/ScalarKeyframeAnimator.cpp`: 标量动画器
