# Segment.cpp - 线段运算核心实现

> 源文件: `modules/bentleyottmann/src/Segment.cpp`

## 概述

`Segment.cpp` 是 Bentley-Ottmann 模块中最核心的实现文件，提供了线段的基本操作、交点计算、扫描线位置比较以及斜率比较等关键算法。该文件中的数学推导和实现确保了所有几何计算在整数域内的正确性，是整个线段交点检测算法正确运行的数学基础。文件包含详尽的数学推导注释。

## 架构位置

- **头文件**：`modules/bentleyottmann/include/Segment.h`
- **被依赖**：`SweepLine.cpp`（使用 `less_than_at`、`point_less_than_segment_in_x`）、`EventQueue.cpp`（使用 `compare_slopes`）、`BruteForceCrossings.cpp`（使用 `intersect`）
- **依赖**：`Int96.h`（96 位精确整数运算）
- **核心地位**：所有线段相关的几何计算都在此文件中实现

## 主要类与结构体

无新类定义。实现 `Segment` 成员函数和多个自由函数。

## 公共 API 函数

### 基本操作
- **`Segment::upper()`**：返回 `std::min(p0, p1)`（Y 较小的端点）
- **`Segment::lower()`**：返回 `std::max(p0, p1)`（Y 较大的端点）
- **`Segment::bounds()`**：返回 `(left, top, right, bottom)` 包围盒
- **`operator==`**：比较归一化（upper/lower）后的端点
- **`operator<`**：先比较 upper 点，再比较 lower 点

### 包围盒快速排除
**`no_intersection_by_bounding_box(s0, s1)`**：如果两线段的包围盒不重叠则返回 true。使用严格不等号（`<=`），因为边界相触不算新的交叉。

### 交点计算
**`intersect(s0, s1)`**：使用参数化线段和叉积计算两条线段的交点。

### 扫描线比较
- **`less_than_at(s0, s1, y)`**：在水平线 y 处比较两线段的 x 截距
- **`point_less_than_segment_in_x(p, segment)`**：比较点 p 的 x 与线段在 p.y 处的 x 截距
- **`rounded_point_less_than_segment_in_x_lower(s, p)`** / **`..._upper(s, p)`**：带四舍五入的比较

### 斜率比较
**`compare_slopes(s0, s1)`**：返回 -1、0 或 1，表示两线段斜率的相对大小。

## 内部实现细节

### intersect 交点计算算法

采用参数化表示和叉积方法：

1. **向量定义**：
   - Q = P1 - P0（第一条线段方向）
   - R = P2 - P0（两线段起点的差向量）
   - T = P3 - P2（第二条线段方向）

2. **参数求解**：
   - t = (Q x R) / (T x Q)
   - s = (T x R) / (T x Q)

3. **有效性检查**（6 次乘法，零舍入误差）：
   - TxQ == 0：线段平行，无交点
   - 符号检查：`(QxR ^ TxQ) < 0` 表示 t < 0
   - 范围检查：t、s 都必须在 [0, 1] 范围内

4. **交点坐标计算**（使用双精度浮点，是临时方案）：
   ```cpp
   const double t = static_cast<double>(QxR) / static_cast<double>(TxQ);
   const int32_t x = std::round(t * (P3.x - P2.x) + P2.x);
   const int32_t y = std::round(t * (P3.y - P2.y) + P2.y);
   ```

叉积使用 64 位运算确保精确性。交叉检测（t 和 s 的范围判断）完全不涉及浮点运算。

### less_than_at 精确比较

比较 `s0(y) < s1(y)` 展开为：
```
[x0(y1-y0) + (y-y0)(x1-x0)] * (y3-y2) <? [x2(y3-y2) + (y-y2)(x3-x2)] * (y1-y0)
```

- 左侧：64 位中间结果 * 32 位 = 96 位
- 使用 `Int96` 类型进行精确比较
- 可以安全交叉乘（因为 y 差值始终为正）

### rounded_point_less_than_segment_in_x 实现

以 `_lower` 版本为例，实现 `s(y) < (x - 0.5)`：

1. 快速路径：包围盒判断
2. 水平线段特殊处理
3. 核心数学变换（消除除法和分数）：
   ```
   x0 + (x1-x0)(y-y0)/(y1-y0) < x - 1/2
   => 2(x1-x0)(y-y0) < (2(x-x0) - 1)(y1-y0)
   ```
   使用 64 位乘法确保精确。

### compare_slopes 斜率比较

使用交叉乘法避免除法：
```
slope(s0) = dx0/dy0, slope(s1) = dx1/dy1
dx0 * dy1 <? dx1 * dy0
```
dy 值始终为正（线段上端点 y < 下端点 y），可安全交叉乘。水平线段的斜率定义为最大值。

## 依赖关系

- `modules/bentleyottmann/include/Segment.h` - 头文件
- `include/private/base/SkAssert.h` - 断言
- `include/private/base/SkTo.h` - `SkToS64`（安全转换到 64 位）
- `modules/bentleyottmann/include/Int96.h` - 96 位整数运算
- `<algorithm>`, `<cmath>` - 标准库

## 设计模式与设计决策

### 整数算术优先
所有几何谓词（交叉检测、位置比较、斜率比较）均使用精确整数运算，只有最终交点坐标的计算使用浮点近似。这是计算几何中保证鲁棒性的经典策略。

### 多级精度
- 32 位输入
- 64 位中间结果（叉积、交叉乘法）
- 96 位最终比较（`less_than_at` 中 64 位 * 32 位）

### 快速路径优化
所有比较函数都先进行包围盒检查，O(1) 排除大部分不相交/不需要精确比较的情况。

### 详尽的数学推导注释
每个函数都包含从数学公式到代码实现的完整推导过程，这是确保实现正确性的文档化方法。

### no_intersection_by_bounding_box 的边界处理
使用 `<=` 而非 `<` 进行包围盒比较。这意味着包围盒仅在边界上相切时也被视为"不相交"。这是正确的，因为线段交点不包含端点（开区间假设），端点处的接触由事件队列单独处理。

### rounded 系列函数的数学推导
这两个函数实现了 `x < floor(s(y) + 0.5)` 的精确整数判断。通过将不等式拆分为上下两部分：
- lower: `(x - 0.5) <= s(y)` 即 `s(y) >= x - 0.5`
- upper: `s(y) < (x + 0.5)`

两次乘以 2 消除分数，得到纯整数比较。这些函数的签名设计为与 `std::lower_bound` 兼容，使得在有序线段序列中可以 O(log n) 查找特定 x 值对应的位置。

## 性能考量

- **包围盒预过滤**：`no_intersection_by_bounding_box` 和各比较函数中的包围盒检查在大多数情况下可以快速返回，通常仅需 4 次整数比较
- **避免除法**：通过交叉乘法将除法转换为乘法比较，同时保持精确性。除法在现代 CPU 上通常需要 20-40 个周期，而乘法仅需 3-5 个周期
- **96 位运算仅在必要时使用**：`less_than_at` 中的 `Int96` 乘法比 64 位运算慢，但只在包围盒检查无法确定时才执行
- **XOR 符号检查**：`(QxR ^ TxQ) < 0` 利用异或快速检测商的符号，避免额外的条件分支，仅需一条 XOR 指令和一次比较
- **TODO 标记**：交点坐标计算目前使用 `double` 是临时方案，计划未来改用精确大整数运算。`double` 提供约 15-16 位有效数字，对于 `int32_t` 范围的坐标通常足够
- **SkToS64 安全转换**：在关键乘法运算前将 `int32_t` 安全扩展为 `int64_t`，确保乘法不溢出

## 相关文件

- `modules/bentleyottmann/include/Segment.h` - 头文件
- `modules/bentleyottmann/include/Int96.h` - 96 位整数运算
- `modules/bentleyottmann/src/SweepLine.cpp` - 使用比较函数
- `modules/bentleyottmann/src/EventQueue.cpp` - 使用 `compare_slopes`
- `modules/bentleyottmann/src/BruteForceCrossings.cpp` - 使用 `intersect`
