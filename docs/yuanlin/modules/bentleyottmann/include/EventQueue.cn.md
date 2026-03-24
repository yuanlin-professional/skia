# EventQueue.h - Bentley-Ottmann 事件队列

> 源文件: `modules/bentleyottmann/include/EventQueue.h`

## 概述

`EventQueue.h` 定义了 Bentley-Ottmann 线段交点算法的事件队列系统。事件队列是该扫描线算法的核心数据结构，负责按照特定顺序管理和分发三种类型的事件：线段上端点（Upper）、线段下端点（Lower）和交叉点（Cross）。事件按照点的位置排序，确保扫描线从上到下、从左到右正确推进。

## 架构位置

在 Bentley-Ottmann 算法架构中，事件队列处于核心协调者的位置：

- **上层调用者**：`bentley_ottmann_1()` 函数（BentleyOttmann1.h）
- **协作对象**：`SweepLine`（通过 `SweepLineInterface` 接口交互）
- **继承关系**：继承自 `EventQueueInterface`，实现 `addCrossing` 方法
- **数据依赖**：使用 `Point`、`Segment`、`Crossing` 数据类型

## 主要类与结构体

### 事件类型（`std::variant`）

#### `Lower`
表示线段下端点事件。所有 Lower 事件视为相等（`operator<` 始终返回 false），因为只需要知道某条线段在此点结束。

#### `Upper`
表示线段上端点事件。包含一条 `Segment`，比较运算符基于线段端点坐标保证队列唯一性。

#### `Cross`
表示两条线段的交叉事件。包含两条 `Segment`（s0, s1），比较运算符基于所有四个端点坐标保证队列唯一性。

### `Event`
```cpp
struct Event {
    Point where;
    EventType type;  // std::variant<Lower, Cross, Upper>
};
```
将事件位置和事件类型组合在一起。排序先按位置（`where`），再按类型（`type`）。

### `EventQueue`
继承自 `EventQueueInterface`，是事件队列的完整实现：
- 内部使用 `std::set<Event>` 作为有序队列
- 维护删除集合（`fDeletionSet`）和插入集合（`fInsertionSet`）作为临时缓冲区
- 跟踪已发现的所有交叉点（`fCrossings`）
- 记录上一个事件点（`fLastEventPoint`）以确保前向推进

## 公共 API 函数

### `EventQueue::Make(SkSpan<const Segment> segments)`
静态工厂方法，从线段集合创建事件队列。检验坐标范围，超出范围时返回 `nullopt`。将每条线段的上端点作为 Upper 事件加入队列。

### `addCrossing(Point, const Segment&, const Segment&)`
实现 `EventQueueInterface` 的虚函数。向队列添加交叉事件，并记录交叉点到 `fCrossings`。

### `hasMoreEvents() const`
返回队列是否还有待处理的事件。

### `handleNextEventPoint(SweepLineInterface* handler)`
处理下一个事件点。收集同一位置的所有事件，将对应的线段分类为删除集合和插入集合，然后通过 `SweepLineInterface` 执行扫描线操作。

### `crossings()`
返回所有已发现的交叉点的副本。

## 内部实现细节

### 事件处理流程（handleNextEventPoint）
1. 清空临时缓冲区 `fDeletionSet` 和 `fInsertionSet`
2. 使用 `std::visit` 和 Visitor 模式遍历同一位置的所有事件：
   - **Lower**：标记存在 Lower 事件
   - **Cross**：将两条线段加入删除和插入集合（交叉时需要在扫描线中交换位置）
   - **Upper**：将线段加入插入集合，并为该线段的下端点添加 Lower 事件
3. 从队列中删除已处理的事件
4. 通过 `SweepLineInterface` 执行删除和插入操作

### EventType 排序
`std::variant` 的默认排序按类型索引排序，因此事件在同一位置按 Lower < Cross < Upper 的顺序处理。

## 依赖关系

- `include/core/SkSpan.h` - 只读数组视图
- `modules/bentleyottmann/include/EventQueueInterface.h` - 基类和相关类型定义
- `modules/bentleyottmann/include/Point.h` - 点类型
- `modules/bentleyottmann/include/Segment.h` - 线段和交叉点类型
- 标准库：`<optional>`, `<set>`, `<tuple>`, `<variant>`, `<vector>`

## 设计模式与设计决策

### 访问者模式
使用 C++17 的 `std::variant` + `std::visit` 实现访问者模式，对三种事件类型进行模式匹配处理。

### 中介者模式
`EventQueue` 充当中介者，协调事件分发和 `SweepLine` 操作，两者通过接口（`EventQueueInterface` 和 `SweepLineInterface`）解耦。

### 单一事件点批量处理
将同一位置的所有事件合并处理，这是 Bentley-Ottmann 算法正确处理退化情况（多条线段通过同一点）的关键。

## 性能考量

- `std::set<Event>` 保证 O(log n) 的插入和删除，适合动态事件队列
- 临时缓冲区（`fDeletionSet`、`fInsertionSet`）在每次事件处理前清空复用，减少内存分配
- 包围盒范围检查（`DifferenceTooBig`）提前检测溢出风险

## 相关文件

- `modules/bentleyottmann/src/EventQueue.cpp` - 实现文件
- `modules/bentleyottmann/include/EventQueueInterface.h` - 接口定义
- `modules/bentleyottmann/include/SweepLine.h` - 扫描线实现
- `modules/bentleyottmann/include/BentleyOttmann1.h` - 算法入口
