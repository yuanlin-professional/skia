# KeyframeAnimator

> 源文件
> - `modules/skottie/src/animator/KeyframeAnimator.h`
> - `modules/skottie/src/animator/KeyframeAnimator.cpp`

## 概述

`KeyframeAnimator` 是 Skottie 动画系统的核心组件,负责实现基于关键帧的属性动画插值。该模块将 Lottie JSON 格式的关键帧数据转换为高效的运行时动画结构,支持常量、线性和贝塞尔曲线三种插值模式。它提供了时间到值的映射功能,是所有 Skottie 动画属性的基础实现。

该模块采用优化的数据结构设计,通过缓存机制和二分查找算法实现高效的关键帧查询,适用于大量并发动画的场景。`KeyframeAnimator` 作为抽象基类,为各种类型的属性动画（如标量、向量、颜色等）提供统一的插值框架。

## 架构位置

`KeyframeAnimator` 位于 Skottie 动画引擎的核心层,是动画系统的基础设施:

```
Skottie 动画引擎
├── Animation (动画管理)
│   └── AnimationBuilder (构建器)
│       └── AnimatorBuilder
│           └── KeyframeAnimator ← 本模块
│               ├── ScalarKeyframeAnimator (标量动画)
│               ├── VectorKeyframeAnimator (向量动画)
│               ├── ColorKeyframeAnimator (颜色动画)
│               └── ShapeKeyframeAnimator (形状动画)
├── Scene Graph (场景图)
│   └── Animatable Properties (可动画属性)
└── Expression Engine (表达式引擎)
```

该模块为上层提供:
- 统一的关键帧解析接口
- 高效的时间插值计算
- 多种插值模式支持

## 主要类与结构体

### Keyframe

关键帧数据结构,存储单个关键帧的所有信息:

```cpp
struct Keyframe {
    struct Value {
        enum class Type {
            kIndex,    // 外部存储（索引）
            kScalar,   // 内联存储（浮点数）
        };

        union {
            uint32_t idx;  // 索引值
            float flt;     // 标量值
        };

        bool equals(const Value& other, Type ty) const;
    };

    float t;           // 时间点
    Value v;           // 关键帧值
    uint32_t mapping;  // 插值映射类型

    // 插值类型常量
    inline static constexpr uint32_t kConstantMapping = 0;   // 常量插值
    inline static constexpr uint32_t kLinearMapping = 1;     // 线性插值
    inline static constexpr uint32_t kCubicIndexOffset = 2;  // 立方插值偏移
};
```

### KeyframeAnimator

关键帧动画器基类,提供核心插值逻辑:

```cpp
class KeyframeAnimator : public Animator {
public:
    ~KeyframeAnimator() override;

    bool isConstant() const {
        return fKFs.size() == 1;
    }

protected:
    KeyframeAnimator(std::vector<Keyframe> kfs, std::vector<SkCubicMap> cms);

    struct LERPInfo {
        float weight;            // 插值权重 [0..1]
        Keyframe::Value vrec0;   // 起始值
        Keyframe::Value vrec1;   // 结束值
    };

    // 主入口：时间 -> 插值信息
    LERPInfo getLERPInfo(float t) const;

private:
    struct KFSegment {
        const Keyframe* kf0;  // 段起始关键帧
        const Keyframe* kf1;  // 段结束关键帧

        bool contains(float t) const;
    };

    KFSegment find_segment(float t) const;
    float compute_weight(const KFSegment& seg, float t) const;

    const std::vector<Keyframe> fKFs;      // 关键帧数组
    const std::vector<SkCubicMap> fCMs;    // 贝塞尔映射器
    mutable KFSegment fCurrentSegment;     // 缓存的当前段
};
```

### AnimatorBuilder

动画器构建器抽象基类,定义解析和构建接口:

```cpp
class AnimatorBuilder : public SkNoncopyable {
public:
    virtual ~AnimatorBuilder();

    // 从关键帧创建动画器
    virtual sk_sp<KeyframeAnimator> makeFromKeyframes(
        const AnimationBuilder&,
        const skjson::ArrayValue&) = 0;

    // 从表达式创建动画器
    virtual sk_sp<Animator> makeFromExpression(
        ExpressionManager&, const char*) = 0;

    // 解析值
    virtual bool parseValue(const AnimationBuilder&, const skjson::Value&) const = 0;

protected:
    explicit AnimatorBuilder(Keyframe::Value::Type ty);

    // 解析单个关键帧值
    virtual bool parseKFValue(const AnimationBuilder&,
                              const skjson::ObjectValue&,
                              const skjson::Value&,
                              Keyframe::Value*) = 0;

    // 解析关键帧数组
    bool parseKeyframes(const AnimationBuilder&, const skjson::ArrayValue&);

    std::vector<Keyframe> fKFs;         // 关键帧记录
    std::vector<SkCubicMap> fCMs;       // 立方映射器

private:
    uint32_t parseMapping(const skjson::ObjectValue&);

    const Keyframe::Value::Type keyframe_type;
    SkPoint prev_c0, prev_c1;           // 前一个立方控制点（去重用）
};
```

## 公共 API 函数

### KeyframeAnimator 核心方法

**isConstant**
```cpp
bool isConstant() const;
```
判断动画是否为常量（只有一个关键帧）。对于常量动画可以进行优化,跳过插值计算。

**getLERPInfo**
```cpp
LERPInfo getLERPInfo(float t) const;
```
核心插值函数,根据时间 `t` 返回插值信息。返回的 `LERPInfo` 包含:
- `weight`: 插值权重 [0..1]
- `vrec0`: 起始关键帧值
- `vrec1`: 结束关键帧值

处理三种边界情况:
1. `t <= 第一个关键帧时间`: 返回第一个关键帧值（钳位）
2. `t >= 最后一个关键帧时间`: 返回最后一个关键帧值（钳位）
3. 常量段（hold keyframe）: 返回起始帧值,权重为 0

### AnimatorBuilder 构建方法

**makeFromKeyframes**
```cpp
virtual sk_sp<KeyframeAnimator> makeFromKeyframes(
    const AnimationBuilder&,
    const skjson::ArrayValue&) = 0;
```
从 JSON 关键帧数组创建动画器实例,由子类实现具体类型的动画器创建逻辑。

**makeFromExpression**
```cpp
virtual sk_sp<Animator> makeFromExpression(
    ExpressionManager&, const char*) = 0;
```
从表达式字符串创建动画器,用于支持 Lottie 表达式功能。

**parseKeyframes**
```cpp
bool parseKeyframes(const AnimationBuilder& abuilder,
                   const skjson::ArrayValue& jkfs);
```
解析 JSON 关键帧数组,构建内部关键帧和立方映射器数组。支持两种格式:
1. 标准格式: 每个关键帧包含 `t` 和 `s`
2. 遗留格式: 每个关键帧包含 `t`、`s` 和 `e`

**parseValue**
```cpp
virtual bool parseValue(const AnimationBuilder&,
                       const skjson::Value&) const = 0;
```
解析单个值,用于解析静态（非动画）属性。

**parseKFValue**
```cpp
virtual bool parseKFValue(const AnimationBuilder&,
                         const skjson::ObjectValue&,
                         const skjson::Value&,
                         Keyframe::Value*) = 0;
```
解析关键帧值,将 JSON 值转换为 `Keyframe::Value` 结构,由子类实现类型特定的解析逻辑。

## 内部实现细节

### 二分查找算法

`find_segment` 使用二分查找在关键帧数组中定位包含给定时间的段:

```cpp
KeyframeAnimator::KFSegment KeyframeAnimator::find_segment(float t) const {
    auto kf0 = &fKFs.front();
    auto kf1 = &fKFs.back();

    // 二分查找,直到缩减到相邻的关键帧
    while (kf0 + 1 != kf1) {
        const auto mid_kf = kf0 + (kf1 - kf0) / 2;

        if (t >= mid_kf->t) {
            kf0 = mid_kf;
        } else {
            kf1 = mid_kf;
        }
    }

    return {kf0, kf1};
}
```

时间复杂度为 O(log n),适合大量关键帧的场景。

### 插值权重计算

`compute_weight` 计算给定时间在关键帧段中的插值权重:

```cpp
float KeyframeAnimator::compute_weight(const KFSegment &seg, float t) const {
    // 线性权重
    auto w = (t - seg.kf0->t) / (seg.kf1->t - seg.kf0->t);

    // 可选的立方映射
    if (seg.kf0->mapping >= Keyframe::kCubicIndexOffset) {
        const auto mapper_index = SkToSizeT(seg.kf0->mapping - Keyframe::kCubicIndexOffset);
        w = fCMs[mapper_index].computeYFromX(w);
    }

    return w;
}
```

支持两种模式:
1. **线性插值**: 直接使用线性权重
2. **贝塞尔插值**: 使用 `SkCubicMap` 将线性权重映射到曲线权重

### 段缓存机制

使用 `fCurrentSegment` 缓存最近访问的关键帧段:

```cpp
if (!fCurrentSegment.contains(t)) {
    fCurrentSegment = this->find_segment(t);
}
```

利用时间查询的局部性原理,大多数连续查询落在同一段内,避免重复的二分查找。

### 关键帧解析优化

**常量值检测**:
```cpp
bool constant_value = true;
for (size_t i = 0; i < jkfs.size(); ++i) {
    // ... 解析关键帧
    constant_value = constant_value && (v.equals(fKFs.front().v, keyframe_type));
}

if (constant_value) {
    // 所有关键帧值相同,只保留一个
    fKFs.resize(1);
}
```

当所有关键帧保持相同值时,只保留一个关键帧,优化内存和查询性能。

**重复值优化**:
```cpp
if (i > 0) {
    auto& prev_kf = fKFs.back();
    if (v.equals(prev_kf.v, keyframe_type)) {
        // 相邻关键帧值相同,使用常量映射
        prev_kf.mapping = Keyframe::kConstantMapping;
    }
}
```

检测相邻关键帧的重复值,自动转换为常量插值,避免不必要的计算。

### 立方映射器去重

```cpp
uint32_t AnimatorBuilder::parseMapping(const skjson::ObjectValue& jkf) {
    SkPoint c0, c1;
    if (!Parse(jkf["o"], &c0) || !Parse(jkf["i"], &c1) ||
        SkCubicMap::IsLinear(c0, c1)) {
        return Keyframe::kLinearMapping;
    }

    // 去除连续重复的立方映射器
    if (c0 != prev_c0 || c1 != prev_c1 || fCMs.empty()) {
        fCMs.emplace_back(c0, c1);
        prev_c0 = c0;
        prev_c1 = c1;
    }

    return SkToU32(fCMs.size()) - 1 + Keyframe::kCubicIndexOffset;
}
```

连续相同的贝塞尔控制点共享同一个 `SkCubicMap` 实例,减少内存占用和重复计算。

### 遗留格式兼容

支持 Lottie 遗留关键帧格式,其中每个关键帧包含起始值（`s`）和结束值（`e`）:

```cpp
if (!parsed && i > 0 && i == jkfs.size() - 1) {
    // 最后一个关键帧可能只有时间,从前一个关键帧的结束值获取
    const skjson::ObjectValue* prev_kf = jkfs[i - 1];
    parsed = this->parseKFValue(abuilder, jkf, (*prev_kf)["e"], v);
}
```

### 时间单调性检查

```cpp
if (i > 0) {
    auto& prev_kf = fKFs.back();
    if (t < prev_kf.t) {
        return false;  // 时间必须单调递增
    }
}
```

确保关键帧按时间顺序排列,违反则解析失败。

## 依赖关系

### 对外依赖

- **SkCubicMap**: 提供贝塞尔曲线插值功能
- **Animator**: 动画器基类,提供统一接口
- **AnimationBuilder**: 动画构建器,提供解析上下文
- **skjson**: JSON 解析库,提供数据访问接口
- **ExpressionManager**: 表达式管理器,用于表达式动画

### 内部依赖

- **SkottieJson**: 提供 JSON 解析辅助函数 `Parse`、`ParseDefault`
- **SkTo**: 提供类型转换函数 `SkToSizeT`、`SkToU32`

### 被依赖情况

- **VectorKeyframeAnimator**: 继承 `KeyframeAnimator`,实现向量属性动画
- **ScalarKeyframeAnimator**: 继承 `KeyframeAnimator`,实现标量属性动画
- **ColorKeyframeAnimator**: 继承 `KeyframeAnimator`,实现颜色属性动画
- **ShapeKeyframeAnimator**: 继承 `KeyframeAnimator`,实现形状路径动画
- **AnimationBuilder**: 使用 `AnimatorBuilder` 创建各类属性动画器

## 设计模式与设计决策

### 模板方法模式

`AnimatorBuilder` 定义了解析关键帧的模板流程（`parseKeyframes`）,而将类型特定的值解析委托给子类（`parseKFValue`）。这种设计使得不同类型的动画器可以共享通用的解析逻辑,只需实现值解析的差异部分。

### 策略模式

通过 `mapping` 字段封装不同的插值策略（常量、线性、贝塞尔）,运行时根据映射类型选择相应的插值算法。这种设计使得插值逻辑可扩展,易于添加新的插值模式。

### 享元模式

通过去重机制共享相同的 `SkCubicMap` 实例,减少内存占用。特别是在大量关键帧使用相同缓动曲线的场景下,效果显著。

### 内联存储优化

`Keyframe::Value` 使用 `union` 实现类型特定的存储策略:
- 标量值直接内联存储（`float`）
- 复杂值外部存储,只保存索引（`uint32_t`）

这种设计在保持结构体紧凑的同时,支持不同大小的值类型。

### 缓存友好设计

- 关键帧数组使用连续存储（`std::vector`）
- 段缓存利用时间查询的局部性
- 二分查找使用指针而非索引,减少间接访问

### 不可变性保证

关键帧数组和立方映射器数组在构造后声明为 `const`,保证线程安全的只读访问。

## 性能考量

### 时间复杂度

- **关键帧查找**: O(1) 最好情况（命中缓存）,O(log n) 最坏情况（二分查找）
- **插值计算**: O(1) 常量时间
- **解析**: O(n) 线性时间,其中 n 为关键帧数量

### 空间优化

**常量动画优化**:
当所有关键帧值相同时,只保留一个关键帧,空间从 O(n) 降到 O(1)。

**立方映射器去重**:
连续相同的贝塞尔曲线共享实例,最坏情况 O(n) 空间,最好情况 O(1) 空间。

**内联标量存储**:
标量值直接存储在 `Keyframe` 结构中,避免额外的堆分配和间接访问。

### 缓存效率

**段缓存**:
利用动画播放的时间连续性,大幅减少二分查找次数。典型动画播放场景,缓存命中率接近 100%。

**数组连续性**:
关键帧和映射器使用 `std::vector` 连续存储,充分利用 CPU 缓存预取。

### 内存压缩

**shrink_to_fit 调用**:
```cpp
fCMs.shrink_to_fit();
```
解析完成后释放多余的预留容量,减少内存浪费。

**预留容量**:
```cpp
fKFs.reserve(jkfs.size());
```
解析前预留足够容量,避免多次重新分配。

### 早期退出优化

```cpp
if (t <= fKFs.front().t) {
    return { 0, fKFs.front().v, fKFs.front().v };
}
if (t >= fKFs.back().t) {
    return { 0, fKFs.back().v, fKFs.back().v };
}
```

边界情况立即返回,避免不必要的查找和计算。

### 线性性检测

```cpp
if (SkCubicMap::IsLinear(c0, c1)) {
    return Keyframe::kLinearMapping;
}
```

检测实际为线性的贝塞尔曲线,避免创建映射器和曲线计算开销。

## 相关文件

**头文件依赖**:
- `include/core/SkCubicMap.h` - 贝塞尔曲线映射器
- `include/core/SkPoint.h` - 2D 点类型
- `include/core/SkRefCnt.h` - 引用计数智能指针
- `include/private/base/SkAssert.h` - 断言宏
- `include/private/base/SkNoncopyable.h` - 不可复制基类
- `modules/skottie/src/animator/Animator.h` - 动画器基类

**实现文件依赖**:
- `include/private/base/SkTo.h` - 类型转换函数
- `modules/jsonreader/SkJSONReader.h` - JSON 读取器
- `modules/skottie/src/SkottieJson.h` - JSON 解析工具

**派生类**:
- `modules/skottie/src/animator/VectorKeyframeAnimator.h` - 向量动画器
- `modules/skottie/src/animator/ScalarKeyframeAnimator.h` - 标量动画器
- `modules/skottie/src/effects/Effects.h` - 效果动画器
- `modules/skottie/src/text/TextAnimator.h` - 文本动画器

**相关模块**:
- `modules/skottie/src/animator/` - 动画器系统
- `modules/skottie/src/` - Skottie 核心
- `modules/sksg/` - 场景图系统
