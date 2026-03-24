# Contour.h - 路径轮廓数据结构

> 源文件: `modules/bentleyottmann/include/Contour.h`

## 概述

`Contour.h` 定义了用于表示和操作路径轮廓（contour）的数据结构。它提供了从 `SkPath` 提取轮廓信息并转换为整数坐标表示的功能，是 Skia 路径系统与 Bentley-Ottmann/Myers 计算几何算法之间的桥梁。通过将浮点路径坐标缩放并四舍五入为整数，为精确的几何计算提供基础。

## 架构位置

该文件位于路径处理与计算几何之间的转换层：

- **输入**：`SkPath`（Skia 核心路径类，使用浮点坐标）
- **输出**：整数坐标轮廓和 `myers::Segment` 线段集合
- **上游**：Skia 路径绘制和布尔运算
- **下游**：Myers 线段交点检测算法

## 主要类与结构体

### `contour::Point`
```cpp
struct Point {
    int32_t x;
    int32_t y;
};
```
简单的二维整数点，与 `bentleyottmann::Point` 和 `myers::Point` 结构相同但属于独立的 `contour` 命名空间。

### `contour::Contour`
```cpp
class Contour {
public:
    SkSpan<const Point> points;
    SkIRect bounds;
};
```
表示一个轮廓：一组有序点和包围矩形。注意这是一个视图类型（`SkSpan` 不拥有数据）。

### `contour::Contours`
核心类，管理从 `SkPath` 提取的所有轮廓数据：

- **存储结构**：
  - `fPoints`：所有轮廓的点序列（扁平化存储）
  - `fContours`：紧凑轮廓记录（`CompactContour`），存储包围矩形和结束索引
- **缩放因子**：`kScaleFactor = 1024`，将浮点坐标放大为整数
- **迭代器**：提供 `Iterator` 内部类，支持范围 for 循环
- **空矩形常量**：`kEmptyRect` 用于初始化包围矩形

### `Contours::Iterator`
- 输入迭代器（`input_iterator_tag`）
- `operator*` 返回 `Contour` 值类型（视图）
- 支持 `operator-` 用于计算迭代器距离

### `CompactContour`（私有）
```cpp
struct CompactContour {
    SkIRect bounds;
    int32_t end;
};
```
紧凑轮廓记录，存储包围矩形和点数组中的结束索引。

## 公共 API 函数

### `Contours::Make(SkPath path)`
静态工厂方法，从 `SkPath` 创建 `Contours`。遍历路径的动词序列（move、line、close 等），提取所有线段轮廓。目前仅支持直线段，圆锥曲线、二次曲线和三次曲线未实现。

### `Contours::operator[](size_t i)`
按索引访问轮廓，返回 `Contour` 视图对象。

### `Contours::begin()` / `end()`
返回迭代器，支持范围 for 循环。

### `Contours::size()` / `empty()`
获取轮廓数量和判空。

### `Contours::segments()`
将所有轮廓转换为 `std::vector<myers::Segment>`（目前标记为未实现）。

## 内部实现细节

### 坐标转换
`RoundSkPoint(SkPoint p)` 将浮点坐标乘以 `kScaleFactor`（1024）后四舍五入为 `int32_t`。放大因子 1024 在保持精度的同时仍在 `int32_t` 范围内留有足够空间。

### 轮廓构建流程
1. `moveToStartOfContour`：记录新轮廓的起始点
2. `addPointToCurrentContour`：添加点到当前轮廓，首次添加时写入起始点
3. `closeContourIfNeeded`：关闭当前轮廓，记录包围矩形和结束索引

### 延迟写入起始点
起始点（moveTo 的目标）在第一个 `addPointToCurrentContour` 调用时才真正写入 `fPoints`，避免为空轮廓分配存储。

### 包围矩形累积
通过 `extend_rect` 辅助函数逐点扩展包围矩形。初始值 `kEmptyRect` 使用 `{INT_MAX, INT_MAX, INT_MIN, INT_MIN}`，确保第一个点总能正确更新所有边界。

### Contours 的不可变性
`Make` 静态工厂方法返回完全构建好的 `Contours` 对象。对象构建完成后，`fPoints` 和 `fContours` 不再修改（虽然不是 const 成员，但没有公共的修改接口）。这使得多个 `Contour` 视图可以安全地同时引用同一 `Contours` 对象的数据。

### 路径迭代协议
`SkPath::Iter` 返回的记录包含动词（verb）和点数组。不同动词对应不同数量的控制点。当前实现仅处理 `kMove`（1 个点）、`kLine`（2 个点，使用 pts[1]）和 `kClose`（无需额外点）。

## 依赖关系

- `include/core/SkRect.h` - `SkIRect` 包围矩形
- `include/core/SkSpan.h` - 只读数组视图
- `include/private/base/SkAssert.h` - 断言
- `<limits.h>`, `<cstddef>`, `<cstdint>`, `<iterator>`, `<vector>` - 标准库
- 前向声明：`SkPath`、`SkPoint`、`myers::Segment`

## 设计模式与设计决策

### 紧凑存储
使用扁平化的点数组加偏移量索引而非独立的容器，减少内存碎片和分配次数。

### 视图模式
`Contour` 是轻量级视图对象（`SkSpan` + `SkIRect`），通过值返回无需动态内存分配。

### 缩放因子的选择
1024（2^10）作为缩放因子是二的幂，有利于某些优化，同时提供约 3 位小数精度。

### 渐进式实现
曲线类型（conic、quad、cubic）标记为 `SK_ABORT("Not implemented")`，暗示未来会通过曲线细分为线段来支持。

### 三个命名空间的 Point 类型
模块中存在三个独立的 Point 类型：`bentleyottmann::Point`、`myers::Point` 和 `contour::Point`。虽然结构相同（都是 `{int32_t x, y}`），但各自独立定义以避免命名空间耦合。`contour::Point` 最为简单，不定义任何运算符。

## 性能考量

- 扁平存储减少了内存分配和指针间接引用，所有轮廓的点共享一个连续的 `std::vector<Point>`
- `Iterator` 为轻量级值类型（仅包含一个引用和一个索引），复制开销极小
- `kScaleFactor` 为常量表达式，乘法可在编译期优化
- `currentContourIsEmpty` 通过比较索引判断，O(1) 复杂度
- `operator[]` 返回视图对象而非拷贝，避免数据复制
- `CompactContour` 结构体使用单个 `end` 索引而非 `start` 和 `end` 两个索引，通过前一个轮廓的 `end` 推导出当前轮廓的 `start`
- `SkIRect` 包围矩形的逐点更新避免了二次遍历

## 相关文件

- `modules/bentleyottmann/src/Contour.cpp` - 实现文件，包含 `Make`、`RoundSkPoint`、轮廓管理方法的实现
- `modules/bentleyottmann/include/Myers.h` - `myers::Segment` 定义，`segments()` 方法的返回类型
- `include/core/SkPath.h` - Skia 路径类，`Make` 方法的输入类型
- `include/core/SkRect.h` - `SkIRect` 整数矩形类，用于轮廓包围盒
- `include/core/SkSpan.h` - `SkSpan` 只读数组视图，`Contour::points` 的类型
- `include/core/SkPoint.h` - `SkPoint` 浮点点类型，`addPointToCurrentContour` 的参数类型
- `include/private/base/SkAssert.h` - `SkASSERT` 断言，用于 `operator[]` 的边界检查
- `modules/bentleyottmann/include/Point.h` - `bentleyottmann::Point`，结构相同但属于不同命名空间
- `modules/bentleyottmann/src/Myers.cpp` - Myers 算法实现，消费 `Contours::segments()` 的输出
- `include/private/base/SkTo.h` - `SkToSizeT` 和 `SkToS32` 安全类型转换
- `<limits.h>` - `INT_MAX` 和 `INT_MIN`，用于 `kEmptyRect` 初始值
- `<iterator>` - `std::input_iterator_tag`，Iterator 的迭代器类别
