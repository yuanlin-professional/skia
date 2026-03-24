# HueSaturationEffect

> 源文件: modules/skottie/src/effects/HueSaturationEffect.cpp

## 概述

HueSaturationEffect 模块实现了色相/饱和度/亮度颜色校正效果,提供对图层颜色属性的精确控制。该效果模拟 Adobe After Effects 的色相/饱和度效果,支持独立调整色相偏移、饱和度缩放和亮度变化,是视频后期制作中常用的颜色校正工具。

## 架构位置

HueSaturationEffect 属于 Skottie 的颜色效果系统:

```
modules/skottie/
  └── src/
      └── effects/
          ├── HueSaturationEffect.cpp  # 色相饱和度实现
          ├── Effects.h                # 效果接口
          └── InvertEffect.cpp         # 其他颜色效果
```

该模块使用 SkRuntimeEffect 实现自定义 SkSL 着色器,通过 HSLA 颜色空间进行高性能颜色变换。

## 主要类与结构体

### HueSaturationEffectAdapter

色相饱和度效果适配器,管理颜色调整参数并生成对应的颜色滤镜。

```cpp
class HueSaturationEffectAdapter final : public AnimatablePropertyContainer
```

**关键成员变量:**
- `fColorFilter` - `sksg::ExternalColorFilter` 智能指针,用于应用颜色变换
- `fChanCtrl` - 通道控制(当前仅支持主通道)
- `fMasterHue` - 主色相偏移(度数,-180 到 +180)
- `fMasterSat` - 主饱和度调整(百分比,-100 到 +100)
- `fMasterLight` - 主亮度调整(百分比,-100 到 +100)

**通道枚举:**
```cpp
enum : uint8_t {
    kMaster_Chan   = 0x01,  // 主通道(所有颜色)
    kReds_Chan     = 0x02,  // 红色通道
    kYellows_Chan  = 0x03,  // 黄色通道
    kGreens_Chan   = 0x04,  // 绿色通道
    kCyans_Chan    = 0x05,  // 青色通道
    kBlues_Chan    = 0x06,  // 蓝色通道
    kMagentas_Chan = 0x07,  // 品红通道
};
```

## 公共 API 函数

### attachHueSaturationEffect

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachHueSaturationEffect(
    const skjson::ArrayValue& jprops,
    sk_sp<sksg::RenderNode> layer) const
```

将色相/饱和度效果附加到渲染节点。

**参数:**
- `jprops` - JSON 属性数组,包含通道控制、色相、饱和度、亮度等参数
- `layer` - 源渲染节点

**返回值:** 应用效果后的渲染节点

**属性索引:**
```cpp
enum : size_t {
    kChannelControl_Index = 0,   // 通道选择
    kChannelRange_Index = 1,     // 通道范围
    kMasterHue_Index = 2,        // 主色相
    kMasterSat_Index = 3,        // 主饱和度
    kMasterLightness_Index = 4,  // 主亮度
    kColorize_Index = 5,         // 着色开关
    kColorizeHue_Index = 6,      // 着色色相
    kColorizeSat_Index = 7,      // 着色饱和度
    kColorizeLightness_Index = 8 // 着色亮度
};
```

## 内部实现细节

### 饱和度调整算法

AE 饱和度语义使用自定义算法,而非简单的 HSL 饱和度调整:

1. **计算色度中点** - 在 RGB 最小值和最大值之间插值
2. **缩放约束** - 限制缩放因子,防止任何通道过饱和或欠饱和
3. **相对缩放** - 相对于色度中点进行插值

**SkSL 饱和度着色器:**

```glsl
uniform half u_scale;

half4 main(half4 c) {
    // 计算 min 和 max 分量
    half2 rg_srt = (c.r < c.g) ? c.rg : c.gr;
    half c_min = min(rg_srt.x, c.b),
         c_max = max(rg_srt.y, c.b),

    // 色度和中点
    ch     = max(c_max - c_min, 0.0001),
    ch_mid = (c_min + c_max)*0.5,

    // 限制缩放以防过饱和
    scale_max = min(ch_mid, c.a - ch_mid)/ch*2,
    scale = min(u_scale, scale_max);

    // 线性插值
    c.rgb = ch_mid + (c.rgb - ch_mid)*scale;

    return c;
}
```

### 控制映射

**色相控制:**
- 线性映射: `hue_offset = fMasterHue / 360`
- 应用 HSLA 矩阵的第一行偏移

**饱和度控制:**
- 去饱和 [-100, 0): `scale = 1 + (sat/100)`  (线性)
- 增饱和 [0, 100]: `scale = 100/(100 - sat)` (非线性)
- 最大缩放限制: 126.0f

**亮度控制:**
- 减亮 [-100, 0): 向 0 插值,`lerp_scale = 1 + (light/100)`
- 增亮 [0, 100]: 向 1 插值,`lerp_scale = 1 - (light/100)`

### 颜色滤镜链构建

```cpp
sk_sp<SkColorFilter> makeColorFilter() const {
    sk_sp<SkColorFilter> cf;

    // 1. 色相偏移
    if (!SkScalarNearlyZero(fMasterHue)) {
        const auto h = fMasterHue/360;
        const float cm[20] = {
            1, 0, 0, 0, h,
            0, 1, 0, 0, 0,
            0, 0, 1, 0, 0,
            0, 0, 0, 1, 0,
        };
        cf = SkColorFilters::HSLAMatrix(cm);
    }

    // 2. 饱和度调整
    if (!SkScalarNearlyZero(fMasterSat)) {
        const auto s = SkTPin(fMasterSat/100, -1.0f, 1.0f);
        const auto chroma_scale = s < 0 ? s + 1 : std::min(1/(1 - s), 126.0f);
        cf = SkColorFilters::Compose(std::move(cf), make_saturate(chroma_scale));
    }

    // 3. 亮度调整
    if (!SkScalarNearlyZero(fMasterLight)) {
        const auto l  = SkTPin(fMasterLight/100, -1.0f, 1.0f);
        const auto ls = 1 - std::abs(l);    // 缩放
        const auto lo = l < 0 ? 0 : 1 - ls; // 偏移

        const float cm[20] = {
            ls,  0,  0, 0, lo,
             0, ls,  0, 0, lo,
             0,  0, ls, 0, lo,
             0,  0,  0, 1,  0,
        };
        cf = SkColorFilters::Compose(std::move(cf), SkColorFilters::Matrix(cm));
    }

    return cf;
}
```

## 依赖关系

### Skia 核心依赖
- `SkColorFilter` - 颜色滤镜基类
- `SkRuntimeEffect` - 运行时 SkSL 编译
- `SkData` - Uniform 数据传递
- `SkString` - SkSL 源代码

### Skottie 框架依赖
- `SkottiePriv.h` - 内部工具和接口
- `animator/Animator.h` - 动画属性系统
- `effects/Effects.h` - 效果构建器
- `SkSGColorFilter.h` - Scene Graph 颜色滤镜节点

### 外部依赖
- `SkColorFilters::HSLAMatrix` - HSLA 颜色空间矩阵变换
- `SkColorFilters::Compose` - 颜色滤镜组合
- `SkColorFilters::Matrix` - RGB 颜色空间矩阵变换

## 设计模式与设计决策

### 组合模式

使用 `SkColorFilters::Compose` 将多个颜色滤镜组合成单一滤镜链,实现色相、饱和度、亮度的独立控制。

### 延迟求值

`onSync()` 方法在属性变化时重新构建颜色滤镜,采用延迟求值策略减少不必要的计算。

### 自定义 SkSL 着色器

饱和度调整使用自定义 SkSL 着色器而非标准 HSL 饱和度,精确模拟 AE 的饱和度语义:
- 保持预乘 alpha 状态
- 组件级缩放约束
- 非线性控制映射

### 条件滤镜构建

只为非零参数创建滤镜,优化无效果情况下的性能。

## 性能考量

### SkRuntimeEffect 缓存

```cpp
static const auto* effect =
    SkRuntimeEffect::MakeForColorFilter(SkString(gSaturateSkSL), {}).effect.release();
```

使用静态变量缓存编译后的 SkSL 效果,避免重复编译。

### Premul 着色器

自定义饱和度着色器在预乘 alpha 空间操作,避免昂贵的 unpremul/premul 转换。

### 快速路径

```cpp
if (static_cast<int>(fChanCtrl) != kMaster_Chan) {
    return nullptr;  // 快速退出
}
```

当前实现仅支持主通道,非主通道请求直接返回空滤镜。

### 零值检测

使用 `SkScalarNearlyZero` 跳过无效果的变换,减少滤镜链长度。

### 数值限制

```cpp
const auto chroma_scale = s < 0 ? s + 1 : std::min(1/(1 - s), kMaxScale);
```

限制饱和度缩放到 126 倍,防止数值爆炸和渲染瑕疵。

## 相关文件

- `modules/skottie/src/effects/InvertEffect.cpp` - 反相效果(类似颜色变换)
- `modules/skottie/src/effects/LevelsEffect.cpp` - 色阶效果
- `modules/skottie/src/effects/Effects.h` - 效果系统接口
- `modules/skottie/src/animator/Animator.h` - 动画属性容器
- `include/effects/SkRuntimeEffect.h` - SkSL 运行时
- `include/effects/SkColorFilter.h` - 颜色滤镜 API
