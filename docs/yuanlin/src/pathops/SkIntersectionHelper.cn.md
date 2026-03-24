# SkIntersectionHelper

> 源文件: src/pathops/SkIntersectionHelper.h

## 概述

`SkIntersectionHelper.h` 是 Skia 路径操作模块中的一个轻量级辅助类头文件,提供了用于遍历和访问路径段(segments)的便捷接口。该类充当 `SkOpSegment` 的包装器,简化了在交点计算过程中对段的迭代和属性查询操作。它是路径操作算法中段遍历和交点查找的核心工具类,通过提供统一的访问接口,使得复杂的几何计算代码更加清晰和易于维护。

该类的设计遵循迭代器模式,支持线性遍历轮廓(contour)中的所有段,并提供了段类型识别、边界框查询、点坐标访问等常用操作,是交点计算管道中不可或缺的基础设施。

## 架构位置

`SkIntersectionHelper.h` 位于路径操作的交点计算层:

- **模块路径**: `src/pathops/`
- **类型**: 头文件(header-only 辅助类)
- **功能层级**: 交点计算辅助工具
- **核心类**: `SkIntersectionHelper`
- **依赖组件**:
  - `SkOpSegment`: 路径段的核心表示
  - `SkOpContour`: 路径轮廓管理
  - `SkPath`: Skia 路径类型定义
  - `SkPathOpsPoint`: 点类型(调试模式)
- **被使用者**:
  - `SkAddIntersections.cpp`: 批量添加交点
  - 各种交点计算函数
  - 轮廓遍历算法

该类是路径操作中段遍历的标准接口,为上层算法提供了一致的访问方式。

## 主要类与结构体

### SkIntersectionHelper (核心辅助类)

轻量级的段访问包装器,封装了 `SkOpSegment*` 指针并提供便捷方法。

**成员变量**:
```cpp
SkOpSegment* fSegment;  // 当前指向的段
```

**段类型枚举**:
```cpp
enum SegmentType {
    kHorizontalLine_Segment = -1,   // 水平线段(特殊优化)
    kVerticalLine_Segment = 0,      // 垂直线段(特殊优化)
    kLine_Segment = SkPath::kLine_Verb,     // 普通直线
    kQuad_Segment = SkPath::kQuad_Verb,     // 二次曲线
    kConic_Segment = SkPath::kConic_Verb,   // 圆锥曲线
    kCubic_Segment = SkPath::kCubic_Verb    // 三次曲线
};
```

注意:水平线和垂直线使用负值和零,与 `SkPath::Verb` 枚举值区分开,以便进行优化处理。

## 公共 API 函数

### 初始化与遍历

#### `void init(SkOpContour* contour)`

初始化辅助器,指向轮廓的第一个段。

**参数**:
- `contour`: 要遍历的轮廓

**用法**:
```cpp
SkIntersectionHelper helper;
helper.init(contour);
```

#### `bool advance()`

前进到下一个段。

**返回值**:
- `true`: 成功前进到下一个段
- `false`: 已到达轮廓末尾

**用法**:
```cpp
while (helper.advance()) {
    // 处理当前段
}
```

#### `bool startAfter(const SkIntersectionHelper& after)`

从指定辅助器的下一个段开始。

**参数**:
- `after`: 参考辅助器

**返回值**:
- `true`: 成功定位到后续段
- `false`: 无后续段

**用途**: 避免重复计算已处理过的段对。

### 属性访问

#### `SkOpSegment* segment() const`

获取当前段的指针。

**返回值**: 当前 `SkOpSegment*`

#### `SkOpContour* contour() const`

获取当前段所属的轮廓。

**返回值**: `SkOpContour*`

#### `const SkPathOpsBounds& bounds() const`

获取当前段的边界框。

**返回值**: 轴对齐边界框(AABB)

**用途**: 快速剔除不相交的段对。

#### `const SkPoint* pts() const`

获取当前段的控制点数组。

**返回值**: 指向控制点数组的指针

**数组大小**:
- 直线: 2个点
- 二次曲线: 3个点
- 三次曲线: 4个点

#### `SegmentType segmentType() const`

获取段的类型,并对水平/垂直线进行特殊标识。

**返回值**: `SegmentType` 枚举值

**实现逻辑**:
```cpp
SegmentType type = (SegmentType) fSegment->verb();
if (type != kLine_Segment) {
    return type;  // 非直线直接返回
}
// 直线需要进一步判断方向
if (fSegment->isHorizontal()) {
    return kHorizontalLine_Segment;
}
if (fSegment->isVertical()) {
    return kVerticalLine_Segment;
}
return kLine_Segment;
```

#### `SkScalar weight() const`

获取圆锥曲线的权重参数。

**返回值**: 权重值(仅对 `kConic_Segment` 有效)

### 边界框快捷访问

以下方法提供对边界框各边的直接访问:

#### `SkScalar left() const` / `SkScalar x() const`
返回边界框的左边界(最小 x 坐标)。

#### `SkScalar right() const`
返回边界框的右边界(最大 x 坐标)。

#### `SkScalar top() const` / `SkScalar y() const`
返回边界框的上边界(最小 y 坐标)。

#### `SkScalar bottom() const`
返回边界框的下边界(最大 y 坐标)。

### 翻转检测

#### `bool xFlipped() const`

检测 x 方向是否翻转(边界框左边界是否不是第一个控制点的 x 坐标)。

**返回值**:
- `true`: x 方向翻转
- `false`: x 方向未翻转

**实现**:
```cpp
return x() != pts()[0].fX;
```

#### `bool yFlipped() const`

检测 y 方向是否翻转。

**返回值**:
- `true`: y 方向翻转
- `false`: y 方向未翻转

## 内部实现细节

### 1. 轻量级包装器设计

`SkIntersectionHelper` 仅包含一个指针成员,开销极小:
```cpp
private:
    SkOpSegment* fSegment;
```

所有操作都是对 `fSegment` 的委托调用,无额外开销。

### 2. 段类型识别的优化

`segmentType()` 方法将水平线和垂直线作为特殊类型标识:

**设计动机**:
- 水平线和垂直线的交点计算有优化算法
- 通过类型快速分发到专用计算函数
- 避免通用旋转和投影计算

**枚举值选择**:
- `kHorizontalLine_Segment = -1`: 负值,与标准 Verb 区分
- `kVerticalLine_Segment = 0`: 零值,便于判断
- 其他类型直接映射到 `SkPath::Verb`

### 3. 遍历模式

典型的使用模式:

```cpp
SkIntersectionHelper outerHelper, innerHelper;
outerHelper.init(contourList);
do {
    innerHelper.startAfter(outerHelper);  // 避免重复计算
    do {
        // 计算 outerHelper.segment() 与 innerHelper.segment() 的交点
        if (outerHelper.bounds().intersects(innerHelper.bounds())) {
            // 边界框相交,进行精确交点计算
        }
    } while (innerHelper.advance());
} while (outerHelper.advance());
```

### 4. 边界框快速剔除

边界框方法支持快速剔除:

```cpp
if (helper1.left() > helper2.right() ||
    helper1.right() < helper2.left() ||
    helper1.top() > helper2.bottom() ||
    helper1.bottom() < helper2.top()) {
    // 边界框不相交,跳过交点计算
}
```

### 5. 翻转检测的用途

`xFlipped()` 和 `yFlipped()` 用于:
- 确定段的方向性
- 调整交点参数的顺序
- 处理反向遍历的情况

边界框的坐标总是最小值在前,但段的控制点顺序可能相反,翻转标志用于检测这种不一致。

## 依赖关系

### 直接依赖

**核心组件**:
- `include/core/SkPath.h`: 路径类型和 Verb 枚举
- `src/pathops/SkOpContour.h`: 轮廓管理
- `src/pathops/SkOpSegment.h`: 段的核心表示

**调试依赖**:
- `src/pathops/SkPathOpsPoint.h`: 点类型(仅调试模式)

### 被依赖情况

该类被以下模块广泛使用:
- `SkAddIntersections.cpp`: 交点批量添加
- 各种交点计算实现文件
- 轮廓排序和遍历算法
- 路径布尔运算的主循环

## 设计模式与设计决策

### 1. 迭代器模式

`SkIntersectionHelper` 实现了迭代器模式的核心接口:
- `init()`: 初始化到起始位置
- `advance()`: 前进到下一个元素
- `segment()`: 访问当前元素

### 2. 外观模式(Facade)

该类作为 `SkOpSegment` 的外观,简化了常用操作:
- 直接访问边界框各边
- 段类型的智能识别
- 隐藏复杂的内部结构

### 3. 轻量级代理

仅持有指针,不拷贝数据:
- 按值传递开销极小
- 多个辅助器可指向同一段
- 支持快速创建和销毁

### 4. 命名一致性

方法命名遵循 Skia 的约定:
- `left()`, `right()`, `top()`, `bottom()`: 与 `SkRect` 一致
- `bounds()`: 标准边界框访问
- `pts()`: Skia 中点数组的常用名称

### 5. 最小接口原则

只暴露交点计算所需的必要接口:
- 不提供修改操作
- 不暴露内部实现细节
- 专注于遍历和查询

## 性能考量

### 1. 零开销抽象

- **内联函数**: 所有方法都是简单的委托调用,编译器可完全内联
- **单指针成员**: 仅 8 字节(64位系统)
- **无虚函数**: 无虚函数表开销

### 2. 缓存友好

- **顺序遍历**: `advance()` 按链表顺序遍历,缓存友好
- **边界框预计算**: `SkOpSegment` 预计算并缓存边界框
- **局部性**: 相邻段通常在内存中相邻

### 3. 快速路径选择

`segmentType()` 支持编译时优化:
```cpp
switch (helper.segmentType()) {
    case kHorizontalLine_Segment:
        // 编译器可生成跳转表
        horizontalIntersect();
        break;
    case kVerticalLine_Segment:
        verticalIntersect();
        break;
    // ...
}
```

### 4. 边界框剔除效率

边界框方法支持 O(1) 的相交测试:
- 避免昂贵的交点计算
- 典型剔除率 > 90%
- SIMD 友好(4个比较操作)

### 5. 避免重复计算

`startAfter()` 方法确保每对段只计算一次:
```cpp
// O(n²/2) 而非 O(n²)
for (outer.init(contour); outer.valid(); outer.advance()) {
    for (inner.startAfter(outer); inner.valid(); inner.advance()) {
        // 只计算 (i, j) 其中 j > i
    }
}
```

## 相关文件

### 核心依赖

- `src/pathops/SkOpSegment.h` / `.cpp`: 段的实现
- `src/pathops/SkOpContour.h` / `.cpp`: 轮廓管理
- `include/core/SkPath.h`: 路径类型定义

### 使用该类的文件

- `src/pathops/SkAddIntersections.cpp`: 主要使用者
- `src/pathops/SkPathOpsOp.cpp`: 布尔运算
- 各种交点计算实现文件

### 相关辅助类

- `src/pathops/SkPathWriter.h`: 路径构建辅助器
- `src/pathops/SkIntersections.h`: 交点集合管理

### 测试文件

- `tests/PathOpsExtendedTest.cpp`: 扩展测试
- `tests/PathOpsThreadedCommon.cpp`: 多线程测试

该文件虽然代码量小(仅113行),但在路径操作系统中扮演了关键的桥梁角色,通过提供清晰、高效的段访问接口,极大地简化了交点计算代码的编写和维护。
