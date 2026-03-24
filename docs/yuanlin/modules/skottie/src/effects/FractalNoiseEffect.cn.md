# FractalNoiseEffect - Skottie 分形噪声效果

> 源文件: `modules/skottie/src/effects/FractalNoiseEffect.cpp`

## 概述

FractalNoiseEffect 实现了 After Effects 中的 ADBE Fractal Noise（分形噪声）效果。该效果通过多层噪声叠加（octaves）生成程序化噪声图案，支持多种噪声滤波方式（最近邻、线性、柔线性）和分形类型（基础、湍流基础、湍流平滑、湍流锐利）。整个效果通过 SkSL（Skia Shading Language）运行时着色器实现，参数丰富，支持演化（evolution）动画、子层级变换和循环控制。

## 架构位置

FractalNoiseEffect 位于 Skottie 效果子系统中，使用自定义渲染节点和运行时着色器实现。

```
EffectBuilder::attachFractalNoiseEffect()
  |
  +-> FractalNoiseNode (自定义渲染节点)
  |     +-> CustomRenderNode
  |     +-> buildEffectShader() [构建 SkSL 着色器]
  |     +-> onRender() [SaveLayer + SrcIn 混合]
  |
  +-> FractalNoiseAdapter (属性适配器)
        +-> DiscardableAdapterBase
        +-> EffectBinder [绑定 30+ 参数]
        +-> onSync() [参数 -> 节点属性映射]
```

## 主要类与结构体

### FractalNoiseNode
- 继承自 `sksg::CustomRenderNode`
- 管理分形噪声的运行时着色器
- SG 属性（通过宏 `SG_ATTRIBUTE`）：
  - `Matrix` / `SubMatrix` - 主变换和子层变换矩阵
  - `NoiseFilter` / `NoiseFractal` - 噪声滤波和分形类型
  - `NoisePlanes` / `NoiseWeight` - 噪声平面和插值权重（演化控制）
  - `Octaves` / `Persistence` - 八度数和持久性
- `buildEffectShader()` 根据当前参数构建 SkRuntimeShaderBuilder
- `onRender()` 使用 SaveLayer + SrcIn 混合模式将噪声应用到子内容

### FractalNoiseAdapter
- 继承自 `DiscardableAdapterBase<FractalNoiseAdapter, FractalNoiseNode>`
- 通过 `EffectBinder` 绑定 AE 效果的全部参数（索引 0-30）
- 私有方法：
  - `noise()` - 计算噪声平面和插值权重
  - `shaderMatrix()` - 构建着色器主变换矩阵
  - `subMatrix()` - 构建子层变换矩阵
  - `noiseFilter()` / `noiseFractal()` - 枚举映射

### NoiseFilter（枚举）
- `kNearest` - 最近邻采样
- `kLinear` - 双线性插值
- `kSoftLinear` - smoothstep 插值

### NoiseFractal（枚举）
- `kBasic` - 直接噪声
- `kTurbulentBasic` - `2*abs(0.5 - n)`
- `kTurbulentSmooth` - `(2*abs(0.5 - n))^2`
- `kTurbulentSharp` - `sqrt(2*abs(0.5 - n))`

## 公共 API 函数

### `EffectBuilder::attachFractalNoiseEffect`
```cpp
sk_sp<sksg::RenderNode> attachFractalNoiseEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `FractalNoiseNode` 包装子图层
- 创建 `FractalNoiseAdapter` 绑定动画参数
- 返回配置好的渲染节点

## 内部实现细节

### SkSL 着色器架构
着色器代码 `gNoiseEffectSkSL` 使用 `%s` 占位符和 `%u` 格式化参数，在编译时根据滤波/分形类型组合注入不同的函数实现。

**Uniform 参数：**
- `u_submatrix` - 3x3 子层变换矩阵
- `u_noise_planes` - 两个噪声平面索引（float2）
- `u_noise_weight` - 平面间插值权重
- `u_octaves` - 八度数（可为小数）
- `u_persistence` - 相对振幅权重

**核心算法：**
1. `hash(float3 v)` - 基于 hash13 的哈希函数
2. `sample_noise(float2 xy)` - 在离散 (x,y,e) 空间采样并在两个噪声平面间插值
3. `filter(float2 xy)` - 可选的插值滤波（最近邻/双线性/smoothstep）
4. `fractal(float n)` - 分形变换函数
5. 主循环：累加 `ceil(u_octaves)` 层噪声，每层应用 `u_submatrix` 变换和 `u_persistence` 衰减

**小数八度处理：**
最后一层的权重为 `amp * min(oct, 1.0)`，其中 `oct` 是剩余的八度计数。小数部分自然调制最后一层的振幅。

### 着色器缓存
```cpp
static SkRuntimeEffect* kEffectCache[bins][filters][fractals];
```
- 三维缓存数组按循环次数分档（bin）、滤波类型和分形类型索引
- 分档策略：{1, 2, 3, 4, 8, 20} 循环次数，低复杂度使用更细的分档
- 缓存使用裸指针 + `sk_ref_sp` 避免析构时清理（全局静态缓存）

### 演化（Evolution）计算
```cpp
std::tuple<SkV2, float> noise() const;
```
- `evolution` 输入（度）转换为弧度并缩放（`kEvolutionScale = 0.25f`）
- 循环演化：调整缩放因子使周期为整数（`SkScalarRoundToScalar`），确保平滑循环
- `random_seed` 通过 `SkRandom` 转换为噪声平面偏移
- 返回两个噪声平面索引和插值权重

### 变换矩阵构建
**shaderMatrix：**
```
Translate(offset) * Scale(scale * 0.01) * RotateDeg(rotation) * Scale(gridSize=64)
```
- 缩放范围限制在 [1%, 10000%]
- 统一缩放模式使用 `fScale`，非统一模式使用 `fScaleWidth`/`fScaleHeight`

**subMatrix：**
```
Translate(-subOffset * 0.01) * RotateDeg(-subRotation) * Scale(100/subScale)
```
- 子层缩放范围限制在 [10%, 10000%]

### 渲染流程
1. `onRevalidate` 中重建着色器
2. `onRender` 中：
   - `ScopedRenderContext` 设置隔离
   - `saveLayer` 绘制子内容
   - 使用 `SkBlendMode::kSrcIn` 混合模式将噪声着色器覆盖子内容
   - 仅在子内容不透明区域显示噪声

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkRuntimeEffect.h` | SkSL 运行时着色器 |
| `SkCanvas.h` / `SkPaint.h` | 渲染和混合模式 |
| `SkMatrix.h` / `SkM44.h` | 变换矩阵 |
| `SkRandom.h` | 随机种子处理 |
| `Adapter.h` | DiscardableAdapterBase 基类 |
| `Effects.h` | EffectBinder 属性绑定 |
| `SkSGRenderNode.h` / `SkSGNode.h` | CustomRenderNode 基类 |
| `SkottieValue.h` | ScalarValue / Vec2Value |

## 设计模式与设计决策

- **模板化 SkSL 编译**：使用 C 格式化字符串在编译时组合滤波和分形函数，避免运行时条件分支。
- **分档缓存**：将连续的八度值离散化为 6 个档位，在着色器变体数量（6 x 3 x 4 = 72）和精度之间取得平衡。
- **SrcIn 混合**：通过 SaveLayer + SrcIn 将噪声限制在子内容的不透明区域内，实现遮罩效果。
- **双平面插值**：演化参数映射到两个离散噪声平面之间的插值，实现平滑的噪声过渡动画。
- **子层累积变换**：每个八度层通过 `u_submatrix` 累积变换，实现 AE 中的子层缩放/旋转/偏移效果。

## 性能考量

- SkSL 着色器在 GPU 上执行，利用并行计算处理每像素噪声生成。
- 着色器缓存避免重复编译（全局静态数组，程序生命周期内有效）。
- 循环次数通过分档固定为编译时常量，GPU 编译器可展开循环优化。
- 哈希函数使用简单的算术运算（fract/dot/floor），避免纹理查找。
- 双线性插值（4 次采样）和 smoothstep 相比三次样条（16 次采样）有显著性能优势。
- `onRevalidate` 仅在参数变化时重建着色器，通过 Scene Graph 失效机制控制。
- TODO 注释表明对比度、亮度和反转功能尚未实现。

### 滤波方式详解

三种滤波方式在视觉质量和性能之间提供了不同的权衡：

1. **最近邻（Nearest）**：直接取最近格点的噪声值，产生块状像素化效果。仅 1 次采样，最快。

2. **线性（Linear）**：对 4 个相邻格点进行双线性插值（`fract(xy)` 作为插值系数），产生平滑但仍有可见网格感的结果。4 次采样。

3. **柔线性（Soft Linear）**：与线性相同的 4 点采样，但使用 `smoothstep(0, 1, fract(xy))` 代替线性插值系数。smoothstep 在边界处导数为零，消除了网格感，产生更自然的结果。4 次采样 + smoothstep 运算。

### 分形类型详解

四种分形类型通过对基础噪声值的后处理产生不同的视觉特征：

1. **Basic**：`f(n) = n`，直接使用噪声值，产生平滑的梯度变化。
2. **Turbulent Basic**：`f(n) = 2*abs(0.5 - n)`，将噪声映射为 V 形，产生类似湍流的纹理。
3. **Turbulent Smooth**：`f(n) = (2*abs(0.5 - n))^2`，V 形的平方，湍流效果更柔和。
4. **Turbulent Sharp**：`f(n) = sqrt(2*abs(0.5 - n))`，V 形的平方根，湍流效果更尖锐。

所有湍流变体都将中间值（0.5 附近）映射为零，高值和低值映射为非零，产生边缘/脊线特征。

### 循环演化的数学原理

循环演化（Cycle Evolution）确保演化动画可以无缝循环：

1. 演化值转换为弧度：`evo_rad = degrees * PI/180`
2. 周期确定：`rev_rad = max(cycleRevolutions, 1) * 2*PI`
3. 缩放调整：为确保缩放后的周期为整数（`SkScalarRoundToScalar`），调整缩放因子 `scale = cycle / rev_rad`
4. 最终演化值经过 `floor` 取整得到噪声平面索引，小数部分作为插值权重

由于噪声平面索引通过 `glsl_mod` 取模，当演化值回绕时，噪声平面也会回绕，实现无缝循环。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder 和效果注册
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `modules/sksg/include/SkSGRenderNode.h` - CustomRenderNode 基类
- `include/effects/SkRuntimeEffect.h` - SkSL 运行时效果
- `modules/skottie/src/effects/BulgeEffect.cpp` - 类似的 SkSL 着色器效果
