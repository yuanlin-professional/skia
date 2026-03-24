# SkConicalGradient - 锥形（两点锥形）渐变着色器

> 源文件: `src/shaders/gradients/SkConicalGradient.h`, `src/shaders/gradients/SkConicalGradient.cpp`

## 概述

SkConicalGradient 实现了两点锥形渐变（Two-Point Conical Gradient），也称为聚焦渐变。颜色在两个圆之间过渡，起始圆（center0, radius0）和结束圆（center1, radius1）定义了渐变的几何形状。这种渐变可以模拟聚光灯、光晕等复杂光照效果。

根据几何参数的不同，锥形渐变被分类为三种内部类型：Radial（同心圆）、Strip（等半径条带）和 Focal（一般焦点情况），每种类型使用不同的优化管线阶段。

## 架构位置

```
SkShaderBase
  └── SkGradientBaseShader (渐变基类)
        └── SkConicalGradient (锥形渐变)
```

- **公共 API**: `SkShaders::TwoPointConicalGradient()`
- **设计文档**: https://skia.org/dev/design/conical

## 主要类与结构体

### SkConicalGradient
**成员变量**:
- `fCenter1 / fCenter2` — 两个圆的中心
- `fRadius1 / fRadius2` — 两个圆的半径
- `fType` (Type) — 内部类型（kRadial / kStrip / kFocal）
- `fFocalData` (FocalData) — 焦点情况的额外参数

### FocalData
焦点类型的优化参数：
- `fR1` — 映射后的 r1 值
- `fFocalX` — 焦点 X 坐标 (f)
- `fIsSwapped` — 是否交换了 r0/r1

**焦点分类方法**:
- `isFocalOnCircle()` — 焦点位于结束圆上（线性退化）
- `isWellBehaved()` — 良好情况（非焦点在圆上且 r1>1）
- `isNativelyFocal()` — 天然焦点（f 接近 0）
- `isSwapped()` — r0/r1 是否被交换

### Type 枚举
- `kRadial` — 同心圆，中心重合
- `kStrip` — 等半径条带，r0 约等于 r1
- `kFocal` — 一般焦点情况

## 公共 API 函数

```cpp
sk_sp<SkShader> SkShaders::TwoPointConicalGradient(
    SkPoint start, float startRadius,
    SkPoint end, float endRadius,
    const SkGradient& grad, const SkMatrix* lm);
```

**退化情况处理**:
- 中心重合 + 半径相等: 使用退化渐变（Clamp+radius>0 时创建硬边渐变）
- 中心重合 + startRadius=0: 退化为普通径向渐变
- 单色渐变: 扩展为双色渐变

## 内部实现细节

### Create 工厂方法
根据几何参数确定类型和变换矩阵：
1. **同心圆**（中心距接近零）: 使用以较大半径归一化的缩放矩阵
2. **一般情况**: 使用 `MapToUnitX` 将两中心映射到 {(0,0), (1,0)}
3. 等半径时为 Strip 类型，否则为 Focal 类型
4. Focal 类型通过 `FocalData::set` 计算焦点参数并调整矩阵

### FocalData::set
将焦点映射到原点 (0,0) 的过程：
1. 计算 focalX = r0 / (r0 - r1)
2. 若 focalX 接近 1，则交换 r0/r1 并反转矩阵
3. 使用 PolyToPoly 将 {焦点, (1,0)} 映射到 {(0,0), (1,0)}
4. 根据焦点位置应用优化缩放

### appendGradientStages
根据类型选择不同的管线阶段：

**Radial 类型**: `xy_to_radius` + 仿射变换（缩放和偏移映射 t 到 [r1,r2]）

**Strip 类型**: `xy_to_2pt_conical_strip` + `mask_2pt_conical_nan`，后处理使用 `apply_vector_mask`

**Focal 类型**: 根据焦点特性选择以下之一：
- `xy_to_2pt_conical_focal_on_circle` — 焦点在圆上
- `xy_to_2pt_conical_well_behaved` — 良好情况
- `xy_to_2pt_conical_smaller` / `greater` — 其他情况

然后根据需要追加补偿阶段：
- `mask_2pt_conical_degenerates` — 退化掩码
- `negate_x` — X 取反
- `alter_2pt_conical_compensate_focal` — 焦点补偿
- `alter_2pt_conical_unswap` — 交换还原

### isOpaque
锥形渐变始终返回 false，因为锥体外的区域是未触及的（除非能证明锥体填满整个平面）。

## 依赖关系

- `SkGradientBaseShader` — 渐变基类
- `SkRasterPipeline` — 光栅化管线
- `SkMatrix::PolyToPoly` — 多点映射
- `SkArenaAlloc` — 管线上下文分配

## 设计模式与设计决策

1. **类型分类优化**: 将锥形渐变分为三种类型，每种使用最优化的管线阶段
2. **焦点预处理**: 在创建时完成复杂的几何变换，避免运行时开销
3. **交换技巧**: 当 focalX 接近 1 时交换 r0/r1 以避免数值不稳定
4. **保守不透明**: isOpaque 始终返回 false，因为判断锥体是否填满平面代价过高
5. **向后兼容**: 序列化时使用旧名称 "SkTwoPointConicalGradient" 进行注册

## 性能考量

- Radial 类型最快，仅需 sqrt + 仿射变换
- Strip 类型需要额外的 NaN 掩码处理
- Focal 类型最复杂，可能需要多达 5 个额外管线阶段
- Well-behaved focal 比其他 focal 子类型更快（无退化掩码处理）

## 相关文件

- `src/shaders/gradients/SkGradientBaseShader.h` — 渐变基类
- `include/effects/SkGradient.h` — 渐变公共 API
- `src/core/SkRasterPipelineOpContexts.h` — Conical2PtCtx 上下文
- https://skia.org/dev/design/conical — 设计文档

### 附录: Focal 管线阶段组合

根据焦点特性的不同组合，Focal 类型使用不同的管线阶段：

| 条件 | 坐标变换阶段 | 退化掩码 | 取反 | 焦点补偿 | 交换还原 |
|------|------------|---------|------|---------|---------|
| isFocalOnCircle | focal_on_circle | 否 | 否 | 否 | 否 |
| isWellBehaved | well_behaved | 否 | 否 | 可能 | 可能 |
| isSwapped 或 1-f<0 | smaller | 是 | 是 | 可能 | 可能 |
| 其他 | greater | 是 | 否 | 可能 | 可能 |

"可能" 表示取决于 isNativelyFocal 和 isSwapped 标志。

### 附录: 退化处理决策树

```
中心距 接近 0?
├── 是: 半径相等?
│   ├── 是: 退化渐变 (Clamp+r>0 时创建硬边渐变)
│   └── 否: startRadius 接近 0?
│       ├── 是: 退化为 RadialGradient
│       └── 否: 使用 Type::kRadial 的锥形渐变
└── 否: 正常锥形渐变
    └── 半径相等?
        ├── 是: Type::kStrip
        └── 否: Type::kFocal
```
