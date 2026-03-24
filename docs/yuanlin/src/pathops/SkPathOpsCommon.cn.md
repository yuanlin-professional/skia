# SkPathOpsCommon

> 源文件: src/pathops/SkPathOpsCommon.h, src/pathops/SkPathOpsCommon.cpp

## 概述

`SkPathOpsCommon` 是 Skia PathOps 模块的核心工具集合,提供了路径操作算法中通用的辅助函数和处理逻辑。该模块主要负责处理路径操作中的关键步骤,包括角度绕组计算、轮廓排序、巧合(coincidence)检测和处理、以及寻找未完成的线段等。这些函数是实现路径布尔运算(并集、交集、差集等)和路径简化的基础设施。

该模块的设计目标是将路径操作算法中重复出现的通用逻辑提取出来,为上层的 Op 和 Simplify 操作提供统一的、可复用的底层支持。它处理了路径操作中最复杂和最容易出错的部分,如巧合边的检测、绕组数的正确计算、以及角度排序等。

## 架构位置

`SkPathOpsCommon` 位于 PathOps 模块的核心层,在整体架构中处于以下位置:

```
应用层 API (SkPathOps.h)
    ↓
操作层 (SkPathOpsOp, SkPathOpsSimplify)
    ↓
协调层 (SkPathOpsCommon) ← 当前模块
    ↓
核心数据结构层 (SkOpContour, SkOpSegment, SkOpSpan, SkOpAngle)
    ↓
几何计算层 (SkPathOpsCurve, SkPathOpsQuad, SkPathOpsCubic)
```

该模块是连接高层操作逻辑和底层数据结构的桥梁,为路径操作提供算法流程控制。

## 主要类与结构体

该模块主要提供独立的工具函数,不定义类或结构体,但大量使用以下核心类型:

### 使用的核心类型

- **SkOpContourHead**: 轮廓链表的头节点,管理所有轮廓
- **SkOpContour**: 表示一个完整的轮廓(封闭或开放的曲线序列)
- **SkOpSegment**: 轮廓中的一段曲线(直线、二次或三次贝塞尔曲线)
- **SkOpSpan/SkOpSpanBase**: 线段上的参数点,存储绕组信息
- **SkOpAngle**: 表示线段在某点的方向角度
- **SkOpCoincidence**: 管理巧合边的检测和处理
- **SkTDArray**: 动态数组模板,用于存储 span 追踪列表

## 公共 API 函数

### AngleWinding
```cpp
const SkOpAngle* AngleWinding(SkOpSpanBase* start, SkOpSpanBase* end,
                              int* windingPtr, bool* sortable)
```
计算从 start 到 end 的角度环路的绕组值。该函数遍历角度链表,寻找有效的绕组数。如果角度环路包含不可排序的 span,则直接计算每个 span 的绕组值。返回角度指针,并通过参数返回绕组值和可排序标志。

### FindUndone
```cpp
SkOpSpan* FindUndone(SkOpContourHead* contourHead)
```
在轮廓链表中查找第一个未完成的 span。该函数遍历所有轮廓,返回第一个尚未处理的 span,用于驱动路径操作的主循环。

### FindChase
```cpp
SkOpSegment* FindChase(SkTDArray<SkOpSpanBase*>* chase,
                       SkOpSpanBase** startPtr, SkOpSpanBase** endPtr)
```
从追踪列表中寻找下一个要处理的线段。该函数从 chase 栈中弹出 span,查找其活动角度,计算绕组值,并更新所有相关角度的标记。这是路径追踪算法的核心函数。

### SortContourList
```cpp
bool SortContourList(SkOpContourHead** contourList, bool evenOdd, bool oppEvenOdd)
```
对轮廓链表进行排序。该函数收集所有非空轮廓,设置它们的 XOR 模式(even-odd 或 non-zero),然后按几何顺序排序。排序后的轮廓链表便于后续的路径操作处理。

### HandleCoincidence
```cpp
bool HandleCoincidence(SkOpContourHead* contourList, SkOpCoincidence* coincidence)
```
处理路径操作中的巧合边。这是最复杂的函数之一,包含多个步骤:
1. 添加扩展的巧合点
2. 移动多重交点以消除 t 值不一致
3. 移动临近点以消除微小间隙
4. 修正端点并添加端点移动的 span
5. 添加缺失的巧合(A-B 和 A-C 中存在但 B-C 中缺失的巧合)
6. 扩展巧合范围
7. 标记巧合 span
8. 查找遗漏的巧合线和曲线
9. 应用巧合调整绕组值
10. 查找并处理重叠的巧合对
11. 计算和排序角度

该函数包含多重安全检查循环,最多迭代 3 次以确保收敛。

### FixWinding
```cpp
bool FixWinding(SkPath* path)
```
修正路径的绕组方向(声明但未在此文件中实现)。

### OpDebug / SimplifyDebug
```cpp
std::optional<SkPath> OpDebug(const SkPath& one, const SkPath& two, SkPathOp op
                              SkDEBUGPARAMS(bool skipAssert)
                              SkDEBUGPARAMS(const char* testName))
std::optional<SkPath> SimplifyDebug(const SkPath& path
                                   SkDEBUGPARAMS(bool skipAssert)
                                   SkDEBUGPARAMS(const char* testName))
```
调试版本的路径操作函数,包含断言跳过和测试名称参数。

### ComputeTightBounds
```cpp
bool ComputeTightBounds(const SkPath& path, SkRect* rect)
```
计算路径的紧密边界矩形(声明但未在此文件中实现)。

## 内部实现细节

### calc_angles (静态)
```cpp
static void calc_angles(SkOpContourHead* contourList)
```
遍历所有轮廓,计算每个轮廓的角度信息。在处理完巧合后调用,为后续的角度排序做准备。

### missing_coincidence (静态)
```cpp
static bool missing_coincidence(SkOpContourHead* contourList)
```
检查所有轮廓是否存在遗漏的巧合。某些巧合可能在初始交点检测中被遗漏,需要在后续步骤中补充检测。

### move_multiples (静态)
```cpp
static bool move_multiples(SkOpContourHead* contourList)
```
移动多重交点。当某些线段上存在交点而其他线段上不存在时,需要调整 t 值使其对齐,以便正确处理巧合。

### move_nearby (静态)
```cpp
static bool move_nearby(SkOpContourHead* contourList)
```
移动临近的 t 值和点,以消除微小或极小的间隙。浮点误差可能导致理论上重合的点在数值上略有偏差,该函数修正这些偏差。

### sort_angles (静态)
```cpp
static bool sort_angles(SkOpContourHead* contourList)
```
对所有轮廓的角度进行排序。角度排序是确定路径遍历顺序的关键步骤,排序失败将导致路径操作无法正确完成。

## 依赖关系

### 头文件依赖
- `include/pathops/SkPathOps.h`: 公共 API 定义
- `src/pathops/SkPathOpsTypes.h`: 类型定义
- `include/core/SkTypes.h`: Skia 核心类型
- `include/private/base/SkTDArray.h`: 动态数组模板
- `src/base/SkTSort.h`: 排序算法
- `src/pathops/SkOpAngle.h`: 角度类
- `src/pathops/SkOpCoincidence.h`: 巧合处理类
- `src/pathops/SkOpContour.h`: 轮廓类
- `src/pathops/SkOpSegment.h`: 线段类
- `src/pathops/SkOpSpan.h`: Span 类

### 类依赖
该模块是多个 PathOps 核心类的协调者,依赖关系网络复杂:
- **数据结构**: SkOpContour, SkOpSegment, SkOpSpan, SkOpAngle
- **算法模块**: SkOpCoincidence (巧合检测)
- **工具类**: SkTDArray (动态数组), SkTSort (排序)

## 设计模式与设计决策

### 函数式组织
该模块采用纯函数式的设计,不定义类,所有功能都通过独立函数提供。这种设计使得代码更易于测试和理解,函数之间的依赖关系更加清晰。

### 迭代式收敛算法
`HandleCoincidence` 函数体现了迭代式收敛算法的设计模式。巧合检测和处理是一个相互依赖的过程:
- 检测巧合 → 调整点位 → 重新检测 → 发现新巧合 → 再调整
- 使用安全计数器(SAFETY_COUNT = 3)防止无限循环
- 每次迭代都在逐步完善结果,直到收敛或达到迭代上限

### 分阶段处理
巧合处理被分解为多个独立的阶段:
1. 扩展 (expand)
2. 添加缺失 (addMissing)
3. 移动多重点 (moveMultiples)
4. 移动临近点 (moveNearby)
5. 标记 (mark)
6. 应用 (apply)

每个阶段只关注特定类型的问题,使得算法更易于理解和调试。

### 调试支持
大量使用宏定义的调试参数:
- `DEBUG_COIN_DECLARE_PARAMS()`: 声明调试参数
- `DEBUG_PHASE_PARAMS()`: 传递阶段信息
- `DEBUG_ITER_PARAMS()`: 传递迭代计数

在 Release 模式下这些宏展开为空,在 Debug 模式下提供详细的跟踪信息。

### 容错设计
- 返回布尔值指示成功/失败,允许调用者决定如何处理错误
- 使用 `SK_MinS32` 作为无效绕组值的标记
- 在检测到不可排序的角度时,切换到直接计算模式

## 性能考量

### 早期退出优化
- `FindUndone`: 找到第一个未完成 span 立即返回,不遍历所有轮廓
- `AngleWinding`: 找到第一个有效绕组值立即停止遍历

### 排序优化
- `SortContourList`: 只有在轮廓数量大于 1 时才执行排序
- 使用 `SkTQSort` 快速排序算法

### TRY_ROTATE 优化
代码中包含 `TRY_ROTATE` 条件编译选项:
- 启用时使用 `insert(0)` 在列表头部插入(可能改善缓存局部性)
- 禁用时使用 `append()` 在尾部追加(更高效)

### 内存管理
- 使用 `SkTDArray` 动态数组,避免固定大小限制
- chase 栈采用后进先出(LIFO)策略,通过 `back()` 和 `pop_back()` 高效访问

### 循环展开
角度遍历使用 do-while 循环,减少了分支预测开销:
```cpp
do {
    angle = angle->next();
    // 处理逻辑
} while (angle != firstAngle);
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/pathops/SkOpAngle.h/cpp` | 依赖 | 角度计算和排序 |
| `src/pathops/SkOpCoincidence.h/cpp` | 依赖 | 巧合检测和处理的核心算法 |
| `src/pathops/SkOpContour.h/cpp` | 依赖 | 轮廓数据结构和操作 |
| `src/pathops/SkOpSegment.h/cpp` | 依赖 | 线段数据结构和绕组计算 |
| `src/pathops/SkOpSpan.h/cpp` | 依赖 | Span 数据结构和参数化点 |
| `src/pathops/SkPathOpsOp.cpp` | 被依赖 | 路径布尔运算,调用本模块函数 |
| `src/pathops/SkPathOpsSimplify.cpp` | 被依赖 | 路径简化,调用本模块函数 |
| `src/pathops/SkPathOpsTypes.h` | 依赖 | 类型定义和常量 |
| `include/pathops/SkPathOps.h` | 依赖 | 公共 API 定义 |
| `src/base/SkTSort.h` | 依赖 | 快速排序算法实现 |
| `include/private/base/SkTDArray.h` | 依赖 | 动态数组模板类 |
| `src/pathops/SkPathOpsDebug.h` | 依赖 | 调试工具和可视化 |
