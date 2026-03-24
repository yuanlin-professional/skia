# SkRadialGradient - 径向渐变着色器

> 源文件: `src/shaders/gradients/SkRadialGradient.h`, `src/shaders/gradients/SkRadialGradient.cpp`

## 概述

SkRadialGradient 实现了从中心点向外辐射的圆形径向渐变效果。颜色从中心沿径向方向均匀过渡。这是最常见的渐变类型之一，常用于模拟光照、阴影或聚焦效果。

## 架构位置

```
SkShaderBase
  └── SkGradientBaseShader (渐变基类)
        └── SkRadialGradient (径向渐变)
```

- **公共 API**: `SkShaders::RadialGradient()`
- **管线阶段**: `xy_to_radius` 将坐标转换为距中心的距离

## 主要类与结构体

### SkRadialGradient
继承自 `SkGradientBaseShader`。

**成员变量**:
- `fCenter` (SkPoint): 渐变中心点
- `fRadius` (SkScalar): 渐变半径

## 公共 API 函数

```cpp
sk_sp<SkShader> SkShaders::RadialGradient(
    SkPoint center, float radius,
    const SkGradient& grad, const SkMatrix* lm);
```

**参数验证**: 半径为负时返回 nullptr。半径接近零时使用退化渐变。

### 查询方法
- `center()` — 渐变中心
- `radius()` — 渐变半径
- `asGradient()` — 返回 `GradientType::kRadial` 及渐变信息

## 内部实现细节

### ptsToUnit 矩阵
通过 `rad_to_unit_matrix` 计算：将中心平移到原点，然后缩放使半径归一化到 1.0。

### appendGradientStages
径向渐变仅需一个阶段：`xy_to_radius`，计算 `sqrt(x*x + y*y)` 得到归一化的 t 值。

### 序列化
在基类数据之后写入 center 和 radius。

## 依赖关系

- `SkGradientBaseShader` — 渐变基类
- `SkRasterPipeline` — 光栅化管线

## 设计模式与设计决策

1. **矩阵预变换**: 将中心平移和半径缩放编码到 ptsToUnit 矩阵中，运行时无需额外计算
2. **退化处理委托**: 半径接近零时委托给 `MakeDegenerateGradient` 统一处理

## 性能考量

- `xy_to_radius` 涉及一次 `sqrt` 运算，是径向渐变的主要开销
- 矩阵变换已在管线设置时完成，不影响像素级性能

### ptsToUnit 矩阵详细计算

`rad_to_unit_matrix` 的计算步骤：
```
inv = 1.0 / radius
matrix.setTranslate(-center.fX, -center.fY)  // 平移中心到原点
matrix.postScale(inv, inv)                     // 缩放使半径归一化为 1.0
```

变换后，单位圆 (x^2 + y^2 = 1) 对应原始空间中的渐变边界圆。

### appendGradientStages 说明

径向渐变的 `appendGradientStages` 实现极为简单：仅追加一个 `xy_to_radius` 操作。该操作在管线中计算 `t = sqrt(x*x + y*y)`，其中 (x,y) 已经通过 ptsToUnit 矩阵变换到归一化空间。

不需要 postPipeline 阶段。

### 退化处理

当 radius 接近零（小于 kDegenerateThreshold = 1/2^15）时：
- 渐变区域退化为一个点
- 委托给 `SkGradientBaseShader::MakeDegenerateGradient`
- 该函数根据平铺模式返回：Decal 模式返回空着色器，Repeat/Mirror 返回平均色，Clamp 返回最后一个颜色

与锥形渐变不同，径向渐变的退化处理不需要特殊的 Clamp 逻辑。

### 序列化格式

径向渐变的序列化数据包括：
1. 基类数据（通过 SkGradientBaseShader::flatten）：颜色、位置、平铺模式、插值参数、色彩空间
2. center 点坐标
3. radius 值

### GradientInfo 填充

`asGradient` 方法填充 GradientInfo 时：
- `info->fPoint[0]` = center（中心点）
- `info->fRadius[0]` = radius（半径）
- localMatrix = Identity
- 返回 GradientType::kRadial

### 工厂方法 GRADIENT_FACTORY_EARLY_EXIT

`SkShaders::RadialGradient` 使用 GRADIENT_FACTORY_EARLY_EXIT 宏进行通用的早期退出检查：
1. 验证渐变参数合法性（颜色、平铺模式、插值设置）
2. 单色渐变直接返回纯色着色器
3. localMatrix 不可逆时返回 nullptr

### Flattenable 注册

`SkRegisterRadialGradientShaderFlattenable()` 注册 SkRadialGradient 的序列化支持，在 Skia 初始化时调用。

## 相关文件

- `src/shaders/gradients/SkGradientBaseShader.h` — 渐变基类
- `include/effects/SkGradient.h` — 渐变公共 API
- `src/core/SkRasterPipelineOpList.h` — xy_to_radius 操作
- `src/shaders/gradients/SkConicalGradient.h` — 锥形渐变（同心圆退化为径向类型）
- `src/shaders/gradients/SkLinearGradient.h` — 线性渐变
- `src/shaders/gradients/SkSweepGradient.h` — 扫描渐变
