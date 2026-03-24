# SkPathOpsWinding

> 源文件
> - src/pathops/SkPathOpsWinding.cpp

## 概述

`SkPathOpsWinding` 实现了 PathOps 算法中最关键的 winding 数（缠绕数）计算功能。Winding 数决定了路径操作中哪些区域被认为是"内部"，哪些是"外部"，是路径布尔运算的核心概念。

该文件通过光线投射（ray casting）算法计算每个路径段的 winding 数：
1. 从待计算的点发射一条光线
2. 统计光线与其他路径段的交点
3. 根据交点处路径段的方向累计 winding 数
4. 使用 winding 数判断点是否在路径内部

这个算法需要处理大量的边界情况，包括退化交点、共线边、数值精度等问题。

## 架构位置

`SkPathOpsWinding` 位于 PathOps 算法的核心层：

```
src/pathops/
├── SkOpContour.h/cpp         // 轮廓管理，调用 winding 计算
├── SkOpSegment.h/cpp         // 路径段，提供光线交点查询
├── SkOpSpan.h/cpp            // 路径段关键点，存储 winding 数
├── SkPathOpsTypes.h          // 精度比较函数
├── SkPathOpsWinding.cpp      // Winding 计算（当前模块）
└── SkOpBuilder.cpp           // 路径操作入口
```

## 主要类与结构体

### SkOpRayDir 枚举

```cpp
enum class SkOpRayDir {
    kLeft,    // 向左发射光线
    kTop,     // 向上发射光线
    kRight,   // 向右发射光线
    kBottom,  // 向下发射光线
};
```

定义光线投射的四个主要方向，用于计算 winding 数。

### SkOpRayHit 结构体

```cpp
struct SkOpRayHit {
    SkOpRayHit* fNext;        // 链表：下一个交点
    SkOpSpan* fSpan;          // 交点所在的 span
    SkPoint fPt;              // 交点位置
    double fT;                // 交点的 t 参数
    SkDVector fSlope;         // 交点处的切线方向
    bool fValid;              // 交点是否有效

    SkOpRayDir makeTestBase(SkOpSpan* span, double t);
};
```

表示光线与路径段的一个交点，包含位置、参数、方向等信息。

## 核心算法

### 光线投射算法

**主函数:**
```cpp
bool SkOpSpan::sortableTop(SkOpContour* contourHead);
```

**算法流程：**

1. **选择测试点和方向：**
```cpp
double t = get_t_guess(fTopTTry++, &dirOffset);
SkOpRayHit hitBase;
SkOpRayDir dir = hitBase.makeTestBase(this, t);
```
   - 根据尝试次数选择 t 值
   - 计算测试点和切线
   - 选择与切线最垂直的光线方向

2. **收集所有交点：**
```cpp
SkOpContour* contour = contourHead;
do {
    contour->rayCheck(hitBase, dir, &hitHead, &allocator);
} while ((contour = contour->next()));
```
   - 遍历所有轮廓
   - 查找光线与路径段的交点
   - 构建交点链表

3. **排序交点：**
```cpp
SkTQSort(sorted.begin(), sorted.end(),
         xy_index(dir) ? less_than(dir) ? hit_compare_y : reverse_hit_compare_y
                       : less_than(dir) ? hit_compare_x : reverse_hit_compare_x);
```
   - 根据光线方向选择排序函数
   - 按交点距离基准点的距离排序

4. **计算 winding 数：**
```cpp
for (int index = 0; index < count; ++index) {
    hit = sorted[index];
    bool ccw = ccw_dxdy(hit->fSlope, dir);
    int windValue = ccw ? -span->windValue() : span->windValue();
    wind += windValue;
    oppWind += oppValue;

    int windSum = SkOpSegment::UseInnerWinding(lastWind, wind) ? wind : lastWind;
    if (spanSum == SK_MinS32) {
        span->setWindSum(windSum);
    }
}
```
   - 遍历排序后的交点
   - 根据切线方向判断是顺时针还是逆时针
   - 累加 winding 值
   - 设置每个 span 的 windSum 和 oppSum

### 光线-曲线交点计算

**SkOpSegment::rayCheck():**
```cpp
void SkOpSegment::rayCheck(const SkOpRayHit& base, SkOpRayDir dir,
                           SkOpRayHit** hits, SkArenaAlloc* allocator)
```

**实现步骤：**

1. **边界检查：**
```cpp
if (!sideways_overlap(fBounds, base.fPt, dir)) {
    return;  // 光线不可能与段相交
}
```

2. **计算交点：**
```cpp
int roots = (*CurveIntercept[fVerb * 2 + xy_index(dir)])(fPts, fWeight, baseYX, tVals);
```
   - 调用曲线-直线求交函数
   - 根据曲线类型和光线方向选择函数

3. **验证交点：**
```cpp
for (int index = 0; index < roots; ++index) {
    double t = tVals[index];
    if (base.fSpan->segment() == this && approximately_equal(base.fT, t)) {
        continue;  // 跳过起始点
    }

    pt = this->ptAtT(t);
    slope = this->dSlopeAtT(t);

    // 检查切线与光线是否近乎平行
    if (fabs(pt_dydx(slope, dir) * 10000) > fabs(pt_dxdy(slope, dir))) {
        valid = true;
    }
}
```

4. **创建交点记录：**
```cpp
SkOpRayHit* newHit = allocator->make<SkOpRayHit>();
newHit->fNext = *hits;
newHit->fPt = pt;
newHit->fSlope = slope;
newHit->fSpan = span;
newHit->fT = t;
newHit->fValid = valid;
*hits = newHit;
```

### 方向判断辅助函数

**ccw_dxdy():**
```cpp
static bool ccw_dxdy(const SkDVector& v, SkOpRayDir dir) {
    bool vPartPos = pt_dydx(v, dir) > 0;
    bool leftBottom = ((static_cast<int>(dir) + 1) & 2) != 0;
    return vPartPos == leftBottom;
}
```

判断切线方向相对于光线是顺时针还是逆时针。

**坐标访问函数：**
```cpp
static int xy_index(SkOpRayDir dir) {
    return static_cast<int>(dir) & 1;
}

static SkScalar pt_xy(const SkPoint& pt, SkOpRayDir dir) {
    return (&pt.fX)[xy_index(dir)];  // 主坐标（光线方向）
}

static SkScalar pt_yx(const SkPoint& pt, SkOpRayDir dir) {
    return (&pt.fX)[!xy_index(dir)];  // 次坐标（垂直于光线）
}
```

使用位操作统一处理四个方向。

### 测试点选择策略

**get_t_guess():**
```cpp
static double get_t_guess(int tTry, int* dirOffset) {
    double t = 0.5;
    *dirOffset = tTry & 1;
    int tBase = tTry >> 1;
    int tBits = 0;
    while (tTry >>= 1) {
        t /= 2;
        ++tBits;
    }
    if (tBits) {
        int tIndex = (tBase - 1) & ((1 << tBits) - 1);
        t += t * 2 * tIndex;
    }
    return t;
}
```

**尝试序列：**
- 尝试 0：t=0.5，方向偏移=0
- 尝试 1：t=0.5，方向偏移=1
- 尝试 2：t=0.25，方向偏移=0
- 尝试 3：t=0.75，方向偏移=0
- ...

逐步细化测试点位置，增加成功率。

## 内部实现细节

### 退化情况处理

1. **零斜率：**
```cpp
if (hitBase.fSlope.fX == 0 && hitBase.fSlope.fY == 0) {
    return false;  // 无法选择光线方向
}
```

2. **切线平行于光线：**
```cpp
if (!pt_dydx(hitBase.fSlope, dir)) {
    return false;  // 切线与光线平行，无法判断方向
}
```

3. **重复交点：**
```cpp
if (last && SkDPoint::ApproximatelyEqual(*last, hit->fPt)) {
    return false;  // 两个交点太接近
}
```

4. **接近端点的交点：**
```cpp
if (approximately_equal(tHit, next->t())) {
    return nullptr;  // 交点在 span 边界上
}
```

### 数值精度处理

**距离比较：**
```cpp
if (!approximately_equal(baseXY, boundsXY) && (baseXY < boundsXY) == checkLessThan)
```

使用 `approximately_equal` 避免浮点误差。

**切线有效性检查：**
```cpp
if (fabs(pt_dydx(slope, dir) * 10000) > fabs(pt_dxdy(slope, dir))) {
    valid = true;
}
```

切线与光线夹角必须足够大（至少 1/10000），避免数值不稳定。

### 内存管理

```cpp
SkSTArenaAlloc<1024> allocator;
SkOpRayHit* newHit = allocator->make<SkOpRayHit>();
```

使用栈上的 arena 分配器：
- 快速分配
- 批量释放
- 无碎片

### Winding 数传播

```cpp
(void) hitSegment->markAndChaseWinding(span, span->next(), windSum, oppSum, nullptr);
(void) hitSegment->markAndChaseWinding(span->next(), span, windSum, oppSum, nullptr);
```

设置 winding 数后，传播到相邻的 span，确保一致性。

## 依赖关系

**直接依赖:**
```cpp
#include "src/pathops/SkOpContour.h"      // 轮廓管理
#include "src/pathops/SkOpSegment.h"      // 路径段
#include "src/pathops/SkOpSpan.h"         // Span
#include "src/pathops/SkPathOpsTypes.h"   // 精度函数
#include "src/pathops/SkPathOpsCurve.h"   // 曲线求交
#include "src/base/SkArenaAlloc.h"        // 内存分配
#include "src/base/SkTSort.h"             // 排序算法
```

**被依赖:**
```cpp
src/pathops/SkOpBuilder.cpp              // 路径操作入口
src/pathops/SkOpContour.cpp              // 调用 FindSortableTop
```

## 设计模式与设计决策

### 1. 迭代策略

```cpp
for (int index = 0; index < SkOpGlobalState::kMaxWindingTries; ++index) {
    SkOpSpan* result = contour->findSortableTop(contourHead);
    if (result) {
        return result;
    }
}
```

最多尝试 `kMaxWindingTries` 次（通常是 10），每次使用不同的测试点。

### 2. 链表数据结构

```cpp
struct SkOpRayHit {
    SkOpRayHit* fNext;
    ...
};
```

使用侵入式链表存储交点，避免动态数组的重新分配。

### 3. 位操作优化

```cpp
static int xy_index(SkOpRayDir dir) {
    return static_cast<int>(dir) & 1;
}
```

使用位运算统一处理 X 和 Y 坐标，避免条件分支。

### 4. UseInnerWinding 规则

```cpp
int windSum = SkOpSegment::UseInnerWinding(lastWind, wind) ? wind : lastWind;
```

选择"内部" winding 数，处理相邻区域的 winding 计算。

## 性能考量

### 1. 早期退出

```cpp
if (!sideways_overlap(fBounds, base.fPt, dir)) {
    return;
}
```

使用边界框快速剔除不可能相交的路径段。

### 2. 批量分配

```cpp
SkSTArenaAlloc<1024> allocator;
```

所有交点在栈上分配，函数返回后自动释放。

### 3. 原地排序

```cpp
SkTQSort(sorted.begin(), sorted.end(), ...);
```

使用快速排序，平均时间复杂度 O(n log n)。

### 4. 缓存友好

遍历轮廓和段时保持顺序访问，利用 CPU 缓存。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/pathops/SkOpContour.h` | 轮廓管理 | 调用 winding 计算 |
| `src/pathops/SkOpSegment.h` | 路径段 | 提供交点查询 |
| `src/pathops/SkOpSpan.h` | Span | 存储 winding 数 |
| `src/pathops/SkPathOpsTypes.h` | 精度函数 | 数值比较 |
| `src/pathops/SkPathOpsCurve.h` | 曲线求交 | 交点计算 |
| `src/base/SkArenaAlloc.h` | 内存分配 | 快速分配 |
| `src/base/SkTSort.h` | 排序算法 | 交点排序 |
| `src/pathops/SkOpBuilder.cpp` | 路径操作 | 入口函数 |
