# VenetianBlindsEffect - Skottie 百叶窗效果

> 源文件: `modules/skottie/src/effects/VenetianBlindsEffect.cpp`

## 概述

VenetianBlindsEffect 实现了 After Effects 中的百叶窗转场效果（Venetian Blinds Transition）。该效果通过一个沿指定方向重复的线性渐变遮罩来模拟百叶窗的开合，支持完成度、方向角度、条纹宽度和羽化程度的动画控制。效果通过 SkShader 渐变实现，避免了昂贵的模糊操作。

## 架构位置

VenetianBlindsEffect 位于 Skottie 效果子系统中，继承自 `MaskShaderEffectBase`，是基于着色器遮罩的效果实现之一。

```
EffectBuilder::attachVenetianBlindsEffect()
  |
  +-> VenetianBlindsAdapter (效果适配器)
        |
        +-> MaskShaderEffectBase (遮罩着色器基类)
        |     +-> onMakeMask() [生成遮罩着色器]
        |
        +-> EffectBinder (属性绑定)
              +-> Completion, Direction, Width, Feather
```

## 主要类与结构体

### VenetianBlindsAdapter
- 继承自 `MaskShaderEffectBase`
- 通过 `EffectBinder` 绑定四个可动画属性
- `onMakeMask()` 生成遮罩着色器或透传信号
- 属性：
  - `fCompletion` - 完成度（0-100），控制百叶窗开合程度
  - `fDirection` - 方向角度（度），控制条纹方向
  - `fWidth` - 条纹宽度
  - `fFeather` - 羽化程度，控制边缘软硬度

## 公共 API 函数

### `EffectBuilder::attachVenetianBlindsEffect`
```cpp
sk_sp<sksg::RenderNode> attachVenetianBlindsEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `VenetianBlindsAdapter` 并附加到图层
- 通过 `attachDiscardableAdapter` 管理生命周期

## 内部实现细节

### 遮罩生成逻辑（onMakeMask）

**快速路径：**
- `fCompletion >= 100`：图层完全隐藏，返回透明色着色器
- `fCompletion <= 0`：图层完全可见，返回 nullptr（无遮罩）

**渐变构建：**

百叶窗效果本质上是一个沿方向向量重复的单周期渐变，其形状由完成度 `t` 和羽化 `feather` 决定。

渐变的四个关键色标位置（相对于归一化的条纹周期）：
```
fp0 = 0         (通过偏移消除)
fp1 = t - df0   (从透明到不透明的过渡结束)
fp2 = t + df1   (从不透明到透明的过渡开始)
fp3 = 1 - df1   (从不透明到透明的过渡结束)
```

其中 `df0` 和 `df1` 是羽化距离（归一化到色标空间），分别限制在 `t` 和 `1-t` 范围内以防溢出。

**梯度值计算：**
- `g01` = 渐变在 fp0/fp1 处的透明度值（当 fp0-fp1 折叠时 > 0）
- `g23` = 渐变在 fp2/fp3 处的透明度值（当 fp2-fp3 折叠时 < 1）
- 四色 RGBA 颜色：`c01, c23, c23, c01`（白色，alpha 不同）

**几何计算：**
- 角度从度转换为弧度：`angle = -fDirection` 度（取负号适配坐标系）
- 渐变中心 = 图层中心点
- 渐变向量 = `size * (cos(angle), -sin(angle))`
- 两个渐变端点通过 `df0` 偏移补偿（使 fp0 与 pts[0] 对齐）

**重复平铺：**
- 使用 `SkTileMode::kRepeat` 实现百叶窗的多条纹效果

### 羽化软化策略
通过调整渐变色标而非后处理模糊来实现羽化，这是一个重要的性能优化。`kFeatherSigmaFactor = 3.0` 和 `kMinFeather = 0.5` 确保即使在零羽化时渐变边缘也有基本的平滑度。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkShader.h` / `SkGradient.h` | 线性渐变着色器 |
| `SkTileMode.h` | 重复平铺模式 |
| `SkottiePriv.h` | AnimationBuilder 定义 |
| `SkottieValue.h` | ScalarValue 类型 |
| `Effects.h` | MaskShaderEffectBase 基类、EffectBinder |
| `SkSGRenderNode.h` | RenderNode 基类 |

## 设计模式与设计决策

- **模板方法模式**：`MaskShaderEffectBase` 定义遮罩应用框架，`VenetianBlindsAdapter` 通过重写 `onMakeMask()` 提供具体遮罩生成逻辑。
- **渐变模拟羽化**：使用带软边的渐变色标代替模糊滤镜，将 O(N*radius) 的模糊操作降低为 O(1) 的渐变采样。
- **快速路径优化**：完成度为 0% 或 100% 时跳过渐变生成，返回预设值。
- **数学简化**：通过渐变偏移消除 fp0 色标，减少渐变色标数量至 4 个。

## 性能考量

- 渐变着色器在 GPU 上高效渲染，避免了模糊滤镜的像素级操作。
- 仅 4 个色标的简单线性渐变，GPU 开销极低。
- `kRepeat` 平铺模式由硬件纹理采样器原生支持。
- 完成度极值（0/100）的快速路径完全跳过着色器创建。
- 三角函数（cos/sin）仅在属性变化时计算，不在每像素执行。

### 渐变数学推导详解

百叶窗效果的渐变构造涉及几个关键数学步骤：

**归一化色标空间：**
一个完整的百叶窗条纹周期被映射到 [0, 1] 区间。阈值 `t`（完成度 / 100）将周期分为透明区域 [0, t] 和不透明区域 [t, 1]。

**羽化距离计算：**
- `df = feather / size` - 将像素空间的羽化距离归一化到色标空间
- `df0 = 0.5 * min(df, t)` - 透明端的羽化距离（不超过透明区域的一半）
- `df1 = 0.5 * min(df, 1-t)` - 不透明端的羽化距离（不超过不透明区域的一半）

**色标折叠处理：**
当羽化距离大于可用空间时，fp0-fp1 或 fp2-fp3 会折叠（两个色标位于同一位置）。此时对应的渐变值 g01 或 g23 会偏离 0/1，产生部分透明效果。这确保了在极端参数组合下效果仍然平滑。

**偏移优化：**
整个渐变向负方向偏移 `df0`，使 fp0 与渐变起点对齐。这消除了一个色标（fp0），将色标数量从 5 个减少到 4 个。

### 方向角度到渐变向量的映射

方向参数 `fDirection` 以度为单位，转换过程：
1. 取负号：`angle = -fDirection`（匹配 AE 的方向定义）
2. 转换为弧度：`angle = SkDegreesToRadians(angle)`
3. 计算渐变向量：`(size * cos(angle), -size * sin(angle))`
4. Y 分量取负号以适配屏幕坐标系（Y 轴向下）

渐变的两个端点从图层中心向两侧偏移，间距为一个条纹周期的宽度（`size`）。

### MaskShaderEffectBase 基类的工作原理

`MaskShaderEffectBase` 提供了一个通用框架，用于通过着色器遮罩控制图层可见性：

1. 子类通过 `onMakeMask()` 返回一个 `MaskInfo`，包含遮罩着色器和可见性标志
2. 基类将遮罩着色器应用到图层上，控制像素级的透明度
3. 返回 nullptr 着色器表示图层完全可见（无遮罩）
4. 返回透明色着色器表示图层完全隐藏
5. `layerSize()` 方法提供图层尺寸供遮罩计算使用

## 相关文件

- `modules/skottie/src/effects/Effects.h` - MaskShaderEffectBase 基类、EffectBinder
- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder
- `modules/skottie/src/Adapter.h` - 适配器基类
- `include/effects/SkGradient.h` - SkShaders::LinearGradient
