# VectorKeyframeAnimator

> 源文件
> - `modules/skottie/src/animator/VectorKeyframeAnimator.h`
> - `modules/skottie/src/animator/VectorKeyframeAnimator.cpp`

## 概述

`VectorKeyframeAnimator` 是 Skottie 动画系统中专门处理向量属性动画的特化实现。该模块继承自 `KeyframeAnimator`,为多维浮点数向量（如位置、尺寸、颜色等）提供高效的关键帧插值功能。它采用连续存储优化策略,将所有向量值存储在单一的连续数组中,通过索引访问,实现了内存紧凑和缓存友好的设计。

该模块支持任意长度的向量值,特别针对 SIMD 指令进行了优化,对于 4 元素及以上的向量使用 `skvx` 库进行向量化计算,显著提升了大量向量动画的性能。同时,模块还提供了重复值去重机制,进一步减少内存占用。

## 架构位置

`VectorKeyframeAnimator` 位于 Skottie 动画系统的具体实现层:

```
Skottie 动画系统
├── Animator (抽象基类)
│   └── KeyframeAnimator (关键帧基类)
│       ├── VectorKeyframeAnimator ← 本模块 (向量动画)
│       ├── ScalarKeyframeAnimator (标量动画)
│       └── ShapeKeyframeAnimator (形状动画)
├── AnimatorBuilder (构建器抽象)
│   └── VectorAnimatorBuilder (向量构建器)
└── ExpressionAnimator
    └── VectorExpressionAnimator (向量表达式动画)
```

应用场景:
- **位置动画**: 2D/3D 点的运动轨迹
- **尺寸动画**: 宽高、缩放等属性
- **颜色动画**: RGBA 颜色值插值
- **多维参数**: 任意维度的自定义向量属性

## 主要类与结构体

### VectorKeyframeAnimator

向量关键帧动画器的核心实现类:

```cpp
class VectorKeyframeAnimator final : public KeyframeAnimator {
public:
    VectorKeyframeAnimator(std::vector<Keyframe> kfs,
                           std::vector<SkCubicMap> cms,
                           std::vector<float> storage,
                           size_t vec_len,
                           std::vector<float>* target_value);

private:
    StateChanged onSeek(float t) override;

    const std::vector<float> fStorage;  // 连续存储所有向量值
    const size_t fVecLen;               // 单个向量的长度
    std::vector<float>* fTarget;        // 目标向量指针
};
```

**存储布局**:
```
fStorage: [vec0][vec1][vec2]...[vecN]
           <--->  <--->        <--->
          fVecLen

fKFs[0].v.idx -> vec0 的偏移量
fKFs[1].v.idx -> vec1 的偏移量
```

### VectorAnimatorBuilder

向量动画器的构建器,负责解析和创建动画器:

```cpp
class VectorAnimatorBuilder final : public AnimatorBuilder {
public:
    using VectorLenParser = bool(*)(const skjson::Value&, size_t*);
    using VectorDataParser = bool(*)(const skjson::Value&, size_t, float*);

    VectorAnimatorBuilder(std::vector<float>* target,
                          VectorLenParser parse_len,
                          VectorDataParser parse_data);

    sk_sp<KeyframeAnimator> makeFromKeyframes(
        const AnimationBuilder&,
        const skjson::ArrayValue&) override;

    sk_sp<Animator> makeFromExpression(
        ExpressionManager&, const char*) override;

private:
    bool parseValue(const AnimationBuilder&, const skjson::Value&) const override;
    bool parseKFValue(const AnimationBuilder&,
                      const skjson::ObjectValue&,
                      const skjson::Value&,
                      Keyframe::Value*) override;

    const VectorLenParser fParseLen;     // 长度解析器
    const VectorDataParser fParseData;   // 数据解析器
    std::vector<float> fStorage;         // 临时存储
    size_t fVecLen;                      // 向量长度
    size_t fCurrentVec = 0;              // 当前向量索引
    std::vector<float>* fTarget;         // 目标向量
};
```

### VectorExpressionAnimator

基于表达式的向量动画器:

```cpp
class VectorExpressionAnimator final : public Animator {
public:
    VectorExpressionAnimator(
        sk_sp<ExpressionEvaluator<std::vector<float>>> expression_evaluator,
        std::vector<float>* target_value);

private:
    StateChanged onSeek(float t) override;

    sk_sp<ExpressionEvaluator<std::vector<float>>> fExpressionEvaluator;
    std::vector<float>* fTarget;
};
```

### VectorValue / ColorValue

向量值类型定义,提供类型转换支持:

```cpp
class VectorValue : public std::vector<float> {
public:
    operator SkV3() const;  // 转换为 3D 向量
};

class ColorValue : public VectorValue {
public:
    operator SkColor() const;    // 转换为 SkColor
    operator SkColor4f() const;  // 转换为 SkColor4f
};
```

## 公共 API 函数

### VectorKeyframeAnimator 方法

**构造函数**
```cpp
VectorKeyframeAnimator(std::vector<Keyframe> kfs,
                       std::vector<SkCubicMap> cms,
                       std::vector<float> storage,
                       size_t vec_len,
                       std::vector<float>* target_value);
```
创建向量关键帧动画器,初始化关键帧、立方映射器、存储和目标向量。

**onSeek**
```cpp
StateChanged onSeek(float t) override;
```
根据时间 `t` 更新目标向量值,执行向量插值计算。使用 SIMD 优化处理 4 元素的倍数部分,剩余部分使用标量计算。

### VectorAnimatorBuilder 方法

**构造函数**
```cpp
VectorAnimatorBuilder(std::vector<float>* target,
                      VectorLenParser parse_len,
                      VectorDataParser parse_data);
```
初始化构建器,接受目标向量指针和两个解析器函数指针。

**makeFromKeyframes**
```cpp
sk_sp<KeyframeAnimator> makeFromKeyframes(
    const AnimationBuilder& abuilder,
    const skjson::ArrayValue& jkfs) override;
```
从 JSON 关键帧数组创建向量动画器:
1. 从第一个关键帧推断向量长度
2. 分配存储空间
3. 解析所有关键帧
4. 应用去重优化
5. 创建并返回动画器实例

**makeFromExpression**
```cpp
sk_sp<Animator> makeFromExpression(
    ExpressionManager& em, const char* expr) override;
```
从表达式字符串创建向量表达式动画器。

**parseValue**
```cpp
bool parseValue(const AnimationBuilder&,
               const skjson::Value& jv) const override;
```
解析静态向量值,用于非动画属性。

**parseKFValue**
```cpp
bool parseKFValue(const AnimationBuilder&,
                 const skjson::ObjectValue&,
                 const skjson::Value& jv,
                 Keyframe::Value* kfv) override;
```
解析单个关键帧值,执行去重检查并设置索引。

### 类型转换操作符

**VectorValue::operator SkV3**
```cpp
operator SkV3() const;
```
将向量值转换为 Skia 3D 向量,不足的维度用 0 填充。

**ColorValue::operator SkColor**
```cpp
operator SkColor() const;
```
将颜色向量转换为 `SkColor` 格式,钳位到 [0, 1] 范围。

**ColorValue::operator SkColor4f**
```cpp
operator SkColor4f() const;
```
将颜色向量转换为 `SkColor4f` 格式,支持不透明度通道。

## 内部实现细节

### 连续存储布局

所有向量值存储在单一的连续数组中,关键帧记录存储偏移量:

```cpp
// 存储布局示例（vec_len = 3）:
// fStorage = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
//             |<- vec0 ->| |<- vec1 ->| |<- vec2 ->|
//
// fKFs[0].v.idx = 0  // 指向 vec0
// fKFs[1].v.idx = 3  // 指向 vec1
// fKFs[2].v.idx = 6  // 指向 vec2
```

### SIMD 优化插值

`onSeek` 方法使用 SIMD 指令优化向量插值:

```cpp
// 处理 4 元素的倍数部分
while (count >= 4) {
    const auto old_val = skvx::float4::Load(dst);
    const auto new_val = Lerp(skvx::float4::Load(v0),
                              skvx::float4::Load(v1),
                              lerp_info.weight);

    changed |= any(new_val != old_val);
    new_val.store(dst);

    v0 += 4; v1 += 4; dst += 4;
    count -= 4;
}

// 处理剩余元素（标量）
while (count-- > 0) {
    const auto new_val = Lerp(*v0++, *v1++, lerp_info.weight);
    changed |= (new_val != *dst);
    *dst++ = new_val;
}
```

SIMD 优化带来的性能提升:
- 4 个浮点数并行计算
- 减少循环次数
- 利用 CPU 向量指令

### 常量值优化

检测相邻关键帧的重复值,避免不必要的插值:

```cpp
const auto is_constant = lerp_info.vrec0.equals(lerp_info.vrec1,
                                               Keyframe::Value::Type::kIndex);
if (is_constant) {
    if (0 != std::memcmp(dst, v0, fVecLen * sizeof(float))) {
        std::copy(v0, v0 + fVecLen, dst);
        return true;
    }
    return false;
}
```

使用 `memcmp` 快速比较整个向量,使用 `std::copy` 批量复制。

### 尾部去重机制

解析关键帧时,检测并去除重复的向量值:

```cpp
// 比较当前向量与前一个向量
if (fCurrentVec > 0 && !memcmp(fStorage.data() + offset,
                               fStorage.data() + offset - fVecLen,
                               fVecLen * sizeof(float))) {
    // 重复值 -> 复用前一个偏移量
    offset -= fVecLen;
} else {
    // 新值 -> 增加当前索引
    fCurrentVec += 1;
}
```

这种去重减少了存储空间,特别是在多个关键帧保持相同值的场景下。

### 分离维度支持

支持每个维度独立动画（separate dimensions）:

```cpp
if (ParseDefault<bool>((*jprop)["s"], false)) {
    // 分离维度模式：x, y, z 独立动画
    *v = { 0, 0, 0 };
    bool boundX = this->bind(abuilder, (*jprop)["x"], v->data() + 0);
    bool boundY = this->bind(abuilder, (*jprop)["y"], v->data() + 1);
    bool boundZ = this->bind(abuilder, (*jprop)["z"], v->data() + 2);
    return boundX || boundY || boundZ;
}
```

每个维度可以有独立的关键帧和缓动曲线。

### 表达式动画实现

`VectorExpressionAnimator` 通过表达式求值器计算动画值:

```cpp
StateChanged onSeek(float t) override {
    std::vector<float> result = fExpressionEvaluator->evaluate(t);
    bool changed = false;
    for (size_t i = 0; i < fTarget->size(); i++) {
        // 结果太短时使用 0 作为默认值
        float val = i >= result.size() ? 0 : result[i];
        if (!SkScalarNearlyEqual(val, (*fTarget)[i])) {
            changed = true;
        }
        (*fTarget)[i] = val;
    }
    return changed;
}
```

### 安全性检查

使用 `SkSafeMath` 防止整数溢出:

```cpp
SkSafeMath safe;
const auto total_size = safe.mul(fVecLen, jkfs.size());

// 必须能够存储所有偏移量到 uint32_t
if (!safe || !SkTFitsIn<uint32_t>(total_size)) {
    return nullptr;
}
```

### 颜色值转换

`ColorValue` 提供颜色格式转换,自动钳位到有效范围:

```cpp
ColorValue::operator SkColor4f() const {
    const auto r = this->size() > 0 ? SkTPin((*this)[0], 0.0f, 1.0f) : 0,
               g = this->size() > 1 ? SkTPin((*this)[1], 0.0f, 1.0f) : 0,
               b = this->size() > 2 ? SkTPin((*this)[2], 0.0f, 1.0f) : 0,
               a = this->size() > 3 ? SkTPin((*this)[3], 0.0f, 1.0f) : 1;

    return { r, g, b, a };
}
```

默认不透明度为 1.0,不足的通道用 0 填充。

## 依赖关系

### 对外依赖

- **KeyframeAnimator**: 基类,提供关键帧查询和插值框架
- **AnimatorBuilder**: 构建器基类,定义解析接口
- **SkCubicMap**: 贝塞尔曲线插值
- **skvx**: SIMD 向量化计算库
- **ExpressionEvaluator**: 表达式求值器
- **ExpressionManager**: 表达式管理器
- **AnimationBuilder**: 动画构建上下文
- **SlotManager**: 插槽管理器,用于颜色插槽绑定

### 内部依赖

- **SkottieJson**: JSON 解析工具 `Parse`、`ParseDefault`
- **SkottieValue**: 定义 `VectorValue`、`ColorValue` 类型
- **SkottiePriv**: 提供 `ParseSlotID` 等工具函数
- **SkSafeMath**: 安全数学运算,防止溢出
- **Skia Core**: `SkColor`、`SkColor4f`、`SkV3` 等类型

### 被依赖情况

- **AnimatablePropertyContainer**: 使用 `VectorAnimatorBuilder` 绑定向量属性
- **Transform**: 位置、缩放等变换属性使用向量动画
- **Paint**: 颜色属性使用颜色动画（继承自向量动画）
- **Effects**: 效果参数使用向量动画

## 设计模式与设计决策

### 策略模式（解析器）

通过函数指针传递解析策略,实现解析逻辑的可定制:

```cpp
VectorAnimatorBuilder builder(
    v,
    // 长度解析策略
    [](const skjson::Value& jv, size_t* len) -> bool {
        if (const skjson::ArrayValue* ja = jv) {
            *len = ja->size();
            return true;
        }
        return false;
    },
    // 数据解析策略
    [](const skjson::Value& jv, size_t len, float* data) {
        return parse_array(jv, data, len);
    });
```

不同的属性类型可以提供不同的解析器实现。

### 模板特化

使用模板特化为不同的向量类型提供专门的绑定逻辑:

```cpp
template <>
bool AnimatablePropertyContainer::bind<VectorValue>(...);

template <>
bool AnimatablePropertyContainer::bind<ColorValue>(...);
```

### 写时复制（COW）优化

只有当值实际改变时才返回 `true`,避免不必要的场景图更新:

```cpp
changed |= (new_val != *dst);
*dst++ = new_val;
return changed;
```

### 延迟调整大小

解析完成后才调整存储大小,利用去重减少内存:

```cpp
fStorage.resize(fCurrentVec * fVecLen);
fStorage.shrink_to_fit();
```

### 类型转换操作符

提供隐式转换操作符,简化与 Skia 类型的互操作:

```cpp
SkColor color = color_value;  // 隐式转换
SkV3 point = vector_value;    // 隐式转换
```

## 性能考量

### SIMD 向量化

使用 `skvx::float4` 一次处理 4 个浮点数,性能提升约 2-4 倍（取决于向量长度和 CPU 架构）。

### 内存布局优化

**连续存储**:
- 所有向量值连续存储,提高缓存命中率
- 减少指针间接访问
- 支持批量操作（memcpy、memcmp）

**去重优化**:
- 重复向量只存储一次
- 减少内存占用
- 提高缓存效率

### 批量操作

使用标准库批量操作函数:
- `std::memcmp`: 快速向量比较
- `std::copy`: 高效向量复制
- `std::vector`: 连续内存分配

### 变更检测

只在值实际改变时返回 `true`,避免:
- 不必要的场景图遍历
- 重复的渲染更新
- 下游动画器的触发

### 预分配策略

```cpp
fStorage.resize(total_size);  // 一次性分配
```

避免多次内存重新分配,减少内存碎片。

### 常量分支预测

```cpp
if (is_constant) {
    // 常量路径（快速）
    if (0 != std::memcmp(...)) {
        std::copy(...);
        return true;
    }
    return false;
}
// 插值路径（较慢）
```

常量情况优先判断,利用分支预测优化。

### 空间换时间

存储所有关键帧值,避免每次从 JSON 解析或计算,以内存换取运行时性能。

## 相关文件

**头文件依赖**:
- `include/core/SkColor.h` - 颜色类型定义
- `include/core/SkCubicMap.h` - 贝塞尔曲线映射
- `include/core/SkM44.h` - 4x4 矩阵类型
- `include/core/SkScalar.h` - 标量类型定义
- `include/private/base/SkTPin.h` - 值钳位函数
- `modules/skottie/src/animator/KeyframeAnimator.h` - 基类

**实现文件依赖**:
- `src/base/SkVx.h` - SIMD 向量化库
- `src/base/SkSafeMath.h` - 安全数学运算
- `modules/skottie/src/SkottieValue.h` - 值类型定义
- `modules/skottie/src/SkottiePriv.h` - 私有工具函数
- `modules/skottie/include/SlotManager.h` - 插槽管理

**相关模块**:
- `modules/skottie/src/animator/Animator.h` - 动画器基类
- `modules/skottie/src/animator/KeyframeAnimator.h` - 关键帧动画基础
- `modules/skottie/src/SkottieJson.h` - JSON 解析工具
- `modules/sksg/` - 场景图系统

**应用示例**:
- `modules/skottie/src/Transform.cpp` - 变换属性动画
- `modules/skottie/src/effects/` - 效果参数动画
- `modules/skottie/src/text/TextAnimator.cpp` - 文本动画器
