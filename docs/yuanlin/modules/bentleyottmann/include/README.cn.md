# bentleyottmann/include - 算法模块公共头文件

## 概述

`modules/bentleyottmann/include/` 目录定义了 Bentley-Ottmann 线段交点算法模块的完整公共接口。头文件分为三个层次:核心数据类型 (`Point`, `Segment`, `Int96`)、算法实现 (`BentleyOttmann1`, `SweepLine`, `EventQueue`) 和辅助功能 (`BruteForceCrossings`, `Myers`, `Contour`)。

所有核心几何类型使用 `int32_t` 整数坐标,通过 `Int96` 类型处理乘法中间结果的精度问题。`EventQueueInterface.h` 定义了事件队列和扫描线之间的抽象接口,支持独立单元测试。

## 关键类与函数

| 头文件 | 核心类型 | 说明 |
|--------|---------|------|
| `BentleyOttmann1.h` | `bentley_ottmann_1()` | 算法主入口函数 |
| `Segment.h` | `Segment`, `Crossing`, `intersect()` | 线段与交点核心类型 |
| `Point.h` | `Point` | 整数坐标点 (int32_t x, y) |
| `Int96.h` | `Int96`, `multiply()` | 96 位精确整数运算 |
| `EventQueue.h` | `EventQueue`, `Event`, `Upper/Lower/Cross` | 事件优先队列 |
| `EventQueueInterface.h` | `EventQueueInterface`, `SweepLineInterface` | 解耦接口 |
| `SweepLine.h` | `SweepLine` | 扫描线维护 |
| `BruteForceCrossings.h` | `brute_force_crossings()` | 暴力求解 |
| `Myers.h` | `myers_find_crossings()`, `myers::Segment` | Myers 算法 |
| `Contour.h` | `Contours`, `Contour` | SkPath 到整数轮廓转换 |

## 相关文档与参考

- 模块概述: `modules/bentleyottmann/README.md`
- 测试代码: `modules/bentleyottmann/tests/`
