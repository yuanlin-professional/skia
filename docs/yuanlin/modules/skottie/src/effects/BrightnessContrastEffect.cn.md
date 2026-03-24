# BrightnessContrastEffect - Skottie 亮度与对比度效果

> 源文件: `modules/skottie/src/effects/BrightnessContrastEffect.cpp`

## 概述

BrightnessContrastEffect 实现了 After Effects (AE) 中的亮度/对比度（Brightness/Contrast）效果。该效果支持两种模式：**现代模式**和**传统模式**（Legacy），它们在数学传递函数和参数范围上有本质区别。现代模式使用基于 SkRuntimeEffect 的运行时着色器进行非线性颜色变换，而传统模式则通过简单的颜色矩阵实现线性缩放与偏移。

## 架构位置

该文件属于 Skottie 动画模块的效果子系统，位于 `skottie::internal` 命名空间中。在 Skottie 的渲染管线中，效果通过 `EffectBuilder` 注册并附加到图层的渲染节点树（Scene Graph）上。该效果作为颜色滤镜（Color Filter）应用于目标图层，使用 `sksg::ExternalColorFilter` 作为场景图节点。

```
AnimationBuilder
  └── EffectBuilder::attachBrightnessContrastEffect()
        └── BrightnessContrastAdapter (DiscardableAdapterBase)
              └── sksg::ExternalColorFilter
                    └── SkColorFilter (Runtime/Matrix)
```

## 主要类与结构体

### `BrightnessContrastAdapter`
- 继承自 `DiscardableAdapterBase<BrightnessContrastAdapter, sksg::ExternalColorFilter>`
- 作为 Lottie JSON 属性与 Skia 渲染之间的桥梁
- 管理三个动画属性：`fBrightness`、`fContrast`、`fUseLegacy`
- 持有两个预编译的 `SkRuntimeEffect` 实例（亮度效果和对比度效果）

### 动画属性枚举
- `kBrightness_Index = 0`：亮度参数
- `kContrast_Index = 1`：对比度参数
- `kUseLegacy_Index = 2`：是否使用传统模式

## 公共 API 函数

### `EffectBuilder::attachBrightnessContrastEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachBrightnessContrastEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- **功能**：将亮度/对比度效果附加到指定图层
- **参数**：`jprops` 为 Lottie JSON 属性数组，`layer` 为目标渲染节点
- **返回值**：包装了效果的新渲染节点

## 内部实现细节

### 对比度传递函数（现代模式）

对比度效果使用三次多项式近似：

```
f(x) = -2*pi*C/3 * x^3 + pi*C * x^2 + (1 - pi*C/3) * x
```

其中 C 为归一化对比度值 [-1..1]。该公式通过以下推导获得：
1. 对 AE 对比度效果进行采样
2. 进行三次多项式曲线拟合
3. 利用约束条件 f(0)=0, f(1)=1, f(0.5)=0.5 求解系数

可选的精确模式（通过 `SKOTTIE_ACCURATE_CONTRAST_APPROXIMATION` 宏启用）使用正弦函数近似：
```
f(x) = x + a * sin(2*pi*x), a = -contrast/(3*pi)
```

### 亮度传递函数（现代模式）

```
f(x) = 1 - (1-x)^(2^(1.8*B))
```

其中 B 为归一化亮度值 [-1..1]。参数范围为 [-150..150]，归一化后映射到 [-1..1]。

### 传统模式（Legacy）

传统模式使用 5x4 颜色矩阵：
- **亮度**：直接作为分量偏移量（基于 255 的范围），范围 [-100..100]
- **对比度**：作为线性缩放+偏移变换
  - `contrast(-100)` 总是产生中灰色 0.5
  - `contrast(0)` 为中性值（恒等变换）
  - `contrast(100)` 总是产生白色 1.0
- 缩放因子 S 从对比度派生，偏移量 B 由亮度和对比度共同决定

### onSync 方法

根据 `fUseLegacy` 标志选择 `makeLegacyCF()` 或 `makeCF()`，通过 `SkScalarRoundToInt` 将浮点值转换为布尔判断。

### SkRuntimeEffect 着色器

对比度和亮度的 SkSL 着色器代码以 `constexpr char` 数组定义，在适配器构造时通过 `SkRuntimeEffect::MakeForColorFilter()` 编译。着色器使用 Horner 方法优化多项式求值：
```glsl
color.rgb = ((a*color.rgb + b)*color.rgb + c)*color.rgb;
```

## 依赖关系

- **Skia 核心**：`SkColorFilter`、`SkData`、`SkScalar`、`SkRuntimeEffect`
- **Skia 工具**：`SkTPin`（值域钳制）
- **Skottie 内部**：`Adapter.h`（`DiscardableAdapterBase`）、`SkottiePriv.h`、`SkottieValue.h`（`ScalarValue`）、`Effects.h`（`EffectBinder`、`EffectBuilder`）
- **SkSG（场景图）**：`SkSGColorFilter.h`（`ExternalColorFilter`）、`SkSGRenderNode.h`

## 设计模式与设计决策

1. **适配器模式**：`BrightnessContrastAdapter` 将 Lottie 动画属性适配到 Skia 场景图节点，遵循 Skottie 效果系统的统一架构。

2. **运行时着色器 vs 矩阵**：现代模式使用 SkRuntimeEffect 实现非线性传递函数，传统模式退化为简单的颜色矩阵，体现了精度与性能的权衡。

3. **编译期多态**：通过 `SKOTTIE_ACCURATE_CONTRAST_APPROXIMATION` 宏在编译期选择对比度近似方案，避免运行时分支。

4. **组合式颜色滤镜**：现代模式通过 `SkColorFilters::Compose` 将亮度和对比度滤镜组合，滤镜为 null 时自动跳过（优化）。

5. **AE 行为模拟**：代码中多处注释标注了 AE 的特殊行为（如传统模式下亮度偏移与对比度缩放的非标准组合方式），确保视觉一致性。

## 性能考量

- 当亮度或对比度接近零时（`SkScalarNearlyZero`），对应的运行时效果不会创建，返回 `nullptr` 以避免无效计算
- 默认的三次多项式近似相比正弦函数近似更快（避免 `sin` 调用），但精度稍低
- SkRuntimeEffect 着色器在构造时编译一次，后续仅更新 uniform 数据
- 传统模式使用颜色矩阵是最高效的路径，仅需一次矩阵-向量乘法
- 使用 `DiscardableAdapterBase` 基类，在动画属性不再变化时可丢弃适配器以释放资源

## 补充说明

### 传统模式缩放因子推导

传统模式中缩放因子 S 的计算逻辑：
- 对比度 [-1, 0] 范围：`S = 1 + contrast`，线性从 0 到 1
- 对比度 (0, 1] 范围：`S = 1 / max(1 - contrast, epsilon)`，从 1 趋向无穷大
- 偏移量 B 同时考虑亮度和对比度：`B = 0.5*(1-S) + brightness * max(S, 1.0)`

这种非对称的处理方式（"Why do these pre/post compose depending on contrast scale?"）完全是为了匹配 AE 的行为。

### 参数范围差异

| 模式   | 亮度范围     | 对比度范围    | 归一化方式     |
|--------|-------------|-------------|---------------|
| 现代   | [-150, 150] | [-50, 100]  | /150, /100    |
| 传统   | [-100, 100] | [-100, 100] | /255, /100    |

注意现代模式的亮度归一化除以 150，而传统模式除以 255，这反映了两种模式完全不同的数学模型。

### 对比度近似方案对比

源代码中引用了 4 个 Desmos 可视化链接用于验证近似精度：
1. AE 采样数据
2. 多项式曲线拟合
3. 三次多项式近似结果
4. 正弦函数近似结果

两种近似方案的主要区别在于 GPU 开销：三次多项式仅需乘加运算，而正弦函数需要超越函数计算。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - 效果系统入口与 EffectBinder/EffectBuilder 定义
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `modules/skottie/src/SkottieValue.h` - ScalarValue 等动画值类型
- `modules/sksg/include/SkSGColorFilter.h` - 场景图颜色滤镜节点
- `include/effects/SkRuntimeEffect.h` - 运行时着色器效果
- `modules/skottie/src/effects/LevelsEffect.cpp` - 另一个使用颜色滤镜的效果实现
