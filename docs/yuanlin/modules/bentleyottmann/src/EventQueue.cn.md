# EventQueue.cpp - Bentley-Ottmann 事件队列实现

> 源文件: `modules/bentleyottmann/src/EventQueue.cpp`

## 概述

`EventQueue.cpp` 实现了 Bentley-Ottmann 线段交点算法的事件队列核心逻辑。事件队列是整个算法的调度中心，负责按照正确的顺序生成和处理三种类型的事件（Upper -- 线段上端点、Lower -- 线段下端点、Cross -- 交叉点），驱动扫描线从上到下推进，并收集所有发现的交叉点。本文件还实现了 `OrderBySlope` 比较器，该比较器用于按斜率排序的插入集合。文件共 133 行，是 Bentley-Ottmann 算法中逻辑最复杂的实现文件。

## 架构位置

- **头文件**：`modules/bentleyottmann/include/EventQueue.h`
- **继承关系**：实现 `EventQueueInterface::addCrossing`
- **协作**：通过 `SweepLineInterface` 驱动 `SweepLine`
- **被调用**：`bentley_ottmann_1()` 创建并使用 EventQueue

## 主要类与结构体

### `Visitor` 模板（辅助）
```cpp
template<class... Ts>
struct Visitor : Ts... { using Ts::operator()...; };
```
C++17 聚合继承技巧，将多个 lambda 合并为一个可调用对象，用于 `std::visit`。

## 公共 API 函数

### `EventQueue::Make(SkSpan<const Segment> segments)`
静态工厂方法：
1. 初始化包围盒为极值
2. 遍历所有线段，累积包围盒并将每条线段的 upper 端点作为 `Upper` 事件插入队列
3. 通过 `Point::DifferenceTooBig` 检测坐标范围是否超出安全范围
4. 超出范围返回 `nullopt`，否则返回构造好的 EventQueue

### `EventQueue::addCrossing(Point, const Segment&, const Segment&)`
由扫描线回调，添加交叉事件到队列并记录交叉信息到 `fCrossings`。

### `EventQueue::hasMoreEvents() const`
判断队列是否为空。

### `EventQueue::handleNextEventPoint(SweepLineInterface*)`
处理下一个事件点的完整逻辑（见内部实现细节）。

### `EventQueue::crossings()`
返回所有交叉点的副本。注意返回的是值而非引用，调用者获得独立的数据所有权。

### `OrderBySlope::operator()(const Segment&, const Segment&)`
使用 `compare_slopes` 比较两条线段的斜率，返回 s0 斜率是否小于 s1 斜率。这是 `InsertionSegmentSet` 的排序谓词。

### `EventQueue::EventQueue(Queue&& queue)`
移动构造函数，接收预构建的队列。仅供 `Make` 工厂方法使用。

### `EventQueue::add(const Event& e)`
私有方法，向队列添加事件。带有前向推进断言：新事件的位置必须严格在 `fLastEventPoint` 之后。

## 内部实现细节

### handleNextEventPoint 核心流程

1. **清空缓冲区**：`fDeletionSet.clear()` 和 `fInsertionSet.clear()`

2. **设置访问者**（使用 Visitor 模式）：
   - `handleLower`：标记存在 Lower 事件（有线段在此点结束）
   - `handleCross`：将两条交叉线段加入删除和插入集合（需要在扫描线中交换位置）
   - `handleUpper`：将新线段加入插入集合，并向队列添加对应的 Lower 事件

3. **收集事件**：遍历队列中所有与当前事件点位置相同的事件，使用 `std::visit(visitor, event.type)` 分发处理

4. **清理队列**：批量删除已处理的事件

5. **执行扫描线操作**：
   - 若有删除需求，调用 `handler->handleDeletions`
   - 若有任何变更，调用 `handler->handleInsertionsAndCheckForNewCrossings`

### 前向推进断言
`SkASSERT(fLastEventPoint < eventPoint)` 确保算法始终向前推进，防止无限循环。

### 事件队列不变量
- 新事件只能添加到当前事件点之后（`fLastEventPoint < event.where`）
- 同一位置的所有事件合并处理
- 使用 `std::set` 自动去重，避免重复事件

### Cross 事件的特殊处理
交叉事件导致两条线段先被删除再被重新插入，实现了在扫描线中"交换"位置的效果。`InsertionSegmentSet` 按斜率排序确保重新插入时顺序正确。

## 依赖关系

- `modules/bentleyottmann/include/EventQueue.h` - 头文件
- `include/private/base/SkAssert.h` - 断言
- `<algorithm>`, `<cstdint>`, `<utility>` - 标准库

## 设计模式与设计决策

### C++17 Visitor 模式
使用模板 `Visitor` 结构体和 CTAD（类模板参数推导）将多个 lambda 组合为 `std::visit` 的访问者，这是处理 `std::variant` 的惯用模式。

### 批量处理同一事件点
所有同位置事件合并处理是 Bentley-Ottmann 算法正确处理退化情况的关键。代码通过游标遍历并批量删除实现。

### 延迟 Lower 事件
Upper 事件处理时才创建对应的 Lower 事件，而非在 `Make` 时预创建。这减少了初始队列大小，也更符合"按需"的事件驱动思想。

### addCrossing 的双重记录
`addCrossing` 既向队列添加 Cross 事件，又向 `fCrossings` 向量记录交叉。Cross 事件用于驱动扫描线更新（交叉线段需要交换位置），而 `fCrossings` 用于最终结果返回。两者不可替代。

### 事件排序的层次结构
事件排序为：(1) 位置 `where`（y 优先，然后 x），(2) 事件类型 `type`（`std::variant` 按索引排序：Lower=0 < Cross=1 < Upper=2），(3) 类型内部排序。Lower 优先处理确保线段在交叉点处先被删除，然后 Cross 导致线段交换，最后 Upper 添加新线段。

### CTAD 推导指南
```cpp
template<class... Ts> Visitor(Ts...) -> Visitor<Ts...>;
```
这是 C++17 的类模板参数推导指南（deduction guide），允许 `Visitor{lambda1, lambda2, lambda3}` 自动推导模板参数。

## 性能考量

- `std::set<Event>` 的插入和删除均为 O(log n)，适合动态事件队列
- 同一事件点的事件通过连续游标遍历，由于 `std::set` 的有序性，同位置事件在树中相邻
- `fDeletionSet` 和 `fInsertionSet` 在每次事件处理前 `clear()` 复用，减少内存分配
- 包围盒范围检查在 `Make` 中一次性完成，避免运行时溢出
- `addCrossing` 中的断言 `fLastEventPoint < event.where` 确保不会添加已过期的事件
- `crossings()` 返回向量副本而非引用，确保线程安全但增加一次拷贝开销

### EventQueue 的生命周期
1. **创建**：`Make()` 静态方法验证输入并初始化队列
2. **运行**：`handleNextEventPoint()` 循环处理事件，期间队列动态增长（新的 Lower 和 Cross 事件被添加）和收缩（已处理的事件被移除）
3. **完成**：`hasMoreEvents()` 返回 false 时算法结束
4. **结果提取**：`crossings()` 返回所有发现的交叉点

### 与 Myers::EventQueue 的对比
Bentley-Ottmann 的 EventQueue 是动态的（运行时添加 Cross 和 Lower 事件），而 Myers 的 EventQueue 是静态的（所有事件在构造时确定）。这使得 Bentley-Ottmann 版本可以只在发现新交叉时才创建对应事件，减少了预计算开销。

### Queue 类型选择
使用 `std::set<Event>` 而非 `std::priority_queue` 是因为：
1. `std::set` 支持在中间位置高效地插入（交叉事件可能在任意位置）
2. `std::set` 自动去重，防止同一交叉事件被多次处理
3. `std::set` 的迭代器支持范围删除（`erase(begin, cursor)`），方便批量处理
4. 虽然 `std::priority_queue` 的常数因子更小，但缺少上述功能

### fLastEventPoint 的初始化
`fLastEventPoint` 初始化为 `Point::Smallest()`（即 `{INT32_MIN, INT32_MIN}`），确保第一个真实事件点可以通过 `fLastEventPoint < eventPoint` 的前向推进断言。这是一个关键的初始化选择，保证了算法从最小可能的坐标开始。

## 相关文件

- `modules/bentleyottmann/include/EventQueue.h` - 头文件和类型定义（Event、Lower、Upper、Cross、EventQueue）
- `modules/bentleyottmann/include/EventQueueInterface.h` - `EventQueueInterface` 和 `SweepLineInterface` 接口定义
- `modules/bentleyottmann/src/SweepLine.cpp` - 扫描线实现（通过 `SweepLineInterface` 回调）
- `modules/bentleyottmann/src/BentleyOttmann1.cpp` - 算法入口，创建并驱动 EventQueue
- `modules/bentleyottmann/include/Segment.h` - `compare_slopes` 函数和线段类型定义
- `modules/bentleyottmann/include/Point.h` - 事件点坐标类型和 `Smallest`/`DifferenceTooBig` 工具函数
- `modules/bentleyottmann/src/Myers.cpp` - Myers 命名空间中的独立 EventQueue 实现（对比参考）
