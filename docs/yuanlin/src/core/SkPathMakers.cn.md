# SkPathMakers

> 源文件
> - src/core/SkPathMakers.h

## 概述

`SkPathMakers.h` 定义了一组模板化的点迭代器类,用于高效生成标准几何形状(矩形、椭圆、圆角矩形)的顶点序列。这些迭代器是 `SkPathRawShapes` 和路径构建系统的辅助工具,提供了一致的接口来遍历形状的关键点。

该文件包含基类模板 `SkPath_PointIterator` 和三个具体实现:`SkPath_RectPointIterator`、`SkPath_OvalPointIterator` 和 `SkPath_RRectPointIterator`。这些类采用编译时多态(模板),避免虚函数开销,适合性能敏感的路径构建场景。

## 架构位置

`SkPathMakers` 位于 Skia 路径系统的内部辅助层:

```
src/core/
├── SkPathRawShapes (标准形状构造)
│   └── 使用 SkPathMakers
├── SkPathMakers.h (点迭代器) ← 当前组件
├── SkPathBuilder (路径构建器)
└── SkPathData (数据容器)
```

使用流程:
```
SkPath_RectPointIterator
    ↓
生成矩形顶点序列
    ↓
SkPathRawShapes::Rect
    ↓
SkPathBuilder::addRect
```

## 主要类与结构体

### SkPath_PointIterator<N> 模板基类

通用点迭代器模板,支持任意 N 个点的形状。

**模板参数**:
- `N`: 形状的顶点数量

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPts | SkPoint[N] | 顶点数组(protected) |
| fCurrent | unsigned | 当前顶点索引(private) |
| fAdvance | unsigned | 前进步长(private) |

**公共接口**:

```cpp
// 构造函数
SkPath_PointIterator(SkPathDirection dir, unsigned startIndex);

// 获取当前点
const SkPoint& current() const;

// 移动到下一个点并返回
const SkPoint& next();
```

### SkPath_RectPointIterator 类

矩形点迭代器,生成4个顶点。

**继承关系**:
```
SkPath_PointIterator<4>
    ↑
SkPath_RectPointIterator
```

**构造函数**:
```cpp
SkPath_RectPointIterator(const SkRect& rect,
                         SkPathDirection dir,
                         unsigned startIndex);
```

**顶点顺序**:
```
fPts[0] = (left,  top)     // 左上
fPts[1] = (right, top)     // 右上
fPts[2] = (right, bottom)  // 右下
fPts[3] = (left,  bottom)  // 左下
```

### SkPath_OvalPointIterator 类

椭圆点迭代器,生成4个关键点(上下左右)。

**继承关系**:
```
SkPath_PointIterator<4>
    ↑
SkPath_OvalPointIterator
```

**构造函数**:
```cpp
SkPath_OvalPointIterator(const SkRect& oval,
                         SkPathDirection dir,
                         unsigned startIndex);
```

**顶点顺序**:
```
fPts[0] = (cx, top)     // 顶部中点
fPts[1] = (right, cy)   // 右侧中点
fPts[2] = (cx, bottom)  // 底部中点
fPts[3] = (left, cy)    // 左侧中点
```

### SkPath_RRectPointIterator 类

圆角矩形点迭代器,生成8个关键点。

**继承关系**:
```
SkPath_PointIterator<8>
    ↑
SkPath_RRectPointIterator
```

**构造函数**:
```cpp
SkPath_RRectPointIterator(const SkRRect& rrect,
                          SkPathDirection dir,
                          unsigned startIndex);
```

**顶点顺序**:
```
fPts[0] = 左上角右端点
fPts[1] = 右上角左端点
fPts[2] = 右上角上端点
fPts[3] = 右下角上端点
fPts[4] = 右下角左端点
fPts[5] = 左下角右端点
fPts[6] = 左下角下端点
fPts[7] = 左上角下端点
```

## 公共 API 函数

### 基类接口

```cpp
// 构造迭代器
SkPath_PointIterator(SkPathDirection dir, unsigned startIndex);

// 获取当前点
const SkPoint& current() const {
    SkASSERT(fCurrent < N);
    return fPts[fCurrent];
}

// 前进到下一个点
const SkPoint& next() {
    fCurrent = (fCurrent + fAdvance) % N;
    return this->current();
}
```

## 内部实现细节

### 方向和起点计算

构造函数处理方向和起点:

```cpp
SkPath_PointIterator(SkPathDirection dir, unsigned startIndex)
    : fCurrent(startIndex % N)
    , fAdvance(dir == SkPathDirection::kCW ? 1 : N - 1)
{}
```

**逻辑**:
- `fCurrent`: 起点索引模 N
- `fAdvance`: 顺时针为1,逆时针为 N-1(等价于 -1 mod N)

### 矩形顶点初始化

```cpp
SkPath_RectPointIterator::SkPath_RectPointIterator(
    const SkRect& rect,
    SkPathDirection dir,
    unsigned startIndex)
    : SkPath_PointIterator(dir, startIndex)
{
    fPts[0] = SkPoint::Make(rect.fLeft, rect.fTop);
    fPts[1] = SkPoint::Make(rect.fRight, rect.fTop);
    fPts[2] = SkPoint::Make(rect.fRight, rect.fBottom);
    fPts[3] = SkPoint::Make(rect.fLeft, rect.fBottom);
}
```

### 椭圆顶点初始化

```cpp
SkPath_OvalPointIterator::SkPath_OvalPointIterator(
    const SkRect& oval,
    SkPathDirection dir,
    unsigned startIndex)
    : SkPath_PointIterator(dir, startIndex)
{
    const SkScalar cx = oval.centerX();
    const SkScalar cy = oval.centerY();

    fPts[0] = SkPoint::Make(cx, oval.fTop);
    fPts[1] = SkPoint::Make(oval.fRight, cy);
    fPts[2] = SkPoint::Make(cx, oval.fBottom);
    fPts[3] = SkPoint::Make(oval.fLeft, cy);
}
```

### 圆角矩形顶点初始化

```cpp
SkPath_RRectPointIterator::SkPath_RRectPointIterator(
    const SkRRect& rrect,
    SkPathDirection dir,
    unsigned startIndex)
    : SkPath_PointIterator(dir, startIndex)
{
    const SkRect& bounds = rrect.getBounds();
    const SkScalar L = bounds.fLeft;
    const SkScalar T = bounds.fTop;
    const SkScalar R = bounds.fRight;
    const SkScalar B = bounds.fBottom;

    // 每个角两个点,按顺序排列
    fPts[0] = SkPoint::Make(L + rrect.radii(SkRRect::kUpperLeft_Corner).fX, T);
    fPts[1] = SkPoint::Make(R - rrect.radii(SkRRect::kUpperRight_Corner).fX, T);
    fPts[2] = SkPoint::Make(R, T + rrect.radii(SkRRect::kUpperRight_Corner).fY);
    fPts[3] = SkPoint::Make(R, B - rrect.radii(SkRRect::kLowerRight_Corner).fY);
    fPts[4] = SkPoint::Make(R - rrect.radii(SkRRect::kLowerRight_Corner).fX, B);
    fPts[5] = SkPoint::Make(L + rrect.radii(SkRRect::kLowerLeft_Corner).fX, B);
    fPts[6] = SkPoint::Make(L, B - rrect.radii(SkRRect::kLowerLeft_Corner).fY);
    fPts[7] = SkPoint::Make(L, T + rrect.radii(SkRRect::kUpperLeft_Corner).fY);
}
```

### 循环前进机制

```cpp
const SkPoint& next() {
    // 模运算实现循环
    fCurrent = (fCurrent + fAdvance) % N;
    return this->current();
}
```

**示例**(N=4, CW):
- `fCurrent=0, fAdvance=1 → next() → fCurrent=1`
- `fCurrent=3, fAdvance=1 → next() → fCurrent=0` (循环)

**示例**(N=4, CCW):
- `fCurrent=0, fAdvance=3 → next() → fCurrent=3`
- `fCurrent=0, fAdvance=3 → next() → fCurrent=3` (等价于 -1)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPoint | 点坐标 |
| SkPathTypes | SkPathDirection |
| SkRRect | 圆角矩形 |
| SkRect | 矩形边界 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkPathRawShapes | 标准形状构造 |
| SkPathBuilder | 间接使用 |

## 设计模式与设计决策

### 模板静态多态

使用 CRTP 风格避免虚函数:
```cpp
template <unsigned N>
class SkPath_PointIterator {
protected:
    SkPoint fPts[N];  // 编译时固定大小
};
```

优点:
- 零运行时开销
- 内联优化
- 类型安全

### 迭代器模式

提供统一的遍历接口:
```cpp
SkPath_RectPointIterator iter(rect, dir, start);
for (int i = 0; i < 4; ++i) {
    SkPoint pt = iter.current();
    // 使用点
    iter.next();
}
```

### 值语义

点存储在迭代器内部:
- 简化内存管理
- 栈分配友好
- 缓存局部性好

### 模运算技巧

使用 `% N` 实现循环:
- 简洁的代码
- 无分支逻辑
- 编译器易优化

### 方向抽象

`fAdvance` 统一处理方向:
- CW: `fAdvance = 1`
- CCW: `fAdvance = N - 1`
- 无需条件判断

## 性能考量

### 编译时优化

- 模板参数 N 在编译时已知
- 数组大小固定,无动态分配
- `% N` 可优化为位运算(当N为2的幂)

### 内联友好

- 所有方法都很小
- 适合内联
- 无虚函数调用

### 缓存友好

- 顶点数据紧凑存储
- 顺序访问模式
- 栈上分配

### 零开销抽象

迭代器生成的机器码几乎等同于手写循环。

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPathTypes.h | 依赖 | SkPathDirection |
| include/core/SkPoint.h | 依赖 | 点坐标 |
| include/core/SkRRect.h | 依赖 | 圆角矩形 |
| src/core/SkPathRawShapes.h | 被使用 | 标准形状构造 |
