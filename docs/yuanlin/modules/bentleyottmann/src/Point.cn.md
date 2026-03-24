# Point.cpp - 二维整数点实现

> 源文件: `modules/bentleyottmann/src/Point.cpp`

## 概述

`Point.cpp` 实现了 `bentleyottmann::Point` 结构体的比较运算符和静态工具函数。这些函数为 Bentley-Ottmann 算法提供了点的排序、相等判断、极值获取和溢出检测功能。排序规则为 (y, x) 字典序，与扫描线算法的从上到下、从左到右推进方向一致。

## 架构位置

- **头文件**：`modules/bentleyottmann/include/Point.h`
- **被使用**：整个 Bentley-Ottmann 模块的几乎所有组件
- **无模块内实现依赖**：仅依赖标准库

## 主要类与结构体

无新定义。实现 `Point.h` 中声明的自由函数和静态成员函数。

## 公共 API 函数

### 比较运算符
- `operator<(p0, p1)`：使用 `std::tie(p0.y, p0.x) < std::tie(p1.y, p1.x)` 实现 (y, x) 字典序
- `operator>(p0, p1)`：委托为 `p1 < p0`
- `operator>=(p0, p1)`：委托为 `!(p0 < p1)`
- `operator<=(p0, p1)`：委托为 `!(p0 > p1)`
- `operator==(p0, p1)`：使用 `std::tie` 比较 (y, x) 相等
- `operator!=(p0, p1)`：委托为 `!(p0 == p1)`

### 静态方法
- `Point::Smallest()`：返回 `{INT32_MIN, INT32_MIN}`，用作事件队列的初始哨兵
- `Point::Largest()`：返回 `{INT32_MAX, INT32_MAX}`，用作范围检查上界
- `Point::DifferenceTooBig(p0, p1)`：检测两点的 x 或 y 坐标差值是否超出 `int32_t` 范围

## 内部实现细节

### DifferenceTooBig 溢出检测
```cpp
auto tooBig = [](int32_t a, int32_t b) {
    return (b > 0 && a < std::numeric_limits<int32_t>::min() + b) ||
           (b < 0 && a > std::numeric_limits<int32_t>::max() + b);
};
return tooBig(p0.x, p1.x) || tooBig(p0.y, p1.y);
```
- 不直接计算 `a - b`（可能溢出），而是通过等价的不溢出条件间接判断
- 当 `b > 0` 时检查 `a - b` 是否下溢；当 `b < 0` 时检查是否上溢
- 对 x 和 y 坐标分别检查，任一维度溢出即返回 true

### 比较运算符实现策略
所有运算符都基于 `operator<` 和 `operator==` 推导，保持一致性并减少错误风险。

## 依赖关系

- `modules/bentleyottmann/include/Point.h` - 头文件
- `<limits>` - `std::numeric_limits`
- `<tuple>` - `std::tie`

## 设计模式与设计决策

### 运算符推导
仅实现 `operator<` 和 `operator==` 的核心逻辑，其他四个运算符通过委托实现，符合 DRY（Don't Repeat Yourself）原则。

### Y 优先排序
扫描线算法要求事件按从上到下（y 递增）、从左到右（x 递增）排序，因此 `operator<` 采用 (y, x) 而非 (x, y) 的字典序。

### 安全的溢出检测
`DifferenceTooBig` 不执行可能溢出的减法运算，而是通过代数变换将减法转换为加法比较，完全避免了未定义行为。

### Smallest 和 Largest 的使用场景
- `Smallest()` 用于 `EventQueue` 初始化 `fLastEventPoint`，确保第一个真实事件点可以通过 `fLastEventPoint < eventPoint` 断言
- `Largest()` 用于 `EventQueue::Make` 初始化包围盒的起始极值，确保第一个线段可以正确更新包围盒
- 两个方法构成了坐标空间的闭区间 `[Smallest, Largest]`

## 性能考量

- 比较运算符使用 `std::tie` 构造临时元组，编译器通常可以将其完全内联优化为两次整数比较
- `DifferenceTooBig` 最多执行 4 次比较和 2 次加法，开销极小
- 所有函数都是纯函数，无副作用，适合编译器优化和内联
- `Smallest()` 和 `Largest()` 在函数内部使用局部 const 变量而非直接返回字面量，这是一种代码清晰性选择

## 相关文件

- `modules/bentleyottmann/include/Point.h` - 头文件
- `modules/bentleyottmann/src/Segment.cpp` - 使用 Point 比较的线段运算
- `modules/bentleyottmann/src/EventQueue.cpp` - 使用 Point 排序的事件队列
