# SkDrawProcs

> 源文件
> - src/core/SkDrawProcs.h

## 概述

`SkDrawProcs` 是一个轻量级的工具函数集合，提供绘制过程中常用的辅助判断函数。核心功能是判断描边（stroke）是否应该被视为发线（hairline）绘制，这对于优化细线渲染和实现一致的视觉效果至关重要。该模块通过分析描边宽度和变换矩阵，决定是否使用抗锯齿发线路径替代标准描边，从而在性能和质量间取得平衡。

## 架构位置

该头文件位于 `src/core` 核心层，属于私有实现（不在公共API中）。它位于 `skcpu` 命名空间，专门服务于CPU光栅化器。该模块被 `SkDraw`、`SkScan` 等绘制模块调用，处于绘制决策层，负责在实际光栅化前确定渲染策略。

## 主要类与结构体

该文件不定义类或结构体，仅提供命名空间内的工具函数。

### 核心函数

```cpp
namespace skcpu {
bool DrawTreatAAStrokeAsHairline(SkScalar strokeWidth, const SkMatrix& matrix,
                                 SkScalar* coverage);

bool DrawTreatAsHairline(const SkPaint& paint, const SkMatrix& matrix,
                         SkScalar* coverage);
}
```

## 公共 API 函数

### DrawTreatAsHairline

```cpp
inline bool DrawTreatAsHairline(const SkPaint& paint,
                                const SkMatrix& matrix,
                                SkScalar* coverage)
```

判断描边是否应视为发线绘制。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `paint` | `const SkPaint&` | 绘制属性（样式、宽度、抗锯齿） |
| `matrix` | `const SkMatrix&` | 当前变换矩阵 |
| `coverage` | `SkScalar*` | 输出参数，返回覆盖率（部分覆盖系数） |

**返回值：**
- `true`：应视为发线，`coverage` 被设置为0到1之间的覆盖率
- `false`：应使用标准描边路径

**判断逻辑：**

1. **检查样式：** 如果不是描边样式（`kStroke_Style`），返回 `false`
2. **零宽度处理：** 如果描边宽度为0，设置 `coverage = 1.0`，返回 `true`（标准发线）
3. **抗锯齿检查：** 如果未启用抗锯齿，返回 `false`（不适合转换）
4. **委托判断：** 调用 `DrawTreatAAStrokeAsHairline` 执行复杂分析

### DrawTreatAAStrokeAsHairline

```cpp
bool DrawTreatAAStrokeAsHairline(SkScalar strokeWidth,
                                 const SkMatrix& matrix,
                                 SkScalar* coverage)
```

针对抗锯齿描边的细粒度判断（声明在此文件，实现在其他地方）。

**分析内容（基于实现推测）：**
- 计算变换后的描边宽度（考虑矩阵缩放）
- 如果变换后宽度 ≤ 1.0像素，返回 `true`
- 计算覆盖率（宽度越小，覆盖率越低，模拟部分覆盖）

**覆盖率计算公式（典型）：**
```
coverage = clamp(transformed_width, 0.0, 1.0)
```

## 内部实现细节

### 零宽度描边的语义

在Skia中，`strokeWidth = 0` 是特殊值，表示"总是绘制1像素宽的线，不受变换影响"。这是"几何发线"，始终恰好1像素宽。

### 抗锯齿发线优化

**标准描边路径：**
1. 将路径扩展为描边轮廓（offset curve）
2. 填充扩展后的路径
3. 开销大（路径复杂度增加、更多三角形）

**发线路径：**
1. 直接扫描原始路径
2. 使用抗锯齿算法柔化边缘
3. 开销小（路径不变、简单扫描线）

**何时适合转换：**
- 描边宽度接近1像素（视觉差异小）
- 启用抗锯齿（可以模拟部分覆盖）
- 变换矩阵缩放较小（不会显著放大宽度）

### 覆盖率的作用

覆盖率（coverage）用于模拟亚像素宽度的线：
- `coverage = 1.0`：完全覆盖，正常发线
- `coverage = 0.5`：半透明发线，模拟0.5像素宽
- `coverage < 某阈值`：线太细，可能不绘制

这使得细描边在不同缩放下保持视觉连续性。

### 矩阵分析

`DrawTreatAAStrokeAsHairline` 需要分析矩阵的缩放效果：

**均匀缩放：**
```cpp
SkScalar scale = matrix.getMinScale();
SkScalar transformedWidth = strokeWidth * scale;
```

**非均匀缩放：**
需要分别计算X和Y方向的缩放，取较小值（保守估计）。

**透视变换：**
透视情况下，缩放在空间中不同位置不同，通常不转换为发线（返回 `false`）。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPaint` | 获取描边样式、宽度、抗锯齿 |
| `SkMatrix` | 查询变换矩阵属性 |
| `SkScalar` | 标量类型 |
| `SkTypes` | 基础类型定义 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkDraw` | 在路径绘制前调用判断 |
| `SkScan` | 选择扫描算法（发线 vs 填充） |
| `SkStroke` | 决定是否执行路径扩展 |

## 设计模式与设计决策

**策略模式：** 根据条件选择不同的渲染策略（发线 vs 描边），封装决策逻辑。

**内联优化：** `DrawTreatAsHairline` 声明为 `inline`，常见的快速路径（非描边、零宽度）直接在调用点执行，避免函数调用开销。

**关注点分离：** 将"是否应该作为发线"的判断从实际绘制代码中分离，提高可测试性和可维护性。

**输出参数模式：** 使用输出参数 `coverage` 而非返回结构体，避免额外的拷贝。

**命名空间隔离：** 使用 `skcpu` 命名空间，明确表明这是CPU特定的逻辑（GPU后端有不同的处理）。

**提前返回：** 使用多级提前返回，快速处理常见情况（非描边、零宽度、无抗锯齿），减少不必要的计算。

## 性能考量

**快速路径优化：** 内联的前置检查（样式、零宽度、抗锯齿）覆盖了大多数情况，避免调用外部函数：
```cpp
if (SkPaint::kStroke_Style != paint.getStyle()) {
    return false;  // 最常见的情况，立即返回
}

if (0 == strokeWidth) {
    *coverage = SK_Scalar1;
    return true;  // 第二常见，立即返回
}
```

**矩阵分析开销：** `DrawTreatAAStrokeAsHairline` 需要分析矩阵，这涉及浮点计算。但相比完整的描边路径扩展，开销微不足道。

**缓存友好：** 函数不维护状态，可以高频调用而不影响缓存。

**分支预测：** 大多数应用中，同一绘制会话内的paint属性相对稳定，分支预测器可以有效工作。

**避免重复工作：** 调用者通常在路径处理前调用一次，结果指导整个路径的渲染，不会重复判断。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkDraw.cpp` | 主要调用者，绘制路径时判断策略 |
| `src/core/SkStroke.cpp` | 描边路径扩展实现 |
| `src/core/SkScan_Hairline.cpp` | 发线扫描算法 |
| `src/core/SkScan_Path.cpp` | 路径填充扫描算法 |
| `include/core/SkPaint.h` | Paint属性定义 |
| `include/core/SkMatrix.h` | 矩阵变换接口 |
