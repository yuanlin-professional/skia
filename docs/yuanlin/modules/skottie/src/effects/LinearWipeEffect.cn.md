# LinearWipeEffect - Skottie 线性擦除效果

> 源文件: `modules/skottie/src/effects/LinearWipeEffect.cpp`

## 概述

LinearWipeEffect 实现了 After Effects 中的"线性擦除"（Linear Wipe）效果。该效果通过线性渐变遮罩实现图层沿指定角度方向的擦除过渡动画，支持可调的边缘羽化效果。实现基于 `MaskShaderEffectBase` 基类，利用线性渐变着色器作为遮罩。

## 架构位置

该文件位于 Skottie 效果子系统中（`skottie::internal` 命名空间）。`LinearWipeAdapter` 继承自 `MaskShaderEffectBase`，该基类专门为基于着色器遮罩的效果设计，提供了遮罩着色器到渲染管线的集成。

```
AnimationBuilder
  └── EffectBuilder::attachLinearWipeEffect()
        └── LinearWipeAdapter (MaskShaderEffectBase)
              └── 线性渐变遮罩着色器
```

## 主要类与结构体

### `LinearWipeAdapter`
- 继承自 `MaskShaderEffectBase`（基于着色器的遮罩效果基类）
- 三个动画属性：
  - `fCompletion`：完成度（0-100）
  - `fAngle`：擦除方向角度
  - `fFeather`：边缘羽化量
- 通过工厂方法 `Make()` 创建

### 属性索引枚举
- `kCompletion_Index = 0`
- `kAngle_Index = 1`
- `kFeather_Index = 2`

### `MaskInfo` 返回结构
```cpp
struct MaskInfo {
    sk_sp<SkShader> shader;  // 遮罩着色器
    bool visible;            // 图层是否可见
};
```

## 公共 API 函数

### `EffectBuilder::attachLinearWipeEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachLinearWipeEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- **功能**：将线性擦除效果附加到目标图层

## 内部实现细节

### onMakeMask 方法

这是核心方法，返回遮罩着色器信息：

1. **完全遮罩**（Completion >= 100）：返回全透明着色器，图层不可见
2. **无遮罩**（Completion <= 0）：返回 null 着色器，图层完全可见
3. **部分遮罩**：构建线性渐变着色器

### 渐变构建算法

核心几何计算：

1. **角度转换**：`angle = SkDegreesToRadians(90 - fAngle)`，将 AE 角度约定转换为标准三角函数角度
2. **方向向量**：`angle_v = {cos_, sin_}` 为擦除方向的单位向量
3. **对角线向量**：`diag_v = {copysign(width, cos_), copysign(height, sin_)}`，根据象限选择正确的对角线
4. **过渡长度**：`len = DotProduct(diag_v, angle_v)`，将对角线投影到方向向量上
5. **羽化扩展**：`grad_len = len + feather * 2`，在两端各添加一个羽化斜坡

### 渐变端点计算

```cpp
const SkPoint pts[] = {
    center_v - adjusted_grad_v * 0.5f,
    center_v + adjusted_grad_v * 0.5f,
};
```
渐变从图层中心沿方向向量两侧等距延伸。注意 Y 轴翻转：`adjusted_grad_v = {grad_v.fX, -grad_v.fY}`。

### 羽化效果

通过调整颜色停止点的间距实现：
```cpp
const auto adjusted_t = t * (len + feather) / grad_len;
const SkScalar pos[] = { adjusted_t, adjusted_t + feather / grad_len };
```
- `t = 0` 时：斜坡完全在过渡域之前
- `t = 1` 时：斜坡完全在过渡域之后
- 停止点间距 = `feather / grad_len`：控制过渡的平滑度

### 渐变颜色

```cpp
static constexpr SkColor4f colors[] = { SkColors::kTransparent, SkColors::kWhite };
```
从透明过渡到白色，白色区域表示图层可见。

## 依赖关系

- **Skia 核心**：`SkColor`、`SkPoint`、`SkShader`、`SkScalar`、`SkSize`
- **Skia 渐变**：`SkGradient`（`SkShaders::LinearGradient`）
- **Skia 工具**：`SkTPin`（值域钳制）
- **Skottie 内部**：`SkottiePriv.h`、`SkottieValue.h`（`ScalarValue`）、`Effects.h`

## 设计模式与设计决策

1. **模板方法模式**：`MaskShaderEffectBase` 定义了遮罩效果的框架（属性绑定、着色器应用），`LinearWipeAdapter` 仅需实现 `onMakeMask()` 方法。

2. **三状态返回**：`MaskInfo` 通过着色器指针和可见性标志组合，优雅地表达"完全遮罩/部分遮罩/无遮罩"三种状态。

3. **几何投影算法**：通过对角线到方向向量的投影计算过渡长度，确保擦除在任何角度下都能覆盖整个图层。

4. **Y 轴翻转**：将数学坐标系中的 Y 方向转换为绘图坐标系（Y 轴向下），这是 Skia 2D 渲染中的常见处理。

## 性能考量

- 完成度为 0 或 100 时的快速退出避免了不必要的渐变着色器创建
- 线性渐变着色器是 GPU 中最高效的着色器类型之一
- 颜色数组声明为 `static constexpr`，避免运行时分配
- 着色器仅在属性变化时重建

## 补充说明

### 对角线投影算法详解

线性擦除需要确定从图层一侧到另一侧的过渡距离。该距离取决于擦除角度和图层尺寸：

1. 对于给定角度，选择正确的对角线向量：`copysign` 确保对角线方向与角度方向一致
2. 将对角线投影到角度方向上：`DotProduct(diag_v, angle_v)` 得到有效过渡长度
3. 这确保了无论角度如何，擦除过渡总能覆盖整个图层

例如：角度为 0 度时，过渡长度等于图层宽度；角度为 90 度时，等于图层高度；角度为 45 度时，等于对角线长度的一部分。

### 羽化斜坡机制

```
[0  <feather_ramp> [                           ] <feather_ramp> |grad_len|]
```

渐变总长度 = 实际过渡长度 + 2 * 羽化量。颜色停止点的间距等于 `feather / grad_len`，当 feather 为 0 时停止点重合形成硬边。

### 与 RadialWipeEffect 的对比

| 特性 | LinearWipe | RadialWipe |
|------|------------|------------|
| 基类 | MaskShaderEffectBase | CustomRenderNode |
| 遮罩类型 | 线性渐变 | 扫描渐变 |
| 方向控制 | 角度（连续） | 顺/逆/双向（离散） |
| 羽化实现 | 渐变停止点间距 | 模糊滤镜（禁用） |

## 相关文件

- `modules/skottie/src/effects/RadialWipeEffect.cpp` - 径向擦除效果（类似的遮罩机制）
- `modules/skottie/src/effects/Effects.h` - MaskShaderEffectBase 基类定义
- `include/effects/SkGradient.h` - 线性渐变 API
- `modules/skottie/src/SkottieValue.h` - ScalarValue 类型
