# SkPathOpsRect - 双精度边界矩形

> 源文件：[src/pathops/SkPathOpsRect.h](../../../../src/pathops/SkPathOpsRect.h)、[src/pathops/SkPathOpsRect.cpp](../../../../src/pathops/SkPathOpsRect.cpp)

## 概述

`SkDRect` 是 Skia 路径操作模块中使用的双精度浮点矩形，用于表示曲线的精确边界框。与单精度的 `SkRect` 不同，`SkDRect` 使用 `double` 类型存储边界值，以满足路径操作中对数值精度的高要求。它提供了针对不同曲线类型（二次、圆锥、三次）的精确边界框计算，通过求解导数为零的极值点来确保边界框的紧密性。

## 架构位置

```
PathOps 几何基础层
  ├── SkDPoint / SkDVector (双精度点和向量)
  ├── SkDRect (双精度矩形) ← 本文件
  └── SkPathOpsBounds (单精度边界框，继承 SkRect)

使用者
  ├── SkDCurve (曲线边界计算)
  ├── SkPathOpsTSect (T-区间细分的边界检测)
  └── SkOpSegment (段的边界框)
```

`SkDRect` 位于 PathOps 几何基础层，被曲线类型和上层算法广泛用于边界框检测和快速排除测试。

## 主要类与结构体

### `SkDRect`
双精度矩形。

**成员变量：**
- `fLeft`：左边界（最小 X）。
- `fTop`：上边界（最小 Y）。
- `fRight`：右边界（最大 X）。
- `fBottom`：下边界（最大 Y）。

## 公共 API 函数

### 基本操作
- `set(const SkDPoint& pt)`：将矩形设置为单个点（宽高为零）。
- `add(const SkDPoint& pt)`：扩展矩形以包含给定点。
- `contains(const SkDPoint& pt)`：使用近似比较判断点是否在矩形内。
- `intersects(const SkDRect& r)`：判断两个矩形是否相交。
- `valid()`：检查矩形是否有效（左 <= 右，上 <= 下）。
- `width()` / `height()`：返回矩形的宽度和高度。

### 曲线边界框计算
- `setBounds(const SkDQuad&)`：计算二次曲线的紧密边界框。
- `setBounds(const SkDQuad&, const SkDQuad&, double tStart, double tEnd)`：计算二次曲线子段的边界框。
- `setBounds(const SkDConic&)` / `setBounds(const SkDConic&, ..., tStart, tEnd)`：圆锥曲线边界框。
- `setBounds(const SkDCubic&)` / `setBounds(const SkDCubic&, ..., tStart, tEnd)`：三次曲线边界框。
- `setBounds(const SkTCurve&)`：多态曲线的边界框（委托给曲线自身）。

### 调试
- `debugInit()`：将所有边界设为 `SK_ScalarNaN`，用于检测未初始化。

## 内部实现细节

### 精确边界框算法
`setBounds` 方法使用以下策略计算紧密边界框：
1. 用端点初始化矩形：`set(sub[0])` + `add(sub[endIndex])`。
2. 检查单调性：如果子曲线在 X 方向不单调，求 X 分量的极值参数。
3. 同样检查 Y 方向的单调性。
4. 对每个极值参数，计算原始曲线（非子曲线）上的对应点并扩展矩形。

关键细节：极值参数 `tValues[index]` 是子曲线的局部参数，需要通过 `t = startT + (endT - startT) * tValues[index]` 映射回原始曲线的全局参数后再求值。这确保了使用原始曲线的精确坐标。

### 近似包含判断
`contains()` 使用 `approximately_between()` 而非精确比较，允许一定的浮点容差，避免边界情况的错误排除。

### 多态支持
`setBounds(const SkTCurve&)` 通过虚函数分发委托给具体曲线类型的实现，支持通用的曲线处理算法。

## 依赖关系

- **SkDPoint**：双精度点类型。
- **SkPathOpsTypes**：`approximately_between` 等精度比较函数。
- **SkDQuad / SkDConic / SkDCubic**：各种曲线类型，提供 `FindExtrema`、`monotonicInX/Y`、`ptAtT` 等方法。
- **SkTCurve**：多态曲线基类。

## 设计模式与设计决策

### 值类型
`SkDRect` 是一个简单的值类型结构体，无虚函数和堆分配。成员变量直接公开访问（public struct）。

### 双参数 setBounds
接受原始曲线和子曲线两个参数的 `setBounds` 重载中，子曲线用于单调性判断和端点，原始曲线用于极值点求值。这种设计利用原始曲线的精确系数，避免子分割引入的额外误差。

### 单参数便利方法
单参数 `setBounds` 方法传递同一曲线作为 curve 和 sub 参数，使用 0 到 1 的全范围，简化了完整曲线的边界框计算。

## 性能考量

- **单调性提前退出**：如果曲线在 X 或 Y 方向上已经单调，则跳过对应方向的极值查找。
- **最少的极值计算**：二次曲线最多 2 个极值（X 和 Y 各 1 个），三次曲线最多 4 个极值（各 2 个），计算量很小。
- **紧密边界框**：精确的极值点计算确保边界框尽可能紧密，提高后续相交测试的排除效率。

## 相关文件

- `src/pathops/SkPathOpsPoint.h`：`SkDPoint` 定义。
- `src/pathops/SkPathOpsTypes.h`：精度比较函数。
- `src/pathops/SkPathOpsQuad.h`：`SkDQuad::FindExtrema`。
- `src/pathops/SkPathOpsConic.h`：`SkDConic::FindExtrema`。
- `src/pathops/SkPathOpsCubic.h`：`SkDCubic::FindExtrema`。
- `src/pathops/SkPathOpsBounds.h`：单精度边界框。
