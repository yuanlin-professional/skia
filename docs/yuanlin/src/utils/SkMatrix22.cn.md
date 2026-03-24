# SkMatrix22 — Givens 旋转矩阵计算

> 源文件：[src/utils/SkMatrix22.h](../../src/utils/SkMatrix22.h)、[src/utils/SkMatrix22.cpp](../../src/utils/SkMatrix22.cpp)

## 概述

`SkMatrix22` 提供了一个单一函数 `SkComputeGivensRotation`，用于计算 Givens 旋转矩阵。Givens 旋转矩阵 G 是一个 2x2 正交旋转矩阵，将给定向量 h 旋转到正水平轴方向，即 `G * h = [hypot(h), 0]`。

该函数主要用于 Skia 的字体渲染系统，在字形变换中计算旋转分量。

## 架构位置

```
字体渲染 / 矩阵分解
    └── SkComputeGivensRotation() ← 本模块
            └── SkMatrix::setSinCos()
```

## 公共 API 函数

### `SkComputeGivensRotation(const SkVector& h, SkMatrix* G)`

计算向量 h 的 Givens 旋转矩阵 G，使得 `G * h` 的结果为 `[|h|, 0]`。

**数值稳定性**：使用部分 hypot 方法避免直接计算 `h.length()` 和除法，分四种情况处理：

1. **b == 0**：h 已在水平轴上，c = sign(a), s = 0
2. **a == 0**：h 在垂直轴上，c = 0, s = -sign(b)
3. **|b| > |a|**：使用 t = a/b 避免大数除以小数的精度损失
4. **|a| >= |b|**：使用 t = b/a 的标准路径

最终调用 `G->setSinCos(s, c)` 设置 2D 旋转矩阵。

## 内部实现细节

算法等价于：
```
r = h.length();
r_inv = r ? 1/r : 0;
h.scale(r_inv);
G->setSinCos(-h.fY, h.fX);
```

但通过分支处理避免了：
- 零除错误（当 h 长度为零时）
- 大数/小数除法的精度损失
- 显式计算 `r`（向量长度）的平方根和倒数

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkMatrix` | 输出矩阵类型 |
| `SkPoint` / `SkVector` | 输入向量类型 |
| `SkScalar` | 标量数学（`SkScalarCopySign`、`SkScalarSqrt`、`SkScalarAbs`） |

## 设计模式与设计决策

1. **数值稳定性优先**：四分支算法牺牲少量代码复杂度换取更好的浮点精度。
2. **单一职责**：整个模块只有一个函数，体现了最小化接口原则。
3. **注释掉的 r 计算**：代码中注释了 r 的计算公式，说明该算法有意跳过向量长度计算以提高效率。

## 性能考量

- 四种情况各只需 1 次除法、1 次平方根和少量乘法，避免了通用 `hypot()` 函数的开销。
- 无堆分配，纯栈操作。
- 分支预测友好：大多数实际使用中命中第 3 或第 4 种情况。

## 相关文件

- `include/core/SkMatrix.h` — 矩阵类（`setSinCos`）
- `include/core/SkPoint.h` — 向量/点类型
