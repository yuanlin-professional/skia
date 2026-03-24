# LevelsEffect - Skottie 色阶效果

> 源文件: `modules/skottie/src/effects/LevelsEffect.cpp`

## 概述

LevelsEffect 实现了 After Effects 中的色阶（Levels）颜色校正效果。该文件包含两个变体：**ADBE Easy Levels2**（简易色阶，单通道控制）和 **ADBE Pro Levels2**（专业色阶，独立 RGBA+RGB 通道控制）。两者均基于输入/输出黑白场映射和 Gamma 校正曲线，使用预计算的 256 项查找表（LUT）实现高效的像素级颜色变换。

## 架构位置

该文件位于 Skottie 效果子系统中（`skottie::internal` 命名空间），使用 `DiscardableAdapterBase` 适配器模式将 Lottie 动画属性映射到 `sksg::ExternalColorFilter` 场景图节点。

```
AnimationBuilder
  ├── EffectBuilder::attachEasyLevelsEffect()
  │     └── EasyLevelsEffectAdapter → sksg::ExternalColorFilter
  └── EffectBuilder::attachProLevelsEffect()
        └── ProLevelsEffectAdapter → sksg::ExternalColorFilter
```

## 主要类与结构体

### `ClipInfo`
```cpp
struct ClipInfo {
    ScalarValue fClipBlack = 1;  // 1: 裁剪, 2/3: 不裁剪
    ScalarValue fClipWhite = 1;
};
```
控制输出值是否裁剪到输出范围。

### `ChannelMapper`
核心数据结构，包含五个参数：
- `fInBlack` / `fInWhite`：输入黑白场
- `fOutBlack` / `fOutWhite`：输出黑白场
- `fGamma`：Gamma 校正指数

提供 `build_lut()` 方法生成 256 项查找表。

### `EasyLevelsEffectAdapter`
- 继承自 `DiscardableAdapterBase<EasyLevelsEffectAdapter, sksg::ExternalColorFilter>`
- 支持按通道选择（RGB、R、G、B、A）应用同一组色阶参数
- 绑定 9 个属性索引（通道、输入/输出黑白场、Gamma、裁剪开关）

### `ProLevelsEffectAdapter`
- 继承自 `DiscardableAdapterBase<ProLevelsEffectAdapter, sksg::ExternalColorFilter>`
- 拥有 5 个独立的 `ChannelMapper`（RGB、R、G、B、A）
- 绑定 38 个属性索引
- RGB 映射器组合在单独通道映射器之外

## 公共 API 函数

### `EffectBuilder::attachEasyLevelsEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachEasyLevelsEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```

### `EffectBuilder::attachProLevelsEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachProLevelsEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```

两者均将色阶效果附加到目标图层，区别在于参数粒度。

## 内部实现细节

### LUT 构建算法 (`ChannelMapper::build_lut`)

这是本文件最核心的算法，将输入范围 [inBlack..inWhite] 映射到输出范围 [outBlack..outWhite]，并应用 Gamma 校正：

```
output = outBlack + (outWhite - outBlack) * ((input - inBlack) / (inWhite - inBlack)) ^ (1/gamma)
```

关键细节：
1. **Gamma 反转**：使用 `1/max(gamma, 0)` 作为实际指数
2. **退化处理**：当 `dIn`（输入范围）接近零时，添加微小扰动避免除零
3. **裁剪控制**：根据 `ClipInfo` 和 Lottie 的 `kLottieDoClip` 值决定是否裁剪输出
4. **恒等检测**：若输入输出范围相同且 gamma 为 1，返回 `nullptr` 跳过 LUT
5. **范围反转**：支持 outBlack > outWhite 的反转映射

### Easy Levels 的 onSync

根据通道选择（1-5）构建 LUT，然后调用 `SkColorFilters::TableARGB()` 创建颜色滤镜，为选中通道应用 LUT，未选中通道传入 `nullptr`。

### Pro Levels 的 onSync

1. 分别为 R、G、B、A 通道构建独立的 LUT
2. 使用 `SkColorFilters::TableARGB` 创建通道级滤镜
3. 额外构建 RGB 通道的统一映射器，通过 `SkColorFilters::Compose` 组合在独立通道滤镜之上

注意：RGB 映射器复用了 `a_lut_storage`，因为 Alpha 通道的 LUT 此时已被 TableARGB 消费。

### 通道枚举
```cpp
enum LottieChannel {
    kRGB_Channel = 1,
    kR_Channel = 2,
    kG_Channel = 3,
    kB_Channel = 4,
    kA_Channel = 5,
};
```

## 依赖关系

- **Skia 核心**：`SkColorFilter`（`TableARGB`、`Compose`）、`SkScalar`
- **Skia 工具**：`SkTPin`、`SkFloatingPoint`（`sk_ieee_float_divide`）
- **Skottie 内部**：`Adapter.h`（`DiscardableAdapterBase`）、`Effects.h`（`EffectBinder`）
- **SkSG**：`SkSGColorFilter.h`（`ExternalColorFilter`）

## 设计模式与设计决策

1. **LUT 预计算**：使用 256 项查找表而非实时函数计算，将复杂的 Gamma 幂运算转化为常量时间查表，这是图像处理中的经典优化策略。

2. **共享 ChannelMapper 结构**：Easy 和 Pro 两个适配器共享同一个 `ChannelMapper` 结构和 `build_lut` 算法，实现了代码复用。

3. **组合式颜色滤镜**：Pro Levels 中 RGB 映射器通过 `Compose` 叠加在通道映射器之上，体现了函数组合的设计思想。

4. **退化安全**：LUT 构建中对 dIn 接近零的退化情况进行了仔细处理，通过添加 epsilon 扰动保证数值稳定性。

5. **null 优化**：当通道映射为恒等变换时返回 nullptr，`TableARGB` 会跳过该通道的处理。

## 性能考量

- 256 项 LUT 在栈上分配（`std::array<uint8_t, 256>`），避免堆内存分配
- LUT 仅在动画属性变化时重建，渲染时为 O(1) 查表
- 恒等映射检测避免创建无效的颜色滤镜
- Pro Levels 最多可有 5 个独立 LUT，但通过 `TableARGB` 一次性应用到四个通道，仅需一次像素遍历
- `DiscardableAdapterBase` 允许在动画属性稳定后释放适配器资源

## 补充说明

### Easy vs Pro Levels 对比

| 特性 | Easy Levels | Pro Levels |
|------|-------------|------------|
| 通道控制 | 1 组，选择目标通道 | 5 组独立通道 |
| 属性数量 | 9 个 | 38 个 |
| RGB 统一映射 | 由通道选择决定 | 独立 RGB 映射 + 组合 |
| 适用场景 | 简单色阶调整 | 专业颜色分级 |

### LUT 退化处理的数学细节

当输入黑白场相同（`dIn == 0`）时，数学公式中的除法会产生无穷大。代码通过以下方式处理：
1. 对 `dIn` 添加 `2 * SK_ScalarNearlyZero` 的符号化扰动
2. 将 `in_0` 向 0.5 方向微调，允许在非退化输出区间时产生突变过渡
3. 这种处理产生了更接近 AE 的视觉效果

### ClipInfo 的 Lottie 编码

裁剪控制使用整数编码：值 1 表示执行裁剪，值 2 或 3 表示不裁剪。这种非直觉的编码方式来自 Lottie 文件格式规范。裁剪的方向（上裁剪或下裁剪）取决于 outBlack 与 outWhite 的大小关系。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBuilder 定义
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `include/core/SkColorFilter.h` - SkColorFilters::TableARGB / Compose
- `modules/skottie/src/effects/BrightnessContrastEffect.cpp` - 另一个颜色校正效果
- `modules/sksg/include/SkSGColorFilter.h` - ExternalColorFilter 场景图节点
