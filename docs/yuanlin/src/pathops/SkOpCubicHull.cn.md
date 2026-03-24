# SkOpCubicHull - 三次贝塞尔曲线凸包

> 源文件:
> - `src/pathops/SkOpCubicHull.cpp`

## 概述

本文件实现了三次贝塞尔曲线控制点的凸包计算。凸包是包含所有端点和控制点的最小凸多边形，结果可能是三角形（3 个顶点）或四边形（4 个顶点）。凸包计算是路径操作中交点检测的基础，用于快速判断两条曲线是否可能相交。

## 架构位置

```
src/pathops/
  SkPathOpsCubic.h          // SkDCubic 类定义
  SkOpCubicHull.cpp          // 本文件 - convexHull() 实现
  SkPathOpsTypes.h           // 工具函数
```

## 主要类与结构体

本文件不定义新类，而是实现 `SkDCubic::convexHull()` 成员方法。

### `SkDCubic::convexHull()`

```cpp
int SkDCubic::convexHull(char order[4]) const;
```

- **参数**：`order` 输出数组，按顺序描述凸包顶点的索引（0-3）
- **返回值**：凸包顶点数（3 或 4）
- 不处理退化为点或线的三次曲线

## 公共 API 函数

### 辅助函数

```cpp
static bool rotate(const SkDCubic& cubic, int zero, int index, SkDCubic& rotPath);
```

将三次曲线绕两个控制点定义的线段进行旋转变换，使该线段水平化。用于判断其余点相对于该线段的位置关系。

```cpp
static int side(double x);
```

返回值的"侧面"标记：0（负）、1（零）、2（正）。

## 内部实现细节

### 算法步骤

1. **找最高点**：选择 Y 值最小（最高）的点作为起始点 `yMin`，Y 相同时选 X 较小的

2. **寻找中间点**：遍历其他三个点作为候选 `midX`：
   - 从 `yMin` 到候选点建立旋转参考线
   - 使用 `rotate()` 变换曲线使参考线水平
   - 检查剩余两个点在参考线的哪一侧
   - `sides == 2`（一上一下）：找到了将凸包分为两半的中间点
   - `sides == 0`（同侧）：记为备用起始点

3. **退化处理**：
   - 若两点重合（`rotate` 返回 false），直接返回三角形
   - 若首轮未找到 `midX`，尝试使用备用起始点重试
   - 若仍未找到，选择 `yMin ^ 3` 作为对端点

4. **判断三角形或四边形**：
   - 从 `least`（最小索引）到 `most`（最大索引）建立参考线
   - 检查 `yMin` 和 `midX` 是否在参考线同侧
   - `midSides != 2`：`midX` 不在两者之间，结果是三角形
   - `midSides == 2`：`midX` 在两者之间，结果是四边形

### `rotate()` 函数

将曲线控制点相对于两个参考点旋转：

- 若两点的 dy 近似为零且 dx 非零，直接复制（水平线段），必要时修正近似水平的控制点
- 否则应用旋转矩阵：
  ```
  rotPath[i].fX = cubic[i].fX * dx + cubic[i].fY * dy
  rotPath[i].fY = cubic[i].fY * dx - cubic[i].fX * dy
  ```

### `other_two()` 辅助函数

通过位运算获取除两个给定索引外的另两个索引的掩码。

### 控制点近重合处理

当多个候选 `midX` 存在（即控制点近似等于端点）时，通过距离平方比较选择更远的控制点作为凸包顶点。

## 依赖关系

- `SkPathOpsCubic.h` - `SkDCubic` 定义和 `other_two()` 工具
- `SkPathOpsPoint.h` - `SkDPoint`、`distanceSquared()`
- `SkPathOpsTypes.h` - `approximately_zero()`、`approximately_equal()` 等

## 设计模式与设计决策

1. **几何变换判断**：通过旋转变换将线段水平化，简化了"点在线段哪一侧"的判断为简单的 Y 坐标比较
2. **多级退化处理**：处理控制点重合、近重合、共线等各种退化情况
3. **双轮尝试**：首轮失败时使用备用起始点重试，增强鲁棒性
4. **位运算索引**：使用 XOR 和掩码操作在 4 个索引间高效切换

## 性能考量

1. **常数时间**：凸包计算只涉及 4 个点，所有操作都是 O(1)
2. **无内存分配**：所有计算使用栈上变量
3. **旋转近似优化**：若 dy 近似为零，跳过旋转矩阵计算，直接复制

### 凸包结果示例

**四边形情况（4 点不共面）：**
```
    P1
   / \
  P0   P2
   \ /
    P3
order = {0, 1, 2, 3}, return 4
```

**三角形情况（1 点在其余 3 点构成的三角形内）：**
```
  P0----P3
   \  P1/
    \ /
     P2
order = {0, 2, 3}, return 3 (P1 在三角形内)
```

**退化情况（2 点重合）：**
```
P0==P1  P2  P3
order = {0, 2, 3}, return 3
```

### `other_two()` 位运算

给定四个索引 {0,1,2,3} 中的两个，返回另外两个的掩码：

```
other_two(0, 3) = 0 ^ 3 = 3 (二进制 11)
  -> side1 = 0 ^ 3 = 3 -> 索引 1 的位
  -> side2 = 3 ^ 3 = 0 -> 索引 2 的位
实际: side1 = yMin ^ mask, side2 = index ^ mask
```

### 旋转变换数学

将四个控制点围绕 `cubic[zero]` 到 `cubic[index]` 的连线旋转，使该连线水平化：

```
dx = cubic[index].fX - cubic[zero].fX
dy = cubic[index].fY - cubic[zero].fY

旋转矩阵：
| dx  dy |
|-dy  dx |

rotPath[i].fX = cubic[i].fX * dx + cubic[i].fY * dy
rotPath[i].fY = cubic[i].fY * dx - cubic[i].fX * dy
```

旋转后，`rotPath[zero]` 和 `rotPath[index]` 具有相同的 Y 值，其他点的 Y 值表示其相对于该连线的侧面。

### side() 函数的三值逻辑

```cpp
static int side(double x) {
    return (x > 0) + (x >= 0);
    // x < 0  -> 0 + 0 = 0 (负侧)
    // x == 0 -> 0 + 1 = 1 (在线上)
    // x > 0  -> 1 + 1 = 2 (正侧)
}
```

两个 side 值的 XOR：
- `0 ^ 0 = 0` 或 `2 ^ 2 = 0`：两点同侧
- `0 ^ 2 = 2`：两点异侧（中间有分割线）
- 含 1 的情况：至少一个点在线上

## 相关文件

- `src/pathops/SkPathOpsCubic.h` - 三次曲线定义
- `src/pathops/SkPathOpsPoint.h` - 点类型
- `src/pathops/SkPathOpsTypes.h` - 近似比较
- `src/pathops/SkTSect.h` - T-sect 算法（凸包的主要使用者）
