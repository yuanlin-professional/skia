# SkPathOpsTSect - T-区间细分求交算法

> 源文件：[src/pathops/SkPathOpsTSect.h](../../../../src/pathops/SkPathOpsTSect.h)、[src/pathops/SkPathOpsTSect.cpp](../../../../src/pathops/SkPathOpsTSect.cpp)

## 概述

`SkPathOpsTSect` 实现了 T-区间细分（T-Sect）算法，这是 Skia 路径操作模块中用于精确求解两条任意曲线交点的核心算法。该算法通过递归地将两条曲线的参数区间一分为二，利用凸包（hull）相交测试快速排除不相交的区间对，最终收敛到精确的交点位置。该文件定义了三个核心类：`SkTCoincident`（重合信息）、`SkTSpan`（参数区间/跨度）和 `SkTSect`（区间集合管理器）。

## 架构位置

```
PathOps 交叉检测层
  ├── SkIntersections (交点存储与查询接口)
  │     ↑ 结果写入
  ├── SkPathOpsTSect (T-区间细分求交) ← 本文件
  │     ├── SkTSect (管理一条曲线的所有区间)
  │     ├── SkTSpan (单个参数区间)
  │     └── SkTCoincident (重合判定信息)
  └── SkTCurve (多态曲线接口)
```

`SkPathOpsTSect` 是 `SkIntersections::intersect(SkDQuad, SkDQuad)` 等高阶曲线交叉方法的底层实现。当两条曲线都是非线性时（quad-quad、conic-cubic 等），使用此算法。

## 主要类与结构体

### `SkTCoincident`
存储跨度的重合信息。

**成员变量：**
- `fPerpPt`：垂足点坐标。
- `fPerpT`：对手曲线上垂足对应的参数 t 值（-1 表示未计算）。
- `fMatch`：是否标记为重合。

**方法：**
- `setPerp(c1, t, cPt, c2)`：从曲线 c1 上的点向曲线 c2 计算垂线交点。
- `markCoincident()`：标记为重合。

### `SkTSpan`
表示一条曲线的参数区间 [startT, endT] 及其相关几何信息。

**关键成员：**
- `fPart`：`SkTCurve*` 子曲线的多态表示。
- `fBounds`：`SkDRect` 区间的边界框。
- `fBounded`：`SkTSpanBounded*` 链表，记录与此区间相交的对手区间。
- `fStartT` / `fEndT`：参数区间范围。
- `fBoundsMax`：边界框最大维度。
- `fCoinStart` / `fCoinEnd`：起止点的重合信息。
- `fIsLinear` / `fIsLine`：线性标记。
- `fPrev` / `fNext`：双向链表。

**关键方法：**
- `hullsIntersect(span, start, oppStart)`：凸包相交测试。
- `linearsIntersect(span)`：线性化后的直线交叉测试。
- `split(work, heap)` / `splitAt(work, t, heap)`：在指定 t 值处分割区间。
- `initBounds(curve)`：初始化子曲线和边界框。
- `addBounded(span, alloc)` / `removeBounded(opp)`：管理关联的对手区间。
- `onlyEndPointsInCommon(opp, ...)`：检查两个区间是否只在端点处相交。

### `SkTSpanBounded`
简单的链表节点，将 `SkTSpan` 链接到其配对的对手区间列表中。

### `SkTSect`
管理一条曲线上所有参数区间的集合。

**关键成员：**
- `fCurve`：`const SkTCurve&` 原始曲线引用。
- `fHeap`：`SkSTArenaAlloc<1024>` 区间节点的内存分配器。
- `fHead`：活跃区间链表头。
- `fCoincident`：重合区间链表。
- `fDeleted`：已删除区间的回收链表。
- `fActiveCount`：活跃区间数量。

**关键方法：**
- `BinarySearch(sect1, sect2, intersections)`：核心静态方法，执行完整的二分搜索求交。
- `coincidentCheck(sect2)`：检测重合段。
- `computePerpendiculars(sect2, first, last)`：计算垂线用于重合判定。
- `extractCoincident(sect2, first, last, result)`：提取重合段。
- `intersects(span, opp, oppSpan, oppResult)`：单个区间对的交叉测试。
- `trim(span, opp)`：裁剪不相交的区间。
- `removeSpan(span)` / `removeSpans(span, opp)`：移除区间。
- `EndsEqual(sect1, sect2, intersections)`：检查端点处的交叉。

## 公共 API 函数

### `SkTSect::BinarySearch(sect1, sect2, intersections)`
核心入口点。算法流程：
1. 初始化两个 `SkTSect`，各包含一个覆盖 [0,1] 的初始区间。
2. 循环迭代：选择边界框最大的区间进行分割。
3. 分割后检查新区间与对手区间的凸包是否相交。
4. 移除不相交的区间对。
5. 当所有活跃区间足够小或检测到线性交叉/重合时终止。
6. 将结果写入 `SkIntersections`。

## 内部实现细节

### 区间管理策略
- 使用双向链表管理活跃区间，支持高效的中间插入和删除。
- 已删除区间放入 `fDeleted` 回收链表，可被 `addOne()` 重用，减少分配。
- 使用 `SkSTArenaAlloc<1024>` 作为局部分配器，适合区间数量适中的典型场景。

### 凸包交叉测试
`hullsIntersect()` 使用曲线的凸包（控制多边形）进行快速排除。如果两个区间的凸包不相交，则它们一定不相交，可以安全移除。如果凸包退化为线性，则标记为线性，后续使用直线交叉。

### 垂线重合检测
`computePerpendiculars()` 从一条曲线上的点向另一条曲线计算垂线。如果垂足距离在容差内，标记该区间端为重合。`extractCoincident()` 收集连续的重合区间。

### 端点枚举
`EndsEqual()` 使用位标志（kZeroS1Set/kOneS1Set/kZeroS2Set/kOneS2Set）跟踪哪些端点已经被检查，避免重复添加端点交叉。

## 依赖关系

- **SkTCurve**：多态曲线接口（`SkTQuad`、`SkTConic`、`SkTCubic`）。
- **SkDRect**：边界框用于快速排除。
- **SkDPoint / SkDVector**：几何运算。
- **SkIntersections**：结果输出。
- **SkArenaAlloc**：内存分配。
- **SkPathOpsTypes**：精度常量。

## 设计模式与设计决策

### 多态曲线接口
通过 `SkTCurve` 虚函数接口操作不同类型的曲线，使 T-区间算法可以统一处理所有曲线组合。

### 区间回收
已删除区间放入回收链表而非释放，减少 arena 分配器的压力，并改善缓存局部性。

### 分离的重合检测
重合检测与交点检测使用不同的策略：垂线投影用于重合，凸包裁剪用于交点。这是因为重合段需要连续的参数范围而非离散点。

## 性能考量

- **O(n log n) 期望复杂度**：二分搜索在每次迭代中将区间数翻倍但通过裁剪减半，期望迭代次数为对数级。
- **凸包快速排除**：大部分区间对在凸包测试阶段即被排除，避免昂贵的精确计算。
- **1024 字节栈分配器**：`SkSTArenaAlloc<1024>` 优先使用栈内存，对于典型的区间数量（几十个）通常不需要堆分配。
- **boundsMax 选择**：总是分割边界框最大的区间，确保收敛速度最优。

## 相关文件

- `src/pathops/SkPathOpsTSect.cpp`：算法实现。
- `src/pathops/SkPathOpsTCurve.h`：多态曲线基类。
- `src/pathops/SkIntersections.h`：交点存储。
- `src/pathops/SkPathOpsRect.h`：边界框。
- `src/pathops/SkPathOpsQuad.h` / `SkPathOpsConic.h` / `SkPathOpsCubic.h`：具体曲线类型。
