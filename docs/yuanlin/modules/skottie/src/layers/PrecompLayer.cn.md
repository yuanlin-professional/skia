# PrecompLayer

> 源文件: modules/skottie/src/layers/PrecompLayer.cpp

## 概述

`PrecompLayer.cpp` 实现了 Skottie 动画系统中的预合成层(Precomposition Layer)功能。预合成层允许将其他动画组合嵌套到当前动画中,支持时间重映射、时间拉伸和外部层集成。该模块是 Skottie 实现复杂层级动画结构的核心组件之一。

## 架构位置

该文件位于 Skottie 模块的层系统中:
- **模块**: `modules/skottie/src/layers/`
- **命名空间**: `skottie::internal`
- **依赖关系**: 依赖 Skia 核心图形库、SkSG 场景图系统和 Skottie 动画构建器
- **角色**: 作为 Skottie 层系统的一部分,处理预合成层的加载、时间映射和渲染

## 主要类与结构体

### TimeRemapper
```cpp
class TimeRemapper final : public AnimatablePropertyContainer
```
时间重映射器类,负责根据层的 "tm" 属性动画化时间。
- **成员变量**:
  - `fScale`: 时间缩放因子
  - `fT`: 标量时间值
- **核心方法**:
  - `t()`: 返回缩放后的时间值 `fT * fScale`
  - `onSync()`: 同步回调(空实现,仅跟踪时间)

### CompTimeMapper
```cpp
class CompTimeMapper final : public Animator
```
组合时间映射器,对子动画器应用偏移、缩放和重映射调整。
- **成员变量**:
  - `fAnimators`: 子动画器作用域
  - `fRemapper`: 时间重映射器智能指针
  - `fTimeBias`: 时间偏移
  - `fTimeScale`: 时间缩放
- **核心方法**:
  - `onSeek(float t)`: 处理时间查找,应用重映射或偏移缩放,并传播给子动画器

### SGAdapter
```cpp
class SGAdapter final : public sksg::RenderNode
```
场景图适配器,将 `ExternalLayer` 实现附加到动画场景图中。
- **成员变量**:
  - `fExternal`: 外部层智能指针
  - `fSize`: 层尺寸
  - `fCurrentT`: 当前时间
- **核心方法**:
  - `onRevalidate()`: 返回层边界矩形
  - `onRender()`: 渲染外部层内容
  - `onNodeAt()`: 点击测试实现

### AnimatorAdapter
```cpp
class AnimatorAdapter final : public Animator
```
动画器适配器,将 `SGAdapter` 连接到动画器树并分发 seek 事件。
- **成员变量**:
  - `fSGAdapter`: 场景图适配器智能指针
  - `fFps`: 帧率
- **核心方法**:
  - `onSeek(float t)`: 将时间转换为秒并设置到 SGAdapter

## 公共 API 函数

### attachExternalPrecompLayer
```cpp
sk_sp<sksg::RenderNode> AnimationBuilder::attachExternalPrecompLayer(
    const skjson::ObjectValue& jlayer,
    const LayerInfo& layer_info) const
```
附加外部预合成层到动画场景图。
- **参数**:
  - `jlayer`: JSON 层对象
  - `layer_info`: 层信息结构
- **返回值**: 渲染节点智能指针,失败返回 nullptr
- **功能**: 通过 `PrecompInterceptor` 加载外部预合成,创建 SGAdapter 和 AnimatorAdapter

### attachPrecompLayer
```cpp
sk_sp<sksg::RenderNode> AnimationBuilder::attachPrecompLayer(
    const skjson::ObjectValue& jlayer,
    LayerInfo* layer_info) const
```
附加预合成层,支持内部和外部预合成。
- **参数**:
  - `jlayer`: JSON 层对象
  - `layer_info`: 层信息结构指针(输出参数)
- **返回值**: 渲染节点智能指针
- **功能**:
  - 解析时间重映射 "tm" 属性
  - 处理起始时间 "st" 和拉伸时间 "sr"
  - 解析层尺寸 "w" 和 "h"
  - 尝试加载外部预合成或内部资产预合成
  - 创建时间映射器(如果需要)

## 内部实现细节

### 时间映射机制
预合成层支持三种时间变换:
1. **时间重映射 (Time Remapping)**: 通过 "tm" 属性完全由外部驱动时间
2. **起始时间偏移 (Start Time Bias)**: 通过 "st" 属性添加时间偏移 `-start_time`
3. **时间拉伸 (Stretch Time)**: 通过 "sr" 属性缩放时间 `1 / stretch_time`

时间变换公式:
```cpp
// 有时间重映射时
t = fRemapper->t()

// 无时间重映射时
t = (t + fTimeBias) * fTimeScale
```

### 外部层隔离渲染
`SGAdapter::onRender()` 使用 `ScopedRenderContext` 实现渲染隔离:
```cpp
const auto local_scope =
    ScopedRenderContext(canvas, ctx).setIsolation(this->bounds(),
                                                  canvas->getTotalMatrix(),
                                                  true);
```
这确保了所有待处理的效果通过独立层提交,因为外部内容不可知。

### 层尺寸解析
预合成层尺寸有两种来源:
1. **显式声明**: 从 jlayer 的 "w" 和 "h" 字段解析
2. **资产尺寸**: 字形预合成使用实际资产组合尺寸(当显式尺寸为空时)

### 作用域管理
使用 `AutoScope` 管理时间映射所需的局部动画器作用域:
```cpp
std::optional<AutoScope> local_scope;
if (requires_time_mapping) {
    local_scope.emplace(this);
}
// ... 构建预合成 ...
if (requires_time_mapping) {
    auto time_mapper = sk_make_sp<CompTimeMapper>(
        local_scope->release(), ...);
    fCurrentAnimatorScope->push_back(std::move(time_mapper));
}
```

## 依赖关系

### 外部依赖
- **Skia 核心**: `SkCanvas`, `SkPoint`, `SkRect`, `SkSize`, `SkScalar`, `SkMatrix`
- **SkSG 场景图**: `sksg::RenderNode`, `sksg::InvalidationController`
- **Skottie 模块**:
  - `ExternalLayer`: 外部层接口
  - `AnimationBuilder`: 动画构建器
  - `CompositionBuilder`: 组合构建器
  - `Animator`: 动画器基类
  - `AnimatablePropertyContainer`: 可动画属性容器

### 内部依赖
- `modules/skottie/include/ExternalLayer.h`: 外部层 API
- `modules/skottie/src/Composition.h`: 组合构建
- `modules/skottie/src/SkottiePriv.h`: 内部工具
- `modules/skottie/src/animator/Animator.h`: 动画器框架

## 设计模式与设计决策

### 适配器模式
使用多层适配器设计:
- **SGAdapter**: 将 `ExternalLayer` 适配到 `sksg::RenderNode`
- **AnimatorAdapter**: 将时间查找适配到 SGAdapter 的时间设置

这种设计允许外部层实现与 Skottie 内部场景图系统解耦。

### 策略模式
`CompTimeMapper` 实现了时间映射策略:
- 如果存在 `fRemapper`,使用时间重映射策略
- 否则使用线性偏移缩放策略

### 组合模式
动画器树使用组合模式:
- `CompTimeMapper` 包含子动画器作用域 `fAnimators`
- 时间查找递归传播到所有子节点

### 延迟初始化
使用 `std::optional<AutoScope>` 延迟创建局部作用域:
```cpp
std::optional<AutoScope> local_scope;
if (requires_time_mapping) {
    local_scope.emplace(this);
}
```
仅在需要时间映射时才创建作用域,避免不必要的开销。

## 性能考量

### 时间映射检测
提前检测是否需要时间映射:
```cpp
const auto requires_time_mapping =
    !SkScalarNearlyEqual(start_time, 0) ||
    !SkScalarNearlyEqual(stretch_time, 1) ||
    time_remapper;
```
避免不必要的作用域创建和时间映射器构建。

### 安全除法
使用 `sk_ieee_float_divide` 处理除法:
```cpp
t_scale = sk_ieee_float_divide(1, stretch_time);
// ...
std::isfinite(t_scale) ? t_scale : 0
```
防止除以零或无穷大结果导致的崩溃。

### 引用计数优化
广泛使用 `sk_sp` 智能指针管理生命周期:
- 避免手动内存管理
- 支持高效的对象共享
- 自动处理循环引用问题

### 渲染隔离开销
外部层渲染强制使用隔离层:
```cpp
setIsolation(this->bounds(), canvas->getTotalMatrix(), true)
```
这会增加渲染开销(额外的图层/表面),但对于未知内容是必需的。

## 相关文件

- `modules/skottie/include/ExternalLayer.h`: 外部层接口定义
- `modules/skottie/src/Composition.h`: 组合构建器
- `modules/skottie/src/SkottiePriv.h`: AnimationBuilder 和工具
- `modules/skottie/src/animator/Animator.h`: 动画器基类
- `modules/sksg/include/SkSGRenderNode.h`: 场景图渲染节点
- `modules/skottie/src/layers/`: 其他层实现(如 SolidLayer, ImageLayer)
- `modules/skottie/include/SkottieProperty.h`: 属性观察器接口
