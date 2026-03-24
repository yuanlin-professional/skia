# RangeSelector

> 源文件
> - `modules/skottie/src/text/RangeSelector.h`
> - `modules/skottie/src/text/RangeSelector.cpp`

## 概述

`RangeSelector` 是 Skottie 文本动画系统中的核心组件,用于选择文本的特定范围并调制其覆盖度（coverage）。该模块实现了 After Effects 风格的范围选择器,支持多种选择域（字符、单词、行）、单位类型（百分比、索引）和形状函数（方波、三角波、正弦波等）,为文本动画提供了精确而灵活的控制能力。

范围选择器通过生成覆盖度信号,控制文本动画器对各个文本片段的影响程度。它支持缓动、平滑度和偏移等高级参数,能够创建复杂的文本动画效果,如逐字显示、波浪效果、渐变过渡等。

## 架构位置

`RangeSelector` 位于 Skottie 文本动画系统的选择器层:

```
Skottie 文本动画系统
├── TextAnimator (文本动画器)
│   ├── RangeSelector ← 本模块 (范围选择器)
│   ├── TextAdapter (文本适配器)
│   └── TextValue (文本值)
├── DomainMaps (域映射)
│   ├── CharactersMap (字符映射)
│   ├── WordsMap (单词映射)
│   └── LinesMap (行映射)
└── ModulatorBuffer (调制缓冲区)
```

工作流程:
1. 根据选择参数解析范围
2. 生成形状函数信号
3. 应用缓动和平滑
4. 调制覆盖度缓冲区
5. 文本动画器使用覆盖度应用效果

## 主要类与结构体

### RangeSelector

范围选择器主类:

```cpp
class RangeSelector final : public SkNVRefCnt<RangeSelector> {
public:
    static sk_sp<RangeSelector> Make(const skjson::ObjectValue*,
                                     const AnimationBuilder*,
                                     AnimatablePropertyContainer*);

    enum class Units : uint8_t {
        kPercentage,  // 值为域大小的百分比
        kIndex,       // 值为直接域索引
    };

    enum class Domain : uint8_t {
        kChars,                   // 域索引映射到字形索引
        kCharsExcludingSpaces,    // 域索引映射到字形索引(忽略空格)
        kWords,                   // 域索引映射到单词索引
        kLines,                   // 域索引映射到行索引
    };

    enum class Mode : uint8_t {
        kAdd,  // 加法模式
        // kSubtract, kIntersect, kMin, kMax, kDifference (未实现)
    };

    enum class Shape : uint8_t {
        kSquare,      // 方波
        kRampUp,      // 上升斜坡
        kRampDown,    // 下降斜坡
        kTriangle,    // 三角波
        kRound,       // 圆形波
        kSmooth,      // 平滑波
    };

    void modulateCoverage(const TextAnimator::DomainMaps&,
                         TextAnimator::ModulatorBuffer&) const;

private:
    RangeSelector(Units, Domain, Mode, Shape);

    std::tuple<float, float> resolve(size_t domain_size) const;

    const Units fUnits;
    const Domain fDomain;
    const Mode fMode;
    const Shape fShape;

    float fStart;       // 起始位置
    float fEnd;         // 结束位置
    float fOffset;      // 偏移量
    float fAmount = 100;      // 影响量 (百分比)
    float fEaseLo = 0;        // 低端缓动 (百分比)
    float fEaseHi = 0;        // 高端缓动 (百分比)
    float fSmoothness = 100;  // 平滑度 (百分比,仅方波)
};
```

### UnitTraits

单位类型特征模板,定义默认值和解析逻辑:

```cpp
template <RangeSelector::Units>
struct UnitTraits;

// 百分比模式
template <>
struct UnitTraits<RangeSelector::Units::kPercentage> {
    static constexpr auto Defaults() {
        return std::make_tuple<float, float, float>(0, 100, 0);
    }

    static auto Resolve(float s, float e, float o, size_t domain_size) {
        return std::make_tuple(domain_size * (s + o) / 100,
                               domain_size * (e + o) / 100);
    }
};

// 索引模式
template <>
struct UnitTraits<RangeSelector::Units::kIndex> {
    static constexpr auto Defaults() {
        return std::make_tuple<float, float, float>(
            0, std::numeric_limits<float>::max(), 0);
    }

    static auto Resolve(float s, float e, float o, size_t domain_size) {
        return std::make_tuple(s + o, e + o);
    }
};
```

### CoverageProcessor

覆盖度处理器,负责应用选择器到目标缓冲区:

```cpp
class CoverageProcessor {
public:
    CoverageProcessor(const TextAnimator::DomainMaps& maps,
                      RangeSelector::Domain domain,
                      RangeSelector::Mode mode,
                      TextAnimator::ModulatorBuffer& dst);

    size_t size() const;

    void operator()(float amount, size_t offset, size_t count) const;

private:
    void add_proc(float amount, size_t offset, size_t count) const;
    void domain_map_proc(float amount, size_t offset, size_t count) const;

    using ProcT = void(CoverageProcessor::*)(float, size_t, size_t) const;

    TextAnimator::ModulatorBuffer& fDst;
    ProcT fProc;                              // 当前处理函数指针
    ProcT fMappedProc = nullptr;              // 映射后的处理函数
    const TextAnimator::DomainMap* fMap = nullptr;  // 域映射表
    size_t fDomainSize;
};
```

### ShapeGenerator

形状信号生成器,使用贝塞尔曲线实现各种波形:

```cpp
struct ShapeGenerator {
    SkCubicMap shape_mapper;   // 形状映射器
    SkCubicMap ease_mapper;    // 缓动映射器
    float e0, e1, crs;         // 边缘和斜坡参数

    ShapeGenerator(const ShapeInfo& sinfo, float ease_lo, float ease_hi);

    float operator()(float t) const {
        t = std::min(t - e0, e1 - t);
        t = sk_ieee_float_divide(t, crs);
        return ease_mapper.computeYFromX(shape_mapper.computeYFromX(t));
    }
};
```

### ShapeInfo

形状参数定义:

```cpp
struct ShapeInfo {
    SkVector ctrl0, ctrl1;  // 贝塞尔控制点
    float e0, e1, crs;      // 左边缘、右边缘、立方斜坡大小
};

static constexpr ShapeInfo gShapeInfo[] = {
    { {0,0}, {1,1}, 0, 1, 0.0f },                   // kSquare
    { {0,0}, {1,1}, 0, SK_FloatInfinity, 1.0f },    // kRampUp
    { {0,0}, {1,1}, SK_FloatNegativeInfinity, 1, 1.0f }, // kRampDown
    { {0,0}, {1,1}, 0, 1, 0.5f },                   // kTriangle
    { {0,.5f}, {.5f,1}, 0, 1, 0.5f },               // kRound
    { {.5f,0}, {.5f,1}, 0, 1, 0.5f },               // kSmooth
};
```

## 公共 API 函数

### Make (工厂方法)

```cpp
static sk_sp<RangeSelector> Make(
    const skjson::ObjectValue* jrange,
    const AnimationBuilder* abuilder,
    AnimatablePropertyContainer* acontainer);
```
从 JSON 创建范围选择器实例:
1. 解析选择器类型（仅支持范围选择器）
2. 解析单位、域、模式、形状枚举
3. 创建选择器实例
4. 绑定可动画属性（start、end、offset、amount、ease）

### modulateCoverage

```cpp
void modulateCoverage(const TextAnimator::DomainMaps& maps,
                     TextAnimator::ModulatorBuffer& mbuf) const;
```
调制覆盖度缓冲区的核心方法:
1. 创建覆盖度处理器
2. 解析范围到目标域
3. 创建形状生成器
4. 应用平滑度（方波）
5. 遍历域,生成并应用覆盖度值

### resolve (内部方法)

```cpp
std::tuple<float, float> resolve(size_t domain_size) const;
```
根据单位类型和域大小解析范围:
- **百分比模式**: 将百分比转换为实际索引
- **索引模式**: 直接使用索引值
- 应用偏移量并确保 `start <= end`

## 内部实现细节

### 形状函数理论

形状生成器基于参数化信号模型:

```
信号 F(t):

1  +               -------------------------
   |              /.           .           .\
   |             / .           .           . \
   |            /  .           .           .  \
   |           /   .           .           .   \
   |          /    .           .           .    \
0  +----------------------------------------------------------
          ^ <----->            ^            <-----> ^
         e0   crs             sp              crs    e1

参数说明:
- e0, e1: 左/右边缘
- sp: 对称点 (sp == (e0+e1)/2)
- crs: 立方斜坡大小 (过渡区域)

分段函数:
F(t) = 0                    , t <= e0
F(t) = Bez((t-e0)/crs)      , e0 < t < e0+crs
F(t) = 1                    , e0+crs <= t <= sp
F(t) = F(reflect(t,sp))     , t > sp
```

不同形状通过调整参数实现:
- **方波**: `e0=0, e1=1, crs=0`
- **上升斜坡**: `e0=0, e1=+inf, crs=1`
- **下降斜坡**: `e0=-inf, e1=1, crs=1`
- **三角波**: `e0=0, e1=1, crs=0.5`
- **圆形波**: `e0=0, e1=1, crs=0.5` + 非线性控制点 `{0,.5f}, {.5f,1}`
- **平滑波**: `e0=0, e1=1, crs=0.5` + 非线性控制点 `{.5f,0}, {.5f,1}`

### 缓动函数

使用贝塞尔曲线实现缓动:

```cpp
SkVector EaseVec(float ease) {
    return (ease < 0) ? SkVector{0, -ease} : SkVector{ease, 0};
}

ease_mapper(EaseVec(ease_lo), SkVector{1,1} - EaseVec(ease_hi))
```

- **负值**: 调整起始控制点,创建缓入效果
- **正值**: 调整结束控制点,创建缓出效果

### 域映射机制

`CoverageProcessor` 实现域映射:

```cpp
void domain_map_proc(float amount, size_t offset, size_t count) const {
    for (auto i = offset; i < offset + count; ++i) {
        const auto& span = (*fMap)[i];
        // 映射域索引到目标缓冲区跨度
        (this->*fMappedProc)(amount, span.fOffset, span.fCount);
    }
}
```

例如,单词域:
- 域索引 0 -> 字符 0-4 (第一个单词)
- 域索引 1 -> 字符 6-9 (第二个单词)

### 加法模式实现

```cpp
void add_proc(float amount, size_t offset, size_t count) const {
    if (!amount || !count) return;

    for (auto* dst = fDst.data() + offset;
         dst < fDst.data() + offset + count; ++dst) {
        dst->coverage = SkTPin<float>(dst->coverage + amount, -1, 1);
    }
}
```

覆盖度累加并钳位到 [-1, 1] 范围。

### 方波平滑度

方波支持额外的平滑度参数:

```cpp
if (fShape == Shape::kSquare) {
    const auto smoothness = SkTPin<float>(fSmoothness / 100, 0, 1);

    r0 -= smoothness / 2;   // 向外扩展左边缘
    len += smoothness;       // 增加范围长度

    gen.crs += smoothness / len;  // 增加斜坡大小
}
```

平滑度引入过渡区域,避免硬边缘。

### 采样策略

使用中点采样策略,减少锯齿:

```cpp
const auto dt = 1 / len;
auto t = (0.5f - r0) / len;  // 采样偏差：单位中点

for (size_t i = 0; i < coverage_proc.size(); ++i, t += dt) {
    coverage_proc(amount * gen(t), i, 1);
}
```

### 枚举解析

使用模板函数解析 1-based JSON 枚举:

```cpp
template <typename T, typename TArray>
T ParseEnum(const TArray& arr, const skjson::Value& jenum,
            const AnimationBuilder* abuilder, const char* warn_name) {
    const auto idx = ParseDefault<int>(jenum, 1);

    if (idx > 0 && SkToSizeT(idx) <= std::size(arr)) {
        return arr[idx - 1];  // 转换为 0-based 索引
    }

    // idx == 0 是占位符,不警告
    if (idx != 0) {
        abuilder->log(Logger::Level::kWarning, nullptr,
            "Ignoring unknown range selector %s '%d'", warn_name, idx);
    }

    return arr[0];  // 默认返回第一个值
}
```

## 依赖关系

### 对外依赖

- **TextAnimator**: 提供 `DomainMaps` 和 `ModulatorBuffer` 类型
- **AnimatablePropertyContainer**: 提供属性绑定功能
- **AnimationBuilder**: 提供解析上下文和日志
- **SkCubicMap**: 提供贝塞尔曲线插值
- **SkNVRefCnt**: 提供非虚引用计数基类

### 内部依赖

- **SkottieJson**: JSON 解析工具 `Parse`、`ParseDefault`
- **SkottiePriv**: 私有工具函数
- **Animator**: 动画器基类
- **SkTPin**: 值钳位函数
- **sk_ieee_float_divide**: IEEE 浮点除法

### 被依赖情况

- **TextAnimator**: 使用范围选择器调制覆盖度
- **TextAdapter**: 通过 `TextAnimator` 间接使用

## 设计模式与设计决策

### 策略模式（处理器）

`CoverageProcessor` 使用成员函数指针实现策略模式:

```cpp
using ProcT = void(CoverageProcessor::*)(float, size_t, size_t) const;
ProcT fProc;  // 当前策略

// 调用策略
(this->*fProc)(amount, offset, count);
```

支持不同的模式（加法、减法等）和域映射策略。

### 特征模板

`UnitTraits` 使用特征模板为不同单位类型提供专门逻辑:

```cpp
template <RangeSelector::Units>
struct UnitTraits;

// 百分比特化
template <>
struct UnitTraits<RangeSelector::Units::kPercentage> {
    static constexpr auto Defaults() { ... }
    static auto Resolve(...) { ... }
};
```

编译时分派,零运行时开销。

### 函数对象

`ShapeGenerator` 和 `CoverageProcessor` 使用函数对象模式,封装状态和操作:

```cpp
ShapeGenerator gen(...);
float value = gen(t);  // operator()
```

### 参数化形状

所有形状通过统一的参数化模型实现,避免重复代码:

```cpp
static constexpr ShapeInfo gShapeInfo[] = { ... };
ShapeGenerator gen(gShapeInfo[static_cast<size_t>(fShape)], ...);
```

### 双重映射

形状映射和缓动映射串联应用:

```cpp
return ease_mapper.computeYFromX(shape_mapper.computeYFromX(t));
```

提供最大灵活性。

## 性能考量

### 预计算查找表

形状信息使用 `constexpr` 静态数组,编译时计算:

```cpp
static constexpr ShapeInfo gShapeInfo[] = { ... };
```

零运行时初始化开销。

### 成员函数指针

使用成员函数指针避免虚函数调用:

```cpp
(this->*fProc)(amount, offset, count);
```

编译器可以内联调用。

### 早期退出

检测空操作并提前返回:

```cpp
if (!amount || !count) return;
```

### 采样优化

使用增量计算避免重复乘法:

```cpp
const auto dt = 1 / len;
auto t = (0.5f - r0) / len;

for (size_t i = 0; i < coverage_proc.size(); ++i, t += dt) {
    // t 增量更新,避免重复计算 i / len
}
```

### 域映射缓存

域映射结果由 `TextAnimator` 预计算并缓存,避免每次重新计算。

### 钳位优化

使用 `SkTPin` 高效钳位值:

```cpp
dst->coverage = SkTPin<float>(dst->coverage + amount, -1, 1);
```

### 内联小函数

`EaseVec` 等小函数自动内联,减少调用开销。

## 相关文件

**头文件依赖**:
- `include/core/SkRefCnt.h` - 引用计数基类
- `include/core/SkCubicMap.h` - 贝塞尔曲线映射
- `include/core/SkPoint.h` - 2D 点类型
- `modules/skottie/src/text/TextAnimator.h` - 文本动画器

**实现文件依赖**:
- `include/private/base/SkFloatingPoint.h` - IEEE 浮点运算
- `include/private/base/SkTPin.h` - 值钳位函数
- `include/private/base/SkTo.h` - 类型转换函数
- `modules/skottie/src/SkottieJson.h` - JSON 解析工具
- `modules/skottie/src/SkottiePriv.h` - 私有工具函数
- `modules/skottie/src/animator/Animator.h` - 动画器基类

**相关模块**:
- `modules/skottie/src/text/TextAnimator.h` - 文本动画器
- `modules/skottie/src/text/TextAdapter.h` - 文本适配器
- `modules/skottie/src/text/TextValue.h` - 文本值

**应用示例**:
文本逐字显示、波浪效果、渐变过渡等文本动画效果。
