# SkPathOpsPoint - 路径操作中的双精度点和向量

> 源文件:
> - `src/pathops/SkPathOpsPoint.h`

## 概述

`SkPathOpsPoint.h` 定义了路径操作子系统使用的双精度浮点数点（`SkDPoint`）和向量（`SkDVector`）类型。与 Skia 核心中使用单精度 `SkPoint` 不同，路径操作需要更高的数值精度来确保正确的几何计算，因此使用双精度表示。

这些类型提供了多种近似相等比较方法，针对不同精度需求提供 `approximately`、`roughly` 和 `wayRoughly` 等不同级别的容差比较。

## 架构位置

```
include/core/SkPoint.h          // 单精度点 (SkPoint)
  |
  v
src/pathops/SkPathOpsPoint.h     // 双精度点 (SkDPoint, SkDVector) - 本文件
  |
  v
所有 pathops 几何计算             // 使用双精度进行交点/距离等计算
```

## 主要类与结构体

### `SkDVector`

双精度二维向量。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fX` | `double` | X 分量 |
| `fY` | `double` | Y 分量 |

**运算方法：**

| 方法 | 说明 |
|------|------|
| `set(SkVector&)` | 从 SkVector 设值 |
| `operator+=/-=/*/\/=` | 算术运算（主要用于测试） |
| `asSkVector()` | 转换为 SkVector |
| `cross(SkDVector&)` | 叉积 |
| `crossCheck(SkDVector&)` | 使用 ULPs 容差的叉积（近零返回 0） |
| `crossNoNormalCheck(SkDVector&)` | 更宽松的叉积容差 |
| `dot(SkDVector&)` | 点积 |
| `length()` / `lengthSquared()` | 长度 / 平方长度 |
| `normalize()` | 归一化 |
| `isFinite()` | 是否有限 |

### `SkDPoint`

双精度二维点。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fX` | `double` | X 坐标 |
| `fY` | `double` | Y 坐标 |

**比较方法（精度递减）：**

| 方法 | 精度级别 | 说明 |
|------|---------|------|
| `operator==` | 精确 | 精确位比较 |
| `approximatelyDEqual()` | 高（Dequal ULPs） | 考虑数值量级的 ULPs 容差 |
| `approximatelyEqual()` | 中（Pequal ULPs） | 考虑数值量级的 ULPs 容差 |
| `roughlyEqual()` | 低（Rough ULPs） | 较宽松的 ULPs 容差 |
| `RoughlyEqual()` (静态) | 低 | SkPoint 版本 |
| `WayRoughlyEqual()` (静态) | 极低 | 仅用于不等检查 |

**其他方法：**

| 方法 | 说明 |
|------|------|
| `set(SkPoint&)` | 从 SkPoint 设值 |
| `operator-(SkDPoint)` | 点差运算返回 SkDVector |
| `asSkPoint()` | 转换为 SkPoint |
| `distance(SkDPoint&)` | 欧几里得距离 |
| `distanceSquared(SkDPoint&)` | 距离平方 |
| `Mid(SkDPoint&, SkDPoint&)` | 中点 |
| `approximatelyZero()` | 近似零点（仅测试用） |
| `dump()` | 调试输出 |

## 公共 API 函数

### 全局函数

```cpp
inline bool AlmostEqualUlps(const SkPoint& pt1, const SkPoint& pt2);
```
使用 ULPs 容差比较两个 SkPoint 是否近似相等。

## 内部实现细节

### 近似相等比较算法

所有近似比较方法遵循相同的模式：

1. **快速路径**：先用 `approximately_equal` 检查各分量
2. **粗筛**：若 `RoughlyEqualUlps` 失败则立即返回 false
3. **距离比较**：计算两点间距离
4. **相对比较**：计算坐标的最大绝对值 `largest`
5. **ULPs 判断**：检查 `largest` 和 `largest + dist` 在 ULPs 意义下是否相等

```cpp
// approximatelyDEqual 示例
double dist = distance(a);
double tiniest = min(min(min(fX, a.fX), fY), a.fY);
double largest = max(max(max(fX, a.fX), fY), a.fY);
largest = max(largest, -tiniest);
return AlmostDequalUlps(largest, largest + dist);
```

这种方法考虑了数值量级，大数值允许较大的绝对误差。

### `crossCheck()` vs `cross()`

`cross()` 是精确叉积，仅用于测试。`crossCheck()` 使用 16 ULPs 容差，当叉积结果近似为零时返回 0，用于路径操作中的排序和分类。`crossNoNormalCheck()` 使用更宽松的容差（NoNormalCheck 版本）。

### `WayRoughlyEqual()`

最宽松的比较，用于快速不等检查：
```cpp
float largestNumber = max(|a.fX|, |a.fY|, |b.fX|, |b.fY|);
float largestDiff = max(|diffs.fX|, |diffs.fY|);
return roughly_zero_when_compared_to(largestDiff, largestNumber);
```

## 依赖关系

- `include/core/SkPoint.h` - SkPoint, SkVector
- `include/core/SkTypes.h` - SkDoubleToScalar, SkIsFinite
- `include/private/base/SkTemplates.h` - SkTAbs
- `src/pathops/SkPathOpsTypes.h` - AlmostEqualUlps, RoughlyEqualUlps, approximately_equal 等

## 设计模式与设计决策

1. **双精度精度**：路径操作使用 double 而非 float 以减少数值误差累积
2. **多级容差**：提供从精确到极粗糙的多种比较方法，适应不同使用场景
3. **相对容差**：近似比较基于数值量级而非绝对值，确保大坐标值仍能正确比较
4. **测试标注**：部分运算符（+=、-=、*=、/=）标注为 "only used by testing"
5. **POD 类型**：SkDPoint 和 SkDVector 是纯 POD 结构体，无虚函数

## 性能考量

1. **内联函数**：所有方法在头文件中定义，编译器可内联优化
2. **距离平方优先**：注释标注可优化为使用 `distanceSquared` 代替 `distance`
3. **快速路径**：近似比较先进行廉价的分量级检查，大多数情况可早返回
4. **`sk_ieee_double_divide`**：`normalize()` 使用 IEEE 除法避免 NaN 问题

## 相关文件

- `src/pathops/SkPathOpsTypes.h` - 近似比较工具函数
- `src/pathops/SkPathOpsCubic.h` - 使用 SkDPoint 的三次曲线
- `src/pathops/SkPathOpsQuad.h` - 使用 SkDPoint 的二次曲线
- `src/pathops/SkPathOpsLine.h` - 使用 SkDPoint 的直线
- `include/core/SkPoint.h` - 单精度点类型
