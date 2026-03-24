# SkPathOpsBounds

> 源文件: src/pathops/SkPathOpsBounds.h

## 概述

`SkPathOpsBounds` 是 Skia PathOps 模块中特殊的边界矩形结构,继承自 `SkRect`,但有一个重要差异:不将直线(水平或垂直线)视为空矩形。在标准的 `SkRect` 中,宽度或高度为零的矩形被视为空矩形,但在路径操作中,这些退化矩形仍然代表有效的几何元素(直线段),因此需要特殊处理。

该结构提供了扩展边界、包含性测试和相交性测试等操作,所有操作都考虑了退化情况(直线)的有效性。这对于路径操作算法正确处理直线段至关重要。

## 架构位置

`SkPathOpsBounds` 在 PathOps 架构中属于基础工具层:

```
数据结构层 (SkOpContour, SkOpSegment)
    ↓
几何计算层 (SkPathOpsCubic, SkPathOpsQuad)
    ↓
基础工具层
    ├─ SkPathOpsBounds ← 当前模块(边界矩形)
    ├─ SkPathOpsRect (双精度矩形)
    └─ SkPathOpsPoint (点和向量)
```

## 主要类与结构体

### SkPathOpsBounds

继承自 `SkRect`,提供路径操作专用的边界矩形功能。

**继承成员:**
- `SkScalar fLeft, fTop, fRight, fBottom`: 矩形边界

## 公共 API 函数

### Intersects (静态)
```cpp
static bool Intersects(const SkPathOpsBounds& a, const SkPathOpsBounds& b)
```
判断两个边界矩形是否相交。使用 ULP(Unit in the Last Place)容差比较:
- `AlmostLessOrEqualUlps`: 允许浮点误差的小于等于比较
- 检查四个方向的重叠:左右、上下

与 `SkRect::intersects()` 的区别:
- 使用容差比较,更鲁棒
- 正确处理退化矩形(直线)

### add (多个重载)
```cpp
void add(SkScalar left, SkScalar top, SkScalar right, SkScalar bottom)
void add(const SkPathOpsBounds& toAdd)
void add(const SkPoint& pt)
void add(const SkDPoint& pt)
```
扩展边界矩形以包含新的元素。与 `SkRect::join()` 的关键区别:
- **不检查空矩形**:即使宽度或高度为零,仍然有效
- **直接更新边界**:无条件地扩展到最小/最大值

四个重载版本:
1. 添加四个标量构成的矩形
2. 添加另一个 `SkPathOpsBounds`
3. 添加单精度点 `SkPoint`
4. 添加双精度点 `SkDPoint`(转换为单精度)

### almostContains
```cpp
bool almostContains(const SkPoint& pt) const
```
判断点是否近似在边界内。使用 ULP 容差比较,允许浮点误差:
- 点在边界上或略微超出(在容差范围内)返回 true
- 适用于处理浮点计算的不精确性

### contains
```cpp
bool contains(const SkPoint& pt) const
```
判断点是否在边界内。使用严格比较(无容差):
- 点必须严格在边界内或边界上
- 标准的包含性测试

## 内部实现细节

### ULP 容差比较

`AlmostLessOrEqualUlps` 是基于 ULP(Unit in the Last Place)的浮点比较:
- ULP 是浮点数的最小可表示间隔
- 允许几个 ULP 的误差范围
- 比绝对误差或相对误差更适合浮点比较

### 边界更新策略

`add` 方法使用无条件更新:
```cpp
if (left < fLeft) fLeft = left;
if (top < fTop) fTop = top;
if (right > fRight) fRight = right;
if (bottom > fBottom) fBottom = bottom;
```

不检查是否为空矩形,确保直线段(宽度或高度为零)也被正确处理。

### 退化矩形处理

对于退化矩形(直线段):
- 水平线:`fTop == fBottom`,但 `fLeft != fRight`
- 垂直线:`fLeft == fRight`,但 `fTop != fBottom`
- 点:`fLeft == fRight && fTop == fBottom`

所有这些情况都被视为有效边界,不会被忽略。

## 依赖关系

### 头文件依赖
- `include/core/SkRect.h`: 基类 SkRect
- `src/pathops/SkPathOpsRect.h`: 双精度矩形和比较函数

### 类型依赖
- **SkRect**: 基类,提供基础边界矩形功能
- **SkPoint**: 单精度点类型
- **SkDPoint**: 双精度点类型
- **AlmostLessOrEqualUlps**: 容差比较函数

## 设计模式与设计决策

### 继承设计

继承 `SkRect` 而非组合:
- 完全兼容 `SkRect` 接口
- 可以在需要 `SkRect` 的地方使用
- 只覆盖或添加必要的方法

### 公共继承

使用 `public` 继承:
- `SkPathOpsBounds` 是一种特殊的 `SkRect`
- 符合 is-a 关系
- 可以隐式转换为 `SkRect`

### 静态方法

`Intersects` 设计为静态方法:
- 明确表示是两个对象的关系,不偏向任何一方
- 语义上更清晰:`Intersects(a, b)` vs `a.intersects(b)`

### 方法重载

`add` 方法提供多个重载:
- 统一的接口名称,语义清晰
- 根据参数类型选择最优实现
- 避免了类型转换和临时对象

### 容差策略

提供两种包含性测试:
- `almostContains`: 带容差,适用于浮点计算
- `contains`: 无容差,适用于精确测试

给用户选择权,根据场景决定使用哪个。

## 性能考量

### 内联候选

所有方法定义在头文件中,可以内联:
- 避免函数调用开销
- 方法体都很小,适合内联
- 提高热路径性能

### 分支最小化

`add` 方法使用四个独立的 if 语句:
- 没有 else 分支,减少分支预测失败
- 每个维度独立更新,无依赖
- 编译器可以优化为条件移动指令

### 缓存友好

数据成员继承自 `SkRect`:
- 4 个 `SkScalar` 连续存储
- 通常 16 字节,一个缓存行内
- 访问局部性好

### 避免分配

所有操作都就地修改:
- `add` 方法直接修改当前对象
- 不创建临时对象或返回新对象
- 减少内存分配和拷贝

### 类型转换优化

`add(const SkDPoint& pt)` 手动转换:
```cpp
fLeft = SkDoubleToScalar(pt.fX);
```
而非先转换整个点,避免了临时对象。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkRect.h` | 基类 | 标准矩形类 |
| `src/pathops/SkPathOpsRect.h` | 依赖 | 双精度矩形和比较函数 |
| `src/pathops/SkPathOpsPoint.h` | 依赖 | 点类型定义 |
| `src/pathops/SkOpSegment.h/cpp` | 被依赖 | 使用边界进行快速剔除 |
| `src/pathops/SkOpContour.h/cpp` | 被依赖 | 轮廓边界计算 |
| `src/pathops/SkPathOpsCurve.h/cpp` | 被依赖 | 曲线边界计算 |
| `src/pathops/SkIntersections.h/cpp` | 被依赖 | 交点计算的边界检查 |
