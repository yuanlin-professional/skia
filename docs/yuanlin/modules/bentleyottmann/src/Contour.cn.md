# Contour.cpp - 路径轮廓提取实现

> 源文件: `modules/bentleyottmann/src/Contour.cpp`

## 概述

`Contour.cpp` 实现了从 `SkPath` 提取轮廓并转换为整数坐标表示的核心逻辑。该文件负责遍历路径中的动词序列（move、line、close），将浮点坐标缩放为整数坐标点，管理轮廓的打开与关闭，以及维护每个轮廓的包围矩形。

## 架构位置

- **头文件**：`modules/bentleyottmann/include/Contour.h`
- **输入源**：Skia 核心 `SkPath` 类
- **输出目标**：整数坐标的轮廓数据，供 Myers 算法使用
- **依赖**：`SkPath`、`SkPoint`、`SkScalar`、`Myers.h`

## 主要类与结构体

无新类定义。实现 `Contours` 类的成员函数和 `extend_rect` 辅助函数。

## 公共 API 函数

### `Contours::Make(SkPath path)`
从 SkPath 创建 Contours 的静态工厂方法：
1. 创建 `SkPath::Iter` 遍历路径
2. 对每个动词进行处理：
   - `kMove`：关闭当前轮廓（如有），记录新起点
   - `kLine`：添加线段端点到当前轮廓
   - `kClose`：关闭当前轮廓
   - `kConic`/`kQuad`/`kCubic`：未实现（`SK_ABORT`）
3. 最终关闭可能未关闭的轮廓

### `Contours::segments() const`
将轮廓转换为 `myers::Segment` 集合。目前标记为未实现。

## 内部实现细节

### `extend_rect(SkIRect r, Point p)`
静态辅助函数，将包围矩形扩展以包含新点 p。使用 `std::min`/`std::max` 更新四条边。

### `Contours::RoundSkPoint(SkPoint p)`
将浮点 `SkPoint` 转换为整数 `contour::Point`：
```cpp
return {SkScalarRoundToInt(p.x() * kScaleFactor), SkScalarRoundToInt(p.y() * kScaleFactor)};
```
坐标乘以 1024 后四舍五入，提供约 10 位的小数精度。

### `Contours::currentContourIsEmpty() const`
通过比较当前点数组大小与最后一个轮廓的结束索引来判断当前轮廓是否为空。如果 `fContours` 为空，则与 0 比较。

### `Contours::addPointToCurrentContour(SkPoint p)`
添加点到当前轮廓：
1. 若当前轮廓为空，先写入起始点 `fContourStart`（延迟写入优化）
2. 转换并添加新点
3. 更新包围矩形

### `Contours::moveToStartOfContour(SkPoint p)`
记录新轮廓的起始点（仅保存，不写入点数组）。

### `Contours::closeContourIfNeeded()`
如果当前轮廓非空，将包围矩形和当前点数组大小记录到 `fContours`，然后重置包围矩形。空轮廓被静默忽略。

## 依赖关系

- `modules/bentleyottmann/include/Contour.h` - 头文件
- `include/core/SkPath.h` - 路径迭代
- `include/core/SkPoint.h` - 浮点点类型
- `include/core/SkScalar.h` - `SkScalarRoundToInt`
- `include/private/base/SkTo.h` - 安全类型转换
- `modules/bentleyottmann/include/Myers.h` - `myers::Segment`
- `<algorithm>`, `<vector>` - 标准库

## 设计模式与设计决策

### 延迟写入起始点
轮廓的起始点（moveTo 目标）只有在第一次 addPointToCurrentContour 调用时才写入。这避免了为只有 moveTo 没有后续线段的"空"轮廓分配存储空间。

### 状态机式处理
路径处理本质上是一个状态机：moveToStartOfContour 设置起始状态，addPointToCurrentContour 在状态中添加数据，closeContourIfNeeded 完成状态转换。

### 安全的空轮廓处理
closeContourIfNeeded 检查轮廓是否为空后才记录，确保不会产生零长度的轮廓记录。

## 性能考量

- 路径遍历是单遍的 O(n)
- 包围矩形逐点更新避免了额外的遍历
- 扁平化存储（所有点在一个 vector 中）具有良好的缓存局部性
- `SkScalarRoundToInt` 的浮点到整数转换是必要的开销

## 相关文件

- `modules/bentleyottmann/include/Contour.h` - 头文件
- `modules/bentleyottmann/include/Myers.h` - Myers 线段类型
- `include/core/SkPath.h` - Skia 路径类及迭代器
- `modules/bentleyottmann/src/Myers.cpp` - Myers 算法实现
