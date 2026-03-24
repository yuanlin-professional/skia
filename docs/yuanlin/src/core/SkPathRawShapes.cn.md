# SkPathRawShapes

> 源文件
> - src/core/SkPathRawShapes.h
> - src/core/SkPathRawShapes.cpp

## 概述

`SkPathRawShapes` 是 Skia 中提供栈上分配路径形状的命名空间。它包含一系列类（`Rect`、`Oval`、`RRect`、`Triangle`），这些类继承自 `SkPathRaw` 并提供自己的栈存储空间，用于常见几何形状的高效表示。这些类避免了堆内存分配，非常适合性能敏感的渲染代码，特别是在已知形状类型的场景下。

## 架构位置

`SkPathRawShapes` 位于 Skia 核心路径系统的实用层：

- 位于 `src/core` 目录，作为内部优化工具
- 建立在 `SkPathRaw` 基础之上，提供具体形状实现
- 使用 `SkPathMakers` 中的迭代器辅助类生成路径点
- 为渲染管线提供零堆分配的形状创建方式
- 与 `SkPathBuilder` 和 `SkPath` 形成性能优化的替代方案

## 主要类与结构体

### SkPathRawShapes::Rect

栈分配的矩形路径。

**继承关系**

继承自 `SkPathRaw`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStorage` | `SkPoint[4]` | 存储矩形四个顶点的栈数组 |

**构造函数**

```cpp
explicit Rect(const SkRect&, SkPathDirection = SkPathDirection::kCW, unsigned index = 0);
```

从 `SkRect` 创建路径，支持指定绘制方向和起始顶点索引。

### SkPathRawShapes::Oval

栈分配的椭圆路径。

**继承关系**

继承自 `SkPathRaw`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStorage` | `SkPoint[9]` | 存储椭圆控制点的栈数组（9个点：1个起点 + 4个圆锥曲线，每个圆锥曲线2个点） |

**构造函数**

```cpp
explicit Oval(const SkRect&, SkPathDirection = SkPathDirection::kCW, unsigned index = 1);
```

从边界矩形创建椭圆路径，使用4个圆锥曲线表示。

### SkPathRawShapes::RRect

栈分配的圆角矩形路径。

**继承关系**

继承自 `SkPathRaw`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStorage` | `SkPoint[13]` | 存储圆角矩形控制点的栈数组（最坏情况：1个起点 + 4个圆锥曲线 + 4条线段） |

**构造函数**

```cpp
RRect(const SkRRect&, SkPathDirection dir, unsigned index);
RRect(const SkRRect& rr, SkPathDirection dir);
explicit RRect(const SkRRect& rr);
```

支持多种构造方式，可指定绘制方向和起始索引。内部会检测退化情况（矩形或椭圆）。

### SkPathRawShapes::Triangle

栈分配的三角形路径。

**继承关系**

继承自 `SkPathRaw`

**构造函数**

```cpp
Triangle(SkSpan<const SkPoint> threePoints, const SkRect& bounds);
```

从三个点和边界矩形创建三角形路径，构造时会计算凸性方向。

## 公共 API 函数

所有形状类通过继承 `SkPathRaw` 获得其公共 API：

- `points()`, `verbs()`, `conics()` - 访问路径数据
- `bounds()`, `fillType()`, `convexity()` - 访问元数据
- `iter()` - 获取路径迭代器

各形状类主要通过构造函数提供特定形状的创建功能。

## 内部实现细节

### 矩形生成

`set_as_rect` 函数实现矩形路径生成：

```cpp
// 动词序列：Move, Line, Line, Line, Close
const SkPathVerb gRectVerbs[] = {
    SkPathVerb::kMove,
    SkPathVerb::kLine,
    SkPathVerb::kLine,
    SkPathVerb::kLine,
    SkPathVerb::kClose
};
```

使用 `SkPath_RectPointIterator` 按指定方向和起始索引生成4个顶点。

### 椭圆生成

`set_as_oval` 函数使用4个圆锥曲线表示椭圆：

```cpp
// 动词序列：Move, Conic, Conic, Conic, Conic, Close
const SkPathVerb gOvalVerbs[] = {
    SkPathVerb::kMove,
    SkPathVerb::kConic,
    SkPathVerb::kConic,
    SkPathVerb::kConic,
    SkPathVerb::kConic,
    SkPathVerb::kClose
};

// 每个圆锥曲线的权重为 √2/2（四分之一圆的标准权重）
const float gFourQuarterCircleConics[] = {
    SK_ScalarRoot2Over2,
    SK_ScalarRoot2Over2,
    SK_ScalarRoot2Over2,
    SK_ScalarRoot2Over2,
};
```

椭圆使用9个点：1个起点 + 8个控制点（每个圆锥曲线2个）。

### 圆角矩形生成

`set_as_rrect` 函数处理圆角矩形的复杂情况：

**动词序列优化**

根据起始位置选择不同的动词序列：

- **线段起始**（`gRRectVerbs_LineStart`）：Line-Conic 交替，最多13个点
- **圆锥曲线起始**（`gRRectVerbs_ConicStart`）：Conic-Line 交替，最后一条线段由 Close 完成，12个点

**退化检测**

构造函数会检测并处理退化情况：

```cpp
if (rrect.isRect() || rrect.isEmpty()) {
    // 退化为矩形
    set_as_rect(this, fStorage, bounds, dir, (index + 1) / 2);
} else if (rrect.isOval()) {
    // 退化为椭圆
    set_as_oval(this, fStorage, bounds, dir, index / 2);
} else {
    // 完整圆角矩形
    set_as_rrect(this, fStorage, rrect, dir, index);
}
```

### 三角形凸性计算

`tri_to_convexity` 函数使用叉积判断三角形的绕向：

```cpp
SkVector u = pts[1] - pts[0];
SkVector v = pts[2] - pts[1];
float cross = u.fX * v.fY - u.fY * v.fX;

return cross > 0 ? SkPathConvexity::kConvex_CW
                 : (cross < 0) ? SkPathConvexity::kConvex_CCW
                                : SkPathConvexity::kConvex_Degenerate;
```

### 共享常量

为避免重复定义，圆锥曲线权重 `gFourQuarterCircleConics` 被椭圆和圆角矩形共用。

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkPathRaw` | 基类，提供路径视图接口 |
| `SkPathMakers` | 提供点迭代器（`SkPath_RectPointIterator` 等） |
| `SkPathTypes` | 路径类型定义（方向、填充类型等） |
| `SkRRect` | 圆角矩形定义 |
| `SkRect` | 矩形定义 |
| `SkPoint` | 点数据类型 |

**被依赖的模块**

| 模块 | 关系 |
|------|------|
| 渲染管线 | 使用这些形状进行快速形状绘制 |
| 图形上下文 | 在性能敏感路径中使用栈分配形状 |

## 设计模式与设计决策

### 栈分配优化

核心设计目标是完全避免堆分配：

- 每个形状类包含固定大小的 `fStorage` 数组
- 继承 `SkPathRaw` 使用存储数组的跨度
- 适合短生命周期、频繁创建的形状对象

### 退化处理策略

`RRect` 构造函数智能检测退化情况：

- 圆角半径为0时退化为矩形
- 圆角半径等于半边长时退化为椭圆
- 避免不必要的复杂路径生成，提高性能

### 起始索引灵活性

所有形状支持指定起始索引：

- 允许从不同顶点开始绘制
- 保持路径一致性，同时满足不同的绘制需求
- 对于圆角矩形，起始索引从0到7（8个可能的起始点）

### 方向参数化

支持顺时针（CW）和逆时针（CCW）绘制方向：

- 影响路径的凸性判断
- 与填充规则（Winding）配合使用
- 统一的方向参数接口

### 迭代器模式

使用 `SkPath_RectPointIterator`、`SkPath_OvalPointIterator` 和 `SkPath_RRectPointIterator`：

- 封装复杂的点生成逻辑
- 支持不同方向和起始索引
- 代码复用和维护性提升

## 性能考量

### 零堆分配

最重要的性能优势：

- 所有数据在栈上分配
- 避免内存分配器开销
- 避免内存碎片化
- 缓存局部性好

### 常量路径数据

动词和圆锥曲线权重使用静态常量数组：

- 避免每次构造时的初始化开销
- 数据共享，减少内存占用
- 编译器优化友好

### 最小化计算

- 退化检测避免不必要的复杂计算
- 点迭代器高效生成路径点
- 预计算的分段掩码和凸性信息

### 适用场景

最佳使用场景：

- 已知形状类型的快速渲染
- 高频率形状创建和销毁
- 性能关键路径（如动画循环）
- 需要避免内存分配的实时系统

### 性能权衡

相比完整的 `SkPath`：

- **优势**：零堆分配，创建速度快
- **劣势**：仅支持固定形状，不可动态修改
- **适用性**：临时几何形状的理想选择

### 内存占用

各形状类的栈空间占用：

- `Rect`: 4个点 = 32字节（64位系统）
- `Oval`: 9个点 = 72字节
- `RRect`: 13个点 = 104字节
- `Triangle`: 使用外部点数据，无额外存储

加上 `SkPathRaw` 的元数据（约40-50字节），总开销小于200字节。

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `src/core/SkPathRaw.h/.cpp` | 基类定义和实现 |
| `src/core/SkPathMakers.h` | 点迭代器辅助类 |
| `include/core/SkRRect.h` | 圆角矩形定义 |
| `include/core/SkRect.h` | 矩形定义 |
| `include/core/SkPathTypes.h` | 路径类型和枚举 |
| `src/core/SkPathEnums.h` | 路径凸性枚举 |
| `include/core/SkPath.h` | 标准路径类对比 |
