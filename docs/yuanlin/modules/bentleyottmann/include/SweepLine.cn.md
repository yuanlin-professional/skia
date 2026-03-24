# SweepLine.h - Bentley-Ottmann 扫描线定义

> 源文件: `modules/bentleyottmann/include/SweepLine.h`

## 概述

`SweepLine.h` 定义了 Bentley-Ottmann 算法中的扫描线类 `SweepLine`。扫描线维护当前水平扫描位置处的线段有序序列，是算法中负责检测线段交叉的核心组件。它实现了 `SweepLineInterface` 接口，与事件队列配合完成交叉检测。

## 架构位置

- **实现接口**：`SweepLineInterface`（定义于 `EventQueueInterface.h`）
- **协作对象**：`EventQueue` 通过接口驱动扫描线操作
- **上层入口**：`bentley_ottmann_1()` 函数创建并使用 `SweepLine`
- **实现文件**：`modules/bentleyottmann/src/SweepLine.cpp`

## 主要类与结构体

### `SweepLine`
```cpp
class SweepLine : public SweepLineInterface {
public:
    SweepLine();
    void handleDeletions(Point eventPoint, const DeletionSegmentSet& removing) override;
    void handleInsertionsAndCheckForNewCrossings(
        Point eventPoint, const InsertionSegmentSet& inserting,
        EventQueueInterface* queue) override;
private:
    std::vector<Segment> fSweepLine;
};
```
- 使用 `std::vector<Segment>` 存储当前扫描线上的线段有序序列
- 构造时初始化左右哨兵线段
- 提供测试友元 `SweepLineTestingPeer`

## 公共 API 函数

### `SweepLine()`
构造函数，初始化扫描线并插入左右哨兵线段。

### `handleDeletions(Point, const DeletionSegmentSet&)`
从扫描线中移除在事件点处结束的线段以及需要交换的交叉线段。

### `handleInsertionsAndCheckForNewCrossings(Point, const InsertionSegmentSet&, EventQueueInterface*)`
在事件点处插入新线段，并检查插入位置左右邻居是否产生新的交叉。

## 内部实现细节

### `verify(int32_t y)` 调试方法
私有方法，用于调试时验证扫描线在给定 y 坐标处的线段顺序是否正确。遍历所有相邻线段对，断言 `less_than_at(left, right, y)` 为真。此方法仅在 debug 构建中有效。

### 线段排序不变量
扫描线维护的核心不变量是：在当前扫描 y 坐标处，`fSweepLine` 中的线段按 x 截距从左到右排序。当线段交叉时，通过删除+重新插入的方式恢复排序。

### 测试友元
`SweepLineTestingPeer` 友元声明允许测试代码直接访问 `fSweepLine` 私有成员，以验证扫描线的内部状态。

## 依赖关系

- `modules/bentleyottmann/include/EventQueueInterface.h` - 基类和类型定义
- `modules/bentleyottmann/include/Segment.h` - 线段类型和比较函数
- `<cstdint>`, `<vector>` - 标准库

## 设计模式与设计决策

### 哨兵模式
左右哨兵线段避免了边界检查，简化了插入和邻居查找逻辑。

### 向量存储
使用 `std::vector` 而非平衡二叉树存储线段，对于中等规模数据集更友好（缓存局部性好）。

### 接口驱动
通过 `SweepLineInterface` 接口与事件队列交互，支持独立单元测试。

## 性能考量

- 向量预分配（`reserve(8)`）减少初始阶段的重新分配
- `std::remove_if` 加 `erase` 的删除策略效率适中
- `std::lower_bound` 用于 O(log n) 查找插入位置

## 相关文件

- `modules/bentleyottmann/src/SweepLine.cpp` - 实现文件
- `modules/bentleyottmann/include/EventQueueInterface.h` - 接口定义
- `modules/bentleyottmann/include/EventQueue.h` - 协作的事件队列
- `modules/bentleyottmann/include/Segment.h` - 线段比较函数
