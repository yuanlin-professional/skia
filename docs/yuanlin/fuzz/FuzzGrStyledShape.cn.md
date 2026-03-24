# GrStyledShape 模糊测试

> 源文件: `fuzz/FuzzGrStyledShape.cpp`

## 概述

此文件对 Ganesh GPU 后端的 `GrStyledShape` 类进行模糊测试。`GrStyledShape` 封装了带样式的几何形状，是 Ganesh 路径渲染管线的核心类型。测试覆盖了从多种来源（Path、Rect、RRect）创建 Shape 并执行其所有查询方法。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，专门针对 Ganesh GPU 后端的几何处理。

## 主要类与结构体

无自定义结构体。测试对象为 `GrStyledShape`。

## 公共 API 函数

- `DEF_FUZZ(GrStyledShape, fuzz)` - 创建多种 Shape 并全面测试其方法

## 内部实现细节

- 创建 10 种不同来源的 Shape：带 Paint 的 Path/Rect/RRect、无 Paint 的 Path/Rect/RRect、Rect/RRect/Oval 路径、以及 MakeFilled 副本
- `exercise_shape` lambda 调用 Shape 的所有查询方法：`style()`, `simplified()`, `applyStyle()`, `isRect()`, `asRRect()`, `asLine()`, `asNestedRects()`, `asPath()`, `isEmpty()`, `bounds()`, `styledBounds()`, `knownToBeConvex()` 等
- 使用 `SkASSERT_RELEASE` 验证 `asPath()` 返回有效路径

## 依赖关系

- `fuzz/Fuzz.h`, `fuzz/FuzzCommon.h`
- `src/gpu/ganesh/geometry/GrStyledShape.h`

## 设计模式与设计决策

**全面方法覆盖**：对被测对象的每个公共方法都进行调用，确保不会在任何输入下崩溃。

## 性能考量

测试轻量级，每次调用创建 10 个 Shape 并分别测试。

## 相关文件

- `src/gpu/ganesh/geometry/GrStyledShape.h` - 被测类
