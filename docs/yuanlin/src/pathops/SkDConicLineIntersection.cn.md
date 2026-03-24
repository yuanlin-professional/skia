# SkDConicLineIntersection - 圆锥曲线与直线的交点计算

> 源文件:
> - `src/pathops/SkDConicLineIntersection.cpp`

## 概述

本文件实现了圆锥曲线（conic，即有理二次贝塞尔曲线）与直线的交点计算。圆锥曲线由三个控制点和一个权重值（weight）定义，可以精确表示圆弧、椭圆弧、抛物线和双曲线。该算法支持一般直线、水平线和垂直线与圆锥曲线的交叉检测。

与三次曲线-直线交点不同，圆锥曲线-直线交点的求解归结为求解二次方程（最多 2 个根），但权重值的参与使方程系数更复杂。

## 架构位置

```
src/pathops/
  SkIntersections.h                // 交点结果容器
  SkDConicLineIntersection.cpp      // 本文件 (conic-line)
  SkDCubicLineIntersection.cpp      // cubic-line
  SkDQuadLineIntersection.cpp       // quad-line
  SkPathOpsConic.h                  // 圆锥曲线定义
```

## 主要类与结构体

### `LineConicIntersections`

计算圆锥曲线和直线交点的工作类。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fConic` | `const SkDConic&` | 圆锥曲线引用 |
| `fLine` | `const SkDLine*` | 直线指针 |
| `fIntersections` | `SkIntersections*` | 交点结果 |
| `fAllowNear` | `bool` | 是否允许近似端点匹配 |

提供两个构造函数：
1. 完整构造：接受曲线、直线和交点容器（最大 4 个交点）
2. 仅曲线构造：用于独立的水平/垂直截距计算

## 公共 API 函数

通过 `SkIntersections` 的成员函数访问：

```cpp
int SkIntersections::intersect(const SkDConic& conic, const SkDLine& line);
int SkIntersections::intersectRay(const SkDConic& conic, const SkDLine& line);
int SkIntersections::horizontal(const SkDConic& conic, double left, double right, double y, bool flipped);
int SkIntersections::vertical(const SkDConic& conic, double top, double bottom, double x, bool flipped);
int SkIntersections::HorizontalIntercept(const SkDConic& conic, SkScalar y, double* roots);
int SkIntersections::VerticalIntercept(const SkDConic& conic, SkScalar x, double* roots);
```

## 内部实现细节

### `validT()` - 核心求解

```cpp
int validT(double r[3], double axisIntercept, double roots[2]);
```

将交点问题转化为二次方程求解：

```
A = r[2] + r[0] - 2 * B_adjusted
B_adjusted = r[1] * weight - axisIntercept * weight + axisIntercept
C = r[0] - axisIntercept
```

使用 `SkDQuad::RootsValidT()` 求解 `At^2 + 2Bt + C = 0` 中 [0,1] 范围内的根。权重 `fConic.fWeight` 参与 B 系数的计算，这是与普通二次曲线的关键区别。

### `intersectRay()` - 射线交点

将曲线控制点投影到垂直于直线的方向上得到 `r[0..2]`，然后调用 `validT()` 求解。

### `horizontalIntersect()` / `verticalIntersect()` - 轴对齐交点

分别使用 Y 坐标或 X 坐标数组调用 `validT()`，简化了一般性的射线投影。

### 端点处理

与 cubic-line 交点类似的端点处理策略：
- `addExactEndPoints()` - 精确端点匹配
- `addNearEndPoints()` - 近似端点匹配
- `addLineNearEndPoints()` - 直线端点近似匹配
- 水平/垂直变体

### `pinTs()` - 参数值验证

与 cubic 版本类似但有额外逻辑：
- 使用 `approximately_one_or_less_double` / `approximately_zero_or_more_double`（双精度版本）
- 额外检查：若已有一个交点且新交点的 lineT 与其近似相等则拒绝

### `checkCoincident()` - 重合检测

检查相邻交点之间曲线段是否与直线重合。

## 依赖关系

- `SkIntersections` - 交点结果容器
- `SkPathOpsConic` - 圆锥曲线（`SkDConic`、`ptAtT`、`kPointCount`、`kPointLast`）
- `SkPathOpsQuad` - 二次曲线求根（`SkDQuad::RootsValidT`）
- `SkPathOpsLine` - 直线工具方法
- `SkPathOpsCurve` - 曲线通用接口（`nearPoint`）

## 设计模式与设计决策

1. **二次归约**：圆锥曲线-直线交点归结为二次方程，最多 2 个根
2. **权重处理**：`validT()` 中权重 `w` 参与 B 系数计算，正确处理有理参数化
3. **与 cubic 对称设计**：端点处理、pinTs、uniqueAnswer 等结构与 cubic-line 对称
4. **最大交点数 4**：设为 4（2 个离散交点 + 可能的短部分重合）
5. **仅曲线构造函数**：允许独立计算水平/垂直截距，无需直线和交点容器

## 性能考量

1. **二次方程求解**：比三次方程更高效（2 vs 3 个根）
2. **端点优先**：先处理端点避免求解器精度问题
3. **轴对齐特化**：水平/垂直线有简化路径，避免向量投影

### 有理贝塞尔方程

圆锥曲线（有理二次贝塞尔）的参数方程为：

```
P(t) = [w*P1*(1-t)^2 + 2*w*P1*t*(1-t) + P2*t^2] / [w*(1-t)^2 + 2*w*t*(1-t) + t^2]
```

其中 `w` 为权重值。当 `w=1` 时退化为标准二次贝塞尔。

### validT 方程推导

将有理二次曲线与直线方程联立，消去空间坐标后得到关于 t 的二次方程：

```
原始：r[i] = 曲线控制点投影到直线法线方向的值
A = r[2] + r[0] - 2*(r[1]*w - xCept*w + xCept)
B = r[1]*w - xCept*w + xCept - r[0]
C = r[0] - xCept

方程：A*t^2 + 2*B*t + C = 0
```

### close_to 调试验证

仅在 `SK_DEBUG` 模式下编译的 `close_to()` 函数验证交点精度：

```cpp
static bool close_to(double a, double b, const double c[3]) {
    double max = std::max(-std::min(c[0], c[1], c[2]), std::max(c[0], c[1], c[2]));
    return approximately_zero_when_compared_to(a - b, max);
}
```

通过将差值与控制点值的量级比较来判断精度是否足够。

### 与 cubic-line 交点的对比

| 特性 | Conic-Line | Cubic-Line |
|------|-----------|-----------|
| 最大交点数 | 2 | 3 |
| 方程次数 | 二次 | 三次 |
| 控制点数 | 3 | 4 |
| 权重参数 | 有 (fWeight) | 无 |
| 端点索引 | kPointCount/kPointLast | 硬编码 0, 3 |
| 直线存储 | 指针 (const SkDLine*) | 引用 (const SkDLine&) |

### pinTs 中的额外检查

与 cubic 版本不同，conic 的 `pinTs()` 包含一个额外的重复检测：

```cpp
if (fIntersections->used() > 0 && approximately_equal((*fIntersections)[1][0], *lineT)) {
    return false;
}
```

这防止在端点附近产生几乎重叠的交点。

## 相关文件

- `src/pathops/SkIntersections.h` - 交点结果容器
- `src/pathops/SkPathOpsConic.h` - 圆锥曲线定义
- `src/pathops/SkPathOpsQuad.h` - 二次方程求根
- `src/pathops/SkDCubicLineIntersection.cpp` - 三次曲线与直线交点（对比参考）
- `src/pathops/SkPathOpsTypes.h` - 近似比较工具
