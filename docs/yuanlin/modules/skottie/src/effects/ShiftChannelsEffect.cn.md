# ShiftChannelsEffect - Skottie 通道偏移效果

> 源文件: `modules/skottie/src/effects/ShiftChannelsEffect.cpp`

## 概述

ShiftChannelsEffect 实现了 After Effects 中的通道偏移（Shift Channels）效果，允许将输出的 R、G、B、A 四个通道分别映射到输入的任意通道或预定义的亮度/HSL 值。效果通过构建 5x4 颜色矩阵实现，利用 Skia 的矩阵颜色滤镜进行逐像素颜色变换。支持 10 种通道源选项，包括直接通道映射、亮度映射、全开/全关和预留的 HSL 映射。

## 架构位置

ShiftChannelsEffect 位于 Skottie 效果子系统中，使用矩阵颜色滤镜管线。

```
EffectBuilder::attachShiftChannelsEffect()
  |
  +-> ShiftChannelsEffectAdapter (效果适配器)
        |
        +-> AnimatablePropertyContainer
        +-> sksg::ExternalColorFilter [颜色滤镜节点]
        +-> EffectBinder [绑定 4 个通道参数]
        +-> onSync() [构建 5x4 颜色矩阵]
```

## 主要类与结构体

### ShiftChannelsEffectAdapter
- 继承自 `AnimatablePropertyContainer`
- 持有 `sksg::ExternalColorFilter` 节点
- 属性（4 个可动画参数）：
  - `fR` - 红色通道源（默认 Source::kRed）
  - `fG` - 绿色通道源（默认 Source::kGreen）
  - `fB` - 蓝色通道源（默认 Source::kBlue）
  - `fA` - Alpha 通道源（默认 Source::kAlpha）
- JSON 属性索引：Alpha=0, Red=1, Green=2, Blue=3

### Source（枚举）
定义 10 种通道源：
```cpp
kAlpha      = 1    // 原始 Alpha 通道
kRed        = 2    // 原始红色通道
kGreen      = 3    // 原始绿色通道
kBlue       = 4    // 原始蓝色通道
kLuminance  = 5    // 亮度（BT.709 系数）
kHue        = 6    // 色相（TODO 未实现）
kLightness  = 7    // 明度（TODO 未实现）
kSaturation = 8    // 饱和度（TODO 未实现）
kFullOn     = 9    // 常量 1
kFullOff    = 10   // 常量 0
```

## 公共 API 函数

### `EffectBuilder::attachShiftChannelsEffect`
```cpp
sk_sp<sksg::RenderNode> attachShiftChannelsEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `ShiftChannelsEffectAdapter` 绑定参数
- 返回 ExternalColorFilter 节点

## 内部实现细节

### 颜色矩阵构建

每种通道源对应一组 5 维系数向量 `[R_coeff, G_coeff, B_coeff, A_coeff, Bias]`：

```cpp
static constexpr float gSourceCoeffs[][5] = {
    {             0,              0,              0, 1, 0}, // kAlpha
    {             1,              0,              0, 0, 0}, // kRed
    {             0,              1,              0, 0, 0}, // kGreen
    {             0,              0,              1, 0, 0}, // kBlue
    {SK_LUM_COEFF_R, SK_LUM_COEFF_G, SK_LUM_COEFF_B, 0, 0}, // kLuminance
    {             0,              0,              0, 0, 0}, // kHue (TODO)
    {             0,              0,              0, 0, 0}, // kLightness (TODO)
    {             0,              0,              0, 0, 0}, // kSaturation (TODO)
    {             0,              0,              0, 0, 1}, // kFullOn
    {             0,              0,              0, 0, 0}, // kFullOff
};
```

**矩阵组装：**
```
| rc[0]  rc[1]  rc[2]  rc[3]  rc[4] |   // 输出 R 行
| gc[0]  gc[1]  gc[2]  gc[3]  gc[4] |   // 输出 G 行
| bc[0]  bc[1]  bc[2]  bc[3]  bc[4] |   // 输出 B 行
| ac[0]  ac[1]  ac[2]  ac[3]  ac[4] |   // 输出 A 行
```

每行对应一个输出通道，系数来自该通道选择的源类型。

**示例：** 若 fR=kGreen, fG=kLuminance, fB=kRed, fA=kFullOn：
```
| 0        1        0        0  0 |  // R = 输入G
| 0.2126   0.7152   0.0722   0  0 |  // G = 亮度
| 1        0        0        0  0 |  // B = 输入R
| 0        0        0        0  1 |  // A = 1.0
```

### 亮度系数
- 使用 `SK_LUM_COEFF_R`、`SK_LUM_COEFF_G`、`SK_LUM_COEFF_B`
- 这些是 BT.709 标准的亮度系数（R=0.2126, G=0.7152, B=0.0722）

### 参数范围限制
```cpp
src = SkTPin(src, 1.0f, static_cast<float>(Source::kMax));
```
- 源值限制在 [1, 10] 范围内（对应 Source 枚举的有效范围）
- 转换为数组索引：`static_cast<size_t>(src) - 1`

### Alpha 通道覆盖范围
```cpp
fColorFilter->setCoverage(fA == static_cast<float>(Source::kFullOn)
    ? sksg::ExternalColorFilter::Coverage::kBoundingBox
    : sksg::ExternalColorFilter::Coverage::kNormal);
```
- 当 Alpha 源为 kFullOn 时，将覆盖范围扩展到内容边界框
- 这是因为 kFullOn 会使原本透明的区域变为不透明，需要扩展渲染区域

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkColorFilter.h` | SkColorFilters::Matrix |
| `SkTPin.h` | 参数范围限制 |
| `SkColorData.h` | SK_LUM_COEFF_R/G/B 亮度系数 |
| `SkSGColorFilter.h` | ExternalColorFilter |
| `Animator.h` | AnimatablePropertyContainer |
| `Effects.h` | EffectBinder |
| `SkottieValue.h` | ScalarValue |

## 设计模式与设计决策

- **系数查表法**：通过预定义的系数表将通道源枚举映射到矩阵行，避免了复杂的条件分支。
- **矩阵颜色滤镜**：使用 Skia 标准的 5x4 颜色矩阵，能够表达线性颜色变换和常量偏置。
- **覆盖范围控制**：kFullOn Alpha 源需要特殊处理覆盖范围，确保原本透明区域也被渲染。
- **渐进式实现**：HSL 相关源（Hue、Lightness、Saturation）标记为 TODO，当前输出全零（等效于 kFullOff）。注释提到完整 HSL 支持需要自定义颜色滤镜。
- **工厂方法**：`ShiftChannelsEffectAdapter::Make` 封装节点创建和绑定。

## 性能考量

- `SkColorFilters::Matrix` 在 GPU 上作为颜色滤镜高效执行，仅需一次矩阵-向量乘法。
- 系数查表为常量时间操作 O(1)。
- 颜色矩阵仅在参数变化时重建，不在每像素执行。
- `static_assert` 确保系数表与枚举同步，编译时安全保障。
- 4 个通道参数独立动画，任一变化触发完整矩阵重建（矩阵创建开销极小）。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder
- `modules/sksg/include/SkSGColorFilter.h` - ExternalColorFilter
- `include/core/SkColorFilter.h` - SkColorFilters::Matrix
- `src/core/SkColorData.h` - SK_LUM_COEFF 常量
- `modules/skottie/src/effects/ThresholdEffect.cpp` - 同样使用亮度系数的效果
- `modules/skottie/src/effects/TintEffect.cpp` - 另一种颜色映射效果
