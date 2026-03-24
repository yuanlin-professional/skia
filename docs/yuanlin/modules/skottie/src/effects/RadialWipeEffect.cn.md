# RadialWipeEffect - Skottie 径向擦除效果

> 源文件: `modules/skottie/src/effects/RadialWipeEffect.cpp`

## 概述

RadialWipeEffect 实现了 After Effects 中的"径向擦除"（Radial Wipe）效果。该效果以指定中心点为原点，通过扫描角度渐变遮罩实现图层的圆形擦除过渡动画。支持顺时针、逆时针和双向擦除模式，以及可选的边缘羽化效果。实现上使用自定义渲染节点 `RWipeRenderNode` 和扫描渐变着色器（Sweep Gradient）作为遮罩。

## 架构位置

该文件位于 Skottie 效果子系统中（`skottie::internal` 命名空间），采用双层架构：自定义渲染节点负责实际渲染逻辑，适配器负责属性绑定和同步。

```
AnimationBuilder
  └── EffectBuilder::attachRadialWipeEffect()
        └── RadialWipeAdapter (DiscardableAdapterBase)
              └── RWipeRenderNode (CustomRenderNode)
                    └── SweepGradient 遮罩着色器
```

## 主要类与结构体

### `RWipeRenderNode`
- 继承自 `sksg::CustomRenderNode`
- 五个可动画属性（通过 `SG_ATTRIBUTE` 宏声明）：
  - `Completion`（完成度，0-100）
  - `StartAngle`（起始角度）
  - `WipeCenter`（擦除中心点）
  - `Wipe`（擦除方向：1=顺时针，2=逆时针，3=双向）
  - `Feather`（边缘羽化量）
- 缓存 `fMaskShader` 和 `fMaskSigma` 用于渲染

### `RadialWipeAdapter`
- 继承自 `DiscardableAdapterBase<RadialWipeAdapter, RWipeRenderNode>`
- 绑定 Lottie 动画属性到 RWipeRenderNode 的属性

### 属性索引枚举
- `kCompletion_Index = 0`
- `kStartAngle_Index = 1`
- `kWipeCenter_Index = 2`
- `kWipe_Index = 3`
- `kFeather_Index = 4`

## 公共 API 函数

### `EffectBuilder::attachRadialWipeEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachRadialWipeEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- **功能**：将径向擦除效果附加到目标图层
- **返回值**：包含 RWipeRenderNode 的渲染节点树

## 内部实现细节

### 渲染流程 (onRender)

1. **完全遮罩**（Completion >= 100）：直接返回，不渲染子节点
2. **无遮罩**（Completion <= 0）：直接渲染子节点，不应用遮罩
3. **部分遮罩**：使用 `ScopedRenderContext::modulateMaskShader()` 将扫描渐变着色器作为遮罩应用

### 遮罩着色器构建 (onRevalidate)

核心算法在 `onRevalidate` 中构建扫描渐变遮罩：

1. 计算过渡参数 `t = completion * 0.01`
2. 角度规范化：使用 `sanitize_angle` 将角度映射到 [0, 360) 范围
3. 计算起始角度 `a0`（起始角度 - 90 + t * 擦除对齐偏移）和结束角度 `a1 = a0 + t * 360`
4. 确保 `a0 < a1`，必要时交换并同时交换颜色
5. 使用 `SkShaders::SweepGradient` 创建扫描渐变，在 [a0, a1] 范围内产生从透明到不透明的硬边过渡

### 擦除方向对齐 (wipeAlignment)

```cpp
float wipeAlignment() const {
    switch (SkScalarRoundToInt(fWipe)) {
    case 1: return    0.0f; // 顺时针
    case 2: return -360.0f; // 逆时针
    case 3: return -180.0f; // 双向/居中
    }
}
```
通过不同的角度偏移量实现三种擦除方向。

### 渐变颜色设置

```cpp
const SkColor4f grad_colors[] = { c1, c0, c0, c1 };
const SkScalar   grad_pos[] = {  0,  0,  1,  1 };
```
使用硬边停止点创建瞬间过渡效果（两对相同位置的颜色停止点）。

### 边缘羽化

`fMaskSigma` 通过 `feather * kBlurSizeToSigma` 计算，但代码注释表明此功能当前被禁用（`TODO: this feature is disabled ATM`）。

## 依赖关系

- **Skia 核心**：`SkCanvas`、`SkShader`、`SkPoint`、`SkRect`、`SkScalar`
- **Skia 渐变**：`SkGradient`（`SkShaders::SweepGradient`）
- **Skottie 内部**：`Adapter.h`（`DiscardableAdapterBase`）、`Effects.h`（`EffectBinder`）
- **SkSG**：`SkSGRenderNode.h`（`CustomRenderNode`）、`SkSGNode.h`

## 设计模式与设计决策

1. **自定义渲染节点**：使用 `CustomRenderNode` 而非外部滤镜节点，因为径向擦除需要控制完整的渲染流程（包括短路逻辑和遮罩调制）。

2. **SG_ATTRIBUTE 宏**：为渲染节点属性自动生成 getter/setter，集成场景图失效通知机制。

3. **硬边渐变模拟擦除**：利用扫描渐变的硬停止点模拟二值擦除边缘，是一种巧妙的着色器技巧。

4. **无命中测试**：`onNodeAt` 返回 nullptr，表明此效果节点不参与命中测试。

5. **角度规范化**：使用 `fmod` + 条件加法确保角度始终在 [0, 360) 范围内。

## 性能考量

- Completion >= 100 时完全跳过渲染（早期退出），Completion <= 0 时跳过遮罩构建
- 扫描渐变着色器由 GPU 高效执行，无需逐像素计算
- 遮罩着色器仅在 `onRevalidate` 中构建（属性变化时），渲染时直接使用缓存
- 边缘羽化功能虽然计算了 sigma，但模糊过滤器当前禁用，避免了昂贵的模糊操作

## 补充说明

### 擦除方向详解

三种擦除方向的工作原理：
- **顺时针（Wipe=1）**：对齐偏移量为 0，从起始角度顺时针展开
- **逆时针（Wipe=2）**：对齐偏移量为 -360，从起始角度逆时针展开
- **双向/居中（Wipe=3）**：对齐偏移量为 -180，从起始角度向两侧同时展开

### 角度系统

AE 的角度系统与 Skia 的扫描渐变角度系统之间需要转换。代码中 `fStartAngle - 90` 将 AE 的 0 度（12 点钟方向）映射到 Skia 扫描渐变的参考方向。

### 遮罩颜色语义

渐变颜色中，白色 `{1,1,1,1}` 表示图层完全可见，透明黑 `{0,0,0,0}` 表示图层完全被遮罩。当 a0 > a1 时交换颜色和角度，确保渐变方向与擦除方向一致。

### kBlurSizeToSigma 常量

该常量将 AE 的模糊大小值转换为高斯模糊的 sigma 参数，定义在效果基类或公共头文件中，确保所有效果使用一致的模糊尺度映射。

## 相关文件

- `modules/skottie/src/effects/LinearWipeEffect.cpp` - 线性擦除效果（类似的遮罩机制）
- `modules/skottie/src/effects/Effects.h` - EffectBuilder 定义
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `modules/sksg/include/SkSGRenderNode.h` - CustomRenderNode 基类
- `include/effects/SkGradient.h` - 扫描渐变 API
