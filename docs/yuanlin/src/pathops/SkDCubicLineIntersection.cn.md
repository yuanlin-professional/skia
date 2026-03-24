# SkDCubicLineIntersection - 三次贝塞尔曲线与直线的交点计算

> 源文件:
> - `src/pathops/SkDCubicLineIntersection.cpp`

## 概述

本文件实现了三次贝塞尔曲线（cubic Bezier）与直线的交点计算。它是 Skia 路径操作子系统中的核心几何算法之一，支持一般直线、水平线和垂直线与三次曲线的交叉检测。

算法通过将问题转化为求解三次多项式的根来找到交点的参数值（t 值），然后验证这些参数值的有效性和唯一性。

## 架构位置

```
src/pathops/
  SkIntersections.h            // 交点结果容器
  SkDCubicLineIntersection.cpp // 本文件 (cubic-line)
  SkDConicLineIntersection.cpp // conic-line
  SkDQuadLineIntersection.cpp  // quad-line
  SkPathOpsCubic.h             // 三次曲线定义
  SkPathOpsLine.h              // 直线定义
```

## 主要类与结构体

### `LineCubicIntersections`

计算三次曲线和直线交点的工作类。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fCubic` | `const SkDCubic&` | 三次曲线引用 |
| `fLine` | `const SkDLine&` | 直线引用 |
| `fIntersections` | `SkIntersections*` | 交点结果 |
| `fAllowNear` | `bool` | 是否允许近似端点匹配 |

### `PinTPoint` 枚举

```cpp
enum PinTPoint {
    kPointUninitialized,
    kPointInitialized
};
```
标记点是否已由先前计算初始化。

## 公共 API 函数

通过 `SkIntersections` 的成员函数访问：

```cpp
int SkIntersections::intersect(const SkDCubic& cubic, const SkDLine& line);
int SkIntersections::intersectRay(const SkDCubic& cubic, const SkDLine& line);
int SkIntersections::horizontal(const SkDCubic& cubic, double left, double right, double y, bool flipped);
int SkIntersections::vertical(const SkDCubic& cubic, double top, double bottom, double x, bool flipped);
```

以及 `SkDCubic` 的辅助方法：

```cpp
int SkDCubic::horizontalIntersect(double yIntercept, double roots[3]) const;
int SkDCubic::verticalIntersect(double xIntercept, double roots[3]) const;
```

## 内部实现细节

### 数学推导

文件开头包含详细的 Mathematica 推导过程。核心思想是将三次曲线参数方程与直线方程联立消元，得到关于 t 的三次多项式：

**近水平情况 (y = i*x + j)：**
```
A = (-(-e + 3*f - 3*g + h) + i*(-a + 3*b - 3*c + d))
B = 3*(-( e - 2*f +   g  ) + i*( a - 2*b +   c  ))
C = 3*(-(-e +   f        ) + i*(-a +   b        ))
D = (-( e              ) + i*( a              ) + j)
```

**近垂直情况 (x = i*y + j)：** 类似公式但交换了 x/y 坐标。

### `intersectRay()` - 射线交点

```cpp
int intersectRay(double roots[3]);
```

1. 计算直线的方向向量 (adj, opp)
2. 将曲线控制点投影到垂直于直线的方向上
3. 使用 `SkDCubic::Coefficients()` 提取多项式系数
4. 使用 `SkDCubic::RootsValidT()` 求解有效根
5. 若结果不够精确，通过极值搜索 (`searchRoots`) 改进

### `intersect()` - 完整交点计算

```cpp
int intersect();
```

1. 添加精确端点（`addExactEndPoints`）
2. 若允许，添加近似端点（`addNearEndPoints`）
3. 使用 `intersectRay()` 计算射线交点
4. 对每个根，找到对应的直线参数 `lineT`
5. 通过 `pinTs()` 验证和钳位参数值
6. 通过 `uniqueAnswer()` 确保唯一性
7. 检查重合（`checkCoincident`）

### 端点处理

- **精确端点**：`addExactEndPoints()` 检查曲线端点（t=0, t=1）是否恰好在直线上
- **近似端点**：`addNearEndPoints()` 检查曲线端点是否"接近"直线
- **直线端点**：`addLineNearEndPoints()` 检查直线端点是否接近曲线

### `pinTs()` - 参数值验证

1. 检查 `lineT` 是否在 [-epsilon, 1+epsilon] 范围内
2. 钳位 `cubicT` 和 `lineT` 到 [0, 1]
3. 验证对应点是否粗略相等（`roughlyEqual`）
4. 将点捕捉到网格端点

### `uniqueAnswer()` - 唯一性检查

检查新交点是否与已有交点重复。若两个交点的参数中点处的曲线上的点也近似等于交点位置，则认为是同一个交点。

### `checkCoincident()` - 重合检测

检查相邻交点之间是否存在重合（曲线和直线在该区间内完全重叠）。

## 依赖关系

- `SkIntersections` - 交点结果容器
- `SkPathOpsCubic` - 三次曲线（`ptAtT`、`Coefficients`、`RootsValidT`、`FindExtrema`、`searchRoots`）
- `SkPathOpsLine` - 直线（`nearPoint`、`exactPoint`、`ExactPointH`、`NearPointH` 等）
- `SkPathOpsCurve` - 曲线通用接口
- `SkPathOpsTypes` - 近似比较函数

## 设计模式与设计决策

1. **精确到近似的渐进策略**：先检查精确端点，再检查近似端点，最后求解多项式
2. **双精度算术**：所有计算使用 double 以保持数值精度
3. **结果验证**：多层验证确保交点的有效性（pinTs、uniqueAnswer、checkCoincident）
4. **极值回退**：当初始根不够精确时，通过曲线极值细化搜索

## 性能考量

1. **最大交点数**：三次曲线与直线最多 3 个交点，内存预分配为 4（含重合）
2. **端点优先**：先处理端点交点，避免多项式求解对端点的精度问题
3. **水平/垂直特化**：水平线和垂直线有专门的简化实现路径

## 相关文件

- `src/pathops/SkIntersections.h` - 交点结果容器
- `src/pathops/SkPathOpsCubic.h` - 三次曲线
- `src/pathops/SkPathOpsLine.h` - 直线
- `src/pathops/SkDConicLineIntersection.cpp` - 圆锥曲线与直线交点
- `src/pathops/SkDQuadLineIntersection.cpp` - 二次曲线与直线交点
