# bentleyottmann - Bentley-Ottmann 线段交点算法模块

## 概述

`modules/bentleyottmann` 实现了计算几何中经典的 Bentley-Ottmann 算法,用于高效地求解一组线段的所有交点。该算法是路径操作 (Path Operations) 的基础组件,在 Skia 的几何处理流程中扮演重要角色。

Bentley-Ottmann 算法是一种扫描线 (Sweep Line) 算法,其时间复杂度为 O((n + k) log n),其中 n 为线段数量,k 为交点数量。相比暴力求解的 O(n^2) 复杂度,在交点数量远小于线段数量平方时具有显著优势。算法通过维护一个事件队列 (Event Queue) 和一条扫描线 (Sweep Line) 来工作:扫描线从上到下移动,在每个事件点处更新扫描线上的线段顺序并检测新的交点。

模块还实现了 Myers 算法,这是另一种线段交点检测方法,以及暴力求解算法作为参考和测试对照。`Contour` 子系统负责将 `SkPath` 转换为整数坐标的轮廓线段表示,作为算法的输入预处理。

为了保证精确的几何计算,模块使用 `int32_t` 整数坐标(而非浮点数),并引入了 `Int96` 类型来处理中间计算中可能出现的大数乘法溢出,确保交点计算的精确性。

算法的核心入口函数 `bentley_ottmann_1()` 接收线段列表,返回所有交点;如果数据范围溢出,返回 `nullopt`,调用者可将坐标缩小后重试。

## 架构图

```
               SkPath (浮点路径)
                      |
                      v
         +------------------------+
         | Contours (轮廓提取)    |
         | - SkPath -> int32 点序 |
         | - 缩放因子: 1024       |
         | - 生成 Segment 列表    |
         +------------------------+
                      |
                      v
              Segment[] (线段集合)
                      |
         +------------+------------+
         |                         |
         v                         v
+------------------+     +------------------+
| bentley_ottmann_1|     | brute_force_     |
| (高效算法)       |     | crossings        |
| O((n+k)log n)    |     | (暴力对照)       |
+--------+---------+     | O(n^2)           |
         |               +------------------+
         v
+------------------+     +------------------+
| EventQueue       |<--->| SweepLine        |
| (事件队列)       |     | (扫描线)         |
| - Upper 事件     |     | - 有序线段列表   |
| - Lower 事件     |     | - 插入/删除      |
| - Cross 事件     |     | - 交点检测       |
+------------------+     +------------------+
         |
         v
    Crossing[] (交点结果)

+------------------+
| Myers            |
| (替代算法)       |
| myers_find_      |
| crossings()      |
+------------------+
```

## 目录结构

```
modules/bentleyottmann/
+-- BUILD.gn                  # GN 构建配置
+-- BUILD.bazel               # Bazel 构建配置
+-- bentleyottmann.gni        # GNI 源文件列表
+-- include/                  # 公共头文件
|   +-- BUILD.bazel
|   +-- BentleyOttmann1.h     # 算法主入口
|   +-- Segment.h             # 线段定义与交点计算
|   +-- Point.h               # 整数坐标点
|   +-- Int96.h               # 96位整数 (防溢出)
|   +-- EventQueue.h          # 事件队列
|   +-- EventQueueInterface.h # 事件队列/扫描线接口
|   +-- SweepLine.h           # 扫描线
|   +-- BruteForceCrossings.h # 暴力求解
|   +-- Myers.h               # Myers 算法
|   +-- Contour.h             # 路径轮廓提取
+-- src/                      # 实现文件
|   +-- BUILD.bazel
|   +-- BentleyOttmann1.cpp   # 主算法实现
|   +-- Segment.cpp           # 线段操作与交点计算
|   +-- Point.cpp             # 点操作
|   +-- Int96.cpp             # 96位整数运算
|   +-- EventQueue.cpp        # 事件队列管理
|   +-- SweepLine.cpp         # 扫描线维护
|   +-- BruteForceCrossings.cpp # 暴力算法
|   +-- Myers.cpp             # Myers 算法实现
|   +-- Contour.cpp           # SkPath 到轮廓转换
+-- tests/                    # 单元测试
    +-- BUILD.bazel
    +-- BentleyOttmann1Test.cpp
    +-- SegmentTest.cpp
    +-- PointTest.cpp
    +-- Int96Test.cpp
    +-- EventQueueTest.cpp
    +-- SweepLineTest.cpp
    +-- BruteForceCrossingsTest.cpp
    +-- MyersTest.cpp
    +-- ContourTest.cpp
```

## 关键类与函数

| 类/函数 | 文件 | 说明 |
|---------|------|------|
| `bentley_ottmann_1()` | `include/BentleyOttmann1.h` | 主入口: 输入 Segment 集合,返回 Crossing 列表或 nullopt |
| `Segment` | `include/Segment.h` | 线段,由两个 Point (p0, p1) 定义,提供 upper()/lower() |
| `intersect()` | `include/Segment.h` | 计算两线段的交点 (不含端点) |
| `less_than_at()` | `include/Segment.h` | 在给定 y 坐标处比较两线段的 x 坐标 |
| `compare_slopes()` | `include/Segment.h` | 比较两线段的斜率 |
| `Crossing` | `include/Segment.h` | 交叉点记录 (两线段 + 交点坐标) |
| `Point` | `include/Point.h` | 32位整数坐标点,定义排序关系 (y 优先) |
| `Int96` | `include/Int96.h` | 96位有符号整数 (hi:int64 + lo:uint32),用于精确乘法 |
| `EventQueue` | `include/EventQueue.h` | 事件优先队列 (std::set),管理 Upper/Lower/Cross 事件 |
| `SweepLine` | `include/SweepLine.h` | 扫描线,维护有序线段集合,处理插入/删除/交点检测 |
| `EventQueueInterface` | `include/EventQueueInterface.h` | 事件队列与扫描线的解耦接口 |
| `brute_force_crossings()` | `include/BruteForceCrossings.h` | 暴力 O(n^2) 求解所有交点 |
| `myers_find_crossings()` | `include/Myers.h` | Myers 算法求交点 |
| `Contours` | `include/Contour.h` | 从 SkPath 提取整数化轮廓,缩放因子 1024 |
| `Contours::segments()` | `include/Contour.h` | 将轮廓转换为 Myers::Segment 列表 |

## 依赖关系

- **Skia Core**: `SkSpan`, `SkRect`, `SkPath`, `SkPoint` (仅 Contour 转换)
- **C++ 标准库**: `std::set`, `std::vector`, `std::variant`, `std::optional`
- **被依赖**: 路径操作 (pathops) 等几何处理模块

## 设计模式分析

1. **策略模式 (Strategy)**: `EventQueueInterface` 和 `SweepLineInterface` 将事件队列和扫描线解耦,允许独立测试。扫描线通过接口报告新交点给事件队列。

2. **观察者模式 (Observer)**: SweepLine 在检测到新交点时通过 `EventQueueInterface::addCrossing()` 通知事件队列,形成松耦合的事件驱动架构。

3. **变体类型 (Variant)**: `EventType = std::variant<Lower, Cross, Upper>` 使用类型安全的变体来区分三种事件类型。

4. **精确算术**: 通过 `Int96` 类型确保 32 位坐标的乘积不会溢出,在几何计算中保持精确性。

## 数据流

```
SkPath (浮点路径数据)
       |
       v
Contours::Make(path)
  - 缩放 x1024 并四舍五入为 int32
  - 提取闭合轮廓
  - 计算边界框
       |
       v
segments() --> std::vector<Segment>
       |
       v
bentley_ottmann_1(segments)
  1. EventQueue::Make(segments)
     - 为每条线段创建 Upper 和 Lower 事件
  2. while (hasMoreEvents):
     a. 取出当前事件点
     b. 收集该点的所有事件 (删除集 + 插入集)
     c. SweepLine::handleDeletions() -- 移除结束线段
     d. SweepLine::handleInsertionsAndCheckForNewCrossings()
        - 插入新线段
        - 检查相邻线段是否有新交点
        - 通过 addCrossing() 报告新事件
  3. 返回所有 Crossing
       |
       v
std::vector<Crossing> (所有交点)
```

## 相关文档与参考

- Bentley-Ottmann 算法原始论文: Bentley & Ottmann, "Algorithms for Reporting and Counting Geometric Intersections", 1979
- Myers 差分算法: Eugene W. Myers
- Skia 路径操作: `src/pathops/`
- 计算几何算法参考: "Computational Geometry: Algorithms and Applications" (de Berg et al.)
