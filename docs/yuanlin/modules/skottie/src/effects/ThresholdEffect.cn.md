# ThresholdEffect - Skottie 阈值效果

> 源文件: `modules/skottie/src/effects/ThresholdEffect.cpp`

## 概述

ThresholdEffect 实现了 After Effects 中的阈值（Threshold）效果，将图层转换为纯黑白图像。该效果基于像素亮度（luminance）和可动画的阈值参数进行二值化：亮度高于阈值的像素变为白色，低于阈值的变为黑色。实现使用 SkSL 运行时颜色滤镜，通过 GLSL `step()` 函数实现高效的阈值判断。

## 架构位置

ThresholdEffect 位于 Skottie 效果子系统中，使用 SkSL 运行时颜色滤镜管线。

```
EffectBuilder::attachThresholdEffect()
  |
  +-> ThresholdAdapter (效果适配器)
        |
        +-> DiscardableAdapterBase<..., sksg::ExternalColorFilter>
        +-> EffectBinder [绑定 Level 参数]
        +-> onSync() [创建 SkSL 颜色滤镜]
        +-> threshold_effect() [全局缓存的 SkRuntimeEffect]
```

## 主要类与结构体

### ThresholdAdapter
- 继承自 `DiscardableAdapterBase<ThresholdAdapter, sksg::ExternalColorFilter>`
- 单一属性 `fLevel`（阈值级别）
- JSON 属性索引：kLevel_Index = 0
- `onSync()` 创建带当前阈值的颜色滤镜

## 公共 API 函数

### `EffectBuilder::attachThresholdEffect`
```cpp
sk_sp<sksg::RenderNode> attachThresholdEffect(const skjson::ArrayValue& jprops,
                                               sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `ThresholdAdapter` 绑定参数
- 通过 `attachDiscardableAdapter` 管理生命周期

## 内部实现细节

### SkSL 着色器代码
```glsl
uniform half t;

half4 main(half4 color) {
    half4 c = unpremul(color);
    half lum = dot(c.rgb, half3(0.2126, 0.7152, 0.0722)),
          bw = step(t, lum);
    return bw.xxx1 * c.a;
}
```

**工作流程：**
1. `unpremul(color)` - 将预乘 alpha 颜色还原为直通颜色
2. 使用 ITU-R BT.709 标准系数计算亮度：`lum = 0.2126*R + 0.7152*G + 0.0722*B`
3. `step(t, lum)` - 当 `lum >= t` 时返回 1（白色），否则返回 0（黑色）
4. `bw.xxx1 * c.a` - 扩展到 RGB 通道并重新应用原始 alpha

### 效果缓存
```cpp
static sk_sp<SkRuntimeEffect> threshold_effect() {
    static const SkRuntimeEffect* effect =
        SkRuntimeEffect::MakeForColorFilter(SkString(gThresholdSkSL), {}).effect.release();
    return sk_ref_sp(effect);
}
```
- 全局静态缓存，整个程序生命周期内只编译一次
- 使用 `release()` + `sk_ref_sp()` 模式：`release()` 将所有权转移到裸指针，后续通过 `sk_ref_sp` 获取共享引用

### Uniform 数据传递
```cpp
void onSync() override {
    auto cf = threshold_effect()->makeColorFilter(
        SkData::MakeWithCopy(&fLevel, sizeof(fLevel)));
    this->node()->setColorFilter(std::move(cf));
}
```
- `fLevel` 值直接作为二进制数据拷贝到 uniform 块
- `sizeof(fLevel)` = sizeof(float) = 4 字节，对应 SkSL 中的 `uniform half t`

### Alpha 保留
着色器输出 `bw.xxx1 * c.a` 确保：
- RGB 通道被二值化结果替换
- Alpha 通道保留原始值
- 结果是预乘 alpha 格式（黑白值 * alpha）

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkRuntimeEffect.h` | SkSL 运行时颜色滤镜 |
| `SkData.h` | Uniform 数据传递 |
| `SkString.h` | SkSL 代码字符串 |
| `Adapter.h` | DiscardableAdapterBase |
| `Effects.h` | EffectBinder |
| `SkSGColorFilter.h` | ExternalColorFilter |
| `SkottieValue.h` | ScalarValue |

## 设计模式与设计决策

- **SkSL 颜色滤镜**：使用 SkRuntimeEffect 而非预定义滤镜，提供精确的 AE 行为匹配。
- **全局缓存编译**：SkSL 着色器仅编译一次并全局缓存，避免重复编译开销。
- **BT.709 亮度**：使用标准的 ITU-R BT.709 亮度系数（0.2126, 0.7152, 0.0722），与 AE 的亮度计算一致。
- **step 函数**：利用 GLSL 内建 `step()` 函数实现无分支的阈值判断，GPU 友好。
- **预乘 alpha 处理**：先 unpremul 再计算亮度，最后重新乘以 alpha，确保 alpha 通道不影响亮度判断。

## 性能考量

- SkSL 颜色滤镜在 GPU 上逐像素并行执行，性能优异。
- `step()` 是 GPU 原生操作，无分支开销。
- 每帧仅创建新的颜色滤镜对象（轻量操作），SkRuntimeEffect 本身被缓存。
- `SkData::MakeWithCopy` 仅拷贝 4 字节，开销可忽略。
- 单一 uniform 参数，数据传输开销最小。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase
- `modules/sksg/include/SkSGColorFilter.h` - ExternalColorFilter
- `include/effects/SkRuntimeEffect.h` - SkSL 运行时效果
- `modules/skottie/src/effects/ShiftChannelsEffect.cpp` - 类似的逐像素颜色操作
