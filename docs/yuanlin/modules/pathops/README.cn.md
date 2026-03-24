# pathops - 路径操作模块

## 概述

`modules/pathops` 是 Skia 的路径布尔操作模块的构建配置占位目录。该模块为路径操作功能提供了模块级别的构建集成点。路径操作 (Path Operations) 是计算几何中的核心功能,允许对两个或多个 `SkPath` 对象执行布尔运算(并集、交集、差集、异或)。

值得注意的是,路径操作的实际核心实现代码位于 Skia 源码树的 `src/pathops/` 目录中,而非此模块目录。本模块主要作为构建系统中的集成入口点,通过 `pathops.gni` 配置文件将路径操作功能暴露为可选的模块级构建目标。

路径操作的主要功能包括:
- **路径布尔运算**: 对两个路径执行 Union (并集)、Intersect (交集)、Difference (差集)、XOR (异或)、ReverseDifference (反差集) 等操作
- **路径简化**: 将自交叉的路径简化为非自交叉的等价路径
- **路径紧凑**: 将路径转换为使用最少控制点的等价表示

这些操作在矢量图形编辑器、SVG 处理、字体轮廓操作等场景中广泛使用。

## 架构图

```
+-------------------------------+
|   modules/pathops/            |
|   (构建配置入口)              |
|   pathops.gni                 |
+-------------------------------+
              |
              | 引用
              v
+-------------------------------+
|   src/pathops/                |
|   (核心实现)                  |
|   - SkOpBuilder              |
|   - SkOpContour              |
|   - SkOpSegment              |
|   - SkPathOpsOp              |
|   - SkPathOpsSimplify        |
+-------------------------------+
              |
              v
+-------------------------------+
|   include/pathops/            |
|   (公共 API)                  |
|   - SkPathOps.h              |
+-------------------------------+

布尔运算类型:
  A ∪ B  (Union)           A ∩ B  (Intersect)
  A - B  (Difference)      A ⊕ B  (XOR)
  B - A  (ReverseDifference)
```

## 目录结构

```
modules/pathops/
+-- pathops.gni    # GNI 构建配置 (客户端迁移占位)
```

## 关键类与函数

路径操作的核心 API 定义在 `include/pathops/SkPathOps.h` 中,主要函数包括:

| 函数 | 说明 |
|------|------|
| `Op(path1, path2, op, result)` | 对两个路径执行布尔运算 |
| `Simplify(path, result)` | 简化自交叉路径 |
| `TightBounds(path, bounds)` | 计算路径的紧凑边界 |
| `AsWinding(path, result)` | 将 EvenOdd 填充规则路径转换为 Winding 填充规则 |

## 依赖关系

- **Skia Core**: `SkPath`, `SkRect`, `SkPoint`
- **modules/bentleyottmann**: 线段交点检测算法
- **src/pathops/**: 路径操作的实际实现代码

## 设计模式分析

1. **外观模式 (Facade)**: 模块为复杂的路径操作算法提供简洁的顶层 API (`Op`, `Simplify`)，隐藏了内部的轮廓分析、线段求交、区域拓扑重建等复杂实现。

2. **模块化构建**: 通过独立的 GNI 配置文件,路径操作可以作为可选功能按需编译,减少不需要此功能的构建目标的体积。

## 数据流

```
SkPath A + SkPath B + SkPathOp 运算符
       |
       v
Op(pathA, pathB, op, &result)
  1. 路径分解为轮廓 (Contours)
  2. 轮廓分解为线段/曲线段
  3. 求所有线段交点 (Intersections)
  4. 在交点处分割线段
  5. 确定每个区域的内外关系
  6. 根据布尔运算类型选择保留的区域
  7. 重建输出路径
       |
       v
SkPath result (布尔运算结果)
```

## 相关文档与参考

- 路径操作公共 API: `include/pathops/SkPathOps.h`
- 核心实现: `src/pathops/`
- Bentley-Ottmann 算法: `modules/bentleyottmann/`
- Skia SkPath: `include/core/SkPath.h`
