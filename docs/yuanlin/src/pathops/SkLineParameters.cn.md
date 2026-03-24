# SkLineParameters - 路径操作中的直线参数化

> 源文件:
> - `src/pathops/SkLineParameters.h`

## 概述

`SkLineParameters` 类将线段转换为参数化直线表示形式 `ax + by + c = 0`，并提供计算点到直线距离的方法。它是 Skia 路径操作（pathops）子系统中的核心几何工具，用于贝塞尔裁剪（Bezier clipping）算法，支持三次曲线、二次曲线和直线的距离计算。

该实现参考了论文 "Computer-Aided Design, Volume 22, Number 9, November 1990, pp 538-549"（贝塞尔裁剪方法）。

## 架构位置

```
src/pathops/
  SkLineParameters.h       // 本文件
  SkPathOpsCubic.h          // 三次贝塞尔曲线
  SkPathOpsQuad.h           // 二次贝塞尔曲线
  SkPathOpsLine.h           // 直线
  SkIntersections.h         // 交点计算
```

## 主要类与结构体

### `SkLineParameters`

将线段参数化为 `ax + by + c = 0` 形式的直线。

**成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fA` | `double` | 直线方程系数 a（= pts[s].fY - pts[e].fY） |
| `fB` | `double` | 直线方程系数 b（= pts[e].fX - pts[s].fX） |
| `fC` | `double` | 直线方程系数 c（= pts[s].fX * pts[e].fY - pts[e].fX * pts[s].fY） |

当 `a^2 + b^2 == 1` 时直线已归一化，此时距离计算直接给出欧几里得距离。

## 公共 API 函数

### 三次曲线相关

```cpp
bool cubicEndPoints(const SkDCubic& pts);
```
从三次曲线的端点构建直线。处理退化情况（切线在 x 轴上、控制点近重合），尝试使用 pts[0]-pts[1]，失败则 pts[0]-pts[2]，最后 pts[0]-pts[3]。

```cpp
void cubicEndPoints(const SkDCubic& pts, int s, int e);
```
从三次曲线的指定两个点构建直线。

```cpp
double cubicPart(const SkDCubic& part);
```
计算三次曲线部分的特征距离。

```cpp
void cubicDistanceY(const SkDCubic& pts, SkDCubic& distance) const;
```
计算三次曲线每个控制点到直线的距离，结果存储为新的三次曲线（X 坐标为参数化位置 0, 1/3, 2/3, 1；Y 坐标为距离值）。

### 二次曲线相关

```cpp
bool quadEndPoints(const SkDQuad& pts);
void quadEndPoints(const SkDQuad& pts, int s, int e);
double quadPart(const SkDQuad& part);
void quadDistanceY(const SkDQuad& pts, SkDQuad& distance) const;
```
与三次曲线版本类似，但针对二次曲线。

### 直线相关

```cpp
void lineEndPoints(const SkDLine& pts);
```
从直线的两个端点构建参数化直线。

### 距离与归一化

```cpp
double normalSquared() const;   // 返回 a^2 + b^2
bool normalize();               // 归一化使 a^2 + b^2 == 1
double controlPtDistance(const SkDCubic& pts, int index) const;  // 控制点距离
double controlPtDistance(const SkDQuad& pts) const;              // 二次控制点距离
double pointDistance(const SkDPoint& pt) const;                  // 任意点距离
```

### 方向访问

```cpp
double dx() const { return fB; }    // 直线的 x 方向分量
double dy() const { return -fA; }   // 直线的 y 方向分量
```

## 内部实现细节

### 退化处理

`cubicEndPoints(const SkDCubic& pts)` 中的退化处理逻辑：

1. 尝试 pts[0] 到 pts[1] 建立直线
2. 若 dy==0 且 dx==0（两点重合），尝试 pts[0] 到 pts[2]
3. 若仍退化，使用 pts[0] 到 pts[3]
4. 特殊处理：当切线在 x 轴上（dy==0, dx>0），检查下一个控制点打破顺/逆时针平局
5. 使用 `DBL_EPSILON` 微调 fA 值以避免精确零值

### 非归一化距离

注意：`cubicDistanceY`、`quadDistanceY`、`controlPtDistance`、`pointDistance` 返回的距离值未必是归一化的。要获得真实距离，需要：
- 在调用端点方法后调用 `normalize()`，或
- 将距离除以 `sqrt(normalSquared())`

## 依赖关系

- `SkPathOpsCubic.h` - 三次贝塞尔曲线（`SkDCubic`）
- `SkPathOpsQuad.h` - 二次贝塞尔曲线（`SkDQuad`）
- `SkPathOpsLine.h` - 直线（`SkDLine`）
- `SkPathOpsTypes.h` - 近似比较函数（`approximately_zero`、`NotAlmostEqualUlps`）

## 设计模式与设计决策

1. **隐式表示**：使用 `ax + by + c = 0` 隐式方程表示直线，便于快速距离计算
2. **延迟归一化**：不强制归一化，允许调用者根据需要选择归一化或比较非归一化距离
3. **退化容错**：多级回退策略处理曲线退化为点或线的情况
4. **精度微调**：使用 `DBL_EPSILON` 避免精确零值导致的排序问题

## 性能考量

1. **内联实现**：所有方法都在头文件中内联，减少函数调用开销
2. **双精度运算**：使用 `double` 而非 `float` 以保证路径操作的数值精度
3. **避免不必要的归一化**：距离比较通常不需要归一化，避免额外的平方根运算

## 相关文件

- `src/pathops/SkPathOpsCubic.h` - 三次曲线定义
- `src/pathops/SkPathOpsQuad.h` - 二次曲线定义
- `src/pathops/SkPathOpsLine.h` - 直线定义
- `src/pathops/SkPathOpsTypes.h` - 近似比较函数
