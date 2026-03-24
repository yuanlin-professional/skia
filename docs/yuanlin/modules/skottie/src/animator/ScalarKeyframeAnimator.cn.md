# ScalarKeyframeAnimator

> 源文件: modules/skottie/src/animator/ScalarKeyframeAnimator.cpp

## 概述

`ScalarKeyframeAnimator.cpp` 实现了标量值的关键帧动画和表达式动画。该模块将浮点数值内联存储在关键帧中,支持线性插值和三次贝塞尔缓动曲线。这是 Skottie 标量属性动画的核心实现,用于不透明度、旋转、缩放等单值属性。

## 架构位置

- **模块**: `modules/skottie/src/animator/`
- **命名空间**: `skottie::internal`
- **角色**: 标量值动画器,实现 `KeyframeAnimator` 和 `Animator` 接口

## 主要类与结构体

### ScalarKeyframeAnimator
```cpp
class ScalarKeyframeAnimator final : public KeyframeAnimator
```
标量关键帧动画器,在关键帧间线性插值。

**成员变量**:
- `fTarget`: 目标标量值指针

**核心方法**:
- `onSeek()`: 计算插值并更新目标值

### ScalarExpressionAnimator
```cpp
class ScalarExpressionAnimator final : public Animator
```
标量表达式动画器,使用表达式计算值。

**成员变量**:
- `fExpressionEvaluator`: 表达式求值器
- `fTarget`: 目标标量值指针

### ScalarAnimatorBuilder
```cpp
class ScalarAnimatorBuilder final : public AnimatorBuilder
```
构建器类,解析 JSON 并创建标量动画器。

## 公共 API 函数

### AnimatablePropertyContainer::bind<ScalarValue>
```cpp
template <>
bool AnimatablePropertyContainer::bind<ScalarValue>(
    const AnimationBuilder& abuilder,
    const skjson::ObjectValue* jprop,
    ScalarValue* v)
```
将 JSON 属性绑定到标量值,支持 SlotID 跟踪。

## 内部实现细节

### 插值计算
```cpp
*fTarget = Lerp(lerp_info.vrec0.flt, lerp_info.vrec1.flt, lerp_info.weight);
```
使用 `getLERPInfo()` 获取插值参数,执行线性插值。

### 表达式求值
```cpp
*fTarget = fExpressionEvaluator->evaluate(t);
```
在每次 seek 时求值表达式。

### SlotID 跟踪
```cpp
if (const auto* sid = ParseSlotID(jprop)) {
    abuilder.fSlotManager->trackScalarValue(SkString(sid->begin()), v, sk_ref_sp(this));
}
```
支持动态属性插槽系统。

## 依赖关系

- **Skia 核心**: `SkCubicMap`(缓动曲线)
- **Skottie**: `KeyframeAnimator`, `Animator`, `AnimatorBuilder`, `ExpressionEvaluator`, `SlotManager`

## 设计模式

- **模板方法**: 继承 `KeyframeAnimator` 并实现 `onSeek()`
- **构建器**: `ScalarAnimatorBuilder` 封装解析逻辑
- **策略**: 关键帧 vs 表达式两种动画策略

## 性能考量

- **内联存储**: 标量值直接存储在 `Keyframe::Value::flt`
- **指针更新**: 直接修改目标值,无需回调
- **状态检测**: 仅在值改变时返回 `true`

## 相关文件

- `modules/skottie/src/animator/KeyframeAnimator.h`: 基类
- `modules/skottie/src/animator/Vec2KeyframeAnimator.cpp`: 向量动画器
- `modules/skottie/src/SkottieValue.h`: `ScalarValue` 定义
