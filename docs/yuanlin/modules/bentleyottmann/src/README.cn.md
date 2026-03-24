# bentleyottmann/src - 算法模块实现代码

## 概述

`modules/bentleyottmann/src/` 目录包含 Bentley-Ottmann 算法模块所有头文件对应的实现。核心实现文件 `BentleyOttmann1.cpp` 将 `EventQueue` 和 `SweepLine` 组合起来运行完整的扫描线算法。`Segment.cpp` 实现了精确的线段交点计算,使用 `Int96` 避免整数溢出。

`EventQueue.cpp` 管理事件优先队列,在每个事件点收集需要删除和插入的线段集合。`SweepLine.cpp` 维护扫描线上线段的有序状态,在插入新线段后检查相邻线段对是否产生新交点。

`Contour.cpp` 实现了从 `SkPath` 到整数化轮廓的转换,将浮点坐标乘以 1024 并四舍五入为整数,然后提取闭合轮廓。`Myers.cpp` 实现了另一种交点检测算法。

## 目录结构

```
src/
+-- BUILD.bazel
+-- BentleyOttmann1.cpp   # 主算法: EventQueue + SweepLine 协同
+-- Segment.cpp           # 线段交点、斜率比较、边界框检测
+-- Point.cpp             # 点排序与极值
+-- Int96.cpp             # 96位整数加法与乘法
+-- EventQueue.cpp        # 事件队列管理与事件分发
+-- SweepLine.cpp         # 扫描线插入/删除与邻居交点检测
+-- BruteForceCrossings.cpp # 暴力 O(n^2) 实现
+-- Myers.cpp             # Myers 算法实现
+-- Contour.cpp           # SkPath 轮廓提取与整数化
```

## 关键实现细节

| 文件 | 核心逻辑 |
|------|---------|
| `BentleyOttmann1.cpp` | 主循环: 取事件 -> 删除 -> 插入+检测 -> 收集交点 |
| `Segment.cpp` | `intersect()` 使用 Int96 精确计算; `less_than_at()` 在扫描线 y 处比较 |
| `EventQueue.cpp` | `handleNextEventPoint()` 收集同一点的全部事件并分发 |
| `SweepLine.cpp` | `handleInsertionsAndCheckForNewCrossings()` 检查新邻居对 |

## 相关文档与参考

- 公共 API: `modules/bentleyottmann/include/`
- 测试验证: `modules/bentleyottmann/tests/`
