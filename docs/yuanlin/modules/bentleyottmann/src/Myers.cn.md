# Myers.cpp - Myers 线段交点检测算法实现

> 源文件: `modules/bentleyottmann/src/Myers.cpp`

## 概述

`Myers.cpp` 实现了基于 Myers 算法的线段交点检测系统。与 Bentley-Ottmann 算法的事件驱动方式不同，Myers 算法使用预计算事件队列和插入排序风格的扫描线。该文件包含完整的 Point 运算、Segment 操作、事件队列、扫描线、交叉累积器的实现，以及两个入口函数：`myers_find_crossings`（扫描线算法）和 `brute_force_crossings`（暴力枚举）。文件内部还实现了健壮的线段相交谓词。

## 架构位置

- **头文件**：`modules/bentleyottmann/include/Myers.h`
- **独立命名空间**：`myers`，与 `bentleyottmann` 并行
- **共享组件**：使用 `bentleyottmann::Int96` 进行精确 96 位运算
- **被引用**：`Contour.h/cpp` 中的轮廓系统产出 `myers::Segment`
- **自包含**：包含所有内部组件（EventQueue、SweepLine、CrossingAccumulator）

## 主要类与结构体

### `Event`（内部）
```cpp
struct Event {
    const int32_t y;
    SkSpan<const Segment> begin;      // 在 y 处开始的线段
    SkSpan<const Segment> horizontal; // 在 y 处的水平线段
    SkSpan<const Segment> end;        // 在 y 处结束的线段
};
```
表示扫描线在特定 y 坐标处需要处理的所有事件。将线段按类型分组。

### `EventQueue`（内部）
预计算的事件队列，与 `bentleyottmann::EventQueue` 不同：
- **静态生成**：一次性从所有线段创建全部事件，运行时不添加新事件
- **紧凑存储**：使用 `CompactEvent`（5 个 int32_t 字段）和扁平化的 `fSegmentStorage`
- **迭代器**：支持范围 for 循环遍历事件
- **SetupTuple**：内部用于排序的中间表示，包含 y 坐标、事件类型、x 坐标和原始线段
- **去重**：排序后使用 `std::unique` 移除重复事件

### `CrossingAccumulator`（内部）
交叉收集器，负责过滤端点交叉：
- 排除上-下端点重合（`s0.upper() == s1.lower()`）
- 排除上-上或下-下端点重合但斜率不同的情况（共享端点但非共线）
- 仅保留真正的交叉（线段内部交叉或共线重叠）

### `SweepLine`（内部）
插入排序风格的扫描线：
- 使用 `std::vector<Segment>` 存储状态线
- 左右哨兵为 `INT32_MIN`/`INT32_MAX` 的垂直线段
- **核心区别**：通过排序检测交叉（而非显式交叉检测）

## 公共 API 函数

### `myers_find_crossings(SkSpan<const Segment> segments)`
Myers 扫描线算法入口：
1. 创建预计算事件队列
2. 创建扫描线
3. 对每个事件调用 `sweepLine.handleEvent`
4. 返回收集的交叉

### `brute_force_crossings(SkSpan<Segment> segments)`
暴力枚举交叉检测（注意参数为非 const）：
1. 分离零长度线段
2. 排序并去重
3. O(n^2) 遍历所有线段对
4. 使用 `s0_intersects_s1` 检测交叉

## 内部实现细节

### 核心辅助函数

#### `cross(Point d0, Point d1)`
计算二维向量叉积，使用 64 位运算：`d0.x * d1.y - d1.x * d0.y`。

#### `compare_slopes(s0, s1)`
比较斜率 dx/dy（注意是 dx/dy 而非 dy/dx），返回 `cross(d0, d1)` 的符号。水平线段斜率定义为最大值。

#### `compare_point_to_segment(p, s)`
判断点 p 相对于线段 s 的位置关系：
- 负值：p 在 s 左侧
- 零：p 在 s 上
- 正值：p 在 s 右侧
- 使用叉积 `(p - u) x (l - u)` 计算

#### `segment_less_than_upper_to_insert(segment, to_insert)`
用于 `std::lower_bound` 的比较器。先比较 `to_insert.upper()` 与 `segment` 的位置关系，相等时比较斜率。

#### `s0_less_than_s1_at_y(s0, s1, y)`
在 y 处比较两条非水平线段的 x 截距。使用 96 位整数（`bentleyottmann::Int96`）进行精确计算。数学推导：
```
s0(y) = u0.x + (y - u0.y) * d0.x / d0.y
s1(y) = u1.x + (y - u1.y) * d1.x / d1.y
```
交叉乘法消除除法，得到 96 位整数比较。

### EventQueue::Make 详解

1. **事件生成**：对每条线段生成 SetupTuple：
   - 水平线段：kHorizontal 类型
   - 非水平线段：kBegin（上端点）+ kEnd（下端点）两个事件
   - 零长度线段被跳过

2. **排序**：按 (y, 事件类型, -x) 排序。事件类型顺序：kBegin < kHorizontal < kEnd

3. **去重**：`std::unique` 移除完全相同的事件

4. **紧凑化**：转换为 CompactEvent，线段存储在 fSegmentStorage 中

### SweepLine 工作流程

#### `sortAndRecord(y)`
使用插入排序对扫描线状态排序。关键创新：如果排序过程中发生元素交换，说明对应的两条线段在此 y 值处发生了交叉，直接记录。

#### `handleBeginnings(y, inserting)`
对每条开始的线段：
1. 用 `lower_bound` 找到插入位置
2. 检查插入点左右的线段是否经过新线段的上端点（共点情况）
3. 插入到状态线

#### `handleHorizontals(y, horizontals)`
水平线段的特殊处理：
1. 找到插入位置
2. 检查左右线段是否与水平线段交叉（使用两个端点的位置关系）
3. 插入后立即删除（水平线段不参与后续排序）

#### `handleEndings(removing)`
从状态线中移除结束的线段。

### s0_intersects_s1 健壮相交谓词

基于 "Robust Plane Sweep for Intersecting Segments" 论文（第 10 页）：

1. **规范化**：确保 s0.upper().y <= s1.upper().y
2. **包围盒快速排除**
3. **叉积检测**：
   - 计算 D0（s0 方向）与 U0toU1（s0 起点到 s1 起点）的叉积
   - 若叉积为 0：u1 在 s0 上，直接交叉
   - 若 l1.y <= l0.y（s1 在 s0 范围内）：检查 u1 和 l1 是否在 s0 两侧
   - 若 l1.y > l0.y（s1 延伸超过 s0）：检查 l0 相对于 s1 的位置

### 算法对比

| 特性 | bentleyottmann | myers |
|------|---------------|-------|
| 事件队列 | 动态（运行时添加交叉事件） | 静态（预计算所有事件） |
| 交叉检测 | 邻居检查 + 事件报告 | 插入排序 + 交换记录 |
| 水平线段 | 未特殊处理 | 专门的 horizontal 事件类型 |
| 交叉信息 | 交叉线段对 + 交点坐标 | 仅交叉线段对 |
| 交叉过滤 | 无 | CrossingAccumulator 过滤端点交叉 |

## 依赖关系

- `modules/bentleyottmann/include/Myers.h` - 头文件
- `include/core/SkSpan.h` - 只读数组视图
- `include/private/base/SkAssert.h` - 断言
- `include/private/base/SkTo.h` - 安全类型转换
- `modules/bentleyottmann/include/Int96.h` - 96 位精确整数运算
- `<algorithm>`, `<climits>`, `<cstdint>`, `<iterator>`, `<tuple>`, `<utility>`, `<vector>` - 标准库

## 设计模式与设计决策

### 自包含实现
所有内部类（EventQueue、SweepLine、CrossingAccumulator）均定义在 .cpp 文件中，不暴露实现细节。这是一种极端的封装方式。

### 插入排序检测交叉
Myers 算法的核心创新：在对扫描线进行插入排序时，每次元素交换意味着两条线段交叉。这比 Bentley-Ottmann 的显式邻居检查更简单，但可能检测到更多的（包括退化的）交叉。

### 水平线段的一等公民处理
水平线段在 Bentley-Ottmann 算法中是棘手的退化情况。Myers 实现将其作为独立事件类型处理，有专门的 `handleHorizontals` 方法，使用"插入-检查-立即删除"策略。

### CrossingAccumulator 的过滤逻辑
端点交叉在路径布尔运算中已经隐式表示，无需重复记录。过滤条件精确区分了以下情况：
- 上端-下端重合：总是排除
- 同端点但不同斜率：排除（不是真正的交叉）
- 同端点且同斜率（共线）：保留

### 健壮的相交谓词
`s0_intersects_s1` 引用了学术论文，使用纯整数叉积计算，处理了包括端点在线段上、线段延伸超过另一线段等所有退化情况。

### 命名空间别名
```cpp
namespace bo = bentleyottmann;
using Int96 = bo::Int96;
```
在 `s0_less_than_s1_at_y` 中使用命名空间别名简化 `bentleyottmann::Int96` 的引用。这是 Myers 模块使用 Bentley-Ottmann 模块基础设施的唯一地方。

## 性能考量

- **预计算事件队列**：排序一次（O(n log n)）、遍历一次（O(n)），避免了动态事件队列的 O(log n) 单次插入开销。对于无交叉或少量交叉的场景尤其有利
- **插入排序**：对几乎有序的数据（扫描线状态通常只有少量变化）非常高效，接近 O(n)。标准库的 `std::sort` 对小数组可能有更高的常数因子
- **去重**：事件生成后排序去重，避免运行时重复处理。使用 `std::unique` 原地去重，无额外内存分配
- **96 位运算的使用**：仅在 `s0_less_than_s1_at_y` 中使用 `Int96`，其余运算使用 64 位叉积
- **暴力枚举的预处理**：`brute_force_crossings` 先用 `std::partition` 分离零长度线段、`std::sort` 排序、`std::unique` 去重，减少实际比较次数
- **哨兵线段**：`kLeftStatusSentinel` 和 `kRightStatusSentinel` 为 `constexpr`，编译器可将其嵌入代码段而非数据段
- **模板化的 checkCrossingsLeftAndRight**：通过模板参数 `CrossingCheck` 参数化交叉检查逻辑，编译器对每个调用点生成专门化代码，避免虚函数开销
- **CompactEvent 的紧凑性**：每个事件仅需 5 个 `int32_t`（20 字节），加上扁平化的线段存储，内存使用远优于指针链接结构
- **反向迭代器**：`checkCrossingsLeftAndRight` 中向左搜索使用 `std::make_reverse_iterator`，哨兵确保循环在 O(1) 内终止于大多数情况

## 相关文件

- `modules/bentleyottmann/include/Myers.h` - 头文件和公共类型定义
- `modules/bentleyottmann/include/Int96.h` - 96 位整数运算
- `modules/bentleyottmann/src/Segment.cpp` - bentleyottmann 版本的线段运算（对比）
- `modules/bentleyottmann/src/BentleyOttmann1.cpp` - Bentley-Ottmann 算法（替代方案）
- `modules/bentleyottmann/include/Contour.h` - 产出 `myers::Segment` 的轮廓系统
