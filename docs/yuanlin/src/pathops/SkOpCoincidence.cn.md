# SkOpCoincidence - 路径操作重合段管理

> 源文件：[src/pathops/SkOpCoincidence.h](../../../../src/pathops/SkOpCoincidence.h)、[src/pathops/SkOpCoincidence.cpp](../../../../src/pathops/SkOpCoincidence.cpp)

## 概述

`SkOpCoincidence` 是 Skia 路径操作模块中管理重合段（coincident spans）的核心类。当两条不同的路径段在某个参数范围内重叠（即几何上重合）时，该类负责检测、记录、扩展、合并和标记这些重合关系。重合段的正确处理是路径布尔运算（交集、并集、差集等）产生正确结果的关键。

## 架构位置

```
PathOps 数据结构层
  ├── SkOpGlobalState (持有 SkOpCoincidence 实例)
  │     └── SkOpCoincidence (重合段管理) ← 本文件
  │           └── SkCoincidentSpans (单个重合段对 - 链表)
  ├── SkOpContour / SkOpSegment / SkOpSpan
  └── SkIntersections
```

`SkOpCoincidence` 由 `SkOpGlobalState` 持有，作为全局重合段注册表。在路径操作的多个阶段（交点添加、重合检测、缠绕数标记等）中被频繁访问和修改。

## 主要类与结构体

### `SkCoincidentSpans`
单个重合段对的记录。

**成员变量：**
- `fNext`：链表下一个节点。
- `fCoinPtTStart` / `fCoinPtTEnd`：主段的起止点-参数对。
- `fOppPtTStart` / `fOppPtTEnd`：对手段的起止点-参数对。

**关键方法：**
- `collapsed(test)`：检查重合段是否坍塌（起止点相同）。
- `contains(s, e)`：检查给定的参数范围是否在此重合段内。
- `expand()`：通过检查相邻跨度扩展重合范围。
- `extend()`：将给定范围合并到此重合段中。
- `correctEnds()`：修正端点引用，使其与段的跨度定义一致。
- `flipped()`：检查对手段的 t 方向是否与主段相反。
- `ordered(result)`：检查重合段内的 t 值是否有序。
- `set()`：设置完整的重合段参数。

### `SkOpCoincidence`
重合段的全局管理器。

**成员变量：**
- `fHead`：主重合段链表头。
- `fTop`：临时链表头（处理过程中使用）。
- `fGlobalState`：全局状态引用。
- `fContinue`：标记是否需要继续处理。
- `fSpanDeleted` / `fPtAllocated` / `fCoinExtended` / `fSpanMerged`：各种处理状态标志。

## 公共 API 函数

### 重合段添加
- `add(coinPtTStart, coinPtTEnd, oppPtTStart, oppPtTEnd)`：添加新的重合段对。自动确保正确的排序顺序，规范化 PtT 引用，通过 arena 分配存储。
- `addEndMovedSpans()`：检测端点移动后产生的新重合段。处理 A-B 重合但 B 端点处有隐含连接线可能与其他曲线重合的情况。
- `addExpanded()`：为每个重合段对匹配跨度。当跨度不匹配时，将缺失的点添加到段中。
- `addMissing(bool* added)`：添加缺失的重合段。扫描所有重合段对的重叠区域。

### 重合段处理
- `expand()`：对所有重合段调用 `SkCoincidentSpans::expand()`，检查相邻跨度是否也重合。
- `extend(coinPtTStart, coinPtTEnd, oppPtTStart, oppPtTEnd)`：如果已有重叠的重合段对，扩展其范围。
- `mark()`：标记重合段的缠绕值和对手值。这是将重合信息传播到缠绕数系统的关键步骤。
- `apply()`：应用重合标记的最终步骤。
- `correctEnds()`：修正所有重合段的端点引用。

### 查询
- `contains(coinPtTStart, coinPtTEnd, oppPtTStart, oppPtTEnd)`：检查指定的重合段对是否已存在。
- `isEmpty()`：检查是否没有重合段。
- `findOverlaps()`：查找重合段之间的重叠区域。

### 维护
- `fixUp(deleted, kept)`：当一个 PtT 被删除时，更新所有引用它的重合段。
- `markCollapsed(ptT)`：标记坍塌的重合段。
- `release(segment)`：释放与指定段关联的重合段。
- `releaseDeleted()`：清理已删除的重合段。

### 排序
- `Ordered(coinPtTStart, oppPtTStart)`：确定两个段的标准顺序。
- `Ordered(coin, opp)`：基于段指针确定顺序。

## 内部实现细节

### 两级链表结构
`SkOpCoincidence` 使用两个链表头 `fHead` 和 `fTop` 管理重合段。在 `addEndMovedSpans` 处理过程中，`fHead` 的内容临时移到 `fTop`，新发现的重合段添加到 `fHead`。处理完成后通过 `restoreHead()` 合并两个链表。这避免了在遍历链表时修改它。

### 端点移动检测算法
`addEndMovedSpans` 处理一种微妙的重合情况：当 A 与 B 在一个范围内重合，但 B 的端点处 A 的对应点不是端点（存在一条隐含的连接线），该隐含线可能与相邻曲线重合。算法通过垂线射线交叉检测这些额外的重合关系。

### 跨度匹配（addExpanded）
对每个重合段对同步遍历两段的跨度。当一段有跨度但另一段没有对应跨度时，使用 t 值比例估算缺失跨度的位置，然后在对应段上添加新的 t 值。这确保了两个重合段的跨度一一对应。

### 排序规范
通过 `Ordered()` 确保重合段对总是以确定的顺序存储，避免重复添加和查找时的顺序混乱。

### 逃生舱门
`addEndMovedSpans` 使用 `escapeHatch` 计数器（100000 次迭代上限）防止模糊测试生成的极端输入导致的无限循环。

## 依赖关系

- **SkOpSpan / SkOpPtT**：跨度和点-参数对，重合段的基本构建块。
- **SkOpSegment**：路径段，重合段的载体。
- **SkOpGlobalState**：全局状态和 arena 分配器。
- **SkIntersections**：在 `addEndMovedSpans` 中用于射线交叉。
- **SkPathOpsCurve**：`CurveIntersectRay` 函数指针表。
- **SkArenaAlloc**：重合段节点的内存分配。

## 设计模式与设计决策

### 侵入式链表
使用侵入式单向链表（每个 `SkCoincidentSpans` 有 `fNext` 指针）管理重合段集合。相比标准容器，这避免了额外的内存分配（节点本身已通过 arena 分配）。

### 成员指针（已弃用模式）
`correctOneEnd` 使用 C++ 成员函数指针来参数化 getter/setter 对，代码注释中标注该模式已不受推荐，未来可能替换为其他方法。

### 多阶段处理
重合段的处理分为多个明确的阶段（correctEnds -> expand -> addExpanded -> addEndMovedSpans -> addMissing -> mark -> apply），每个阶段都有对应的 `DEBUG_SET_PHASE` 调用用于调试跟踪。

### 保守失败
大量使用 `FAIL_IF` 宏在遇到意外状态时安全返回 false，而不是崩溃。这对于处理模糊测试生成的极端输入尤为重要。

## 性能考量

- **Arena 分配**：所有 `SkCoincidentSpans` 节点通过 arena 分配器创建，避免频繁的堆分配。
- **PtT 规范化**：在添加时将 PtT 规范化为跨度链表的头部，减少后续遍历。
- **提前退出**：`contains` 等查询方法在找到匹配后立即返回。
- **逃生舱门**：防止极端输入导致的长时间计算。

## 相关文件

- `src/pathops/SkOpSpan.h`：`SkOpPtT` 和 `SkOpSpan` 定义。
- `src/pathops/SkOpSegment.h`：段操作。
- `src/pathops/SkPathOpsTypes.h`：基础类型和辅助函数。
- `src/pathops/SkPathOpsCurve.h`：曲线函数指针分发表。
- `src/pathops/SkPathOpsDebug.h`：调试版本的重合段检查方法。
