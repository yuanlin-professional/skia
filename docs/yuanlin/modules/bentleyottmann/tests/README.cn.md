# bentleyottmann/tests - 算法模块测试

## 概述

`modules/bentleyottmann/tests/` 目录包含 Bentley-Ottmann 算法模块的完整单元测试套件。每个核心组件都有对应的测试文件,确保数据类型、算法逻辑和集成行为的正确性。

测试策略包括:对基本数据类型 (Point, Int96, Segment) 的单元测试、对独立组件 (EventQueue, SweepLine) 的隔离测试(通过接口解耦)、以及对完整算法 (BentleyOttmann1) 的集成测试。暴力算法 (BruteForceCrossings) 常被用作验证 Bentley-Ottmann 结果正确性的参考基准。

## 目录结构

```
tests/
+-- BUILD.bazel
+-- BentleyOttmann1Test.cpp    # 主算法集成测试
+-- SegmentTest.cpp            # 线段交点和比较测试
+-- PointTest.cpp              # 点排序和极值测试
+-- Int96Test.cpp              # 96位整数运算测试
+-- EventQueueTest.cpp         # 事件队列逻辑测试
+-- SweepLineTest.cpp          # 扫描线维护测试
+-- BruteForceCrossingsTest.cpp # 暴力算法测试
+-- MyersTest.cpp              # Myers 算法测试
+-- ContourTest.cpp            # 轮廓提取测试
```

## 相关文档与参考

- 模块实现: `modules/bentleyottmann/src/`
- 公共 API: `modules/bentleyottmann/include/`
