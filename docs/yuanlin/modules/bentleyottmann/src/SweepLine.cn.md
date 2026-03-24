# SweepLine.cpp - Bentley-Ottmann 扫描线实现

> 源文件: `modules/bentleyottmann/src/SweepLine.cpp`

## 概述

`SweepLine.cpp` 实现了 Bentley-Ottmann 算法中的扫描线逻辑。扫描线维护了当前水平位置处与之相交的所有线段的有序序列。当事件队列驱动事件处理时，扫描线执行线段的删除和插入操作，并在插入时检查相邻线段是否产生新的交叉，将发现的交叉报告回事件队列。

## 架构位置

- **头文件**：`modules/bentleyottmann/include/SweepLine.h`
- **实现接口**：`SweepLineInterface`
- **调用者**：`EventQueue::handleNextEventPoint` 通过接口驱动
- **回调**：通过 `EventQueueInterface::addCrossing` 报告新交叉

## 主要类与结构体

无新类定义。实现 `SweepLine` 类的成员函数。

## 公共 API 函数

### `SweepLine::SweepLine()`
构造函数初始化：
- 创建左哨兵：x 极小值的垂直线段 `(-MAX, -MAX) -> (-MAX, MAX)`
- 创建右哨兵：x 极大值的垂直线段 `(MAX, -MAX) -> (MAX, MAX)`
- 预分配 8 个元素的容量
- 初始状态：`[左哨兵, 右哨兵]`

### `SweepLine::handleDeletions(Point eventPoint, const DeletionSegmentSet& removing)`
删除操作实现：
- 若删除集合为空：仅移除 lower 端点等于事件点的线段（自然结束的线段）
- 若删除集合非空：移除自然结束的线段和删除集合中的线段（交叉需要交换的线段）
- 使用 `std::remove_if` + `erase` 惯用法

### `SweepLine::handleInsertionsAndCheckForNewCrossings(Point, const InsertionSegmentSet&, EventQueueInterface*)`
插入和交叉检测实现（见内部实现细节）。

## 内部实现细节

### 插入点查找
```cpp
auto comp = [](const Segment& s, Point p) {
    return !point_less_than_segment_in_x(p, s);
};
const auto rightOfInsertion = std::lower_bound(
        fSweepLine.begin(), fSweepLine.end(), eventPoint, comp);
const auto leftOfInsertion = rightOfInsertion - 1;
```
使用 `std::lower_bound` 和自定义比较器找到事件点在扫描线中的位置。`rightOfInsertion` 指向第一个在事件点右侧的线段。

### 无插入时的交叉检测
当只有删除没有插入时，删除点两侧的线段成为新的邻居。检查它们是否相交：
```cpp
if (auto crossingPoint = intersect(*leftOfInsertion, *rightOfInsertion)) {
    queue->addCrossing(crossingPoint.value(), *leftOfInsertion, *rightOfInsertion);
}
```

### 有插入时的交叉检测
插入新线段时：
1. 检查最左插入线段与其左邻居的交叉
2. 检查最右插入线段与其右邻居的交叉
3. 不检查插入线段之间的交叉（它们共享同一事件点，由 InsertionSegmentSet 的斜率排序保证正确位置）

### 哨兵的作用
左右哨兵确保 `leftOfInsertion` 和 `rightOfInsertion` 始终有效，无需特判扫描线为空或在端点处的情况。哨兵的 x 坐标为极值，永远不会与正常线段产生真正的交叉。

### verify 方法
调试辅助方法，遍历扫描线验证相邻线段在给定 y 处的顺序是否正确（`less_than_at`）。

## 依赖关系

- `modules/bentleyottmann/include/SweepLine.h` - 头文件
- `include/private/base/SkAssert.h` - 断言
- `modules/bentleyottmann/include/EventQueueInterface.h` - 接口
- `modules/bentleyottmann/include/Point.h` - 点类型
- `<algorithm>`, `<iterator>`, `<limits>`, `<optional>`, `<set>` - 标准库

## 设计模式与设计决策

### 哨兵模式
左右哨兵线段消除了所有边界条件，使核心逻辑更简洁。哨兵是跨越整个 y 范围的垂直线段，确保在任何 y 位置都有效。

### 线性扫描删除
使用 `std::remove_if` 进行线性扫描删除，虽然单次操作 O(n)，但在实践中扫描线中的线段数量通常不大。

### 二分查找插入
使用 `std::lower_bound` 进行 O(log n) 的插入位置查找，配合 `std::vector::insert` 完成插入。

### 仅检查新邻居对
只检查插入/删除操作产生的新邻居对是否交叉，而非检查所有线段对。这是 Bentley-Ottmann 算法效率的关键。

## 性能考量

- `std::vector` 的缓存局部性优于链表或树结构
- 预分配 8 个元素减少小规模场景的重新分配
- 删除操作使用 `remove_if` + `erase` 是 vector 中删除元素的标准高效方法
- 插入操作涉及元素移动，最坏情况 O(n)，但平均情况因 lower_bound 的 O(log n) 查找而较好
- 对于大量线段的场景，平衡树（如 `std::set`）可能更高效，但 vector 在中小规模时胜出

## 相关文件

- `modules/bentleyottmann/include/SweepLine.h` - 头文件
- `modules/bentleyottmann/src/EventQueue.cpp` - 事件队列实现
- `modules/bentleyottmann/src/Segment.cpp` - 线段比较函数
- `modules/bentleyottmann/include/EventQueueInterface.h` - 接口定义
