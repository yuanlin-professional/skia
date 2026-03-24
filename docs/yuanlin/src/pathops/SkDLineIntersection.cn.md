# SkDLineIntersection

> 源文件: src/pathops/SkDLineIntersection.cpp

## 概述

`SkDLineIntersection.cpp` 是 Skia 路径操作模块中负责计算直线与直线交点的核心文件。该文件实现了直线段交点的精确计算,包括普通直线、水平线、垂直线等多种情况,并特别处理了平行线、重合线、端点匹配等复杂几何场景。该模块是路径布尔运算的基础组件,为所有涉及直线段的几何计算提供高精度、鲁棒的交点判断能力。

该文件采用参数化直线表示和向量叉积方法,通过严谨的数学推导和细致的数值处理,确保在各种退化情况下都能给出正确结果。特别针对平行线和重合线设计了专门的清理和标记机制,是整个路径操作系统中最基础也最关键的几何计算模块之一。

## 架构位置

`SkDLineIntersection.cpp` 位于路径操作的交点计算基础层:

- **模块路径**: `src/pathops/`
- **功能层级**: 几何基础算法层
- **依赖组件**:
  - `SkDLine`: 双精度直线表示
  - `SkIntersections`: 交点集合管理
  - `SkDPoint`: 双精度点结构
  - `SkPathOpsTypes.h`: 类型和工具函数
- **被使用者**:
  - `SkAddIntersections.cpp`: 批量交点添加
  - `SkOpSegment.cpp`: 段的交点查找
  - 各种路径布尔运算模块

该文件处于几何计算金字塔的底层,为所有高级操作提供可靠的直线交点计算服务。

## 主要类与结构体

### SkIntersections (交点管理类)

管理和存储交点的核心类。

**关键成员**:
```cpp
double fT[2][9];        // 两条曲线的参数值
SkDPoint fPt[9];        // 交点坐标
uint8_t fIsCoincident[2]; // 重合标记位
int fUsed;              // 已使用的交点数
int fMax;               // 最大容量
bool fAllowNear;        // 是否允许近似匹配
```

**核心方法** (本文件实现的):
- `intersect(const SkDLine& a, const SkDLine& b)`: 两条直线交点
- `intersectRay(const SkDLine& a, const SkDLine& b)`: 射线交点(无范围限制)
- `horizontal(const SkDLine& line, ...)`: 与水平线交点
- `vertical(const SkDLine& line, ...)`: 与垂直线交点
- `HorizontalIntercept()` / `VerticalIntercept()`: 静态截距计算

### SkDLine (直线类)

双精度直线表示,包含两个端点。

**结构**:
```cpp
SkDPoint[2];  // 直线的两个端点
```

**关键方法**:
- `exactPoint()`: 精确点匹配
- `nearPoint()`: 近似点匹配
- `ExactPointH()` / `ExactPointV()`: 水平/垂直精确匹配
- `NearPointH()` / `NearPointV()`: 水平/垂直近似匹配

## 公共 API 函数

### `int SkIntersections::intersect(const SkDLine& a, const SkDLine& b)`

计算两条直线段的交点。

**参数**:
- `a`: 第一条直线
- `b`: 第二条直线

**返回值**: 交点数量(0, 1, 或 2)
- 0: 不相交(平行但不重合)
- 1: 单点交集或端点接触
- 2: 重合线段

**特性**:
- 精确端点匹配优先
- 支持近似匹配(可配置)
- 自动检测和标记重合段
- 清理冗余交点

### `int SkIntersections::intersectRay(const SkDLine& a, const SkDLine& b)`

计算两条直线的交点,不限制参数范围(视为无限长直线或射线)。

**参数**:
- `a`: 第一条直线
- `b`: 第二条直线

**返回值**: 交点数量
- 0: 平行不相交
- 1: 有唯一交点
- 2: 重合(返回默认端点)

**用途**: 用于需要直线延长的几何判断。

### `int SkIntersections::horizontal(const SkDLine& line, double left, double right, double y, bool flipped)`

计算直线与水平线段的交点。

**参数**:
- `line`: 直线
- `left`, `right`: 水平线段的左右边界
- `y`: 水平线的纵坐标
- `flipped`: 是否翻转参数顺序

**返回值**: 交点数量

**优化**: 针对水平线进行专门优化,避免通用计算。

### `int SkIntersections::vertical(const SkDLine& line, double top, double bottom, double x, bool flipped)`

计算直线与垂直线段的交点。

**参数**:
- `line`: 直线
- `top`, `bottom`: 垂直线段的上下边界
- `x`: 垂直线的横坐标
- `flipped`: 是否翻转参数顺序

**返回值**: 交点数量

### `double SkIntersections::HorizontalIntercept(const SkDLine& line, double y)` (静态)

计算直线与水平线 y 的交点参数。

**参数**:
- `line`: 直线
- `y`: 水平线纵坐标

**返回值**: 直线的参数 t ∈ [0, 1]

**前提**: `line[0].fY != line[1].fY` (非水平线)

**公式**: `t = (y - line[0].fY) / (line[1].fY - line[0].fY)`

### `double SkIntersections::VerticalIntercept(const SkDLine& line, double x)` (静态)

计算直线与垂直线 x 的交点参数。

**前提**: `line[0].fX != line[1].fX` (非垂直线)

## 内部实现细节

### 1. 数学原理

#### 参数化直线表示

直线 L(t) = P0 + t·(P1 - P0),其中 t ∈ [0, 1] 表示线段,t ∈ ℝ 表示无限直线。

#### 交点计算(向量方法)

给定两条直线:
```
A(s) = A0 + s·(A1 - A0)
B(t) = B0 + t·(B1 - B0)
```

求解 A(s) = B(t):
```
A0 + s·aLen = B0 + t·bLen
s·aLen - t·bLen = B0 - A0
```

使用叉积消元:
```
分母 denom = aLen × bLen = aLen.x·bLen.y - aLen.y·bLen.x
分子 numerA = (B0 - A0) × bLen
分子 numerB = (B0 - A0) × aLen

s = numerA / denom
t = numerB / denom
```

**平行判断**: `denom ≈ 0` 表示平行或重合。

### 2. 核心算法

#### `intersectRay()` 实现

```cpp
int SkIntersections::intersectRay(const SkDLine& a, const SkDLine& b) {
    fMax = 2;
    SkDVector aLen = a[1] - a[0];
    SkDVector bLen = b[1] - b[0];

    // 计算分母(叉积)
    double denom = bLen.fY * aLen.fX - aLen.fY * bLen.fX;

    int used;
    if (!approximately_zero(denom)) {
        // 非平行情况
        SkDVector ab0 = a[0] - b[0];
        double numerA = ab0.fY * bLen.fX - bLen.fY * ab0.fX;
        double numerB = ab0.fY * aLen.fX - aLen.fY * ab0.fX;
        numerA /= denom;
        numerB /= denom;
        fT[0][0] = numerA;
        fT[1][0] = numerB;
        used = 1;
    } else {
        // 平行或重合
        // 检查是否在同一直线上
        if (!AlmostEqualUlps(aLen.fX * a[0].fY - aLen.fY * a[0].fX,
                             aLen.fX * b[0].fY - aLen.fY * b[0].fX)) {
            return fUsed = 0;  // 平行不重合
        }
        // 重合,返回默认参数
        fT[0][0] = fT[1][0] = 0;
        fT[0][1] = fT[1][1] = 1;
        used = 2;
    }
    computePoints(a, used);
    return fUsed;
}
```

#### `intersect()` 实现流程

1. **精确端点匹配**: 检查一条线的端点是否精确在另一条线上
2. **通用交点计算**: 使用向量叉积计算内部交点
3. **近似端点匹配**: 如果启用 `fAllowNear`,检查近似匹配
4. **平行线清理**: `cleanUpParallelLines()` 处理冗余交点
5. **重合标记**: 标记 `fIsCoincident` 位

### 3. 平行线处理

#### `cleanUpParallelLines(bool parallel)` 函数

清理平行线或重合线产生的冗余交点:

**处理逻辑**:
1. **限制交点数**: 最多保留2个交点
2. **非平行情况**:
   - 检查端点匹配情况
   - 移除不合理的中间交点
   - 优先保留端点匹配
3. **平行(重合)情况**:
   - 保留2个交点
   - 标记为重合: `fIsCoincident[0] = fIsCoincident[1] = 0x03`

**重合标记含义**:
- `0x03` = 二进制 `0b11`,表示索引0和1都是重合段的端点

### 4. 水平/垂直线优化

#### 水平线算法

```cpp
int SkIntersections::horizontal(const SkDLine& line,
                                double left, double right, double y,
                                bool flipped) {
    fMax = 3;

    // 1. 精确端点匹配
    // 检查水平线段的端点是否在直线上

    // 2. 检查直线端点是否在水平线段范围内

    // 3. 计算交点
    int result = horizontal_coincident(line, y);
    if (result == 1 && fUsed == 0) {
        // 单点交集
        fT[0][0] = HorizontalIntercept(line, y);
        double xIntercept = line[0].fX + fT[0][0] * (line[1].fX - line[0].fX);
        if (between(left, xIntercept, right)) {
            // 交点在范围内
            fT[1][0] = (xIntercept - left) / (right - left);
            // 存储交点
        }
    }

    // 4. 近似匹配
    if (fAllowNear || result == 2) {
        // 添加近似端点
    }

    // 5. 清理
    cleanUpParallelLines(result == 2);
    return fUsed;
}
```

#### 重合检测辅助函数

```cpp
static int horizontal_coincident(const SkDLine& line, double y) {
    double min = line[0].fY, max = line[1].fY;
    if (min > max) swap(min, max);

    if (min > y || max < y) return 0;  // 不相交

    if (AlmostEqualUlps(min, max) && max - min < fabs(line[0].fX - line[1].fX)) {
        return 2;  // 重合
    }
    return 1;  // 单点相交
}
```

### 5. 近似匹配策略

当 `fAllowNear` 为 true 时,使用容差判断:

```cpp
// 对于每个端点
for (int iA = 0; iA < 2; ++iA) {
    bool notB;
    double aNearB = b.nearPoint(a[iA], &notB);
    if (aNearB >= 0 && notB) {
        // a[iA] 接近 b 上的某点
        // 但不是精确匹配
        // 插入近似交点
    }
}
```

**复杂近似逻辑**:
- 跟踪哪些端点已匹配
- 避免重复插入
- 特殊处理"每条线贡献一个端点"的情况
- 使用 `insertNear()` 保留两个不同的点

### 6. 参数翻转处理

`flipped` 参数用于调整参数顺序:

```cpp
if (flipped) {
    for (int index = 0; index < result; ++index) {
        fT[1][index] = 1 - fT[1][index];  // 反转参数
    }
}
```

**用途**: 当线段方向需要反转时,确保参数语义正确。

## 依赖关系

### 直接依赖

**核心数据结构**:
- `src/pathops/SkIntersections.h`: 交点管理类
- `src/pathops/SkPathOpsLine.h`: 直线表示
- `src/pathops/SkPathOpsPoint.h`: 点和向量类型
- `src/pathops/SkPathOpsTypes.h`: 类型定义和工具函数

**标准库**:
- `<cmath>`: 数学函数(`fabs`)
- `<cstdint>`: 整数类型
- `<utility>`: `std::swap`

**Skia 基础**:
- `include/core/SkTypes.h`: 基础类型

### 被依赖情况

- `SkAddIntersections.cpp`: 批量交点计算
- `SkOpSegment.cpp`: 段的交点查找
- `SkPathOpsOp.cpp`: 路径布尔运算
- 所有需要直线交点的几何算法

## 设计模式与设计决策

### 1. 多阶段匹配策略

交点计算采用三阶段策略:
1. **精确匹配**: 优先检查精确重合的端点
2. **几何计算**: 计算内部交点
3. **近似匹配**: 使用容差处理数值误差

### 2. 分离射线和线段计算

- `intersectRay()`: 无参数范围限制,纯几何计算
- `intersect()`: 完整的线段交点,包括端点和近似处理

### 3. 专用优化路径

为水平线和垂直线提供专用函数:
- 避免通用旋转和投影
- 利用轴对齐特性简化计算
- 提高数值稳定性

### 4. 容差可配置

通过 `fAllowNear` 控制近似匹配:
- 严格模式: 只接受精确匹配
- 宽松模式: 使用容差处理浮点误差

### 5. 重合段标记

使用位掩码 `fIsCoincident` 标记重合:
- 高效的存储(单字节)
- 支持多对重合段(最多4对)
- 清晰的语义(位索引对应交点索引)

## 性能考量

### 1. 时间复杂度

- **主计算**: O(1),固定次数算术运算
- **端点匹配**: O(1),最多4个端点
- **清理阶段**: O(n),n 为交点数(通常 ≤ 3)
- **总体**: O(1)常数时间

### 2. 空间复杂度

- **交点存储**: 固定大小数组(fMax = 3)
- **局部变量**: O(1)
- **无动态分配**

### 3. 数值稳定性

**叉积方法的优势**:
- 避免显式计算斜率(避免除以小数)
- 对称的计算公式
- 分子分母都是线性组合

**容差函数**:
- `approximately_zero()`: 判断接近零
- `AlmostEqualUlps()`: ULP (Unit in the Last Place) 比较
- `between()`: 范围判断带容差

**参数钳制**:
```cpp
fT[0][0] = SkPinT(fT[0][0]);  // 限制到 [0, 1]
```

### 4. 早期退出优化

```cpp
if (!precisely_between(min, x, max)) {
    return 0;  // 快速剔除不相交情况
}
```

### 5. 缓存友好

- 顺序访问端点数组
- 局部变量优先使用栈
- 避免随机内存访问

### 6. 分支预测友好

常见路径优先:
- 非平行情况是主流
- 单点交集比重合常见
- 精确匹配比近似匹配常见

## 相关文件

### 核心依赖

- `src/pathops/SkIntersections.h` / `.cpp`: 交点管理
- `src/pathops/SkPathOpsLine.h` / `.cpp`: 直线表示
- `src/pathops/SkPathOpsPoint.h`: 点和向量
- `src/pathops/SkPathOpsTypes.h`: 类型和工具

### 相关交点计算

- `src/pathops/SkDQuadLineIntersection.cpp`: 二次曲线-直线
- `src/pathops/SkDCubicLineIntersection.cpp`: 三次曲线-直线
- `src/pathops/SkDConicLineIntersection.cpp`: 圆锥曲线-直线

### 上层调用者

- `src/pathops/SkAddIntersections.cpp`: 统一交点接口
- `src/pathops/SkOpSegment.cpp`: 段操作
- `src/pathops/SkPathOpsOp.cpp`: 路径布尔运算

### 测试文件

- `tests/PathOpsLineIntersectionTest.cpp`: 单元测试
- `tests/PathOpsExtendedTest.cpp`: 扩展测试

该文件是 Skia 路径操作几何计算的基石,通过严谨的数学方法和细致的工程实现,为所有涉及直线的几何计算提供了可靠、高效的交点判断能力。其344行代码覆盖了直线交点的所有复杂场景,是路径操作系统中最关键的基础模块之一。
