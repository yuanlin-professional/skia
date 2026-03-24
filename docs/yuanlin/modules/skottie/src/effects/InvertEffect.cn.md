# InvertEffect

> 源文件: modules/skottie/src/effects/InvertEffect.cpp

## 概述

InvertEffect 模块实现了通道反相效果,支持在 RGB、HSL 和 YIQ 多种颜色空间中对单个或全部通道进行反相操作。该效果对应 Adobe After Effects 的 "Invert" 通道效果,广泛用于颜色校正、视觉特效和图像处理工作流。

## 架构位置

InvertEffect 是 Skottie 颜色效果系统的重要组成部分:

```
modules/skottie/
  └── src/
      └── effects/
          ├── InvertEffect.cpp         # 反相效果实现
          ├── HueSaturationEffect.cpp  # 色相饱和度效果
          └── Effects.h                # 效果接口定义
```

该模块利用颜色空间变换矩阵实现高效的通道反相,支持 RGB、HSL(HLS)和 YIQ 三种颜色空间。

## 主要类与结构体

### InvertEffectAdapter

反相效果适配器,根据选定的通道和颜色空间生成相应的颜色矩阵。

```cpp
class InvertEffectAdapter final : public AnimatablePropertyContainer
```

**核心成员:**
- `fColorFilter` - `sksg::ExternalColorFilter` 节点,应用颜色变换
- `fChannel` - 当前选中的通道(RGB、HLS、YIQ 或单通道)

**通道常量:**
```cpp
enum : uint8_t {
    kRGB_Channel =  1,  // RGB 全通道
    kR_Channel   =  2,  // 红色通道
    kG_Channel   =  3,  // 绿色通道
    kB_Channel   =  4,  // 蓝色通道

    kHLS_Channel =  6,  // HLS 全通道
    kH_Channel   =  7,  // 色相通道
    kL_Channel   =  8,  // 亮度通道
    kS_Channel   =  9,  // 饱和度通道

    kYIQ_Channel = 11,  // YIQ 全通道
    kY_Channel   = 12,  // 亮度(Y)通道
    kI_Channel   = 13,  // 色度(I)通道
    kQ_Channel   = 14,  // 色度(Q)通道

    kA_Channel   = 16,  // Alpha 通道
};
```

## 公共 API 函数

### attachInvertEffect

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachInvertEffect(
    const skjson::ArrayValue& jprops,
    sk_sp<sksg::RenderNode> layer) const
```

将反相效果附加到图层渲染节点。

**参数:**
- `jprops` - JSON 属性数组,包含通道选择参数
- `layer` - 源渲染节点

**返回值:** 应用反相效果的渲染节点

**属性索引:**
```cpp
enum : size_t {
    kChannel_Index = 0,  // 通道选择
};
```

## 内部实现细节

### 缩放平移颜色矩阵(STColorMatrix)

反相操作表示为缩放-平移变换:

```cpp
struct STColorMatrix {
    std::array<float,4> scale,  // 通道缩放因子
                        trans;  // 通道平移量
    CS                  cs;     // 颜色空间(RGB/HSL/YIQ)
};
```

**基本反相公式:**
- RGB: `c' = 1 - c` → scale = -1, trans = 1
- Alpha: `a' = 1 - a` → scale = -1, trans = 1
- 色相: `h' = 0.5 - h` → scale = -1, trans = 0.5
- 色度(I/Q): `i' = -i` → scale = -1, trans = 0

### 通道映射表

```cpp
switch (static_cast<uint8_t>(fChannel)) {
    case   kR_Channel: return { {-1, 1, 1, 1}, {  1,0,0,0}, CS::kRGB };
    case   kG_Channel: return { { 1,-1, 1, 1}, {  0,1,0,0}, CS::kRGB };
    case   kB_Channel: return { { 1, 1,-1, 1}, {  0,0,1,0}, CS::kRGB };
    case   kA_Channel: return { { 1, 1, 1,-1}, {  0,0,0,1}, CS::kRGB };
    case kRGB_Channel: return { {-1,-1,-1, 1}, {  1,1,1,0}, CS::kRGB };

    case   kH_Channel: return { {-1, 1, 1, 1}, {.5f,0,0,0}, CS::kHSL };
    case   kS_Channel: return { { 1,-1, 1, 1}, {  0,1,0,0}, CS::kHSL };
    case   kL_Channel: return { { 1, 1,-1, 1}, {  0,0,1,0}, CS::kHSL };
    case kHLS_Channel: return { {-1,-1,-1, 1}, {.5f,1,1,0}, CS::kHSL };

    case   kY_Channel: return { {-1, 1, 1, 1}, {  1,0,0,0}, CS::kYIQ };
    case   kI_Channel: return { { 1,-1, 1, 1}, {  0,0,0,0}, CS::kYIQ };
    case   kQ_Channel: return { { 1, 1,-1, 1}, {  0,0,0,0}, CS::kYIQ };
    case kYIQ_Channel: return { {-1,-1,-1, 1}, {  1,0,0,0}, CS::kYIQ };

    default: return { { 1, 1, 1, 1}, {  0,0,0,0}, CS::kRGB };
}
```

### RGB 颜色矩阵构建

```cpp
SkColorMatrix m(
    stcm.scale[0],             0,             0,             0, stcm.trans[0],
                0, stcm.scale[1],             0,             0, stcm.trans[1],
                0,             0, stcm.scale[2],             0, stcm.trans[2],
                0,             0,             0, stcm.scale[3], stcm.trans[3]
);
```

### YIQ 颜色空间转换

YIQ 通道反相需要 RGB ↔ YIQ 转换矩阵:

**RGB to YIQ:**
```cpp
static constexpr SkColorMatrix RGB2YIQ(
    0.2990f,  0.5870f,  0.1140f, 0, 0,
    0.5959f, -0.2746f, -0.3213f, 0, 0,
    0.2115f, -0.5227f,  0.3112f, 0, 0,
          0,        0,        0, 1, 0
);
```

**YIQ to RGB:**
```cpp
static constexpr SkColorMatrix YIQ2RGB(
          1,  0.9560f,  0.6190f, 0, 0,
          1, -0.2720f, -0.6470f, 0, 0,
          1, -1.1060f,  1.7030f, 0, 0,
          0,        0,        0, 1, 0
);
```

**复合变换:**
```cpp
if (stcm.cs == CS::kYIQ) {
    m.preConcat (RGB2YIQ);  // RGB → YIQ
    m.postConcat(YIQ2RGB);  // YIQ → RGB
}
```

### 颜色滤镜选择

```cpp
fColorFilter->setColorFilter(
    stcm.cs == CS::kHSL
        ? SkColorFilters::HSLAMatrix(m)  // HSL 空间
        : SkColorFilters::Matrix(m)       // RGB/YIQ 空间
);
```

## 依赖关系

### Skia 核心依赖
- `SkColorFilter` - 颜色滤镜基类
- `SkColorMatrix` - 5x4 颜色变换矩阵
- `SkColorFilters::Matrix` - RGB 矩阵滤镜
- `SkColorFilters::HSLAMatrix` - HSLA 矩阵滤镜

### Skottie 框架依赖
- `SkottiePriv.h` - 内部构建工具
- `animator/Animator.h` - 动画属性系统
- `effects/Effects.h` - `EffectBuilder` 接口
- `SkSGColorFilter.h` - Scene Graph 颜色滤镜节点

### 标准库依赖
- `<array>` - `std::array` 用于矩阵存储
- `<cstdint>` - `uint8_t` 通道类型

## 设计模式与设计决策

### 查找表模式

使用 lambda 函数返回静态映射表,避免运行时计算,提升性能:

```cpp
const auto stcm = [this]() -> STColorMatrix {
    switch (static_cast<uint8_t>(fChannel)) {
        // ... 映射表
    }
}();
```

### 颜色空间抽象

引入 `CS` 枚举抽象颜色空间,统一处理 RGB、HSL、YIQ 三种空间:

```cpp
enum class CS { kRGB, kHSL, kYIQ };
```

### 矩阵组合

YIQ 通道反相通过矩阵的前乘和后乘实现颜色空间转换:

```
RGB → YIQ → Invert → RGB
```

这种设计避免了在运行时切换颜色空间的复杂性。

### 无效通道快速路径

未识别的通道返回单位矩阵,确保不会产生视觉错误:

```cpp
default: return { { 1, 1, 1, 1}, {  0,0,0,0}, CS::kRGB };
```

## 性能考量

### 编译时常量

YIQ 转换矩阵使用 `static constexpr`,在编译时求值并存储在只读内存中。

### 单次矩阵乘法

所有反相操作都被简化为单个颜色矩阵,GPU 只需执行一次矩阵乘法。

### Lambda 优化

通道映射 lambda 通常会被编译器内联,消除函数调用开销。

### 零拷贝设计

颜色矩阵直接传递给 Skia 滤镜,无需额外的数据拷贝。

### 快速通道选择

使用整数 switch 而非浮点比较,提升通道选择速度。

### 条件颜色空间

只在需要时应用 HSL 或 YIQ 转换,RGB 通道直接使用矩阵滤镜。

## 相关文件

- `modules/skottie/src/effects/HueSaturationEffect.cpp` - HSL 空间颜色效果
- `modules/skottie/src/effects/LevelsEffect.cpp` - 通道映射效果
- `modules/skottie/src/effects/Effects.h` - 效果系统接口
- `include/effects/SkColorMatrix.h` - 颜色矩阵工具
- `include/effects/SkColorFilter.h` - 颜色滤镜 API
- `modules/sksg/include/SkSGColorFilter.h` - Scene Graph 节点
