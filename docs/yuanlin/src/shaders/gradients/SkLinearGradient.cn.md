# SkLinearGradient - 线性渐变着色器

> 源文件: `src/shaders/gradients/SkLinearGradient.h`, `src/shaders/gradients/SkLinearGradient.cpp`

## 概述

SkLinearGradient 实现了两点之间的线性渐变效果。颜色沿起点到终点的方向线性过渡，垂直方向上颜色相同。这是最简单也是最常用的渐变类型。

## 架构位置

```
SkShaderBase
  └── SkGradientBaseShader (渐变基类)
        └── SkLinearGradient (线性渐变)
```

- **公共 API**: `SkShaders::LinearGradient()`
- **管线阶段**: 无额外阶段（ptsToUnit 矩阵直接提供 t 值）

## 主要类与结构体

### SkLinearGradient
继承自 `SkGradientBaseShader`。

**成员变量**:
- `fStart` (SkPoint): 渐变起点
- `fEnd` (SkPoint): 渐变终点

## 公共 API 函数

```cpp
sk_sp<SkShader> SkShaders::LinearGradient(
    const SkPoint pts[2],
    const SkGradient& grad, const SkMatrix* lm);
```

**退化处理**: 起点和终点距离接近零时使用退化渐变（Clamp 模式返回末色）。

### 查询方法
- `start()` / `end()` — 起点和终点
- `asGradient()` — 返回 `GradientType::kLinear`

## 内部实现细节

### ptsToUnit 矩阵
通过 `pts_to_unit_matrix` 计算：
1. 计算起点到终点的方向向量并归一化
2. 使用 `setSinCos` 创建旋转矩阵使渐变方向对齐 X 轴
3. 平移使起点位于原点
4. 缩放使起点到终点的距离归一化为 1.0

### appendGradientStages
线性渐变是最简单的渐变：**不需要追加任何额外阶段**。ptsToUnit 矩阵已经将坐标变换为 t 值（X 分量即为 t），基类的管线阶段直接使用。

### 序列化
在基类数据之后写入 fStart 和 fEnd 两个点。

## 依赖关系

- `SkGradientBaseShader` — 渐变基类
- `SkMatrix` — 矩阵运算

## 设计模式与设计决策

1. **零阶段设计**: 线性渐变将所有几何变换编码到 ptsToUnit 矩阵中，不需要额外的管线阶段，这使其成为最高效的渐变类型
2. **退化检测**: 使用 kDegenerateThreshold (1/2^15) 作为阈值，比默认的 SkScalarNearlyZero 更严格

## 性能考量

- 线性渐变是所有渐变中最快的，因为没有额外的坐标变换阶段
- 所有计算都在矩阵变换中完成，属于管线的标准开销

### ptsToUnit 矩阵详细计算

`pts_to_unit_matrix` 的计算步骤：
```
vec = pts[1] - pts[0]                                  // 方向向量
mag = vec.length()                                      // 长度
inv = mag ? 1/mag : 0                                   // 反长度
vec.scale(inv)                                          // 归一化方向
matrix.setSinCos(-vec.fY, vec.fX, pts[0].fX, pts[0].fY) // 旋转对齐X轴
matrix.postTranslate(-pts[0].fX, -pts[0].fY)           // 平移起点到原点
matrix.postScale(inv, inv)                              // 缩放归一化
```

变换后，pts[0] 映射到 (0,0)，pts[1] 映射到 (1,0)。X 坐标就是渐变的 t 值。

### 退化处理

当两点距离小于 kDegenerateThreshold 时：
- 渐变方向未定义
- 委托给 `MakeDegenerateGradient`
- Clamp 模式下始终使用最后一个颜色（因为垂直分界线位置未定义）

### appendGradientStages 说明

线性渐变的 `appendGradientStages` 方法体为空。这是因为 ptsToUnit 矩阵已经将空间坐标变换为 t 值——变换后 X 坐标就是 t，不需要任何额外的数学运算。这使得线性渐变成为所有渐变类型中开销最低的。

### 序列化格式

线性渐变的序列化数据包括：
1. 基类数据（SkGradientBaseShader::flatten 输出）
2. fStart 点坐标
3. fEnd 点坐标

### GradientInfo 填充

`asGradient` 方法设置：
- `info->fPoint[0]` = fStart
- `info->fPoint[1]` = fEnd
- localMatrix = Identity
- 返回 GradientType::kLinear

### 与其他渐变的管线阶段对比

| 渐变类型 | 额外管线阶段 | 复杂度 |
|---------|------------|--------|
| Linear | 无 | O(1) |
| Radial | xy_to_radius (1次sqrt) | O(1) |
| Sweep | xy_to_unit_angle (1次atan2) | O(1) |
| Conical | 多个阶段（类型相关） | O(1) 但常数较大 |

### Flattenable 注册

`SkRegisterLinearGradientShaderFlattenable()` 注册 SkLinearGradient 的序列化支持。

### GRADIENT_FACTORY_EARLY_EXIT 宏

在 `SkShaders::LinearGradient` 中使用此宏进行通用验证：
1. ValidGradient 检查颜色数组和参数合法性
2. 单色渐变返回纯色着色器
3. localMatrix 不可逆时返回 nullptr

## 相关文件

- `src/shaders/gradients/SkGradientBaseShader.h` — 渐变基类
- `include/effects/SkGradient.h` — 渐变公共 API
- `src/shaders/gradients/SkRadialGradient.h` — 径向渐变
- `src/shaders/gradients/SkSweepGradient.h` — 扫描渐变
- `src/shaders/gradients/SkConicalGradient.h` — 锥形渐变
