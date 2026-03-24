# BentleyOttmann1.cpp - Bentley-Ottmann 算法实现

> 源文件: `modules/bentleyottmann/src/BentleyOttmann1.cpp`

## 概述

`BentleyOttmann1.cpp` 实现了 Bentley-Ottmann 线段交点检测算法的入口函数 `bentley_ottmann_1`。该函数将 `EventQueue` 和 `SweepLine` 组合在一起，形成完整的扫描线算法流程。代码非常简洁（仅约 10 行有效代码），体现了良好的模块化设计。

## 架构位置

- **头文件**：`modules/bentleyottmann/include/BentleyOttmann1.h`
- **协调角色**：作为算法的顶层协调者，组装 EventQueue 和 SweepLine
- **下层组件**：`EventQueue`（事件管理）、`SweepLine`（线段排序和交叉检测）

## 主要类与结构体

无新定义。使用 `EventQueue`、`SweepLine`、`Crossing`、`Segment`。

## 公共 API 函数

### `bentley_ottmann_1(SkSpan<const Segment> segments)`
算法主函数，流程如下：
1. 调用 `EventQueue::Make(segments)` 创建事件队列；若失败返回 `nullopt`
2. 创建空的 `SweepLine`
3. 循环：当事件队列非空时，调用 `handleNextEventPoint` 处理下一个事件
4. 返回 `eventQueue.crossings()`

## 内部实现细节

```cpp
std::optional<std::vector<Crossing>> bentley_ottmann_1(SkSpan<const Segment> segments) {
    if (auto possibleEQ = EventQueue::Make(segments)) {
        EventQueue eventQueue = std::move(possibleEQ.value());
        SweepLine sweepLine;
        while(eventQueue.hasMoreEvents()) {
            eventQueue.handleNextEventPoint(&sweepLine);
        }
        return eventQueue.crossings();
    }
    return std::nullopt;
}
```

关键的算法逻辑实际分布在 `EventQueue` 和 `SweepLine` 中：
- `EventQueue::Make` 进行输入验证和初始事件生成
- `handleNextEventPoint` 驱动事件处理循环
- `SweepLine` 通过 `SweepLineInterface` 回调 `EventQueue::addCrossing` 报告新发现的交叉

## 依赖关系

- `modules/bentleyottmann/include/BentleyOttmann1.h` - 头文件
- `modules/bentleyottmann/include/EventQueue.h` - 事件队列
- `modules/bentleyottmann/include/Segment.h` - 线段和交叉点
- `modules/bentleyottmann/include/SweepLine.h` - 扫描线
- `<optional>`, `<utility>`, `<vector>` - 标准库

## 设计模式与设计决策

### 门面模式
将 EventQueue 和 SweepLine 的复杂交互封装在单个函数中，对外暴露最简接口。

### 组合优于继承
通过局部变量组合 EventQueue 和 SweepLine，而非创建包含两者的算法类。

### 值语义的 EventQueue
`EventQueue` 通过 `std::move` 从 optional 中取出，避免不必要的拷贝。

### 算法终止性保证
算法的终止性由以下因素保证：
1. 每次 `handleNextEventPoint` 至少从队列中移除一个事件
2. 新加入的事件（Lower 和 Cross）的位置严格在当前事件点之后
3. `fLastEventPoint` 断言确保严格前向推进
4. 交叉事件不会产生链式反应（同一对线段只会交叉一次）

## 性能考量

- 算法整体复杂度 O((n+k) log n)，由 EventQueue 和 SweepLine 的内部实现决定
- 本文件无额外开销，仅负责组装和驱动
- `EventQueue::Make` 的失败检测是 O(n) 的，因此即使输入无效也能快速返回
- `std::move` 从 optional 中取出 EventQueue，避免拷贝整个队列数据结构

## 相关文件

- `modules/bentleyottmann/include/BentleyOttmann1.h` - 头文件
- `modules/bentleyottmann/src/EventQueue.cpp` - 事件队列实现
- `modules/bentleyottmann/src/SweepLine.cpp` - 扫描线实现
- `modules/bentleyottmann/src/BruteForceCrossings.cpp` - 暴力替代实现
