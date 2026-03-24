# EventQueueInterface.h - 事件队列与扫描线接口定义

> 源文件: `modules/bentleyottmann/include/EventQueueInterface.h`

## 概述

`EventQueueInterface.h` 定义了 Bentley-Ottmann 算法中事件队列与扫描线之间的抽象接口。通过将 `EventQueueInterface` 和 `SweepLineInterface` 分离，使得事件队列和扫描线可以独立测试。该文件还定义了删除集合（`DeletionSegmentSet`）和插入集合（`InsertionSegmentSet`）的类型别名以及按斜率排序的比较器。

## 架构位置

该文件是 Bentley-Ottmann 算法模块中的接口层，位于事件队列和扫描线之间：

- **实现者**：`EventQueue` 实现 `EventQueueInterface`；`SweepLine` 实现 `SweepLineInterface`
- **解耦作用**：使事件队列和扫描线互不直接依赖，便于单元测试
- **被依赖**：`EventQueue.h`、`SweepLine.h` 均包含此头文件

## 主要类与结构体

### `EventQueueInterface`
```cpp
class EventQueueInterface {
public:
    virtual void addCrossing(Point crossingPoint, const Segment& s0, const Segment& s1) = 0;
};
```
- 纯虚接口，定义了向事件队列添加交叉事件的能力
- 提供完整的特殊成员函数（拷贝、移动构造/赋值、虚析构）

### `SweepLineInterface`
```cpp
class SweepLineInterface {
public:
    virtual void handleDeletions(Point eventPoint, const DeletionSegmentSet& removing) = 0;
    virtual void handleInsertionsAndCheckForNewCrossings(
            Point eventPoint, const InsertionSegmentSet& inserting, EventQueueInterface* queue) = 0;
};
```
- 纯虚接口，定义了扫描线的两个核心操作
- `handleDeletions`：从扫描线移除线段
- `handleInsertionsAndCheckForNewCrossings`：向扫描线插入线段并检查新的交叉

### `OrderBySlope`
```cpp
struct OrderBySlope {
    bool operator()(const Segment& s0, const Segment& s1) const;
};
```
- 函数对象，按线段斜率排序
- 用于 `InsertionSegmentSet`，确保通过同一点的线段按斜率正确排列

### 类型别名
- `DeletionSegmentSet = std::set<Segment>`：按默认排序的待删除线段集合
- `InsertionSegmentSet = std::set<Segment, OrderBySlope>`：按斜率排序的待插入线段集合

## 公共 API 函数

### `EventQueueInterface::addCrossing(...)`
向事件队列报告新发现的交叉点。扫描线在执行插入操作时调用此方法通知事件队列。

### `SweepLineInterface::handleDeletions(...)`
处理在事件点处结束或需要交换的线段的删除操作。

### `SweepLineInterface::handleInsertionsAndCheckForNewCrossings(...)`
处理新线段的插入，并检查插入位置的邻居是否产生新的交叉。

## 内部实现细节

`InsertionSegmentSet` 使用 `OrderBySlope` 而非默认排序，因为在同一事件点处开始或交叉的多条线段必须按斜率顺序插入扫描线，才能保证扫描线的正确排序。

## 依赖关系

- `modules/bentleyottmann/include/Point.h` - 点类型
- `modules/bentleyottmann/include/Segment.h` - 线段类型
- `<set>` - 有序集合容器

## 设计模式与设计决策

### 依赖倒置原则
事件队列和扫描线通过抽象接口交互，而非直接依赖具体实现。这使得测试代码可以提供模拟（mock）实现。

### 关注点分离
文件注释明确指出接口设计的目的：允许 EventQueue 和 SweepLine 独立测试。

### 斜率排序的插入集合
插入集合按斜率排序而非按端点排序，这是 Bentley-Ottmann 算法在处理同一事件点多条线段时保证正确性的关键设计。

## 性能考量

- `std::set` 提供 O(log n) 的插入和查找
- 接口的虚函数调用开销在算法的整体复杂度中可忽略
- 集合类型的选择平衡了正确性（自动排序和去重）与性能

## 相关文件

- `modules/bentleyottmann/include/EventQueue.h` - `EventQueueInterface` 的实现
- `modules/bentleyottmann/include/SweepLine.h` - `SweepLineInterface` 的实现
- `modules/bentleyottmann/include/Segment.h` - 线段定义和 `compare_slopes` 函数
- `modules/bentleyottmann/src/EventQueue.cpp` - `OrderBySlope` 的实现
