# SkOpAngle - 路径操作角度排序

> 源文件：[src/pathops/SkOpAngle.h](../../../../src/pathops/SkOpAngle.h)、[src/pathops/SkOpAngle.cpp](../../../../src/pathops/SkOpAngle.cpp)

## 概述

`SkOpAngle` 是 Skia 路径操作模块中的角度排序类。在路径布尔运算的关键步骤——确定交点处的缠绕数（winding number）和选择正确的输出路径——中，需要对从同一交点出发的所有曲线段按角度排序。`SkOpAngle` 表示从一个跨度到相邻跨度的曲线段方向，并提供了复杂的排序逻辑来处理各种退化和近似重合的情况。

## 架构位置

```
PathOps 拓扑层
  ├── SkOpAngle (角度排序) ← 本文件
  │     ├── 扇区分类 (32 等分圆)
  │     ├── 凸包重叠测试
  │     └── 端点交叉判断
  ├── SkOpSegment (持有角度引用)
  └── SkOpSpan (起止跨度)
```

`SkOpAngle` 在路径操作中用于缠绕数传播算法。每个交点处的角度形成一个循环链表，按逆时针排序。

## 主要类与结构体

### `SkOpAngle`

**关键成员变量：**
- `fOriginalCurvePart`：`SkDCurve`，从起点到终点的原始曲线部分。
- `fPart`：`SkDCurveSweep`，经过偏移调整的曲线部分及其扫掠向量。
- `fSide`：用于排序的侧面值。
- `fTangentHalf`：`SkLineParameters`，用于排序线段或线性段对。
- `fNext`：循环链表中的下一个角度。
- `fStart` / `fEnd`：起止跨度。
- `fSectorStart` / `fSectorEnd`：扇区索引（圆的 32 等分）。
- `fUnorderable`：标记为不可排序。
- `fTangentsAmbiguous`：切线方向不明确。
- `fCheckCoincidence`：需要检查重合。

**枚举 `IncludeType`：**
- `kUnaryWinding`：一元缠绕操作。
- `kUnaryXor`：一元异或操作。
- `kBinarySingle`：二元单侧操作。
- `kBinaryOpp`：二元对侧操作。

## 公共 API 函数

- `set(start, end)`：设置角度的起止跨度并计算几何信息。
- `insert(angle)`：将角度插入到循环链表中的正确位置。
- `next()`：返回链表中的下一个角度。
- `previous()`：返回链表中的上一个角度。
- `segment()`：返回所属段。
- `start()` / `end()`：返回起止跨度。
- `starter()`：返回较小 t 值的跨度。
- `loopContains(angle)`：检查循环链表中是否包含指定角度。
- `loopCount()`：返回链表中的角度数量。
- `lastMarked()` / `setLastMarked(marked)`：标记追踪。
- `unorderable()`：是否不可排序。
- `tangentsAmbiguous()`：切线是否不明确。
- `distEndRatio(dist)`：距离与端点间距的比值。

## 内部实现细节

### 排序算法
角度排序是 PathOps 中最复杂的算法之一，使用多级策略：

1. **扇区分类**：将圆分为 32 个扇区，基于曲线切线方向确定扇区。不同扇区的角度可以直接比较。
2. **凸包重叠**：对于同一扇区内的角度，检查凸包是否重叠来确定顺序。
3. **端点交叉测试**：通过计算曲线终点与另一条曲线的位置关系确定顺序。
4. **中点测试**：使用曲线中点和终点的内外关系进一步细化。
5. **平行线检查**：处理两条近似平行曲线的退化情况。
6. **切线发散测试**：检查两条曲线的切线是否发散以确定顺序。

### `orderable()` 方法
返回 -1（不可排序）、0（this < rh）或 1（this > rh）。这是排序的核心比较函数。

### 循环链表插入
`insert()` 方法遍历现有链表，使用 `after()` 比较函数找到正确的插入位置，确保链表始终按角度顺序排列。

### 扇区计算
`computeSector()` 和 `findSector()` 将曲线起始方向映射到 32 等分的扇区中。跨越零度线的角度需要特殊处理。

## 依赖关系

- **SkDCurve / SkDCurveSweep**：曲线几何和扫掠方向。
- **SkLineParameters**：线参数化用于切线比较。
- **SkOpSpanBase / SkOpSpan**：起止跨度。
- **SkOpSegment**：所属段。
- **SkPathOpsTypes**：精度比较。

## 设计模式与设计决策

### 循环链表
角度使用侵入式循环链表（通过 `fNext` 指针），反映了交点周围角度的循环拓扑结构。

### 多级排序策略
复杂的排序策略是为了处理各种退化情况（近似平行、近似重合、零长度段等），确保在任何输入下都能产生一致的排序结果。

### 扇区预分类
32 扇区的预分类大幅减少了需要执行昂贵比较的角度对数量。只有同一扇区内的角度才需要精细比较。

## 性能考量

- **扇区快速排除**：大多数角度对可以通过扇区比较直接确定顺序。
- **延迟计算**：扇区和几何信息仅在需要时计算。
- **O(n^2) 插入**：链表插入是 O(n)，总排序为 O(n^2)，但交点处的角度数量通常很少（2-8 个）。

## 相关文件

- `src/pathops/SkOpSegment.h`：段的角度计算和排序。
- `src/pathops/SkOpSpan.h`：跨度定义。
- `src/pathops/SkPathOpsCurve.h`：`SkDCurve` 和 `SkDCurveSweep`。
- `src/pathops/SkLineParameters.h`：线参数化。
