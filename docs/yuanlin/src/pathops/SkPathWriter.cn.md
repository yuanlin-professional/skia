# SkPathWriter

> 源文件
> - src/pathops/SkPathWriter.h
> - src/pathops/SkPathWriter.cpp

## 概述

`SkPathWriter` 是 Skia PathOps 模块中负责重建路径的核心类。它通过逐轮廓构建路径，处理路径操作算法产生的片段化轮廓数据，最终组装成完整的路径。该类的主要职责包括：

1. **延迟写入**：缓冲 move 和 line 操作，避免生成退化的线段
2. **轮廓完整性管理**：区分闭合轮廓和开放轮廓
3. **部分轮廓组装**：将具有不匹配起点和终点的轮廓片段连接起来

这个类是 PathOps 算法的输出阶段，将内部表示转换回 `SkPath` 对象。

## 架构位置

`SkPathWriter` 位于 PathOps 模块的输出层：

```
src/pathops/
├── SkOpSegment.h/cpp           // 路径段表示
├── SkOpSpan.h/cpp              // 路径段上的关键点
├── SkPathOpsTypes.h/cpp        // 基础类型定义
├── SkPathWriter.h/cpp          // 路径重建（当前模块）
└── SkOpBuilder.cpp             // 路径操作构建器（调用者）
```

它接收来自 PathOps 算法（交集、并集、差集等）的处理结果，并将其转换为可供外部使用的 `SkPath` 对象。

## 主要类与结构体

### SkPathWriter

**构造函数:**
```cpp
SkPathWriter(SkPathFillType);
```
- 初始化路径构建器并设置填充类型

**核心成员变量:**
```cpp
SkPathBuilder fBuilder;         // 最终输出的路径构建器
SkPathBuilder fCurrent;         // 当前正在构建的轮廓
TArray<SkPathBuilder> fPartials; // 未闭合的部分轮廓
SkTDArray<const SkOpPtT*> fEndPtTs; // 部分轮廓的起点和终点
const SkOpPtT* fDefer[2];       // [0]=延迟的move, [1]=延迟的line
const SkOpPtT* fFirstPtT;       // 当前轮廓的第一个点
```

**状态查询方法:**
```cpp
bool hasMove() const { return !fFirstPtT; }
bool isClosed() const;
SkPath nativePath() { return fBuilder.detach(); }
```

## 公共 API 函数

### 轮廓构建方法

**init():**
```cpp
void init()
```
- 重置当前轮廓的状态
- 清空延迟缓冲区

**deferredMove():**
```cpp
void deferredMove(const SkOpPtT* pt)
```
- 延迟执行 move 操作
- 如果已有延迟的点且不匹配当前点，则先完成当前轮廓
- 设置新的起始点

**deferredLine():**
```cpp
bool deferredLine(const SkOpPtT* pt)
```
- 延迟执行 line 操作
- 检测退化线段（起点终点相同）并跳过
- 检测斜率变化，决定是否真正绘制线段
- 返回值：true 表示操作被接受

**曲线绘制方法:**
```cpp
void quadTo(const SkPoint& pt1, const SkOpPtT* pt2);
void conicTo(const SkPoint& pt1, const SkOpPtT* pt2, SkScalar weight);
void cubicTo(const SkPoint& pt1, const SkPoint& pt2, const SkOpPtT* pt3);
```
- 添加二次曲线、圆锥曲线、三次曲线
- 自动处理延迟的 move 和 line 操作
- 使用 `update()` 方法处理端点

### 轮廓完成方法

**finishContour():**
```cpp
void finishContour()
```
- 完成当前轮廓的构建
- 如果轮廓闭合，调用 `close()`
- 如果轮廓未闭合，保存为部分轮廓待后续组装

**assemble():**
```cpp
void assemble()
```
- 组装所有部分轮廓
- 计算轮廓端点之间的距离，寻找最佳连接方案
- 使用图论算法连接轮廓片段
- 这是最复杂的方法，占据了实现的大部分代码

## 内部实现细节

### 延迟写入机制

`SkPathWriter` 使用双缓冲延迟机制避免生成退化几何：

```cpp
fDefer[0] = fDefer[1] = nullptr;
```

- `fDefer[0]`：延迟的 move 操作的目标点
- `fDefer[1]`：延迟的 line 操作的目标点

**延迟写入的逻辑:**
1. `deferredMove()` 设置 `fDefer[0]`
2. `deferredLine()` 设置 `fDefer[1]`
3. 只有在下一个操作（曲线绘制或新的 line）到来时，才真正执行延迟的操作
4. 如果延迟的 line 与下一个点形成共线关系，则跳过中间点

### 斜率变化检测

```cpp
bool changedSlopes(const SkOpPtT* ptT) const {
    SkVector deferDxdy = fDefer[1]->fPt - fDefer[0]->fPt;
    SkVector lineDxdy = ptT->fPt - fDefer[1]->fPt;
    return deferDxdy.fX * lineDxdy.fY != deferDxdy.fY * lineDxdy.fX;
}
```

使用叉积判断三点是否共线：
- 如果叉积为零，三点共线，可以省略中间点
- 如果叉积非零，斜率改变，需要保留中间点

### 点的匹配逻辑

```cpp
bool matchedLast(const SkOpPtT* test) const {
    if (test == fDefer[1]) {
        return true;
    }
    if (!test || !fDefer[1]) {
        return false;
    }
    return test->contains(fDefer[1]);
}
```

使用 `SkOpPtT::contains()` 方法判断两个点是否表示同一个位置：
- 考虑了 T 值和点坐标的精度问题
- 处理了同一点在不同曲线上的多重表示

### update() 方法

```cpp
SkPoint update(const SkOpPtT* pt) {
    if (!fDefer[1]) {
        this->moveTo();
    } else if (!this->matchedLast(fDefer[0])) {
        this->lineTo();
    }
    SkPoint result = pt->fPt;
    if (fFirstPtT && result != fFirstPtT->fPt && fFirstPtT->contains(pt)) {
        result = fFirstPtT->fPt;  // 使用第一个点的坐标，避免浮点误差
    }
    fDefer[0] = fDefer[1] = pt;
    return result;
}
```

这个方法在添加曲线时被调用，确保：
1. 延迟的操作被执行
2. 如果终点与起点重合，使用起点坐标（保证精确闭合）
3. 更新延迟状态

### 部分轮廓组装算法

`assemble()` 方法实现了复杂的轮廓连接算法：

**第一阶段：延长部分轮廓**
```cpp
for (int pIndex = 0; pIndex < endCount; pIndex++) {
    SkOpPtT* opPtT = const_cast<SkOpPtT*>(runs[pIndex]);
    // 检查端点是否可以沿着简单段继续延伸
    const SkOpSegment* nextSegment = opSegment->isSimple(&start, &step);
    if (nextSegment) {
        nextSegment->addCurveTo(start, opSpanEnd, &partWriter);
    }
}
```

**第二阶段：计算距离矩阵**
```cpp
for (rIndex = 0; rIndex < endCount - 1; ++rIndex) {
    for (iIndex = rIndex + 1; iIndex < endCount; ++iIndex) {
        double dx = iPtT->fPt.fX - oPtT->fPt.fX;
        double dy = iPtT->fPt.fY - oPtT->fPt.fY;
        double dist = dx * dx + dy * dy;
        distances.push_back(dist);
    }
}
```

**第三阶段：排序并匹配端点**
```cpp
SkTQSort<int>(sortedDist.begin(), sortedDist.end(), DistanceLessThan(distances.begin()));
```
按距离从小到大排序，优先连接距离最近的端点。

**第四阶段：构建连接图**
```cpp
bool flip = endOne == endTwo;
linkOne[ndxOne] = flip ? ~ndxTwo : ndxTwo;
linkTwo[ndxTwo] = flip ? ~ndxOne : ndxOne;
```
使用负数表示需要反转的连接。

**第五阶段：遍历连接图生成路径**
```cpp
do {
    SkPath contour = fPartials[rIndex].snapshot();
    if (forward) {
        fBuilder.addPath(contour, SkPath::kExtend_AddPathMode);
    } else {
        SkPathPriv::ReversePathTo(&fBuilder, contour);
    }
} while (true);
```

## 依赖关系

**直接依赖:**
```cpp
#include "include/core/SkPath.h"
#include "include/core/SkPathBuilder.h"
#include "src/pathops/SkOpSegment.h"
#include "src/pathops/SkOpSpan.h"
#include "src/pathops/SkPathOpsTypes.h"
#include "src/core/SkPathPriv.h"
#include "src/base/SkTSort.h"
```

**被依赖:**
- `SkOpBuilder` - 路径操作构建器
- `SkOpSegment` - 通过 `addCurveTo()` 调用
- PathOps 的各种算法实现

## 设计模式与设计决策

### 1. 延迟执行模式
通过缓冲操作避免生成退化几何，这是一种性能优化和质量保证的设计：
- 减少路径中的冗余点
- 避免数值精度问题导致的微小线段
- 提高后续渲染性能

### 2. 两阶段构建
将路径构建分为两个阶段：
- **构建阶段**：收集轮廓到 `fPartials` 和 `fBuilder`
- **组装阶段**：连接部分轮廓

这种分离简化了算法实现，每个阶段专注于特定任务。

### 3. 图论算法
使用图论的思想处理轮廓连接：
- 轮廓端点作为图的节点
- 端点之间的距离作为边的权重
- 通过贪心算法找到最优连接方案

### 4. 原地修改优化
```cpp
SkOpPtT* opPtT = const_cast<SkOpPtT*>(runs[pIndex]);
```
虽然使用了 `const_cast`，但这是经过仔细考虑的优化，避免了数据复制。

## 性能考量

### 1. 内存预分配
```cpp
STArray<8, double, true> distances(entries);
STArray<8, int, true> sortedDist(entries);
```
使用栈上数组（小于8个元素时）避免堆分配，提高小规模路径的性能。

### 2. 距离平方比较
```cpp
double dist = dx * dx + dy * dy;  // 不计算平方根
```
距离比较只需要平方值，避免昂贵的平方根运算。

### 3. 排序优化
使用自定义比较器和 `SkTQSort` 快速排序算法，针对小数组进行了优化。

### 4. 早期退出
```cpp
if (!--remaining) {
    break;
}
```
一旦所有端点都被配对，立即退出循环。

### 5. 路径构建器复用
使用 `SkPathBuilder` 而非 `SkPath`，避免多次重新分配内存。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/pathops/SkOpSegment.h` | 路径段表示 | 提供曲线数据源 |
| `src/pathops/SkOpSpan.h` | 路径段上的关键点 | 提供点和参数信息 |
| `include/core/SkPathBuilder.h` | 路径构建器 | 用于构建输出路径 |
| `include/core/SkPath.h` | 路径对象 | 最终输出类型 |
| `src/core/SkPathPriv.h` | 路径私有接口 | 提供路径反转等功能 |
| `src/pathops/SkOpBuilder.cpp` | 路径操作构建器 | 主要调用者 |
| `src/pathops/SkPathOpsTypes.h` | 基础类型定义 | 提供精度控制 |
| `src/base/SkTSort.h` | 排序算法 | 用于距离排序 |
| `src/pathops/SkPathOpsSimplify.cpp` | 路径简化 | 使用路径写入器 |
| `src/pathops/SkPathOpsOp.cpp` | 路径操作实现 | 使用路径写入器 |
