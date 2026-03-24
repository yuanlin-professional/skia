# Point.h - 二维整数点定义

> 源文件: `modules/bentleyottmann/include/Point.h`

## 概述

`Point.h` 定义了 Bentley-Ottmann 线段交点算法模块中使用的二维整数点结构体 `Point`。该结构体使用 `int32_t` 坐标，提供完整的比较运算符集合、极值静态方法、溢出检测以及基本的向量算术运算。这是整个计算几何模块最基础的数据类型。

## 架构位置

`Point` 是 `bentleyottmann` 命名空间中最底层的数据类型：

- **被依赖**：`Segment.h`、`EventQueue.h`、`EventQueueInterface.h`、`SweepLine.h` 等几乎所有模块文件
- **无模块内依赖**：仅依赖标准库 `<cstdint>`
- **实现文件**：`modules/bentleyottmann/src/Point.cpp`

## 主要类与结构体

### `Point`
```cpp
struct Point {
    int32_t x;
    int32_t y;
};
```
- 简单的二维整数坐标点
- 提供全套比较运算符（`<`, `>`, `<=`, `>=`, `==`, `!=`）
- 排序规则：先比较 y 坐标，再比较 x 坐标（适合从上到下的扫描线顺序）
- 支持点的加法和减法运算（向量语义）

## 公共 API 函数

### 比较运算符
- `operator<`：按 (y, x) 字典序排序，y 优先。这与扫描线从上到下、从左到右的推进方向一致
- `operator>`, `operator>=`, `operator<=`：基于 `operator<` 推导
- `operator==`, `operator!=`：精确相等比较

### 静态方法
- `Point::Smallest()`：返回坐标均为 `int32_t` 最小值的点，用作哨兵
- `Point::Largest()`：返回坐标均为 `int32_t` 最大值的点，用作哨兵
- `Point::DifferenceTooBig(p0, p1)`：检测两点坐标差值是否会导致 `int32_t` 溢出

### 算术运算符（内联定义）
- `operator+`：点加法（向量加法）
- `operator-`：点减法（向量减法）

## 内部实现细节

比较运算符的实现使用 `std::tie` 创建 `(y, x)` 元组进行字典序比较。`DifferenceTooBig` 通过检查减法是否会溢出 `int32_t` 范围来判断坐标差值是否过大。

## 依赖关系

- `<cstdint>` - `int32_t` 类型定义

## 设计模式与设计决策

### 整数坐标
使用 `int32_t` 而非浮点数作为坐标类型，这是计算几何中避免浮点精度问题的经典做法。整数运算可以保证比较的精确性。

### Y 优先排序
`operator<` 按 (y, x) 排序而非 (x, y)，这与 Bentley-Ottmann 扫描线算法的扫描方向（从上到下、从左到右）完全匹配。

### 哨兵值
`Smallest()` 和 `Largest()` 用作事件队列和扫描线的哨兵，简化边界条件处理。

### 溢出安全设计
`DifferenceTooBig` 静态方法是防御性编程的体现。在 `EventQueue::Make` 中用于提前检测输入数据的坐标范围，若差值过大则返回 `nullopt` 而非冒着溢出风险继续计算。

### 向量语义
`operator+` 和 `operator-` 赋予 Point 向量语义。虽然 Point 主要表示位置，但在线段运算中经常需要计算方向向量（如 `P1 - P0`），因此这些运算符简化了大量几何计算代码。

## 性能考量

- 结构体仅含两个 `int32_t` 成员，总大小 8 字节，适合值传递和在容器中高效存储
- 算术运算符内联定义，无函数调用开销
- 整数比较比浮点比较更快且无精度损失
- `std::tie` 构造的元组会被编译器完全内联和优化，不产生额外内存分配
- 作为值类型，Point 在 `std::vector` 和 `std::set` 中存储时具有良好的缓存局部性

## 相关文件

- `modules/bentleyottmann/src/Point.cpp` - 实现文件
- `modules/bentleyottmann/include/Segment.h` - 使用 Point 的线段定义
- `modules/bentleyottmann/include/EventQueue.h` - 使用 Point 的事件队列
- `modules/bentleyottmann/include/Myers.h` - Myers 命名空间中的独立 Point 定义
