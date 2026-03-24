# WangsFormula - Wang 公式曲线细分计算

> 源文件: `src/gpu/tessellate/WangsFormula.h`

## 概述

WangsFormula.h 实现了 Wang 公式（Wang's Formula）在 Skia GPU 曲线细分（tessellation）系统中的应用。Wang 公式是计算贝塞尔曲线最少均匀参数线段数的经典算法，确保所有线段与真实曲线的距离不超过 `1/precision` 像素。

该文件提供了针对二次贝塞尔（quadratic）、三次贝塞尔（cubic）和圆锥曲线（conic）的特化实现，支持仿射变换下的计算，并包含多种优化变体（原始值、4 次幂值、log2 值）。所有函数都标记为 `SK_ALWAYS_INLINE` 以确保在热路径中零开销。

## 架构位置

```
Skia GPU 曲线细分系统
  -> PatchWriter (补丁写入器)
    -> WangsFormula (计算所需线段数)
      -> VectorXform (仿射变换)
    -> 决定是否需要 chop 曲线
```

WangsFormula 是曲线细分系统的数学核心，被 PatchWriter 用于判断每条曲线需要多少线段才能精确渲染。

## 主要类与结构体

### `VectorXform`
- **职责**: 表示仿射变换的上 2x2 矩阵部分，仅用于变换向量（差分）
- **内部表示**: 两列向量 `fC0` 和 `fC1`
- **构造**: 从 `SkMatrix` 或 `SkM44` 构造（断言无透视）
- **操作**: `operator()` 接受 `float2` 或 `float4` 向量并返回变换后的结果

## 公共 API 函数

### 辅助数学函数
| 函数 | 说明 |
|------|------|
| `length_term<Degree>(precision)` | 计算 Wang 公式中的长度系数 `n*(n-1)/8 * precision` |
| `length_term_p2<Degree>(precision)` | 长度系数的平方（用于避免开方） |
| `root4(x)` | 计算四次根 `sqrt(sqrt(x))` |
| `nextlog2(x)` | 向上取整的 log2，对 x<=1 返回 0 |
| `nextlog4(x)` | 向上取整的 log4（`(nextlog2(x)+1)>>1`） |
| `nextlog16(x)` | 向上取整的 log16（`(nextlog2(x)+3)>>2`） |

### 二次贝塞尔（Quadratic）
| 函数 | 说明 |
|------|------|
| `quadratic_p4(precision, p0, p1, p2, xform)` | Wang 公式 4 次幂（float2 版本） |
| `quadratic_p4(precision, pts[], xform)` | Wang 公式 4 次幂（SkPoint 数组版本） |
| `quadratic(precision, pts[], xform)` | Wang 公式原始值 |
| `quadratic_log2(precision, pts[], xform)` | Wang 公式的 log2 向上取整 |

### 三次贝塞尔（Cubic）
| 函数 | 说明 |
|------|------|
| `cubic_p4(precision, p0, p1, p2, p3, xform)` | Wang 公式 4 次幂 |
| `cubic(precision, pts[], xform)` | Wang 公式原始值 |
| `cubic_log2(precision, pts[], xform)` | Wang 公式的 log2 向上取整 |
| `worst_case_cubic_p4(precision, devW, devH)` | 给定包围盒尺寸的最坏情况 4 次幂 |
| `worst_case_cubic(precision, devW, devH)` | 最坏情况原始值 |
| `worst_case_cubic_log2(precision, devW, devH)` | 最坏情况 log2 |

### 圆锥曲线（Conic）
| 函数 | 说明 |
|------|------|
| `conic_p2(precision, p0, p1, p2, w, xform)` | 圆锥曲线公式的平方 |
| `conic(tolerance, pts[], w, xform)` | 圆锥曲线公式原始值 |
| `conic_log2(tolerance, pts[], w, xform)` | 圆锥曲线公式的 log2 |

## 内部实现细节

### Wang 公式的数学推导
对于 n 阶贝塞尔曲线，Wang 公式为：
```
numSegments = sqrt(maxLength * precision * n*(n-1)/8)
```
其中 `maxLength = max(|p[i+2] - 2*p[i+1] + p[i]|)` 是二阶差分的最大长度。

### p4 变体的优化
直接计算 `numSegments` 需要开四次根。`_p4` 变体返回 `numSegments^4`，可以延迟开方操作到最终需要实际段数时。这允许使用更廉价的整数运算（`nextlog16`）替代浮点开方。

### nextlog2 的位操作实现
```cpp
int nextlog2(float x) {
    uint32_t bits = SkFloat2Bits(x);
    bits += (1u << kDigitsAfterBinaryPoint) - 1u;  // 向上进位
    const int exp = ((bits >> kDigitsAfterBinaryPoint) & 0xFF) - 127;
    return exp > 0 ? exp : 0;
}
```
通过直接操作 IEEE 754 浮点数的位表示来计算 log2 的向上取整，避免了 `log2f` 和 `ceilf` 的开销。还正确处理了 NaN（返回 0）和正无穷（返回 128）。

### 圆锥曲线的特殊处理
圆锥曲线的公式不是 Wang 原始论文的内容，而是基于 Zheng 和 Sederberg 2000 年论文的类似分析。它通过将控制点平移到包围盒中心来提高平移不变性（见论文第 3.3 节），并处理了权重 `w` 的影响。

### VectorXform 的向量化操作
`VectorXform::operator()(float4)` 同时变换两个向量（存储为 float4 的前后两半），利用 SIMD 并行性一次处理两个二阶差分向量。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/base/SkVx.h` | SIMD 向量类型和操作 |
| `src/base/SkFloatBits.h` | SkFloat2Bits 浮点位操作 |
| `src/base/SkUtils.h` | sk_bit_cast |
| `include/core/SkMatrix.h` | SkMatrix 变换矩阵 |
| `include/core/SkM44.h` | SkM44 4x4 矩阵 |
| `include/core/SkPoint.h` | SkPoint 点类型 |

## 设计模式与设计决策

1. **模板化精度参数**: `length_term<Degree>` 使用模板参数指定曲线阶数，编译时计算常量系数。

2. **延迟开方策略**: 提供 `_p4` 和 `_p2` 变体返回高次幂值，允许调用者在整数域进行比较和 log 计算，避免昂贵的开方运算。

3. **变换分离**: `VectorXform` 仅处理 2x2 线性部分，因为 Wang 公式只涉及向量差分（平移不影响结果）。这比传递完整 4x4 矩阵更高效。

4. **位操作 log2**: `nextlog2` 通过直接操作浮点位表示实现，比标准库的 log2/ceil 组合快得多，且在热路径中使用。

## 性能考量

1. **SIMD 加速**: 二阶差分计算使用 `skvx::float2` 和 `skvx::float4`，单条 SIMD 指令完成两个分量的运算。
2. **无分支计算**: 大多数函数不包含条件分支，对 CPU 流水线友好。
3. **全内联**: 所有函数标记 `SK_ALWAYS_INLINE`，确保无函数调用开销。
4. **nextlog16 替代 root4**: `nextlog16(x) == ceil(log2(sqrt(sqrt(x))))` 仅使用整数移位操作完成，远快于两次 `sqrtf` 调用。
5. **最坏情况预估**: `worst_case_cubic_*` 函数允许在不知道具体控制点的情况下，仅根据包围盒尺寸估算上界，用于预分配缓冲区。

## 相关文件

- `src/gpu/tessellate/PatchWriter.h` - 使用 Wang 公式决定曲线切分
- `src/gpu/tessellate/Tessellation.h` - 细分常量和参数
- `src/gpu/tessellate/LinearTolerances.h` - 线性容差管理
- `src/gpu/tessellate/StrokeIterator.h` - 笔画迭代器
