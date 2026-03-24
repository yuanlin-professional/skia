# BentleyOttmann1.h - Bentley-Ottmann 算法入口接口

> 源文件: `modules/bentleyottmann/include/BentleyOttmann1.h`

## 概述

`BentleyOttmann1.h` 声明了 Bentley-Ottmann 线段交点检测算法的顶层入口函数 `bentley_ottmann_1`。该函数接受一组线段，使用基于扫描线的 Bentley-Ottmann 算法高效地找出所有交点，时间复杂度为 O((n+k) log n)（其中 n 是线段数，k 是交点数）。

## 架构位置

该头文件是 Bentley-Ottmann 算法模块的公共入口：

- **外部调用者**：需要线段交点检测的 Skia 上层代码
- **内部依赖**：通过实现文件间接使用 `EventQueue` 和 `SweepLine`
- **同层替代**：`BruteForceCrossings.h` 提供 O(n^2) 的暴力替代方案

## 主要类与结构体

无新定义。使用前向声明引用 `Crossing` 和 `Segment`。

## 公共 API 函数

### `bentley_ottmann_1(SkSpan<const Segment> segments)`
- 参数：只读线段数组
- 返回：`std::optional<std::vector<Crossing>>`
  - `std::nullopt`：输入数据坐标范围过大，可能导致溢出。建议将所有坐标除以 2 后重试
  - 空向量：无交点
  - 非空向量：所有交点及对应的线段对

## 内部实现细节

实现在 `BentleyOttmann1.cpp` 中，流程为：
1. 使用 `EventQueue::Make()` 创建事件队列。此步骤将所有线段的上端点（upper point）注册为 Upper 事件，并验证坐标范围
2. 创建空的 `SweepLine` 实例（初始仅包含左右哨兵线段）
3. 进入主循环：当事件队列非空时，调用 `handleNextEventPoint` 处理下一个事件点。每次处理可能产生新的 Cross 事件加入队列
4. 循环结束后，从事件队列中提取所有已收集的交叉点并返回

### 算法正确性保证
- 事件队列使用 `std::set` 保证事件按 (y, x) 顺序处理
- 每个事件点只处理一次，`fLastEventPoint` 断言确保前向推进
- 扫描线在每次事件后维护正确的线段排序

### 坐标范围验证
`EventQueue::Make` 内部计算所有线段的全局包围盒，并通过 `Point::DifferenceTooBig` 检查。若包围盒对角线的坐标差超过 `int32_t` 范围，则 96 位精确比较可能不足，此时返回 `nullopt` 提示调用者缩小坐标范围。

## 依赖关系

- `include/core/SkSpan.h` - 只读数组视图
- `<optional>`, `<vector>` - 标准库
- `Crossing`, `Segment`（前向声明）

## 设计模式与设计决策

### 简洁的门面模式
单一函数封装了整个 Bentley-Ottmann 算法的复杂性，对外暴露最简接口。

### 可选返回值
使用 `std::optional` 区分"算法正常完成但无交点"和"输入数据超出算法处理范围"两种情况。

### 后缀 "1"
函数名中的 "1" 暗示这是第一个版本的实现，可能计划在未来提供更多变体。

## 性能考量

- Bentley-Ottmann 算法的时间复杂度 O((n+k) log n) 远优于暴力方法的 O(n^2)。对于 n=1000 条线段和 k=100 个交点，效率提升约 100 倍
- 当线段坐标范围过大时提前返回 `nullopt`，避免整数溢出导致的错误计算。这是 O(n) 的预检查，开销可忽略
- 算法的空间复杂度为 O(n+k)：事件队列最多同时持有 O(n+k) 个事件，扫描线最多持有 O(n) 条线段

### 与 Myers 算法的选择
两种算法的选择取决于使用场景：
- `bentley_ottmann_1` 返回精确交点坐标，但对坐标范围有限制
- `myers_find_crossings` 不受坐标范围限制，但不计算交点坐标
- 对于需要交点坐标的场景使用 Bentley-Ottmann；对于只需知道哪些线段交叉的场景使用 Myers

## 相关文件

- `modules/bentleyottmann/src/BentleyOttmann1.cpp` - 实现文件
- `modules/bentleyottmann/include/EventQueue.h` - 事件队列（管理 Upper/Lower/Cross 事件）
- `modules/bentleyottmann/include/SweepLine.h` - 扫描线（维护线段有序序列）
- `modules/bentleyottmann/include/EventQueueInterface.h` - 事件队列和扫描线的交互接口
- `modules/bentleyottmann/include/BruteForceCrossings.h` - 暴力求交替代方案（用于验证）
- `modules/bentleyottmann/include/Segment.h` - 线段和交叉点定义
- `modules/bentleyottmann/include/Myers.h` - Myers 替代算法
