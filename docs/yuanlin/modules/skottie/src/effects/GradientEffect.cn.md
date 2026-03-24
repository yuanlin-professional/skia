# GradientEffect

> 源文件: modules/skottie/src/effects/GradientEffect.cpp

## 概述

GradientEffect 模块实现了渐变叠加效果(Gradient Ramp Effect),允许在图层上叠加线性或径向渐变。该效果对应 Adobe After Effects 的渐变渐变效果,常用于创建渐变遮罩、颜色叠加和视觉过渡效果。

## 架构位置

GradientEffect 位于 Skottie 效果系统的渲染效果分支:

```
modules/skottie/
  └── src/
      └── effects/
          ├── GradientEffect.cpp   # 渐变效果实现
          ├── Effects.h            # 效果接口
          └── ShiftChannelsEffect.cpp  # 其他渲染效果
```

该模块使用 Scene Graph 的着色器效果节点,通过渐变着色器实现高性能的GPU加速渲染。

## 主要类与结构体

### GradientRampEffectAdapter

渐变效果适配器,管理渐变类型、颜色和位置参数。

```cpp
class GradientRampEffectAdapter final : public AnimatablePropertyContainer
```

**核心成员:**
- `fShaderEffect` - `sksg::ShaderEffect` 节点,应用渐变着色器
- `fGradient` - `sksg::Gradient` 渐变对象(线性或径向)
- `fInstanceType` - 当前渐变实例类型
- `fStartColor` / `fEndColor` - 渐变起始和结束颜色
- `fStartPoint` / `fEndPoint` - 渐变起始和结束位置
- `fShape` - 渐变形状(1=线性, 7=径向)
- `fBlend` - 混合比例
- `fScatter` - 散射参数

**实例类型枚举:**
```cpp
enum class InstanceType {
    kNone,    // 未初始化
    kLinear,  // 线性渐变
    kRadial,  // 径向渐变
};
```

## 公共 API 函数

### attachGradientEffect

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachGradientEffect(
    const skjson::ArrayValue& jprops,
    sk_sp<sksg::RenderNode> layer) const
```

为图层附加渐变效果。

**参数:**
- `jprops` - JSON 属性数组
- `layer` - 源渲染节点

**返回值:** 应用渐变效果的渲染节点

**属性索引:**
```cpp
enum : size_t {
    kStartPoint_Index = 0,   // 起始点
    kStartColor_Index = 1,   // 起始颜色
    kEndPoint_Index = 2,     // 结束点
    kEndColor_Index = 3,     // 结束颜色
    kRampShape_Index = 4,    // 渐变形状
    kRampScatter_Index = 5,  // 散射
    kBlendRatio_Index = 6,   // 混合比例
};
```

## 内部实现细节

### Scene Graph 结构

渐变效果构建以下 SG 片段:

```
ShaderEffect [fShaderEffect]
  ├── GradientShader [fGradient]
  └── child/wrapped fragment
```

### 动态实例类型切换

渐变类型可以动画化,需要在线性和径向之间切换:

```cpp
auto update_gradient = [this] (InstanceType new_type) {
    if (new_type != fInstanceType) {
        fGradient = new_type == InstanceType::kLinear
                ? sk_sp<sksg::Gradient>(sksg::LinearGradient::Make())
                : sk_sp<sksg::Gradient>(sksg::RadialGradient::Make());

        fShaderEffect->setShader(fGradient);
        fInstanceType = new_type;
    }

    fGradient->setColorStops({{0, fStartColor},
                              {1,   fEndColor}});
};
```

### 形状值映射

```cpp
static constexpr int kLinearShapeValue = 1;
const auto instance_type = (SkScalarRoundToInt(fShape) == kLinearShapeValue)
        ? InstanceType::kLinear
        : InstanceType::kRadial;
```

### 线性渐变参数

```cpp
if (instance_type == InstanceType::kLinear) {
    auto* lg = static_cast<sksg::LinearGradient*>(fGradient.get());
    lg->setStartPoint(start_point);
    lg->setEndPoint(end_point);
}
```

### 径向渐变参数

```cpp
else {
    SkASSERT(instance_type == InstanceType::kRadial);

    auto* rg = static_cast<sksg::RadialGradient*>(fGradient.get());
    rg->setStartCenter(start_point);
    rg->setEndCenter(start_point);  // 起始和结束中心相同
    rg->setEndRadius(SkPoint::Distance(start_point, end_point));
}
```

径向渐变的半径由起始点和结束点之间的距离决定。

### 颜色停止点

使用简单的两色渐变:
```cpp
fGradient->setColorStops({{0, fStartColor},
                          {1,   fEndColor}});
```

位置 0 对应起始颜色,位置 1 对应结束颜色。

## 依赖关系

### Skia 核心依赖
- `SkPoint` - 2D 点坐标
- `SkScalar` - 标量值类型

### Skottie 框架依赖
- `SkottiePriv.h` - 内部构建工具
- `SkottieValue.h` - `ColorValue`, `Vec2Value`, `ScalarValue`
- `animator/Animator.h` - 动画属性系统
- `effects/Effects.h` - `EffectBuilder`

### Scene Graph 依赖
- `sksg::Gradient` - 渐变基类
- `sksg::LinearGradient` - 线性渐变
- `sksg::RadialGradient` - 径向渐变
- `sksg::ShaderEffect` - 着色器效果节点
- `sksg::RenderNode` - 渲染节点基类

## 设计模式与设计决策

### 策略模式

使用 `InstanceType` 枚举和动态类型切换实现策略模式,在运行时选择线性或径向渐变。

### 延迟初始化

渐变对象在第一次同步时才创建:

```cpp
InstanceType fInstanceType = InstanceType::kNone;
```

### Lambda 封装

使用 lambda 函数封装渐变更新逻辑,减少代码重复:

```cpp
auto update_gradient = [this] (InstanceType new_type) { ... };
```

### 类型安全的向下转型

使用 `static_cast` 和 `SkASSERT` 确保类型安全:

```cpp
auto* lg = static_cast<sksg::LinearGradient*>(fGradient.get());
```

## 性能考量

### 实例复用

只在类型变化时创建新渐变对象,避免不必要的对象分配:

```cpp
if (new_type != fInstanceType) {
    // 仅在类型变化时创建新实例
}
```

### GPU 加速

使用 `sksg::ShaderEffect` 和 Skia 渐变着色器,利用 GPU 进行高性能渲染。

### 最小化状态更新

每次同步只更新必要的渐变参数(位置、颜色),而不重建整个渐变。

### 两色优化

当前实现仅支持两色渐变,简化了颜色停止点的计算和存储。

## 相关文件

- `modules/sksg/include/SkSGGradient.h` - Scene Graph 渐变节点定义
- `modules/sksg/include/SkSGRenderEffect.h` - 着色器效果节点
- `modules/skottie/src/effects/Effects.h` - 效果系统接口
- `modules/skottie/src/SkottieValue.h` - 可动画值类型
- `modules/skottie/src/animator/Animator.h` - 动画属性容器

**注意:** `fBlend` 和 `fScatter` 参数尚未实现,代码中标记为 TODO。
