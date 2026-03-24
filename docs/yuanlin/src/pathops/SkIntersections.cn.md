# SkIntersections - 路径操作交点计算

> 源文件：[src/pathops/SkIntersections.h](../../../../src/pathops/SkIntersections.h)、[src/pathops/SkIntersections.cpp](../../../../src/pathops/SkIntersections.cpp)

## 概述

`SkIntersections` 是 Skia 路径操作（PathOps）模块中的核心类，负责计算两条曲线之间的交点。它支持直线、二次曲线（Quad）、圆锥曲线（Conic）和三次曲线（Cubic）之间的所有组合交叉检测，同时支持与水平线和垂直线的交点计算。该类不仅存储交点坐标，还维护参数 t 值、重合段标记和近似相等标记等丰富的交点元数据。

## 架构位置

```
PathOps 模块
  ├── 曲线类型 (SkDLine, SkDQuad, SkDConic, SkDCubic)
  ├── SkIntersections (交点计算与存储)
  ├── SkOpSegment (路径段管理)
  ├── SkOpContour (轮廓管理)
  └── SkPathOps (公共 API)
```

`SkIntersections` 位于 PathOps 模块的底层计算层，作为曲线交点检测的统一接口。上层的 `SkAddIntersections` 和 `SkOpSegment` 调用该类来确定路径段之间的交叉关系。

## 主要类与结构体

### `SkIntersections`
交点计算与存储的主要类。

**关键成员变量：**
- `fPt[13]`：存储交点坐标的数组，最多可容纳 13 个交点（三次曲线间的理论最大值加上余量）。
- `fPt2[2]`：存储"近似相同"交点的替代坐标。
- `fT[2][13]`：两条曲线上交点对应的参数 t 值。`fT[0]` 存储第一条曲线的参数，`fT[1]` 存储第二条曲线的参数。
- `fIsCoincident[2]`：位标记数组，标识每个交点是否属于重合段。
- `fNearlySame[2]`：标记端点是否近似匹配。
- `fUsed`：当前存储的交点数量。
- `fMax`：允许的最大交点数，由调用者根据曲线类型设置。
- `fSwap`：交换标志，用于统一不同顺序的曲线对。
- `fAllowNear`：是否允许近似交点。

### `SkIntersections::TArray`
内部辅助类，提供对 t 值数组的只读访问。通过 `operator[]` 实现双层索引：`intersections[curveIndex][pointIndex]`。

## 公共 API 函数

### 曲线与水平/垂直线交叉
- `lineHorizontal` / `lineVertical`：直线与水平/垂直扫描线的交点。
- `quadHorizontal` / `quadVertical`：二次曲线与水平/垂直扫描线的交点。
- `conicHorizontal` / `conicVertical`：圆锥曲线与水平/垂直扫描线的交点。
- `cubicHorizontal` / `cubicVertical`：三次曲线与水平/垂直扫描线的交点。

### 曲线与直线交叉
- `lineLine`：两条直线的交点（最多 2 个，含重合线段端点）。
- `quadLine`：二次曲线与直线的交点。
- `conicLine`：圆锥曲线与直线的交点（最多 3 个，允许小重合段）。
- `cubicLine`：三次曲线与直线的交点（最多 3 个）。

### 曲线间交叉
- `intersect(SkDLine, SkDLine)`：直线-直线交叉。
- `intersect(SkDQuad, SkDLine)` 到 `intersect(SkDCubic, SkDCubic)`：所有曲线类型组合的交叉计算。
- `intersectRay`：射线交叉，允许 t 值超出 [0,1] 范围。

### 交点管理
- `insert(double one, double two, const SkDPoint& pt)`：插入新交点，保持 t 值排序。自动去重并处理近似相等的交点。
- `insertNear`：插入近似交点，记录两个略有不同的坐标。
- `insertCoincident`：插入重合交点并设置重合标记。
- `insertSwap`：根据交换标志决定参数顺序后插入。
- `removeOne(int index)`：移除指定索引的交点，维护位标记的一致性。
- `merge`：合并来自两个 `SkIntersections` 的单个交点。

### 查询函数
- `closestTo`：在指定 t 值范围内找到离目标点最近的交点。
- `mostOutside`：在指定范围内找到相对于原点最外侧的交点（通过叉积判断）。
- `hasT` / `hasOppT`：检查是否存在 t=0 或 t=1 的端点交叉。
- `used()`：返回当前交点数量。
- `nearlySame(int index)`：查询指定端是否近似匹配。
- `isCoincident(int index)`：查询指定交点是否为重合点。

### 状态管理
- `reset()`：重置交点数据，保留 swap 和 max 设置。
- `flip()`：翻转第二条曲线的所有 t 值（`t = 1 - t`）。
- `swap()`：切换交换标志。
- `setMax(int max)`：设置最大交点数上限。
- `allowNear(bool)`：控制是否接受近似交点。

## 内部实现细节

### 交点插入算法
`insert()` 方法是最核心的内部操作。其步骤如下：
1. 检查是否在重合段内部插入非重合交点（不允许）。
2. 遍历现有交点，检测精确或近似重复。如果发现近似重复，移除旧交点并重新插入更精确的版本。
3. 通过二分查找找到正确的插入位置（保持 `fT[0]` 排序）。
4. 使用 `memmove` 移动后续元素，同时通过位运算更新重合标记的位偏移。

### 重合标记位运算
重合标记使用 `uint16_t` 位图，每个位对应一个交点。插入/删除交点时需要移位操作来维护位图的一致性。`clearMask` 计算确保只有受影响的位被移动。

### 近似交点处理
`insertNear()` 处理端点（t=0 或 t=1）附近两条曲线不完全相交但非常接近的情况。它在 `fPt2` 中存储替代坐标，供后续处理时选择更合适的点。

### 射线交叉
`intersectRay` 系列方法与普通 `intersect` 的区别在于不限制 t 值在 [0,1] 范围内，允许计算曲线延长线上的交点，用于确定缠绕数（winding number）。

## 依赖关系

- **SkDLine / SkDQuad / SkDConic / SkDCubic**：各种曲线类型的数学表示。
- **SkDPoint / SkDVector**：双精度点和向量。
- **SkDRect**：双精度矩形，用于边界框检测。
- **SkPathOpsTypes**：路径操作的基础类型和精度常量（`BUMP_EPSILON`、`more_roughly_equal`、`precisely_equal` 等）。
- **SkPathOpsDebug**：调试支持。
- **SkTCurve**：曲线的多态接口，支持 `intersectRay` 虚函数分发。

## 设计模式与设计决策

### 固定大小数组
使用固定大小的数组（13 个交点）而非动态分配，因为曲线交点数有理论上限，且该类在路径操作中被频繁创建和销毁，避免堆分配带来的开销。

### 参数 t 值排序
保持 `fT[0]` 数组始终排序，使得范围查询和重复检测更高效。这是一个设计不变量，由 `insert()` 方法维护。

### 交换机制
`fSwap` 标志使得两条曲线的顺序对调用者透明。当交叉计算需要颠倒曲线顺序时（如从 `intersect(A, B)` 内部调用子程序），`insertSwap` 自动将参数放到正确的位置。

### 重合段的位图表示
使用 `uint16_t` 位图表示重合性，既节省空间又允许高效的按位操作。但这限制了最大交点数不超过 16 个（实际上 13 足够）。

## 性能考量

- **零堆分配**：所有数据存储在栈上的固定大小数组中，避免动态内存分配。
- **memmove 操作**：插入和删除交点使用 `memmove` 进行批量内存移动，比逐元素操作更快。
- **提前去重**：在插入时即检测重复，避免后续处理中出现冗余交点。
- **调试开销隔离**：大量调试代码通过 `#ifdef SK_DEBUG` 和 `DEBUG_T_SECT_LOOP_COUNT` 宏隔离，不影响发布版本性能。

## 相关文件

- `src/pathops/SkPathOpsLine.h`：直线交叉的具体实现。
- `src/pathops/SkPathOpsQuad.h`：二次曲线交叉。
- `src/pathops/SkPathOpsConic.h`：圆锥曲线交叉。
- `src/pathops/SkPathOpsCubic.h`：三次曲线交叉。
- `src/pathops/SkPathOpsTSect.h`：T-区间细分求交算法。
- `src/pathops/SkAddIntersections.h`：将交点添加到路径段中。
- `src/pathops/SkPathOpsTypes.h`：精度常量和辅助函数。
