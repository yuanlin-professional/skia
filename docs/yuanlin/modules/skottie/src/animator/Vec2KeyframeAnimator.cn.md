# Vec2KeyframeAnimator

> 源文件: modules/skottie/src/animator/Vec2KeyframeAnimator.cpp

## 概述

`Vec2KeyframeAnimator.cpp` 实现了二维向量值的关键帧动画,支持空间插值(沿贝塞尔曲线路径)和自动方向跟踪(rotation)。该模块是 Skottie 位置动画的核心实现,支持线性插值、三次贝塞尔曲线和路径跟随。

## 架构位置

- **模块**: `modules/skottie/src/animator/`
- **命名空间**: `skottie::internal`
- **角色**: 二维向量动画器,支持空间插值和方向跟踪

## 主要类与结构体

### Vec2KeyframeAnimator
```cpp
class Vec2KeyframeAnimator final : public KeyframeAnimator
```

**SpatialValue 结构**:
```cpp
struct SpatialValue {
    Vec2Value v2;
    sk_sp<SkContourMeasure> cmeasure;  // 可选的轮廓测量器
};
```

**成员变量**:
- `fValues`: 空间值向量
- `fVecTarget`: 位置目标指针(必需)
- `fRotTarget`: 旋转目标指针(可选)

**核心方法**:
- `onSeek()`: 处理空间插值或线性插值
- `update()`: 更新位置和旋转(从切线计算)

### Vec2ExpressionAnimator
```cpp
class Vec2ExpressionAnimator final : public Animator
```
使用数组表达式求值二维向量。

### Vec2AnimatorBuilder
```cpp
class Vec2AnimatorBuilder final : public AnimatorBuilder
```
构建器类,处理空间关键帧检测和贝塞尔曲线创建。

## 公共 API 函数

### bindAutoOrientable
```cpp
bool AnimatablePropertyContainer::bindAutoOrientable(
    const AnimationBuilder& abuilder,
    const skjson::ObjectValue* jprop,
    Vec2Value* v,
    float* orientation)
```
绑定二维向量属性,可选自动方向跟踪。

**JSON 参数**:
- `"s"`: 分离维度(Separate Dimensions)
  - `true`: X/Y 独立动画
  - `false`: 统一二维动画(默认)
- `"ti"`: 切入控制点(Tangent In)
- `"to"`: 切出控制点(Tangent Out)

### bind<Vec2Value>
```cpp
template <>
bool AnimatablePropertyContainer::bind<Vec2Value>(
    const AnimationBuilder& abuilder,
    const skjson::ObjectValue* jprop,
    Vec2Value* v)
```
简化版本,无方向跟踪。

## 内部实现细节

### 空间插值
```cpp
if (v0.cmeasure) {
    const float len = v0.cmeasure->length(),
           distance = len * lerp_info.weight;
    if (v0.cmeasure->getPosTan(distance, &pos, &tan)) {
        // 处理超调
        if (distance < 0 || distance > len) {
            const float overshoot = std::copysign(std::max(-distance, distance - len), distance);
            pos += tan * overshoot;
        }
        return this->update({pos.fX, pos.fY}, {tan.fX, tan.fY});
    }
}
```
沿贝塞尔曲线路径插值,处理缓动函数导致的超调。

### 旋转计算
```cpp
const auto new_rot_value = SkRadiansToDegrees(std::atan2(new_tan_value.y, new_tan_value.x));
```
从切线向量计算旋转角度。

### 空间关键帧检测
```cpp
bool parseKFValue(...) {
    fTi = ParseDefault<SkV2>(jkf["ti"], {0,0});
    fTo = ParseDefault<SkV2>(jkf["to"], {0,0});
    fPendingSpatial = fTi != SkV2{0,0} || fTo != SkV2{0,0};

    if (fPendingSpatial) {
        this->backfill_spatial(val);
    }
}
```
检测非零切线并回填空间插值数据。

### 贝塞尔曲线创建
```cpp
void backfill_spatial(const SpatialValue& val) {
    SkPathBuilder p;
    p.moveTo(prev_val.v2.x, prev_val.v2.y);
    p.cubicTo(prev_val.v2.x + fTo.x, prev_val.v2.y + fTo.y,
              val.v2.x + fTi.x, val.v2.y + fTi.y,
              val.v2.x, val.v2.y);
    prev_val.cmeasure = SkContourMeasureIter(p.detach(), false).next();
}
```
从控制点构造三次贝塞尔曲线并创建轮廓测量器。

### 直线优化
```cpp
// Check whether v0 and v1 have the same direction AND ||v0||>=||v1||
if (check_vecs(val.v2 - prev_val.v2, fTo) &&
    check_vecs(prev_val.v2 - val.v2, fTi)) {
    // 控制点在直线段上 => 退化为直线
    return;
}
```
检测控制点是否共线,退化为线性插值。

### 最后关键帧特殊处理
```cpp
// 旋转跟踪时,最后关键帧需要特殊处理:
// 它不存储空间信息但期望保持前一方向
if (fRotTarget && vidx == fValues.size() - 1 && vidx > 0) {
    lerp_info.weight = 1;
    lerp_info.vrec0 = {vidx - 1};
}
```
AE 语义:最后关键帧维持前一个方向。

### 分离维度模式
```cpp
if (ParseDefault<bool>((*jprop)["s"], false)) {
    bool boundX = this->bind(abuilder, (*jprop)["x"], &v->x);
    bool boundY = this->bind(abuilder, (*jprop)["y"], &v->y);
    return boundX || boundY;
}
```
X/Y 分量独立动画(每个作为标量)。

## 依赖关系

- **Skia 核心**: `SkContourMeasure`, `SkCubicMap`, `SkPathBuilder`, `SkPoint`
- **Skottie**: `KeyframeAnimator`, `ExpressionEvaluator`, `SlotManager`

## 设计模式

- **策略模式**: 空间插值 vs 线性插值
- **延迟初始化**: 仅在需要时创建 `SkContourMeasure`
- **回填模式**: 解析当前关键帧时更新前一关键帧

## 性能考量

- **直线检测**: 避免不必要的贝塞尔曲线创建
- **去重**: 相同连续值被去重(除非有空间数据)
- **内存优化**: `shrink_to_fit()` 释放多余容量
- **超调处理**: 使用切线外推避免边界夹紧

## 相关文件

- `modules/skottie/src/animator/KeyframeAnimator.h`: 基类
- `include/core/SkContourMeasure.h`: 路径测量 API
- `modules/skottie/src/SkottieValue.h`: `Vec2Value` 定义
- `modules/skottie/src/animator/ScalarKeyframeAnimator.cpp`: 标量动画器
