# SkDQuadLineIntersection

> 源文件: src/pathops/SkDQuadLineIntersection.cpp

## 概述

`SkDQuadLineIntersection.cpp` 是 Skia 路径操作模块中负责计算二次贝塞尔曲线(Quadratic Bezier Curve)与直线交点的核心文件。该文件实现了基于数学推导的精确交点计算算法,通过将直线和二次曲线的参数方程联立求解,找出所有有效的交点。这是路径布尔运算中最基础的几何计算之一,直接影响到路径操作的准确性和效率。

该文件采用解析几何方法,通过坐标旋转将问题简化为求解二次方程的根,支持普通直线、水平线、垂直线等多种情况,并处理端点精确匹配、近似匹配、重合检测等复杂场景,确保数值稳定性和鲁棒性。

## 架构位置

`SkDQuadLineIntersection.cpp` 位于 Skia 路径操作的交点计算层:

- **模块路径**: `src/pathops/`
- **功能层级**: 几何基础算法层
- **主要类**: `LineQuadraticIntersections` (内部辅助类)
- **公共接口**: 通过 `SkIntersections` 类暴露方法
- **依赖组件**:
  - `SkDQuad`: 二次曲线的双精度表示
  - `SkDLine`: 直线的双精度表示
  - `SkIntersections`: 交点集合管理
  - `SkDPoint`: 双精度点结构
- **被使用者**:
  - `SkAddIntersections.cpp`: 批量添加交点
  - `SkOpSegment.cpp`: 段的交点查找
  - 路径布尔运算的各个模块

该文件是路径操作几何计算的基石,为上层布尔运算提供高精度的交点数据。

## 主要类与结构体

### LineQuadraticIntersections (核心计算类)

内部辅助类,封装了线-二次曲线交点的所有计算逻辑。

**成员变量**:
```cpp
const SkDQuad& fQuad;              // 二次曲线引用
const SkDLine* fLine;              // 直线指针
SkIntersections* fIntersections;   // 交点结果集合
bool fAllowNear;                   // 是否允许近似匹配
```

**关键枚举**:
```cpp
enum PinTPoint {
    kPointUninitialized,  // 点未初始化
    kPointInitialized     // 点已初始化
};
```

### SkIntersections (交点管理类)

外部接口类,管理交点的存储和查询。

**主要公共方法**:
- `horizontal()`: 计算与水平线的交点
- `vertical()`: 计算与垂直线的交点
- `intersect()`: 计算与任意直线的交点
- `intersectRay()`: 计算射线交点(不限制线段范围)
- `HorizontalIntercept()`: 静态方法,计算水平截距
- `VerticalIntercept()`: 静态方法,计算垂直截距

### SkDQuad (二次曲线类)

双精度二次贝塞尔曲线表示,包含三个控制点。

**关键方法**:
```cpp
int horizontalIntersect(double yIntercept, double roots[2]) const;
int verticalIntersect(double xIntercept, double roots[2]) const;
SkDPoint ptAtT(double t) const;  // 参数化求点
```

## 公共 API 函数

### SkIntersections::intersect(const SkDQuad& quad, const SkDLine& line)

计算二次曲线与任意直线的交点。

**参数**:
- `quad`: 二次贝塞尔曲线
- `line`: 直线(两个端点定义)

**返回值**: 交点数量(0-2,可能包含重合段)

**特性**:
- 支持精确端点匹配
- 支持近似端点匹配(可配置)
- 自动检测重合情况

### SkIntersections::horizontal(const SkDQuad& quad, double left, double right, double y, bool flipped)

计算二次曲线与水平线段的交点。

**参数**:
- `quad`: 二次曲线
- `left`, `right`: 线段的左右边界
- `y`: 水平线的纵坐标
- `flipped`: 是否翻转t值顺序

**返回值**: 交点数量

**优化点**: 针对水平线进行特殊优化,避免通用旋转计算。

### SkIntersections::vertical(const SkDQuad& quad, double top, double bottom, double x, bool flipped)

计算二次曲线与垂直线段的交点。

**参数**:
- `quad`: 二次曲线
- `top`, `bottom`: 线段的上下边界
- `x`: 垂直线的横坐标
- `flipped`: 是否翻转t值顺序

**返回值**: 交点数量

### SkIntersections::intersectRay(const SkDQuad& quad, const SkDLine& line)

计算二次曲线与射线的交点(不限制线段范围)。

**与 intersect() 的区别**: 不对线参数 t 进行 [0,1] 范围限制。

### SkIntersections::HorizontalIntercept(const SkDQuad& quad, SkScalar y, double* roots)

静态方法,仅计算二次曲线与水平线的 t 值,不构造交点对象。

**参数**:
- `quad`: 二次曲线
- `y`: 水平线纵坐标
- `roots`: 输出数组,存储曲线的 t 值(最多2个)

**返回值**: 根的数量

### SkIntersections::VerticalIntercept(const SkDQuad& quad, SkScalar x, double* roots)

静态方法,计算二次曲线与垂直线的 t 值。

## 内部实现细节

### 1. 数学原理

#### 二次贝塞尔曲线参数方程

标准二次曲线表示:
```
x(t) = a(1-t)² + 2b(1-t)t + ct²
y(t) = d(1-t)² + 2e(1-t)t + ft²
```

其中 (a,d), (b,e), (c,f) 分别是三个控制点的坐标。

#### 直线方程

斜率形式: `y = g*x + h`
垂直形式: `x = g'*y + h'`

#### 联立求解

使用 Mathematica 的 Resultant 函数消去 x 或 y,得到关于 t 的二次方程:
```
At² + Bt + C = 0
```

**当直线趋于水平时** (斜率 g 有限):
```cpp
A = -(d - 2*e + f) + g*(a - 2*b + c)
B = 2*((d - e) - g*(a - b))
C = -(d) + g*(a) + h
```

**当直线趋于垂直时** (用 x = g'*y + h' 表示):
```cpp
A = (a - 2*b + c) - g'*(d - 2*e + f)
B = 2*(-(a - b) + g'*(d - e))
C = (a) - g'*(d) - h'
```

### 2. 坐标旋转优化

`intersectRay()` 使用坐标旋转技术将直线旋转到 x 轴,简化计算:

```cpp
double adj = (*fLine)[1].fX - (*fLine)[0].fX;  // 邻边(相当于cos)
double opp = (*fLine)[1].fY - (*fLine)[0].fY;  // 对边(相当于sin)

// 旋转矩阵应用到二次曲线的每个控制点
for (int n = 0; n < 3; ++n) {
    r[n] = (fQuad[n].fY - (*fLine)[0].fY) * adj
         - (fQuad[n].fX - (*fLine)[0].fX) * opp;
}
```

旋转后,问题转化为求解曲线与 y=0 的交点,直接使用 `SkDQuad::RootsValidT()` 求解二次方程。

### 3. 主要计算流程

#### `intersect()` 方法流程

1. **精确端点匹配**: `addExactEndPoints()`
   - 检查曲线端点是否在直线上
   - 保证端点 t=0 和 t=1 的精确性

2. **近似端点匹配**: `addNearEndPoints()`
   - 使用容差判断近似匹配
   - 双向检查(曲线端点→线、线端点→曲线)

3. **求解二次方程**: `intersectRay(rootVals)`
   - 计算旋转后的系数
   - 调用 `SkDQuad::RootsValidT()` 求根
   - 只返回 [0,1] 范围内的有效 t 值

4. **构造交点**: 对每个根 t
   - 计算曲线上的点: `pt = fQuad.ptAtT(t)`
   - 计算对应的线参数: `lineT = findLineT(quadT)`
   - 参数钳制和点调整: `pinTs()`
   - 唯一性检查: `uniqueAnswer()`
   - 插入结果: `fIntersections->insert()`

5. **重合检测**: `checkCoincident()`
   - 检查相邻交点是否形成重合段
   - 标记重合跨度

### 4. 水平/垂直线优化

针对水平和垂直线,直接求解简化的方程,避免旋转计算:

**水平线交点** (`horizontalIntersect()`):
```cpp
D = fQuad[2].fY + fQuad[0].fY - 2*fQuad[1].fY;  // 二次项系数
E = -(fQuad[0].fY - fQuad[1].fY);                // 一次项系数
F = fQuad[0].fY - axisIntercept;                 // 常数项
SkDQuad::RootsValidT(D, 2*E, F, roots);
```

**垂直线交点** (`verticalIntersect()`):
类似,但使用 x 坐标。

### 5. 参数钳制和点调整

`pinTs()` 函数确保参数和点的一致性:

1. **范围检查**: 线参数 lineT ∈ [0, 1]
2. **参数钳制**: 使用 `SkPinT()` 将参数限制到有效范围
3. **点的重新计算**:
   - 当 lineT 在端点时,使用线的端点坐标
   - 否则使用曲线参数计算点
4. **网格对齐**: 检查计算点是否接近已知端点,对齐到精确坐标
5. **重复过滤**: 避免插入相同 lineT 的重复交点

### 6. 唯一性判断

`uniqueAnswer()` 防止重复插入相同交点:

```cpp
bool uniqueAnswer(double quadT, const SkDPoint& pt) {
    for (int inner = 0; inner < fIntersections->used(); ++inner) {
        if (fIntersections->pt(inner) != pt) continue;

        double existingQuadT = (*fIntersections)[0][inner];
        if (quadT == existingQuadT) return false;

        // 检查中点是否也近似相等(退化情况)
        double quadMidT = (existingQuadT + quadT) / 2;
        SkDPoint quadMidPt = fQuad.ptAtT(quadMidT);
        if (quadMidPt.approximatelyEqual(pt)) return false;
    }
    return true;
}
```

### 7. 重合检测算法

`checkCoincident()` 检测连续的交点对是否形成重合段:

1. 计算相邻两交点之间的中点参数 `quadMidT`
2. 计算中点坐标 `quadMidPt`
3. 检查中点是否也在直线上: `fLine->nearPoint(quadMidPt)`
4. 如果在线上,标记这对交点为重合段

## 依赖关系

### 直接依赖

**核心数据结构**:
- `src/pathops/SkPathOpsQuad.h`: 二次曲线定义
- `src/pathops/SkPathOpsLine.h`: 直线定义
- `src/pathops/SkIntersections.h`: 交点管理
- `src/pathops/SkPathOpsPoint.h`: 点类型
- `src/pathops/SkPathOpsCurve.h`: 通用曲线接口

**数学工具**:
- `include/core/SkScalar.h`: 标量类型
- `include/core/SkPoint.h`: 点基础类型
- `<cmath>`: 标准数学函数

**调试支持**:
- `src/pathops/SkPathOpsDebug.h`: 调试工具

### 被依赖情况

- `SkAddIntersections.cpp`: 批量添加段间交点
- `SkOpSegment.cpp`: 段的交点查找
- `SkPathOpsSimplify.cpp`: 路径简化
- `SkPathOpsOp.cpp`: 路径布尔运算
- 其他需要线-曲线交点的模块

## 设计模式与设计决策

### 1. 辅助类封装

`LineQuadraticIntersections` 作为内部类,封装所有计算逻辑:
- 避免污染公共接口
- 支持状态保持(成员变量)
- 便于分阶段计算

### 2. 策略模式

针对不同场景提供不同的计算策略:
- 任意直线: 坐标旋转法
- 水平线: 直接求解 y 方向方程
- 垂直线: 直接求解 x 方向方程
- 射线: 不限制线参数范围

### 3. 两阶段匹配

先精确匹配端点,再进行近似匹配:
- 保证端点的精确性(t=0, t=1)
- 通过容差处理数值误差
- 可配置的 `fAllowNear` 开关

### 4. 参数化表示

使用参数 t ∈ [0,1] 而非笛卡尔坐标:
- 数值稳定性更好
- 便于唯一性判断
- 支持曲线上的精确定位

### 5. 延迟点计算

部分情况下延迟计算交点坐标:
- `HorizontalIntercept()` 只返回 t 值
- 减少不必要的计算
- 上层可根据需要计算点

### 6. 双向检查

端点匹配时双向检查:
- 曲线端点是否在线上
- 线端点是否在曲线上
- 确保不遗漏边界交点

## 性能考量

### 1. 时间复杂度

- **主计算**: O(1),二次方程求解
- **端点匹配**: O(1),固定4个端点
- **唯一性检查**: O(n),n 为已有交点数(通常 ≤ 2)
- **总体**: O(1),常数时间复杂度

### 2. 空间复杂度

- **栈空间**: O(1),固定大小的局部变量
- **输出空间**: O(k),k 为交点数(最多5:短重合段+离散交点)

### 3. 优化技术

**避免三角函数**:
```cpp
// 不使用 cos(θ) 和 sin(θ)
// 直接使用向量的 x, y 分量作为旋转矩阵元素
double adj = line[1].fX - line[0].fX;
double opp = line[1].fY - line[0].fY;
```

**条件判断优化**:
```cpp
// 根据 dx 和 dy 的大小选择更稳定的除法方向
if (fabs(dx) > fabs(dy)) {
    return (xy.fX - (*fLine)[0].fX) / dx;
} else {
    return (xy.fY - (*fLine)[0].fY) / dy;
}
```

**早期退出**:
- 端点已存在时跳过近似匹配
- 参数超出 [0,1] 范围立即拒绝
- 重复交点立即过滤

### 4. 数值稳定性

**使用双精度**:
所有计算使用 `double` 类型,避免单精度累积误差。

**容差比较**:
```cpp
approximately_one_or_less_double(*lineT)
approximately_zero_or_more_double(*lineT)
approximatelyEqual(pt1, pt2)
```

**参数钳制**:
```cpp
*quadT = SkPinT(*quadT);  // 限制到 [0, 1]
*lineT = SkPinT(*lineT);
```

**网格对齐**:
检测到近似端点时,直接使用精确端点坐标,避免浮点累积误差。

### 5. 特殊情况处理

- **重合段**: 通过中点检测自动识别
- **切线接触**: 返回单个交点(重根)
- **退化曲线**: `RootsValidT()` 内部处理线性退化
- **垂直/水平线**: 专用优化路径,避免除零

### 6. 内存访问模式

- 成员变量引用和指针,避免拷贝
- 局部变量优先使用栈
- 输出通过已分配的 `SkIntersections` 对象

## 相关文件

### 核心依赖文件

- `src/pathops/SkPathOpsQuad.h` / `.cpp`: 二次曲线表示和求根算法
- `src/pathops/SkPathOpsLine.h` / `.cpp`: 直线表示和近点判断
- `src/pathops/SkIntersections.h` / `.cpp`: 交点集合管理
- `src/pathops/SkPathOpsPoint.h`: 双精度点类型
- `src/pathops/SkPathOpsCurve.h`: 通用曲线接口

### 相关交点计算

- `src/pathops/SkDCubicLineIntersection.cpp`: 三次曲线-直线交点
- `src/pathops/SkDQuadIntersection.cpp`: 二次曲线-二次曲线交点
- `src/pathops/SkDCubicIntersection.cpp`: 三次曲线-三次曲线交点
- `src/pathops/SkDConicLineIntersection.cpp`: 圆锥曲线-直线交点

### 上层调用者

- `src/pathops/SkAddIntersections.cpp`: 统一的交点添加接口
- `src/pathops/SkOpSegment.cpp`: 段的交点查找
- `src/pathops/SkPathOpsOp.cpp`: 路径布尔运算

### 数学工具

- `src/pathops/SkPathOpsTypes.h`: 类型定义和常量
- `include/private/base/SkMath.h`: 数学辅助函数

### 测试文件

- `tests/PathOpsQuadLineIntersectionTest.cpp`: 单元测试
- `tests/PathOpsExtendedTest.cpp`: 扩展测试套件

该文件是 Skia 路径操作几何计算的基础组件,通过严谨的数学推导和精心的数值处理,为路径布尔运算提供了可靠的交点计算能力。
