# SkOpContour - 路径操作轮廓管理

> 源文件：[src/pathops/SkOpContour.h](../../../../src/pathops/SkOpContour.h)、[src/pathops/SkOpContour.cpp](../../../../src/pathops/SkOpContour.cpp)

## 概述

`SkOpContour` 是 Skia 路径操作模块中表示单个闭合轮廓的核心类。一个轮廓由一系列有序的路径段（`SkOpSegment`）组成，形成一条闭合曲线。该文件还定义了 `SkOpContourHead`（轮廓链表头部管理）和 `SkOpContourBuilder`（轮廓构建器，处理输入简化和内存分配）。

## 架构位置

```
PathOps 数据结构层
  ├── SkOpContourHead (轮廓链表头)
  │     └── SkOpContour (单个轮廓) ← 本文件
  │           └── SkOpSegment (单个段 - 链表)
  │                 └── SkOpSpan (跨度 - 链表)
  │                       └── SkOpPtT (点-参数对)
  └── SkOpGlobalState (全局状态)
```

`SkOpContour` 是 PathOps 中间层数据结构，位于轮廓集合和段之间。它管理段链表的生命周期，协调角度计算、重合检测、缠绕数传播等操作在其包含的所有段上的执行。

## 主要类与结构体

### `SkOpContour`
单个轮廓的容器。

**关键成员变量：**
- `fHead`：首段（内联存储，避免堆分配）。
- `fTail`：尾段指针。
- `fNext`：下一个轮廓指针（构成轮廓链表）。
- `fState`：`SkOpGlobalState*` 全局状态。
- `fBounds`：`SkPathOpsBounds` 边界框。
- `fCount`：段数量。
- `fOperand`：是否为二元操作的第二个参数。
- `fXor` / `fOppXor`：原始/对手路径是否使用 even-odd 填充。
- `fCcw`：逆时针方向标记。
- `fReverse`：输出时是否反转方向。
- `fDone`：是否所有段都已处理完毕。

### `SkOpContourHead`
继承自 `SkOpContour`，作为轮廓链表的头节点，提供链表管理操作。

**方法：**
- `appendContour()`：在链表末尾追加新轮廓（通过 arena 分配器创建）。
- `joinAllSegments()`：对所有轮廓执行段连接操作。
- `remove(SkOpContour*)`：从链表中移除指定轮廓。

### `SkOpContourBuilder`
轮廓的构建辅助类，在添加曲线元素时进行简化处理。

**关键特性：**
- 延迟添加直线段（`fLastIsLine`、`fLastLine`），使得能够检测并消除方向完全相反的相邻线段对。
- 使用 `SkArenaAlloc` 为控制点数组分配内存。

## 公共 API 函数

### 段添加
- `addLine(SkPoint pts[2])`：添加直线段，断言两端点不重合。
- `addQuad(SkPoint pts[3])`：添加二次曲线段。
- `addConic(SkPoint pts[3], SkScalar weight)`：添加圆锥曲线段。
- `addCubic(SkPoint pts[4])`：添加三次曲线段。
- `appendSegment()`：分配并链入新的 `SkOpSegment`。第一个段使用内联的 `fHead`，后续段通过 arena 分配。

### 轮廓操作
- `calcAngles()`：对所有段计算角度。
- `sortAngles()`：对所有段排序角度。
- `joinSegments()`：连接相邻段的端点（循环到头部）。
- `missingCoincidence()`：检测缺失的重合段。
- `moveMultiples()`：移动多重交点使其挂载到正确的跨度上。
- `moveNearby()`：移动邻近的 t 值和点使其共享同一跨度。
- `markAllDone()`：标记所有段为已完成。

### 输出
- `toPath(SkPathWriter*)`：将轮廓正向写入路径，完成后调用 `finishContour` 和 `assemble`。
- `toReversePath(SkPathWriter*)`：反向写入路径。
- `toPartialForward/toPartialBackward`：部分正向/反向写入（不完成轮廓）。

### 查询
- `bounds()`：返回边界框。
- `start()` / `end()`：返回轮廓的起点和终点。
- `first()`：返回第一个段。
- `count()`：返回段数量。
- `done()`：是否已完成。
- `operand()`：是否为第二个操作数。
- `isXor()` / `oppXor()`：填充规则查询。
- `isCcw()`：逆时针方向查询。
- `reversed()`：是否需要反转输出。

### 射线检测
- `rayCheck(base, dir, hits, alloc)`：执行射线检测，用于缠绕数计算。

### 其他
- `init(globalState, operand, isXor)`：初始化轮廓的全局状态、操作数标志和填充规则。
- `complete()`：完成轮廓构建（计算边界框）。
- `setBounds()`：遍历所有段合并边界框。
- `undoneSpan()`：查找第一个未完成的跨度。
- `findSortableTop(SkOpContour*)`：查找可排序的顶部跨度。
- `operator<`：按边界框顶部（然后左侧）排序。

## 内部实现细节

### 段链表管理
`appendSegment()` 使用内联 `fHead` 作为第一个段（避免首次堆分配），后续段通过 `SkArenaAlloc` 分配。段之间通过 `prev/next` 指针形成双向链表。

### 反向线段消除
`SkOpContourBuilder::addLine` 检查新线段是否与上一条线段方向完全相反。如果是，两条线段都不添加（互相抵消）。这处理了路径中退化的来回线段。

### 路径输出
`toPath()` 正向遍历段链表，每段调用 `addCurveTo` 写入路径。`toReversePath()` 反向遍历，并交换每段的头尾参数，实现反向输出。

### 缺失重合检测
`missingCoincidence()` 委托给每个段的同名方法，检查是否存在应该被标记为重合但实际未标记的段对。

## 依赖关系

- **SkOpSegment**：段类，轮廓的核心组成单元。
- **SkOpSpan**：跨度类，段上的参数区间。
- **SkOpGlobalState**：全局状态，包含内存分配器和重合段管理。
- **SkPathOpsBounds**：边界框类型。
- **SkPathWriter**：路径输出工具。
- **SkArenaAlloc**：内存分配器，用于段和控制点的分配。
- **SkOpAngle / SkOpCoincidence**：角度和重合段相关操作。

## 设计模式与设计决策

### 内联首段
使用 `SkOpSegment fHead` 作为内联成员，避免单段轮廓（最常见的情况）的堆分配。后续段通过 arena 分配。这是一种常见的"小对象优化"。

### 链表 vs 数组
段使用链表而非数组存储，因为：
1. 段在构建过程中逐个添加，大小不可预测。
2. 不需要随机访问，操作主要是顺序遍历。
3. arena 分配器使链表节点的分配高效且连续。

### 延迟刷新构建器
`SkOpContourBuilder` 延迟添加直线段，直到遇到非直线段或显式刷新。这允许检测和消除退化的来回线段，简化了后续处理。

### 轮廓链表
多个轮廓通过 `fNext` 指针形成单向链表，由 `SkOpContourHead` 管理。这种设计简单且内存高效，适合轮廓数量不确定的场景。

## 性能考量

- **内联首段**：最常见的单段轮廓不需要额外的堆分配。
- **Arena 分配**：所有段和控制点通过 arena 分配器统一管理，避免频繁的 malloc/free。
- **边界框缓存**：边界框在 `complete()` 时一次计算并缓存，避免重复计算。
- **退化消除**：`SkOpContourBuilder` 在构建时消除退化线段，减少后续处理的工作量。

## 相关文件

- `src/pathops/SkOpSegment.h`：段定义。
- `src/pathops/SkOpSpan.h`：跨度定义。
- `src/pathops/SkPathOpsBounds.h`：边界框类型。
- `src/pathops/SkPathOpsTypes.h`：基础类型和辅助函数。
- `src/pathops/SkPathWriter.h`：路径输出工具。
- `src/base/SkArenaAlloc.h`：内存分配器。
