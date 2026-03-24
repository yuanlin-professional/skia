# skottie/src/animator - 关键帧动画系统

## 概述

`animator/` 目录实现了 Skottie 的关键帧动画系统。该系统负责将 Lottie JSON 中的关键帧数据转换为可以在运行时高效求值的动画器对象。当客户端调用 `Animation::seekFrame()` 时,所有动画器被遍历,根据当前时间计算插值结果,并将结果推送到对应的场景图节点。

动画系统采用分层架构:`Animator` 基类定义了 `seek(t)` 接口;`AnimatablePropertyContainer` 管理一组子动画器并在求值后触发同步;`KeyframeAnimator` 处理具体的关键帧插值逻辑,支持常量、线性和贝塞尔曲线三种插值模式。

## 架构图

```
+-------------------------------------------+
|           Animator (基类)                  |
|   seek(t) -> onSeek(t) -> StateChanged    |
+-------------------------------------------+
        |                       |
        v                       v
+--------------------+  +------------------+
| AnimatableProperty |  | KeyframeAnimator |
| Container          |  | (关键帧求值)     |
|                    |  |                  |
| bind(abuilder,     |  | fKFs[]: Keyframe |
|   jobj, &value)    |  | fCMs[]: CubicMap |
|                    |  |                  |
| onSeek(t):         |  | getLERPInfo(t):  |
|   遍历子动画器     |  |   -> weight      |
|   onSync()         |  |   -> vrec0,vrec1 |
+--------------------+  +------------------+
        |                       |
        v                       v
+------------------------------------------------+
|              具体动画器实现                       |
|                                                 |
| ScalarKeyframeAnimator  -> float               |
| Vec2KeyframeAnimator    -> SkV2                |
| VectorKeyframeAnimator  -> std::vector<float>  |
| ShapeKeyframeAnimator   -> SkPath              |
| TextKeyframeAnimator    -> TextValue (离散)    |
+------------------------------------------------+
```

## 目录结构

```
animator/
├── BUILD.bazel                      # Bazel 构建配置
├── Animator.h                       # 基类: Animator, AnimatablePropertyContainer
├── Animator.cpp                     # AnimatablePropertyContainer 实现
├── KeyframeAnimator.h               # 关键帧: Keyframe, KeyframeAnimator, AnimatorBuilder
├── KeyframeAnimator.cpp             # 关键帧解析和 LERP 计算
├── ScalarKeyframeAnimator.cpp       # 标量 (float) 动画器
├── Vec2KeyframeAnimator.cpp         # 二维向量 (SkV2) 动画器
├── VectorKeyframeAnimator.cpp       # 动态向量/颜色 动画器
├── VectorKeyframeAnimator.h         # VectorKeyframeAnimator 声明
├── ShapeKeyframeAnimator.cpp        # 路径形状 (SkPath) 动画器
└── TextKeyframeAnimator.cpp         # 文本值 (TextValue) 动画器 (离散)
```

## 关键类与函数

### Animator 基类

```cpp
class Animator : public SkRefCnt {
    using StateChanged = bool;
    StateChanged seek(float t);       // 外部入口
protected:
    virtual StateChanged onSeek(float t) = 0; // 派生类实现
};
```

### AnimatablePropertyContainer

所有需要绑定动画属性的适配器的基类。核心机制:

```cpp
class AnimatablePropertyContainer : public Animator {
    // 属性绑定: 根据 JSON 是否包含关键帧,自动选择立即应用或创建动画器
    template <typename T>
    bool bind(const AnimationBuilder&, const skjson::ObjectValue*, T*);

    // 运动路径绑定 (带自动朝向)
    bool bindAutoOrientable(abuilder, jobject, SkV2* v, float* orientation);

    // 判断是否为静态属性(无子动画器且无插槽 ID)
    bool isStatic() const;

protected:
    // 派生类实现: 将当前值推送到场景图节点
    virtual void onSync() = 0;
};
```

### Keyframe 结构

```cpp
struct Keyframe {
    float    t;       // 时间 (帧索引)
    Value    v;       // 值 (内联标量或外部索引)
    uint32_t mapping; // 插值方式:
                      //   0 = 常量 (kConstantMapping)
                      //   1 = 线性 (kLinearMapping)
                      //   n = 贝塞尔 (cubic_mappers[n-2])
};
```

### KeyframeAnimator

```cpp
class KeyframeAnimator : public Animator {
    struct LERPInfo {
        float           weight;   // 插值权重 [0..1]
        Keyframe::Value vrec0;    // 起始值
        Keyframe::Value vrec1;    // 结束值
    };

    LERPInfo getLERPInfo(float t) const;  // 核心: 时间 -> 插值信息
    bool isConstant() const;              // 单帧 = 常量
};
```

### AnimatorBuilder

用于解析 JSON 关键帧数组并构建 `KeyframeAnimator`:

```cpp
class AnimatorBuilder : public SkNoncopyable {
    virtual sk_sp<KeyframeAnimator> makeFromKeyframes(abuilder, jarray);
    virtual sk_sp<Animator> makeFromExpression(exprMgr, expr);
    virtual bool parseValue(abuilder, jvalue) const;
protected:
    virtual bool parseKFValue(abuilder, jobj, jvalue, Keyframe::Value*);
    bool parseKeyframes(abuilder, jarray);
};
```

### 插值函数

```cpp
template <typename T>
T Lerp(const T& a, const T& b, float t) { return a + (b - a) * t; }
```

## 数据流

```
JSON 关键帧数组: [{"t":0,"s":[0],"e":[100]}, {"t":30,"s":[100]}]
                                    |
                                    v
              AnimatorBuilder::parseKeyframes()
                  解析每个关键帧记录:
                  - 时间 t
                  - 值 v (标量内联 / 索引外部存储)
                  - 插值映射 mapping (解析贝塞尔控制点)
                                    |
                                    v
              构建 vector<Keyframe> + vector<SkCubicMap>
                                    |
                                    v
              KeyframeAnimator 实例 (持有 fKFs + fCMs)
                                    |
              === 运行时求值 ===     |
                                    v
              seek(t):
                  find_segment(t)  // 二分查找 + 缓存段
                      -> KFSegment { kf0, kf1 }
                  compute_weight(seg, t)
                      -> 线性权重或贝塞尔曲线映射
                  getLERPInfo()
                      -> LERPInfo { weight, vrec0, vrec1 }
                                    |
                                    v
              派生类执行最终插值:
                  ScalarKFA:  Lerp(flt0, flt1, weight) -> float
                  Vec2KFA:    Lerp(v0, v1, weight) -> SkV2
                  VectorKFA:  逐元素 Lerp -> vector<float>
                  ShapeKFA:   SkPath::interpolate(path0, path1, weight)
                  TextKFA:    离散切换 (weight < 1 ? v0 : v1)
```

## 设计模式分析

- **策略模式**: `AnimatorBuilder` 作为关键帧解析的策略接口,不同动画类型提供不同的 `parseKFValue` 和 `makeFromKeyframes` 实现。
- **缓存段优化**: `KeyframeAnimator` 缓存最近使用的 `KFSegment`,利用动画通常顺序播放的特性避免重复搜索。
- **值类型双态**: `Keyframe::Value` 使用联合体 (`union`) 存储标量值 (`float`) 或外部索引 (`uint32_t`),由 `Keyframe::Value::Type` 区分,避免间接引用的开销。

## 相关文档与参考

- **父目录**: `docs/yuanlin/modules/skottie/src/README.md`
- **skottie 主文档**: `docs/yuanlin/modules/skottie/README.md`
- **SkCubicMap**: `include/core/SkCubicMap.h` - 贝塞尔曲线插值映射
