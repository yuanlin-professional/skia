# SkOpSegment - 路径操作段管理

> 源文件：[src/pathops/SkOpSegment.h](../../../../src/pathops/SkOpSegment.h)、[src/pathops/SkOpSegment.cpp](../../../../src/pathops/SkOpSegment.cpp)

## 概述

`SkOpSegment` 是 Skia 路径操作模块中最核心的数据结构之一，表示一条路径段（直线、二次曲线、圆锥曲线或三次曲线）。每个段管理其上的所有交点（通过跨度链表）、角度信息和缠绕值。段负责交点添加、角度计算、缠绕数传播、曲线输出等关键操作，是路径布尔运算的中枢。

## 架构位置

```
PathOps 核心数据结构
  ├── SkOpContour (轮廓 - 段的容器)
  │     └── SkOpSegment (段) ← 本文件
  │           ├── SkOpSpan (跨度 - 交点间的区间)
  │           │     └── SkOpPtT (点-参数对)
  │           └── SkOpAngle (角度 - 用于排序)
  └── SkOpGlobalState / SkOpCoincidence
```

`SkOpSegment` 是连接轮廓结构和交叉检测结果的桥梁。交叉检测产生的交点被添加到段的跨度链表中，随后段的角度排序和缠绕数传播决定了最终的布尔运算结果。

## 主要类与结构体

### `SkOpSegment`

**关键成员：**
- `fHead` / `fTail`：首尾跨度（内联存储）。
- `fPts`：控制点数组指针。
- `fWeight`：圆锥曲线权重。
- `fVerb`：曲线类型（`SkPath::Verb`）。
- `fBounds`：`SkPathOpsBounds` 边界框。
- `fContour`：所属轮廓。
- `fCount`：跨度数量。
- `fDoneCount`：已完成的跨度数量。
- `fPrev` / `fNext`：段链表指针。

## 公共 API 函数

### 段创建
- `addLine/addQuad/addConic/addCubic`：添加不同类型的段，初始化控制点和边界框。

### 交点管理
- `addT(double t)`：在参数 t 处添加新的跨度。如果 t 已存在则返回现有 PtT。
- `addT(double t, const SkPoint& pt)`：带显式坐标的添加。
- `addMissing(t, opp, allExist)`：添加对手段上缺失的交点。
- `addExpanded(newT, test, startOver)`：添加扩展的交点。

### 角度计算与排序
- `calcAngles()`：为所有交点处创建角度对象。
- `addStartSpan()` / `addEndSpan()`：创建起点和终点的角度。
- `sortAngles()`：对所有角度进行排序。
- `computeSum(start, end, includeType)`：计算缠绕数总和。

### 缠绕数与路径操作
- `activeOp(start, end, xorMiMask, xorSuMask, op)`：确定段在给定操作中是否活跃。
- `activeWinding(start, end)`：确定段在简化操作中是否活跃。
- `ComputeOneSum/ComputeOneSumReverse`：计算单个角度的缠绕数。

### 段查询
- `bounds()`：返回边界框。
- `verb()`：返回曲线类型。
- `pts()`：返回控制点。
- `weight()`：返回权重。
- `contour()`：返回所属轮廓。
- `done()`：是否所有跨度都已完成。
- `head()` / `tail()`：首尾跨度。
- `contains(double t)`：是否包含参数 t 的跨度。

### 重合与近似匹配
- `missingCoincidence()`：检测缺失的重合段。
- `moveMultiples()`：移动多重交点。
- `moveNearby()`：合并邻近的跨度。
- `isClose(midT, oppSeg)`：检查中点处是否与对手段接近。
- `testForCoincidence(...)`：测试是否重合。

### 路径输出
- `addCurveTo(start, end, path)`：将段的子曲线写入路径。
- `subDivide(start, end, curve)`：提取子曲线。

### 几何查询
- `dPtAtT(double t)`：双精度点求值。
- `ptAtT(double t)`：单精度点求值。
- `dSlopeAtT(double t)`：双精度斜率求值。
- `collapsed(startT, endT)`：检查区间是否坍塌。

## 内部实现细节

### 跨度链表
段使用双向链表管理跨度。`fHead` 和 `fTail` 分别对应 t=0 和 t=1 的端点跨度。中间跨度按 t 值排序插入。每个跨度维护缠绕值（windValue/oppValue）和完成状态。

### 角度创建
`calcAngles()` 遍历所有跨度，在有两条以上出入边的交叉点处创建角度对象。角度对象保存从一个跨度到相邻跨度的曲线方向信息。

### 缠绕数传播
`computeSum()` 沿角度环遍历，累加缠绕值。这实现了扫描线算法中的缠绕数传播，决定哪些区域在布尔运算结果的内部。

### 路径输出
`addCurveTo()` 将段的一部分（从 start 到 end 跨度）写入 `SkPathWriter`。它从控制点和参数范围重建子曲线。

## 依赖关系

- **SkOpSpan / SkOpPtT**：跨度和点-参数对。
- **SkOpAngle**：角度排序。
- **SkOpContour**：所属轮廓。
- **SkDCurve / SkPathOpsCurve**：曲线数学运算。
- **SkPathOpsBounds**：边界框。
- **SkPathWriter**：路径输出。
- **SkArenaAlloc**：内存分配。

## 设计模式与设计决策

### 内联首尾跨度
`fHead` 和 `fTail` 作为内联成员，避免了最常见的两端点跨度的堆分配。

### 延迟角度计算
角度仅在所有交点添加完毕后才计算（`calcAngles`），避免了中间状态的不一致。

### 段间链表
段通过 `fPrev`/`fNext` 指针形成双向链表，支持正向和反向遍历（用于正向/反向路径输出）。

## 性能考量

- **内联存储**：首尾跨度和边界框内联存储，减少内存间接访问。
- **排序延迟**：将角度排序推迟到所有交点就绪后批量执行。
- **快速完成检查**：`fDoneCount == fCount` 快速判断段是否全部完成。

## 相关文件

- `src/pathops/SkOpSpan.h`：跨度和 PtT 定义。
- `src/pathops/SkOpAngle.h`：角度定义。
- `src/pathops/SkOpContour.h`：轮廓定义。
- `src/pathops/SkPathOpsCurve.h`：曲线函数。
- `src/pathops/SkPathWriter.h`：路径输出。
