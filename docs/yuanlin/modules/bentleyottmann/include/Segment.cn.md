# Segment.h - 线段定义与交点计算接口

> 源文件: `modules/bentleyottmann/include/Segment.h`

## 概述

`Segment.h` 是 Bentley-Ottmann 线段交点算法模块的核心头文件，定义了二维整数坐标线段（`Segment`）和交叉点（`Crossing`）数据结构，以及一系列线段比较和交点计算的函数声明。这些定义构成了整个计算几何模块的基础数据类型。

## 架构位置

该头文件位于 `modules/bentleyottmann/include/` 目录，是 Bentley-Ottmann 模块的基础层：

- **被依赖**：几乎所有模块内文件都依赖此头文件，包括 `EventQueue.h`、`SweepLine.h`、`EventQueueInterface.h`
- **依赖**：仅依赖 `Point.h`（同模块）和标准库
- **实现文件**：`modules/bentleyottmann/src/Segment.cpp` 提供函数实现

## 主要类与结构体

### `Segment`
```cpp
struct Segment {
    Point p0;
    Point p1;
    Point upper() const;
    Point lower() const;
    std::tuple<int32_t, int32_t, int32_t, int32_t> bounds() const;
};
```
- 表示由两个 `Point` 端点定义的线段
- `upper()` 返回 Y 值较小的端点（屏幕坐标系中较高的点）；水平线段返回左端点
- `lower()` 返回 Y 值较大的端点；水平线段返回右端点
- `bounds()` 返回包围盒 `(left, top, right, bottom)`

### `Crossing`
```cpp
struct Crossing {
    const Segment s0;
    const Segment s1;
    const Point crossing;
};
```
记录两条线段的交叉信息，包含两条线段及其交点坐标。

## 公共 API 函数

### 运算符
- `operator==`：比较两条线段是否相同（比较归一化后的端点）
- `operator<`：线段排序，按 upper 点再按 lower 点排序

### `no_intersection_by_bounding_box(s0, s1)`
通过包围盒快速排除不可能相交的线段对。如果两条线段的包围盒不重叠则返回 `true`。

### `intersect(s0, s1)`
计算两条线段的交点。返回 `std::optional<Point>`，无交点时返回 `nullopt`。注意：假设线段不包含端点（开区间）。

### `less_than_at(s0, s1, y)`
在给定水平扫描线 y 处比较两条线段的 x 截距。用于维护扫描线状态的线段顺序。

### `point_less_than_segment_in_x(p, segment)`
判断点 p 的 x 坐标是否小于线段在 p.y 水平线处的 x 截距。

### `rounded_point_less_than_segment_in_x_lower(s, p)` / `rounded_point_less_than_segment_in_x_upper(s, p)`
带四舍五入的点-线段 x 坐标比较函数。定义为 `x < floor(s(y) + 0.5)`，分别对应不等式的下界和上界。设计用于与 `std::lower_bound` 配合使用。

### `compare_slopes(s0, s1)`
比较两条线段的斜率。返回 -1、0 或 1。水平线段的斜率被定义为最大值。斜率从负 x 轴方向逆时针递增到正 x 轴方向。

## 内部实现细节

交点计算和斜率比较的具体实现位于 `Segment.cpp` 中。这些函数使用 64 位和 96 位整数运算来避免浮点舍入误差。

## 依赖关系

- `modules/bentleyottmann/include/Point.h` - 二维整数点定义
- `<cstdint>` - 整数类型
- `<optional>` - 可选返回值
- `<tuple>` - bounds 返回类型

## 设计模式与设计决策

### 值语义
`Segment` 和 `Crossing` 均为简单结构体，使用值语义，便于在集合和向量中存储和比较。

### 开区间交点
`intersect` 函数将线段视为不包含端点的开区间，这是 Bentley-Ottmann 算法的要求——端点处的"交叉"由事件队列单独处理。

### 自由函数设计
比较和交点函数设计为自由函数而非成员函数，更符合算法库的函数式风格，也便于在标准库算法中作为谓词使用。

## 性能考量

- 包围盒预过滤（`no_intersection_by_bounding_box`）可以快速排除大量不相交的线段对
- 四舍五入比较函数与 `std::lower_bound` 配合使用可实现 O(log n) 的查找
- 整数坐标避免了浮点比较的精度问题

## 相关文件

- `modules/bentleyottmann/src/Segment.cpp` - 函数实现
- `modules/bentleyottmann/include/Point.h` - 点定义
- `modules/bentleyottmann/include/Int96.h` - 96 位整数运算（用于精确比较）
- `modules/bentleyottmann/include/SweepLine.h` - 使用线段比较函数的扫描线
- `modules/bentleyottmann/include/EventQueue.h` - 使用线段的事件队列
