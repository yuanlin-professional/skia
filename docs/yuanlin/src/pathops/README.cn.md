# pathops - 路径布尔运算引擎

## 概述

`src/pathops` 目录是 Skia 图形库中路径布尔运算（Path Boolean Operations）的核心实现，包含约 57 个源文件。该模块提供了对两个 `SkPath` 对象执行集合运算的能力，支持五种布尔操作：差集（Difference）、交集（Intersect）、并集（Union）、异或（XOR）和反向差集（ReverseDifference）。此外，该模块还提供了路径简化（Simplify）功能——将自相交的路径转化为不重叠的轮廓集合，以及将 EvenOdd 填充规则转换为 Winding 填充规则的 `AsWinding` 功能。

路径布尔运算是计算几何中的经典难题之一。Skia 的实现采用了基于扫描线和绕数（winding number）的算法框架，结合高精度双精度浮点数（double）计算来保证数值稳定性。整个计算流程可概括为：将输入路径分解为曲线段（线段、二次曲线、圆锥曲线、三次曲线），计算所有段之间的交点，根据绕数规则确定哪些区域属于输出路径，最终将结果边拼接成封闭轮廓。

该模块的设计特别关注数值精度问题。在 `SkPathOpsTypes.h` 中定义了大量的近似比较函数（如 `approximately_equal`、`roughly_equal`、`precisely_equal`），使用 ULP（Units in the Last Place）方法来比较浮点数，从而在不同精度级别上处理浮点运算的固有误差。这种多级精度策略是整个 pathops 模块能够稳健运行的基础。

内存管理方面，pathops 模块大量使用 `SkArenaAlloc` 进行内存分配。所有在运算过程中创建的临时对象（如 `SkOpSpan`、`SkOpAngle`、`SkOpSegment` 等）均从竞技场分配器中分配，运算结束后整体释放，避免了频繁的堆分配开销，同时简化了内存管理。

调试支持也是该模块的显著特征。通过大量的 `DEBUG_COIN`、`DEBUG_VALIDATE`、`DEBUG_T_SECT` 等条件编译宏，模块在调试构建中提供了极其丰富的验证和诊断信息，包括重合段检查、交点验证、绕数追踪等，这些工具对于诊断复杂几何场景下的边界情况至关重要。

## 架构图

```
                        公共 API 层 (include/pathops/SkPathOps.h)
                 +-------------------------------------------------+
                 |  Op()  |  Simplify()  |  AsWinding()  |  SkOpBuilder  |
                 +---------+------+-------+--------+------+--------+
                           |      |                |               |
                 +---------v------v----------------v---------------v-----+
                 |                   顶层协调层                          |
                 |  SkPathOpsOp.cpp         SkPathOpsSimplify.cpp        |
                 |  SkPathOpsAsWinding.cpp  SkOpBuilder.cpp              |
                 +-----+--------+--------+--------+--------+-----------+
                       |        |        |        |        |
          +------------v--+  +--v--------v--+  +--v--------v----------+
          | 路径解析层     |  | 交点计算层    |  | 重合与绕数处理层      |
          |               |  |              |  |                      |
          | SkOpEdge      |  | SkAddInter   |  | SkOpCoincidence      |
          |   Builder     |  |   sections   |  | SkPathOpsCommon      |
          | SkReduceOrder |  | SkInter      |  |   (HandleCoincidence)|
          |               |  |   sections   |  | SkPathOpsWinding     |
          +-------+-------+  | SkPathOps    |  +----------+-----------+
                  |           |   TSect      |             |
                  |           +---------+----+             |
                  |                     |                  |
          +-------v---------------------v------------------v----------+
          |                   核心数据结构层                            |
          |                                                           |
          |  SkOpContour  -->  SkOpSegment  -->  SkOpSpan/SkOpSpanBase|
          |       |                |                    |              |
          |       |                |              SkOpPtT (交点链表)   |
          |       |                |                    |              |
          |       |           SkOpAngle (角度排序)      |              |
          |       |                                     |              |
          |  SkOpGlobalState (全局状态管理)              |              |
          +---+---------------------+-------------------+-------------+
              |                     |
     +--------v---------+  +-------v---------------------------+
     | 几何基元层        |  | 曲线求交算法层                     |
     |                  |  |                                   |
     | SkDPoint/Vector  |  | SkDConicLineIntersection          |
     | SkDLine          |  | SkDCubicLineIntersection           |
     | SkDQuad          |  | SkDQuadLineIntersection            |
     | SkDConic         |  | SkDLineIntersection                |
     | SkDCubic         |  | SkPathOpsTSect (曲线-曲线求交)     |
     | SkDCurve         |  |                                   |
     | SkTCurve (抽象)  |  +-----------------------------------+
     | SkPathOpsBounds  |
     | SkLineParameters |
     +------------------+
              |
     +--------v---------+
     | 输出构建层        |
     |                  |
     | SkPathWriter     |
     | (路径拼接与输出)  |
     +------------------+
```

## 目录结构

```
src/pathops/
|-- BUILD.bazel                          # Bazel 构建配置
|
|-- [公共 API 入口实现]
|   |-- SkPathOpsOp.cpp                  # Op() 布尔运算主入口（392行）
|   |-- SkPathOpsSimplify.cpp            # Simplify() 路径简化入口（285行）
|   |-- SkPathOpsAsWinding.cpp           # AsWinding() 填充规则转换（~400行）
|   |-- SkOpBuilder.cpp                  # SkOpBuilder 批量运算实现
|
|-- [核心数据结构]
|   |-- SkOpContour.h / .cpp             # 轮廓类：段的容器（462/80行）
|   |-- SkOpSegment.h / .cpp             # 线段类：核心运算单元（466/~1600行）
|   |-- SkOpSpan.h / .cpp                # 跨度/交点类（578/370行）
|   |-- SkOpAngle.h / .cpp               # 角度排序类（156/~1100行）
|   |-- SkOpCoincidence.h / .cpp         # 重合段管理类（307/~1400行）
|   |-- SkPathOpsTypes.h / .cpp          # 全局类型与浮点比较工具（607/180行）
|
|-- [几何基元]
|   |-- SkPathOpsPoint.h                 # 双精度点/向量（SkDPoint/SkDVector）
|   |-- SkPathOpsLine.h / .cpp           # 双精度线段（SkDLine）
|   |-- SkPathOpsQuad.h / .cpp           # 双精度二次贝塞尔曲线（SkDQuad）
|   |-- SkPathOpsConic.h / .cpp          # 双精度圆锥曲线（SkDConic）
|   |-- SkPathOpsCubic.h / .cpp          # 双精度三次贝塞尔曲线（SkDCubic）
|   |-- SkPathOpsCurve.h / .cpp          # 曲线联合体与函数分派表（SkDCurve）
|   |-- SkPathOpsTCurve.h               # 曲线抽象基类（SkTCurve）
|   |-- SkPathOpsRect.h / .cpp           # 双精度矩形（SkDRect）
|   |-- SkPathOpsBounds.h               # 路径边界框（SkPathOpsBounds）
|
|-- [交点计算]
|   |-- SkAddIntersections.h / .cpp      # 交点添加主调度（28000行cpp）
|   |-- SkIntersections.h / .cpp         # 交点存储结构（346/150行）
|   |-- SkIntersectionHelper.h           # 交点计算辅助类
|   |-- SkDLineIntersection.cpp          # 线段-线段求交
|   |-- SkDQuadLineIntersection.cpp      # 二次曲线-线段求交
|   |-- SkDConicLineIntersection.cpp     # 圆锥曲线-线段求交
|   |-- SkDCubicLineIntersection.cpp     # 三次曲线-线段求交
|   |-- SkPathOpsTSect.h / .cpp          # T-Sector 曲线对曲线求交（~70000行cpp）
|   |-- SkDCubicToQuads.cpp              # 三次曲线降阶为二次曲线
|
|-- [辅助算法]
|   |-- SkReduceOrder.h / .cpp           # 曲线降阶（退化检测）
|   |-- SkLineParameters.h              # 参数化直线（ax+by+c=0）
|   |-- SkOpCubicHull.cpp               # 三次曲线凸包计算
|   |-- SkPathOpsCommon.h / .cpp         # 公共算法（排序、绕数、重合处理）
|   |-- SkPathOpsWinding.cpp             # 绕数计算（射线法）
|   |-- SkPathOpsTightBounds.cpp         # 紧密边界框计算
|
|-- [路径构建与输出]
|   |-- SkOpEdgeBuilder.h / .cpp         # SkPath到内部表示的转换器
|   |-- SkPathWriter.h / .cpp            # 内部表示到SkPath的输出器
|
|-- [调试支持]
|   |-- SkPathOpsDebug.h / .cpp          # 调试工具与诊断（~115000行cpp）
```

## 关键类与函数

### 公共 API 函数

| 函数 | 文件 | 说明 |
|------|------|------|
| `Op(const SkPath&, const SkPath&, SkPathOp)` | `SkPathOpsOp.cpp` | 对两个路径执行布尔运算，返回 `std::optional<SkPath>` |
| `Simplify(const SkPath&)` | `SkPathOpsSimplify.cpp` | 将路径简化为无重叠轮廓 |
| `AsWinding(const SkPath&)` | `SkPathOpsAsWinding.cpp` | 将 EvenOdd 填充转换为 Winding 填充 |
| `SkOpBuilder::add()` / `resolve()` | `SkOpBuilder.cpp` | 批量布尔运算构建器 |

### 核心数据结构类

#### `SkOpGlobalState` (`SkPathOpsTypes.h`)

全局状态管理类，贯穿整个运算生命周期。维护以下关键状态：

- `fAllocator`：`SkArenaAlloc*`，内存分配器
- `fCoincidence`：`SkOpCoincidence*`，重合段管理器
- `fContourHead`：`SkOpContourHead*`，轮廓链表头
- `fPhase`：`SkOpPhase`，当前运算阶段（`kIntersecting` / `kWalking` / `kFixWinding`）
- `fWindingFailed`：标记绕数计算是否失败

#### `SkOpContour` / `SkOpContourHead` (`SkOpContour.h`)

轮廓容器类。`SkOpContourHead` 继承自 `SkOpContour`，作为链表头节点。每个轮廓包含：

- `fHead`：内联的第一个 `SkOpSegment`
- `fTail`：指向最后一个段的指针
- `fNext`：下一个轮廓（链表结构）
- `fOperand`：标记是否为第二操作数
- `fXor` / `fOppXor`：是否为 EvenOdd 填充

辅助类 `SkOpContourBuilder` 负责从 `SkPath` 的动词/点序列构建轮廓。

#### `SkOpSegment` (`SkOpSegment.h`)

线段类，是路径运算的核心单元。每个段代表一条原始曲线（线段、二次、圆锥或三次贝塞尔曲线）。关键成员：

- `fHead` / `fTail`：首尾 `SkOpSpan`（t=0 和 t=1）
- `fPts`：控制点数组指针
- `fWeight`：圆锥曲线权重
- `fVerb`：曲线类型（`SkPath::Verb`）
- `fBounds`：紧密边界框
- `fCount` / `fDoneCount`：跨度总数与已处理数

核心方法包括：
- `addT(double t)`：在参数 t 处添加交点
- `calcAngles()`：计算交点处的角度
- `findNextOp()` / `findNextWinding()`：沿路径查找下一段
- `markDone()` / `markWinding()`：标记处理状态和绕数
- `activeOp()` / `activeWinding()`：判断段是否在结果中有效

#### `SkOpSpanBase` / `SkOpSpan` (`SkOpSpan.h`)

跨度类，表示段上的一个交点位置。`SkOpSpan` 继承自 `SkOpSpanBase`，增加了绕数信息：

- `fPtT`：内联的 `SkOpPtT`，存储参数 t 和点坐标
- `fFromAngle` / `fToAngle`：指向该点处的角度对象
- `fWindSum` / `fOppSum`：累积绕数和对手绕数
- `fWindValue` / `fOppValue`：段贡献绕数值
- `fDone`：是否已处理
- `fCoincident`：重合段链表

#### `SkOpPtT` (`SkOpSpan.h`)

交点参数-坐标对类。通过循环链表将同一空间位置上不同段的交点关联起来：

- `fT`：参数值
- `fPt`：点坐标缓存
- `fSpan`：所属跨度
- `fNext`：下一个关联交点（循环链表）

`addOpp()` 方法将两个不同段上的交点合并到同一环形链表中。

#### `SkOpAngle` (`SkOpAngle.h`)

角度排序类，用于在交点处确定相邻段的顺序。使用扇区（sector）机制将角度分为 32 个区域进行快速排序：

- `fSectorStart` / `fSectorEnd`：扇区编号（32 等分圆）
- `fPart`：偏移后的曲线段
- `fTangentHalf`：切线参数化形式
- `insert()`：按角度顺序插入到循环链表

#### `SkOpCoincidence` / `SkCoincidentSpans` (`SkOpCoincidence.h`)

重合段管理类。当两条段在某一参数范围内完全重叠时记录为重合：

- `SkCoincidentSpans`：存储一对重合区间（主段和对手段的 PtT 起止）
- `SkOpCoincidence`：管理所有重合段的链表
- `add()` / `apply()`：添加和应用重合信息
- `mark()` / `expand()`：标记和扩展重合区间

### 几何基元类

#### `SkDPoint` / `SkDVector` (`SkPathOpsPoint.h`)

双精度点和向量。提供 `approximatelyEqual()`、`roughlyEqual()` 等多级精度比较方法，以及 `cross()`、`dot()` 等向量运算。

#### 曲线类层次

| 类 | 文件 | 点数 | 说明 |
|----|------|------|------|
| `SkDLine` | `SkPathOpsLine.h` | 2 | 双精度线段，支持水平/垂直截距计算 |
| `SkDQuad` | `SkPathOpsQuad.h` | 3 | 双精度二次贝塞尔曲线 |
| `SkDConic` | `SkPathOpsConic.h` | 3+权重 | 双精度有理二次曲线（圆锥截面） |
| `SkDCubic` | `SkPathOpsCubic.h` | 4 | 双精度三次贝塞尔曲线 |
| `SkDCurve` | `SkPathOpsCurve.h` | 联合体 | 上述所有曲线类型的联合体 |
| `SkTCurve` | `SkPathOpsTCurve.h` | 虚函数 | 曲线抽象接口（用于 TSect 模板化求交） |

`SkPathOpsCurve.h` 还定义了重要的函数指针表：
- `CurveDPointAtT[]`：按 Verb 索引的求点函数表
- `CurveDSlopeAtT[]`：按 Verb 索引的求导函数表
- `CurveIsVertical[]`：按 Verb 索引的垂直判定函数表
- `CurveIntersectRay[]`：按 Verb 索引的射线求交函数表

#### `SkLineParameters` (`SkLineParameters.h`)

将线段参数化为 `ax + by + c = 0` 的形式，用于计算点到直线的距离。引用了 Bezier 裁剪论文（Sederberg & Nishita, 1990）。

### 交点计算类

#### `SkIntersections` (`SkIntersections.h`)

交点存储类，缓存两条曲线之间最多 13 个交点（三次曲线对三次曲线的理论最大值为 9，加上重合端点）：

- `fPt[13]`：交点坐标
- `fT[2][13]`：两条曲线上的参数值
- `fIsCoincident`：位掩码标记重合交点
- 提供所有曲线组合的 `intersect()` 方法重载

#### `SkTSect` / `SkTSpan` (`SkPathOpsTSect.h`)

T-Sector 算法实现，用于曲线对曲线的求交。这是 pathops 中最复杂的算法之一（实现超过 70000 行）：

- `SkTSpan`：表示曲线参数空间 `[startT, endT]` 的一个区间，维护边界框和重合信息
- `SkTSect`：管理一条曲线上所有 `SkTSpan` 的有序链表
- `BinarySearch()`：核心入口，通过递归细分和裁剪找到所有交点
- 使用凸包相交测试（`hullsIntersect`）快速排除不相交的区间
- 使用垂足计算（`setPerp`）和线性化（`linearsIntersect`）精确确定交点

#### 曲线-线段求交

每种曲线类型都有专门的线段求交实现：

| 文件 | 求交组合 |
|------|---------|
| `SkDLineIntersection.cpp` | 线段 vs 线段 |
| `SkDQuadLineIntersection.cpp` | 二次曲线 vs 线段 |
| `SkDConicLineIntersection.cpp` | 圆锥曲线 vs 线段 |
| `SkDCubicLineIntersection.cpp` | 三次曲线 vs 线段 |

### 辅助工具类

#### `SkOpEdgeBuilder` (`SkOpEdgeBuilder.h`)

将 `SkPath` 转换为 pathops 内部的 `SkOpContour`/`SkOpSegment` 表示。调用 `SkReduceOrder` 对退化曲线进行降阶处理。关键功能：

- `preFetch()`：预取路径中的动词和点数据
- `walk()`：遍历动词序列构建段
- `addOperand()`：添加第二操作数（标记为 operand）
- `xorMask()`：返回填充规则掩码

#### `SkPathWriter` (`SkPathWriter.h`)

将运算结果从内部表示转换回 `SkPath`。支持延迟移动（deferred move）和延迟直线（deferred line）优化。`assemble()` 方法处理无法直接闭合的轮廓碎片，通过端点匹配将它们拼接起来。

#### `SkReduceOrder` (`SkReduceOrder.h`)

曲线降阶工具。检测退化情况（如三次曲线退化为二次、二次退化为线段），返回降阶后的阶数。

## 依赖关系

### 对外部模块的依赖

```
include/core/SkPath.h          -- 输入输出路径类型
include/core/SkPoint.h         -- 基础点类型 (float 精度)
include/core/SkRect.h          -- 基础矩形类型
include/core/SkScalar.h        -- 标量类型定义
include/pathops/SkPathOps.h    -- 公共 API 定义 (SkPathOp 枚举等)
src/base/SkArenaAlloc.h        -- 竞技场内存分配器
src/core/SkPathPriv.h          -- SkPath 私有接口
include/private/base/SkTDArray.h  -- 动态数组
include/private/base/SkTArray.h   -- 模板数组
```

### 模块内部依赖层次

```
底层：SkPathOpsTypes.h  (浮点比较、基础类型)
       |
       v
基元层：SkPathOpsPoint.h -> SkPathOpsLine/Quad/Conic/Cubic.h -> SkPathOpsCurve.h
       |
       v
求交层：SkIntersections.h -> SkD*LineIntersection.cpp, SkPathOpsTSect.h
       |
       v
结构层：SkOpSpan.h -> SkOpSegment.h -> SkOpContour.h
       |                    |
       v                    v
运算层：SkOpAngle.h    SkOpCoincidence.h
       |                    |
       v                    v
协调层：SkPathOpsOp.cpp / SkPathOpsSimplify.cpp
       |
       v
IO 层：SkOpEdgeBuilder.h (输入) / SkPathWriter.h (输出)
```

## 设计模式分析

### 1. 策略模式（Strategy Pattern）——函数指针表

`SkPathOpsCurve.h` 通过函数指针数组实现了一种高效的策略模式，以 `SkPath::Verb` 作为索引来分派不同曲线类型的操作：

```cpp
// 按 Verb 索引的求点函数表
static SkDPoint (* const CurveDPointAtT[])(const SkPoint[], SkScalar, double) = {
    nullptr,            // kMove
    dline_xy_at_t,      // kLine
    dquad_xy_at_t,      // kQuad
    dconic_xy_at_t,     // kConic
    dcubic_xy_at_t      // kCubic
};

// 使用方式 (在 SkOpSegment 中):
SkDPoint dPtAtT(double mid) const {
    return (*CurveDPointAtT[fVerb])(fPts, fWeight, mid);
}
```

类似的函数表还包括 `CurveDSlopeAtT`、`CurveIsVertical`、`CurveIntersectRay`、`CurveIntercept` 等，这种设计避免了虚函数调用开销，同时保持了良好的扩展性。

### 2. 联合体模式（Union/Variant Pattern）

`SkDCurve` 使用 C++ 联合体来统一存储不同类型的曲线：

```cpp
struct SkDCurve {
    union {
        SkDLine fLine;
        SkDQuad fQuad;
        SkDConic fConic;
        SkDCubic fCubic;
    };
};
```

这种设计在需要统一处理不同曲线类型时非常高效，避免了动态分配和虚函数调用。

### 3. 侵入式链表模式（Intrusive Linked List）

核心数据结构大量使用侵入式链表：

- `SkOpContour` 通过 `fNext` 形成轮廓链表
- `SkOpSegment` 通过 `fNext`/`fPrev` 形成双向链表
- `SkOpSpan`/`SkOpSpanBase` 通过 `fNext`/`fPrev` 形成交点链表
- `SkOpPtT` 通过 `fNext` 形成循环链表（关联不同段上的等价交点）
- `SkOpAngle` 通过 `fNext` 形成角度排序的循环链表
- `SkCoincidentSpans` 通过 `fNext` 形成重合段链表
- `SkOpSpan::fCoincident` 形成重合跨度的循环链表

配合 `SkArenaAlloc`，这种侵入式设计实现了零额外内存开销的数据组织。

### 4. 竞技场分配模式（Arena Allocation Pattern）

整个运算过程中的临时对象统一从栈上预分配的 `SkSTArenaAlloc<4096>` 中分配：

```cpp
SkSTArenaAlloc<4096> allocator;
SkOpGlobalState globalState(contourList, &allocator, ...);
// 所有 SkOpSpan、SkOpAngle 等对象均从 allocator 分配
// 函数返回时 allocator 自动销毁所有对象
```

### 5. 阶段模式（Phase Pattern）

`SkOpPhase` 枚举定义了运算的不同阶段，用于断言验证和条件逻辑：

```cpp
enum class SkOpPhase : char {
    kNoChange,       // 无变化
    kIntersecting,   // 求交阶段
    kWalking,        // 遍历阶段
    kFixWinding,     // 修复绕数阶段
};
```

### 6. 模板特化与抽象接口的混合使用

`SkTCurve` 提供了曲线的虚函数接口，用于 `SkTSect`/`SkTSpan` 中的曲线对曲线求交算法。同时，`SkTSect` 内部使用 `SkArenaAlloc` 和具体曲线类型的 `make()` 工厂方法来创建类型正确的对象，兼顾了通用性和类型安全。

## 数据流

### 布尔运算 `Op()` 的完整数据流

```
输入: SkPath one, SkPath two, SkPathOp op
  |
  v
[1] 预处理与快速路径
  |-- 处理反向填充: gOpInverse[op][one.isInverse][two.isInverse]
  |-- 矩形优化: 两个矩形的交集直接计算
  |-- 空路径处理: 根据操作类型选择保留哪个路径
  |
  v
[2] 初始化全局状态
  |-- 创建 SkSTArenaAlloc<4096>
  |-- 创建 SkOpGlobalState
  |-- 创建 SkOpCoincidence
  |
  v
[3] 路径解析 (SkOpEdgeBuilder)
  |-- preFetch(): 提取路径的动词、点、权重
  |-- walk(): 遍历动词序列
  |   |-- 对每个 moveTo/lineTo/quadTo/conicTo/cubicTo:
  |   |   |-- SkReduceOrder 降阶检测
  |   |   |-- 创建 SkOpSegment (addLine/addQuad/addConic/addCubic)
  |   |   |-- 计算段的紧密边界框
  |   |-- close(): 闭合轮廓
  |-- addOperand(): 标记第二操作数并重复以上过程
  |
  v
  内部表示: SkOpContourHead -> SkOpContour* -> SkOpSegment* 链表
  |
  v
[4] 排序轮廓 (SortContourList)
  |-- 按 fBounds.fTop 排序
  |-- 设置 XOR/Winding 填充规则
  |
  v
[5] 计算所有交点 (AddIntersectTs)
  |-- 对每对轮廓 (current, next):
  |   |-- 对每对段 (wt, wn):
  |       |-- 边界框相交测试 (SkPathOpsBounds::Intersects)
  |       |-- 根据段类型分派到对应求交函数:
  |       |   |-- line-line: SkDLineIntersection
  |       |   |-- quad-line: SkDQuadLineIntersection
  |       |   |-- conic-line: SkDConicLineIntersection
  |       |   |-- cubic-line: SkDCubicLineIntersection
  |       |   |-- 曲线-曲线: SkTSect::BinarySearch
  |       |       |-- 递归细分参数空间
  |       |       |-- 凸包相交测试 (hullsIntersect)
  |       |       |-- 线性化求交 (linearsIntersect)
  |       |       |-- 垂足计算 (setPerp)
  |       |-- 将交点添加到段上: segment->addT(t)
  |       |-- 关联对手段交点: ptT->addOpp()
  |       |-- 检测重合段: coincidence->add()
  |
  v
[6] 处理重合 (HandleCoincidence)
  |-- moveMultiples(): 移动多重交点
  |-- moveNearby(): 合并邻近交点
  |-- addExpanded(): 展开重合区间
  |-- missingCoincidence(): 查找遗漏的重合段
  |-- expand(): 扩展重合区间
  |-- mark(): 标记重合段的绕数
  |-- apply(): 应用重合段效果到跨度的 windValue/oppValue
  |
  v
[7] 计算角度与绕数
  |-- calcAngles(): 在每个交点处建立角度对象
  |-- sortAngles(): 按角度排序形成循环链表
  |-- computeSum(): 沿角度链传播绕数
  |
  v
[8] 遍历并构建输出 (bridgeOp)
  |-- FindSortableTop(): 找到最上方的未处理跨度
  |-- 从该点开始沿路径遍历:
  |   |-- activeOp(): 根据 op 类型和绕数判断段是否有效
  |   |   |-- 差集: sumWinding != 0 && oppSumWinding == 0
  |   |   |-- 交集: sumWinding != 0 && oppSumWinding != 0
  |   |   |-- 并集: sumWinding != 0 || oppSumWinding != 0
  |   |   |-- 异或: (sumWinding & 1) ^ (oppSumWinding & 1)
  |   |-- findNextOp(): 在交点处选择下一段
  |   |   |-- 查看角度循环链表
  |   |   |-- 根据绕数规则选择正确的方向
  |   |-- addCurveTo(): 将段写入 SkPathWriter
  |   |-- markDone(): 标记已处理
  |-- finishContour(): 完成一个输出轮廓
  |-- findChaseOp(): 从 chase 栈中恢复未完成的遍历
  |
  v
[9] 组装输出 (SkPathWriter::assemble)
  |-- 如果有无法闭合的轮廓碎片:
  |   |-- 通过端点匹配将碎片拼接
  |-- nativePath(): 转换为 SkPath
  |
  v
输出: std::optional<SkPath> result
```

### 简化 `Simplify()` 的数据流差异

`Simplify()` 与 `Op()` 共享大部分流程，区别在于：

1. 只有一个输入路径（无 operand）
2. 遍历阶段使用 `bridgeWinding()` 或 `bridgeXor()`（根据填充规则）
3. `bridgeWinding()` 使用 `activeWinding()` 和 `findNextWinding()` 代替对应的 Op 版本
4. `bridgeXor()` 使用 `findNextXor()`，逻辑更简单（不考虑对手绕数）

### 曲线求交 `SkTSect::BinarySearch()` 的数据流

```
输入: 两条曲线 (SkTSect sect1, SkTSect sect2)
  |
  v
[1] 初始化
  |-- 每条曲线创建一个 SkTSpan 覆盖 [0, 1]
  |-- 计算初始边界框
  |
  v
[2] 主循环
  |-- 选择边界框最大的 span 进行细分
  |-- 分割为 [startT, midT] 和 [midT, endT]
  |-- 对每个子区间:
  |   |-- 更新边界框
  |   |-- 凸包测试: 剔除不相交的对手 span
  |   |-- 如果区间足够小:
  |       |-- 线性化求交: 将曲线近似为线段
  |       |-- 垂足计算: 精确定位交点
  |
  v
[3] 收敛检测
  |-- 当 span 的 t 范围 < epsilon: 提取交点
  |-- 重合检测: 连续的 span 如果垂距均为零则标记为重合
  |
  v
输出: SkIntersections (交点列表)
```

## 浮点精度策略

pathops 模块定义了多个精度级别的常量和比较函数：

| 常量 | 值 | 用途 |
|------|-----|------|
| `FLT_EPSILON` | ~1.19e-07 | 标准单精度 epsilon |
| `FLT_EPSILON_HALF` | ~5.96e-08 | 更严格的比较 |
| `FLT_EPSILON_DOUBLE` | ~2.38e-07 | 更宽松的比较 |
| `FLT_EPSILON_ORDERABLE_ERR` | ~1.91e-06 | 排序可容忍误差 |
| `FLT_EPSILON_SQUARED` | ~1.42e-14 | 面积级比较 |
| `FLT_EPSILON_SQRT` | ~3.45e-04 | 长度级比较 |
| `DBL_EPSILON_ERR` | ~8.88e-16 | 双精度误差容限 |
| `ROUGH_EPSILON` | ~7.63e-06 | 粗略比较 |
| `MORE_ROUGH_EPSILON` | ~3.05e-05 | 更粗略比较 |
| `WAY_ROUGH_EPSILON` | ~2.44e-04 | 极粗略比较 |
| `BUMP_EPSILON` | ~4.88e-04 | 微调使用 |

对应的比较函数族：
- `approximately_*()`：使用 `FLT_EPSILON`，最常用
- `precisely_*()`：使用 `DBL_EPSILON_ERR`，双精度级别
- `roughly_*()`：使用 `ROUGH_EPSILON`，容忍更大误差
- `AlmostEqualUlps()`：基于 ULP 距离的比较，考虑数值量级

## 相关文档与参考

### Skia 官方资源

- [PathOps 设计文档](https://skia.org/dev/present/pathops)：包含核心算法的可视化说明
- 布尔运算示例和演示文稿链接见源码注释

### 学术参考

- **Bezier 裁剪算法**：Sederberg & Nishita, "Curve intersection using Bezier clipping", *Computer-Aided Design*, Vol.22 No.9, 1990, pp.538-549. 该论文被 `SkLineParameters.h` 引用，是 T-Sector 算法的基础。

### 相关源码目录

| 路径 | 关系 |
|------|------|
| `include/pathops/SkPathOps.h` | 公共 API 定义 |
| `include/core/SkPath.h` | 输入输出路径类型 |
| `src/base/SkArenaAlloc.h` | 内存分配器 |
| `src/core/SkPathPriv.h` | SkPath 内部接口 |
| `tests/PathOps*.cpp` | pathops 单元测试 |

### 关键算法说明

1. **绕数规则判断**：在 `SkOpSegment::activeOp()` 中，根据布尔操作类型和两个路径的绕数，决定一段曲线是否出现在结果中。`gOpInverse` 和 `gOutInverse` 查找表处理了反向填充路径的情况。

2. **角度排序**：`SkOpAngle::orderable()` 方法处理了各种边界情况，包括切线方向相同的段、近似平行的段等。使用扇区机制将圆分为 32 个区域进行快速判定。

3. **重合段处理**：`HandleCoincidence()` 函数是最复杂的协调步骤之一，需要迭代多次才能收敛。它处理移动多重交点、合并邻近点、扩展重合区间、标记绕数等多个子步骤。

4. **T-Sector 求交**：`SkTSect::BinarySearch()` 实现了一种自适应的曲线求交算法，结合了凸包排除、参数空间细分和线性化近似三种技术，能够高效处理各种曲线组合。
