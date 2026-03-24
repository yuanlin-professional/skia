# SkSweepGradient - 扫描渐变着色器

> 源文件: `src/shaders/gradients/SkSweepGradient.h`, `src/shaders/gradients/SkSweepGradient.cpp`

## 概述

SkSweepGradient 实现了围绕中心点的扫描（锥形）渐变效果。颜色沿角度方向变化，类似于雷达扫描或色相环。支持指定起始角度和结束角度，允许渐变仅覆盖部分旋转范围，并通过平铺模式处理范围外的区域。

## 架构位置

```
SkShaderBase
  └── SkGradientBaseShader (渐变基类)
        └── SkSweepGradient (扫描渐变)
```

- **公共 API**: `SkShaders::SweepGradient()`
- **兄弟类**: SkLinearGradient、SkRadialGradient、SkConicalGradient
- **管线阶段**: `xy_to_unit_angle` 将坐标转换为角度值

## 主要类与结构体

### SkSweepGradient
继承自 `SkGradientBaseShader`。

**关键成员变量**:
- `fCenter` (SkPoint): 扫描中心点
- `fTBias` (SkScalar): 角度偏移量，等于 -t0
- `fTScale` (SkScalar): 角度缩放量，等于 1/(t1-t0)

其中 t0 = startAngle/360，t1 = endAngle/360。

## 公共 API 函数

```cpp
sk_sp<SkShader> SkShaders::SweepGradient(
    SkPoint center, float startAngle, float endAngle,
    const SkGradient& grad, const SkMatrix* lm);
```

**退化情况处理**:
- 起始角度等于结束角度时：Clamp 模式下若角度>0，生成首色+末色硬边渐变；其他模式使用默认退化行为
- t 范围覆盖 [0,1] 时自动使用 Clamp 模式以获得更好性能

## 内部实现细节

### 构造函数
将中心点平移矩阵传递给基类作为 ptsToUnit 矩阵：`SkMatrix::Translate(-center.x(), -center.y())`。

### appendGradientStages
扫描渐变仅需两个管线阶段：
1. `xy_to_unit_angle` — 将笛卡尔坐标转换为 [0,1) 范围的角度值
2. 角度仿射变换 — 通过 `Scale(fTScale, 1) * Translate(fTBias, 0)` 映射到目标 t 范围

### 序列化
序列化基类数据后，额外写入 center、tBias、tScale。反序列化时通过 `angles_from_t_coeff` 从 tBias/tScale 还原起始和结束角度。

## 依赖关系

- `SkGradientBaseShader` — 渐变基类（提供颜色插值、平铺、色彩空间转换）
- `SkRasterPipeline` — 光栅化管线
- `SkGradientScope` — 渐变序列化辅助类

## 设计模式与设计决策

1. **角度到 t 的预计算**: 将 startAngle/endAngle 转换为 tBias/tScale，避免运行时除法
2. **自动 Clamp 优化**: 当 t 范围覆盖完整圆时切换到 clamp 模式

## 性能考量

- `xy_to_unit_angle` 使用 atan2 近似实现，是扫描渐变的主要计算开销
- 通过矩阵乘法实现角度范围映射，开销极低

### 角度参数转换

外部 API 使用角度（0-360），内部使用 t 值（0-1）：
- `t0 = startAngle / 360`
- `t1 = endAngle / 360`
- `tBias = -t0`
- `tScale = 1 / (t1 - t0)`

反向转换（反序列化时使用）：
- `startAngle = -tBias * 360`
- `endAngle = (1/tScale - tBias) * 360`

### 退化渐变的特殊处理

当 startAngle 接近 endAngle（差值小于 kDegenerateThreshold）时：
1. **Clamp 模式且角度 > 0**: 创建特殊的三色渐变
   - [0, 1, 1] 位置上的颜色为 [首色, 首色, 末色]
   - 效果是从 0 到 endAngle 为首色，然后硬切换到末色
2. **其他模式**: 使用 MakeDegenerateGradient 默认处理

### 平铺模式优化

当 startAngle <= 0 且 endAngle >= 360 时，t 范围覆盖完整 [0,1]，无论原始模式是什么，都可以安全切换为 Clamp 模式。Clamp 模式通常更快，因为不需要 mirror/repeat 的额外计算。

### GradientInfo 填充

`asGradient` 方法填充 GradientInfo 时：
- `info->fPoint[0]` = 中心点
- `info->fPoint[1].fX` = tScale
- `info->fPoint[1].fY` = tBias
- localMatrix 设为单位矩阵

### SkGradientScope 的使用

反序列化时使用 SkGradientScope 作为临时存储，它在栈上预分配空间存放颜色和位置数组（最多 16 个元素的 STArray），减少小渐变的堆分配。

### 注册

`SkRegisterSweepGradientShaderFlattenable()` 通过 SK_REGISTER_FLATTENABLE 宏注册序列化支持，在 Skia 初始化时调用。

## 相关文件

- `src/shaders/gradients/SkGradientBaseShader.h` — 渐变基类
- `include/effects/SkGradient.h` — 渐变公共 API
- `src/core/SkRasterPipelineOpList.h` — xy_to_unit_angle 操作定义
- `src/shaders/gradients/SkLinearGradient.h` — 兄弟类：线性渐变
- `src/shaders/gradients/SkRadialGradient.h` — 兄弟类：径向渐变
- `src/shaders/gradients/SkConicalGradient.h` — 兄弟类：锥形渐变
