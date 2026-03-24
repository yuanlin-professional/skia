# SkPathOpsTightBounds

> 源文件
> - src/pathops/SkPathOpsTightBounds.cpp

## 概述

`SkPathOpsTightBounds` 提供了计算路径紧凑边界框的功能。与 `SkPath::getBounds()` 返回的控制点边界框不同，紧凑边界框更准确地包围路径的实际几何形状，考虑了曲线的实际形状而非仅仅是控制点位置。

该模块通过两种策略计算边界框：
1. **快速路径**：如果路径"行为良好"（控制点在端点范围内），直接使用 `getBounds()`
2. **精确路径**：构建 PathOps 内部表示，计算曲线的实际边界

这在需要精确布局计算时特别有用，例如文本渲染、图形对齐等场景。

## 架构位置

该模块位于 PathOps 的工具层：

```
src/pathops/
├── SkOpEdgeBuilder.cpp          // 构建路径段
├── SkOpContour.cpp              // 轮廓管理
├── SkPathOpsCommon.cpp          // 通用算法
├── SkPathOpsTightBounds.cpp     // 紧凑边界计算（当前模块）
└── SkPathOpsTypes.h             // 基础类型
```

## 主要函数

### ComputeTightBounds()

```cpp
bool ComputeTightBounds(const SkPath& path, SkRect* result);
```

**参数：**
- `path`：输入路径
- `result`：输出边界框

**返回值：**
- `true`：成功计算边界
- `false`：计算失败（例如路径过于复杂）

**算法流程：**

**阶段1：快速检测**
```cpp
bool wellBehaved = true;
for (auto [verb, pts, w] : SkPathPriv::Iterate(path)) {
    switch (verb) {
        case SkPathVerb::kQuad:
        case SkPathVerb::kConic:
            wellBehaved &= between(pts[0].fX, pts[1].fX, pts[2].fX);
            wellBehaved &= between(pts[0].fY, pts[1].fY, pts[2].fY);
            break;
        case SkPathVerb::kCubic:
            wellBehaved &= between(pts[0].fX, pts[1].fX, pts[3].fX);
            wellBehaved &= between(pts[0].fY, pts[1].fY, pts[3].fY);
            wellBehaved &= between(pts[0].fX, pts[2].fX, pts[3].fX);
            wellBehaved &= between(pts[0].fY, pts[2].fY, pts[3].fY);
            break;
    }
}
```

检查所有曲线控制点是否在端点范围内：
- **二次曲线**：控制点 pts[1] 是否在 pts[0] 和 pts[2] 之间
- **三次曲线**：控制点 pts[1] 和 pts[2] 是否在 pts[0] 和 pts[3] 之间

如果所有控制点都在范围内，曲线不会超出端点边界框。

**阶段2：快速返回**
```cpp
if (wellBehaved) {
    *result = path.getBounds();
    return true;
}
```

**阶段3：精确计算**
```cpp
SkSTArenaAlloc<4096> allocator;
SkOpContour contour;
SkOpContourHead* contourList = static_cast<SkOpContourHead*>(&contour);
SkOpGlobalState globalState(contourList, &allocator
                            SkDEBUGPARAMS(false) SkDEBUGPARAMS(nullptr));

SkOpEdgeBuilder builder(path, contourList, &globalState);
if (!builder.finish()) {
    return false;
}
```

转换为 PathOps 内部表示，考虑曲线的实际形状。

**阶段4：合并边界**
```cpp
SkOpContour* current = contourList;
SkPathOpsBounds bounds = current->bounds();
while ((current = current->next())) {
    bounds.add(current->bounds());
}
*result = bounds;

if (!moveBounds.isEmpty()) {
    result->join(moveBounds);
}
```

合并所有轮廓的边界，包括孤立的 moveTo 点。

## 内部实现细节

### moveTo 点的处理

```cpp
SkRect moveBounds = { SK_ScalarMax, SK_ScalarMax, SK_ScalarMin, SK_ScalarMin };
...
case SkPathVerb::kMove:
    moveBounds.fLeft = std::min(moveBounds.fLeft, pts[0].fX);
    moveBounds.fTop = std::min(moveBounds.fTop, pts[0].fY);
    moveBounds.fRight = std::max(moveBounds.fRight, pts[0].fX);
    moveBounds.fBottom = std::max(moveBounds.fBottom, pts[0].fY);
    break;
```

跟踪所有 moveTo 点的边界，即使它们不属于任何轮廓的一部分。最后与主边界框合并。

### "行为良好"的定义

曲线"行为良好"意味着：
- 所有控制点的 X 坐标在端点 X 坐标之间
- 所有控制点的 Y 坐标在端点 Y 坐标之间

**示例：**
```
良好的二次曲线:
  起点: (0, 0)
  控制点: (5, 5)  // 5 在 [0, 10] 内
  终点: (10, 0)

不良的二次曲线:
  起点: (0, 0)
  控制点: (15, 5)  // 15 不在 [0, 10] 内
  终点: (10, 0)
```

### between() 函数

```cpp
inline bool between(double a, double b, double c) {
    return (a - b) * (c - b) <= 0;
}
```

判断 b 是否在 a 和 c 之间（无需知道 a 和 c 的顺序）。

### 排序的作用

```cpp
if (!SortContourList(&contourList, false, false)) {
    *result = moveBounds;
    return true;
}
```

尝试排序轮廓，如果失败（例如有自相交），退回到 moveBounds。

### 内存分配

```cpp
SkSTArenaAlloc<4096> allocator;
```

使用 4KB 的栈上 arena 分配器，快速分配临时数据结构。

## 依赖关系

**直接依赖:**
```cpp
#include "include/core/SkPath.h"           // SkPath 类型
#include "src/core/SkPathPriv.h"          // SkPathPriv::Iterate
#include "src/pathops/SkOpContour.h"      // SkOpContour
#include "src/pathops/SkOpEdgeBuilder.h"  // SkOpEdgeBuilder
#include "src/pathops/SkPathOpsCommon.h"  // SortContourList
#include "src/pathops/SkPathOpsBounds.h"  // SkPathOpsBounds
#include "src/base/SkArenaAlloc.h"        // SkSTArenaAlloc
```

**被依赖:**
- Skia 公共 API（通过某些导出函数）
- 文本渲染模块（精确边界计算）

## 设计模式与设计决策

### 1. 两层策略

首先尝试简单快速的方法，失败后使用复杂但精确的方法：
- 优化常见情况（大多数路径是良好的）
- 保证正确性（复杂路径仍能正确处理）

### 2. 原地迭代

```cpp
for (auto [verb, pts, w] : SkPathPriv::Iterate(path))
```

使用 C++17 结构化绑定，直接迭代路径数据，无需额外分配。

### 3. 惰性计算

只有在快速路径失败时才构建 PathOps 数据结构。

### 4. 容错设计

```cpp
if (!builder.finish()) {
    return false;
}
```

如果 PathOps 构建失败，返回 false 而非崩溃。

## 性能考量

### 1. 快速路径优化

大多数路径是良好的，快速路径只需遍历一次控制点，时间复杂度 O(n)。

### 2. 栈上分配

```cpp
SkSTArenaAlloc<4096> allocator;
```

4KB 栈空间足以处理大多数路径，避免堆分配。

### 3. 早期退出

```cpp
if (!wellBehaved) {
    break;  // 一旦发现不良曲线，停止检查
}
```

### 4. 避免重复计算

快速路径中，moveBounds 的更新与 wellBehaved 检查同时进行。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `include/core/SkPath.h` | 路径类型 | 输入 |
| `src/core/SkPathPriv.h` | 路径私有接口 | 迭代器 |
| `src/pathops/SkOpContour.h` | 轮廓 | 内部表示 |
| `src/pathops/SkOpEdgeBuilder.h` | 边构建器 | 路径转换 |
| `src/pathops/SkPathOpsCommon.h` | 通用算法 | 排序 |
| `src/pathops/SkPathOpsBounds.h` | 边界类型 | 精确边界 |
| `src/base/SkArenaAlloc.h` | 内存分配 | 临时分配 |
| `src/pathops/SkPathOpsTypes.h` | 基础类型 | between 函数 |
