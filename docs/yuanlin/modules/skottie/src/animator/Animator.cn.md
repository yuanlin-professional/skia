# Animator

> 源文件
> - `modules/skottie/src/animator/Animator.h`
> - `modules/skottie/src/animator/Animator.cpp`

## 概述

`Animator` 是 Skottie 动画系统的根基抽象类,定义了所有动画器的统一接口和生命周期管理。该模块提供了时间驱动的动画更新机制,所有可动画的属性都通过继承该类实现。`AnimatablePropertyContainer` 作为动画器的容器类,负责管理多个子动画器的协同工作,提供属性绑定、同步和批量更新功能。

该模块是 Skottie 动画系统的核心抽象层,确保了动画的一致性和可扩展性。通过引用计数管理生命周期,支持动画器的组合和复用。它还提供了静态属性优化、表达式支持、插槽系统集成等高级功能。

## 架构位置

`Animator` 位于 Skottie 动画系统的顶层抽象:

```
Skottie 动画引擎
├── Animator ← 本模块 (抽象基类)
│   ├── KeyframeAnimator (关键帧动画)
│   │   ├── VectorKeyframeAnimator
│   │   ├── ScalarKeyframeAnimator
│   │   └── ShapeKeyframeAnimator
│   ├── ExpressionAnimator (表达式动画)
│   └── AnimatablePropertyContainer (属性容器)
│       ├── Transform (变换)
│       ├── Paint (绘制样式)
│       ├── Effect (效果)
│       └── TextAnimator (文本动画)
└── Scene Graph (场景图)
```

`AnimatablePropertyContainer` 的作用:
- 管理子动画器的集合
- 处理属性绑定逻辑
- 协调动画器的同步
- 支持静态属性优化

## 主要类与结构体

### Animator

动画器抽象基类,定义核心接口:

```cpp
class Animator : public SkRefCnt {
public:
    using StateChanged = bool;

    // 公共接口：驱动动画到指定时间
    StateChanged seek(float t) {
        return this->onSeek(t);
    }

protected:
    Animator() = default;

    // 派生类实现的虚函数
    virtual StateChanged onSeek(float t) = 0;

private:
    Animator(const Animator&) = delete;
    Animator& operator=(const Animator&) = delete;
};
```

**设计要点**:
- 继承自 `SkRefCnt`,支持引用计数管理
- 不可复制,确保唯一所有权
- 返回 `StateChanged` 标志,指示状态是否改变
- 使用模板方法模式,`seek()` 调用虚函数 `onSeek()`

### AnimatablePropertyContainer

可动画属性容器,管理属性和动画器:

```cpp
class AnimatablePropertyContainer : public Animator {
public:
    // 属性绑定接口
    template <typename T>
    bool bind(const AnimationBuilder&, const skjson::ObjectValue*, T*);

    template <typename T>
    bool bind(const AnimationBuilder& abuilder,
              const skjson::ObjectValue* jobject, T& v) {
        return this->bind<T>(abuilder, jobject, &v);
    }

    // 自动定向绑定（运动路径）
    bool bindAutoOrientable(const AnimationBuilder& abuilder,
                            const skjson::ObjectValue* jobject,
                            SkV2* v, float* orientation);

    // 检查是否为静态（无动画）
    bool isStatic() const {
        return fAnimators.empty() && !fHasSlotID;
    }

protected:
    friend class skottie::SlotManager;

    // 派生类实现的同步回调
    virtual void onSync() = 0;

    void shrink_to_fit();
    void attachDiscardableAdapter(sk_sp<AnimatablePropertyContainer>);

private:
    StateChanged onSeek(float) final;
    bool bindImpl(const AnimationBuilder&,
                  const skjson::ObjectValue*,
                  AnimatorBuilder&);

    std::vector<sk_sp<Animator>> fAnimators;  // 子动画器集合
    bool fHasSynced = false;                  // 是否已同步
    bool fHasSlotID = false;                  // 是否有插槽ID
};
```

## 公共 API 函数

### Animator 接口

**seek**
```cpp
StateChanged seek(float t);
```
驱动动画到指定时间 `t`,返回状态是否改变。这是动画系统的主入口,被动画播放器在每帧调用。

**onSeek (虚函数)**
```cpp
virtual StateChanged onSeek(float t) = 0;
```
派生类实现的具体动画逻辑,根据时间 `t` 更新动画状态。

### AnimatablePropertyContainer 接口

**bind (模板方法)**
```cpp
template <typename T>
bool bind(const AnimationBuilder& abuilder,
          const skjson::ObjectValue* jprop,
          T* value);
```
属性绑定的核心方法,根据 JSON 属性描述,自动处理静态值、关键帧动画或表达式动画:
1. 解析插槽ID（如果存在）
2. 检查表达式属性
3. 尝试解析静态值
4. 创建关键帧动画器
5. 优化常量动画

**bindAutoOrientable**
```cpp
bool bindAutoOrientable(const AnimationBuilder& abuilder,
                        const skjson::ObjectValue* jobject,
                        SkV2* v, float* orientation);
```
特殊的向量绑定,支持运动路径自动定向。当对象沿路径运动时,自动计算方向角度。

**isStatic**
```cpp
bool isStatic() const;
```
检查容器是否为静态（无动画和插槽）。静态容器可以优化处理,避免每帧更新。

**shrink_to_fit**
```cpp
void shrink_to_fit();
```
释放动画器数组的多余容量,减少内存占用。在构建完成后调用。

**attachDiscardableAdapter**
```cpp
void attachDiscardableAdapter(sk_sp<AnimatablePropertyContainer> child);
```
附加子容器:
- 如果子容器是静态的,立即求值并丢弃
- 否则添加到动画器列表

**onSync (虚函数)**
```cpp
virtual void onSync() = 0;
```
派生类实现的同步回调,在动画状态改变后调用。用于将属性值同步到场景图节点。

## 内部实现细节

### 动画器生命周期

`AnimatablePropertyContainer::onSeek` 实现了动画器的协同更新:

```cpp
Animator::StateChanged AnimatablePropertyContainer::onSeek(float t) {
    // 第一次 seek 必须触发同步,确保场景图正确初始化
    bool changed = !fHasSynced;

    // 更新所有子动画器
    for (const auto& animator : fAnimators) {
        changed |= animator->seek(t);
    }

    // 如果有变化,触发同步回调
    if (changed) {
        this->onSync();
        fHasSynced = true;
    }

    return changed;
}
```

**关键设计决策**:
1. **首次同步保证**: 即使没有动画器,第一次也会触发同步
2. **批量更新**: 所有子动画器并行更新
3. **变更传播**: 任一子动画器变化都触发同步
4. **同步标记**: 避免重复的初始化操作

### 属性绑定逻辑

`bindImpl` 实现了复杂的属性绑定决策树:

```cpp
bool AnimatablePropertyContainer::bindImpl(
    const AnimationBuilder& abuilder,
    const skjson::ObjectValue* jprop,
    AnimatorBuilder& builder) {

    if (!jprop) return false;

    // 1. 处理插槽ID
    if (const skjson::StringValue* jpropSlotID = (*jprop)["sid"]) {
        if (!abuilder.getSlotsRoot()) {
            abuilder.log(Logger::Level::kWarning, jprop,
                "Slotid found but no slots were found...");
        } else {
            const skjson::ObjectValue* slot =
                (*(abuilder.getSlotsRoot()))[jpropSlotID->begin()];
            if (slot) {
                jprop = (*slot)["p"];  // 使用插槽属性
            }
        }
    }

    // 2. 处理表达式
    if (const skjson::StringValue* expr = (*jprop)["x"]) {
        if (abuilder.expression_manager()) {
            builder.parseValue(abuilder, jpropK);
            sk_sp<Animator> expression_animator =
                builder.makeFromExpression(*abuilder.expression_manager(),
                                          expr->begin());
            if (expression_animator) {
                fAnimators.push_back(std::move(expression_animator));
                return true;
            }
        }
    }

    // 3. 尝试静态值
    if (!ParseDefault<bool>(jpropA, false)) {
        if (builder.parseValue(abuilder, jpropK)) {
            return true;  // 静态属性
        }
    }

    // 4. 关键帧动画
    sk_sp<KeyframeAnimator> animator;
    const skjson::ArrayValue* jkfs = jpropK;
    if (jkfs && jkfs->size() > 0) {
        animator = builder.makeFromKeyframes(abuilder, *jkfs);
    }

    if (!animator) {
        abuilder.log(Logger::Level::kError, jprop,
            "Could not parse keyframed property.");
        return false;
    }

    // 5. 常量动画优化
    if (animator->isConstant()) {
        animator->seek(0);  // 立即应用并丢弃
    } else {
        fAnimators.push_back(std::move(animator));
    }

    return true;
}
```

**处理优先级**:
1. 插槽ID解析（最高优先级）
2. 表达式动画
3. 静态值
4. 关键帧动画（默认）

### 静态容器优化

`attachDiscardableAdapter` 对静态子容器进行优化:

```cpp
void AnimatablePropertyContainer::attachDiscardableAdapter(
    sk_sp<AnimatablePropertyContainer> child) {
    if (!child) return;

    if (child->isStatic()) {
        // 静态容器：立即求值并丢弃
        child->seek(0);
        return;
    }

    // 动画容器：添加到列表
    fAnimators.push_back(std::move(child));
}
```

这避免了维护不必要的静态容器引用。

### 常量动画优化

当所有关键帧值相同时,不保留动画器:

```cpp
if (animator->isConstant()) {
    // 所有关键帧常量,立即应用值并丢弃动画器
    animator->seek(0);
} else {
    fAnimators.push_back(std::move(animator));
}
```

减少运行时开销和内存占用。

### 插槽系统集成

支持 Lottie 插槽功能,允许运行时替换属性值:

```cpp
if (const skjson::StringValue* jpropSlotID = (*jprop)["sid"]) {
    // 查找插槽定义
    const skjson::ObjectValue* slot =
        (*(abuilder.getSlotsRoot()))[jpropSlotID->begin()];
    if (slot) {
        jprop = (*slot)["p"];  // 使用插槽属性替换原属性
    }
}
```

插槽提供了动态内容替换能力,无需修改动画数据。

### 表达式支持

检测并处理 Lottie 表达式属性:

```cpp
if (const skjson::StringValue* expr = (*jprop)["x"]) {
    if (abuilder.expression_manager()) {
        // 先解析默认值
        builder.parseValue(abuilder, jpropK);
        // 创建表达式动画器
        sk_sp<Animator> expression_animator =
            builder.makeFromExpression(*abuilder.expression_manager(),
                                      expr->begin());
        if (expression_animator) {
            fAnimators.push_back(std::move(expression_animator));
            return true;
        }
    }
}
```

表达式提供程序化动画能力,超越关键帧限制。

## 依赖关系

### 对外依赖

- **SkRefCnt**: 引用计数基类,提供智能指针支持
- **AnimationBuilder**: 动画构建器,提供解析上下文
- **AnimatorBuilder**: 动画器构建器,创建具体动画器实例
- **KeyframeAnimator**: 关键帧动画器基类
- **SlotManager**: 插槽管理器,处理动态内容替换
- **skjson**: JSON 解析库

### 内部依赖

- **SkottieJson**: JSON 解析工具 `ParseDefault`
- **SkottiePriv**: 私有工具函数
- **Logger**: 日志系统,报告错误和警告

### 被依赖情况

所有可动画的 Skottie 组件都依赖该模块:
- **Transform**: 变换动画
- **Paint**: 颜色、渐变等绘制属性动画
- **Effect**: 各种效果参数动画
- **TextAnimator**: 文本动画器
- **ShapeLayer**: 形状图层动画
- **ImageLayer**: 图像图层动画

## 设计模式与设计决策

### 模板方法模式

`Animator` 使用模板方法模式,`seek()` 定义算法骨架,`onSeek()` 由子类实现:

```cpp
StateChanged seek(float t) {
    return this->onSeek(t);  // 调用虚函数
}
```

这确保了统一的接口和可扩展的实现。

### 组合模式

`AnimatablePropertyContainer` 管理 `Animator` 集合,形成树形结构:

```cpp
std::vector<sk_sp<Animator>> fAnimators;
```

支持动画器的递归组合和批量更新。

### 策略模式

通过 `AnimatorBuilder` 注入不同的动画器创建策略:
- `VectorAnimatorBuilder` 用于向量属性
- `ScalarAnimatorBuilder` 用于标量属性
- `ShapeAnimatorBuilder` 用于形状路径

### 引用计数管理

使用 `SkRefCnt` 和 `sk_sp` 智能指针管理生命周期,避免内存泄漏:

```cpp
std::vector<sk_sp<Animator>> fAnimators;
```

自动管理引用计数,简化内存管理。

### 懒惰同步

只在状态实际改变时才调用 `onSync()`,避免不必要的场景图更新:

```cpp
if (changed) {
    this->onSync();
    fHasSynced = true;
}
```

### 不可复制设计

动画器明确禁止复制,确保唯一所有权:

```cpp
Animator(const Animator&) = delete;
Animator& operator=(const Animator&) = delete;
```

## 性能考量

### 批量更新

`onSeek` 遍历所有子动画器,但使用智能指针避免虚函数调用开销:

```cpp
for (const auto& animator : fAnimators) {
    changed |= animator->seek(t);
}
```

### 静态优化

静态容器立即求值并丢弃,避免运行时开销:

```cpp
if (child->isStatic()) {
    child->seek(0);
    return;  // 不添加到动画器列表
}
```

### 常量优化

常量动画器立即应用值并丢弃:

```cpp
if (animator->isConstant()) {
    animator->seek(0);
    // 不添加到 fAnimators
}
```

### 首次同步标记

使用 `fHasSynced` 标记避免重复的初始化:

```cpp
bool changed = !fHasSynced;
```

确保场景图正确设置,同时避免不必要的后续初始化。

### 内存紧凑

调用 `shrink_to_fit()` 释放多余容量:

```cpp
void AnimatablePropertyContainer::shrink_to_fit() {
    fAnimators.shrink_to_fit();
}
```

### 短路求值

使用位或操作符确保所有动画器都被更新:

```cpp
changed |= animator->seek(t);
```

不使用逻辑或 `||`,避免短路导致某些动画器不被更新。

## 相关文件

**头文件依赖**:
- `include/core/SkRefCnt.h` - 引用计数基类
- `modules/skottie/include/Skottie.h` - 公共 API

**实现文件依赖**:
- `modules/skottie/src/SkottieJson.h` - JSON 解析工具
- `modules/skottie/src/SkottiePriv.h` - 私有工具函数
- `modules/skottie/src/animator/KeyframeAnimator.h` - 关键帧动画器
- `modules/jsonreader/SkJSONReader.h` - JSON 读取器

**派生类**:
- `modules/skottie/src/animator/KeyframeAnimator.h` - 关键帧动画基类
- `modules/skottie/src/Transform.cpp` - 变换容器
- `modules/skottie/src/effects/` - 效果容器
- `modules/skottie/src/text/TextAnimator.h` - 文本动画容器

**相关模块**:
- `modules/skottie/src/animator/` - 动画器系统
- `modules/skottie/src/` - Skottie 核心
- `modules/skottie/include/SlotManager.h` - 插槽系统
