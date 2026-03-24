# FuzzPolyUtils (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzPolyUtils.cpp

## 概述

`FuzzPolyUtils.cpp` 测试多边形工具函数,包括偏移、三角剖分、凸包计算等几何算法。这些工具在阴影渲染、路径填充和几何处理中广泛使用。

## 架构位置

测试 `src/utils/SkPolyUtils.h` 中的多边形算法。

## 主要类与结构体

**LLVMFuzzerTestOneInput**:
- 最大输入 4000 字节
- 通过 `#if !defined(SK_ENABLE_OPTIMIZE_SIZE)` 条件编译
- 在尺寸优化构建中禁用

**fuzz_PolyUtils** (外部定义):
- 生成随机多边形点集
- 调用 SkOffsetSimplePolygon
- 调用 SkTriangulateSimplePolygon
- 调用 SkComputeConvexHull
- 调用 SkIsConvexPolygon
- 调用 SkIsSimplePolygon

## 内部实现细节

测试算法包括:
- **多边形偏移**: 内外偏移,处理自交
- **三角剖分**: 耳切法,约束三角剖分
- **凸包**: Graham scan, Jarvis march
- **凸性检测**: 叉积符号检查
- **简单性检测**: 边相交检测

## 依赖关系

- `src/utils/SkPolyUtils.cpp`: 多边形算法实现
- `include/core/SkPath.h`: 路径转多边形

## 设计模式与设计决策

**条件编译**: 在代码大小优化时禁用,因为这些算法可能被内联或移除。

## 性能考量

- **算法复杂度**: 某些操作为 O(n²) 或 O(n³)
- **退化情况**: 共线点、重合点
- **大多边形**: 数千个顶点的性能

## 相关文件

- `src/utils/SkPolyUtils.h`: 多边形工具接口
- `tests/PolyUtilsTest.cpp`: 单元测试
- `src/core/SkShadowUtils.cpp`: 使用多边形偏移实现阴影

该 fuzzer 发现了多个几何算法中的数值稳定性和边界情况问题。
