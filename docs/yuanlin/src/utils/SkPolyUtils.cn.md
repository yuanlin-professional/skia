# SkPolyUtils — 多边形操作工具集

> 源文件：[src/utils/SkPolyUtils.h](../../src/utils/SkPolyUtils.h)、[src/utils/SkPolyUtils.cpp](../../src/utils/SkPolyUtils.cpp)

## 概述

`SkPolyUtils` 模块提供了一组多边形几何操作函数，主要用于阴影渲染中的多边形内缩（inset）、偏移（offset）和三角化（triangulation）。这些函数在 `SK_ENABLE_OPTIMIZE_SIZE` 未定义时可用。

核心功能：
- **凸多边形内缩**：将凸多边形向内等距收缩
- **简单多边形偏移**：将简单多边形向内或向外等距偏移
- **圆弧步进计算**：偏移顶点的圆弧接合点数
- **多边形属性判定**：绕向（winding direction）、凸性、简单性
- **多边形三角化**：将简单多边形分割为三角形

所有输入多边形的坐标值需钳位到最近的 1/16。

## 架构位置

```
阴影渲染 (SkShadowUtils)
    │
    └── SkPolyUtils
            ├── SkInsetConvexPolygon (凸多边形内缩)
            ├── SkOffsetSimplePolygon (简单多边形偏移)
            ├── SkTriangulateSimplePolygon (三角化)
            ├── SkGetPolygonWinding (绕向判定)
            ├── SkIsConvexPolygon (凸性检测)
            ├── SkIsSimplePolygon (简单性检测)
            └── SkComputeRadialSteps (圆弧步进)
```

## 公共 API 函数

### `SkInsetConvexPolygon(inputPolygonVerts, inputPolygonSize, inset, insetPolygon) -> bool`

对凸多边形执行等距内缩。输入多边形必须是凸的且无重合点。`inset` 为正值。如果内缩后多边形退化则返回 false。

### `SkOffsetSimplePolygon(inputPolygonVerts, inputPolygonSize, bounds, offset, offsetPolygon, polygonIndices) -> bool`

对简单多边形执行等距偏移。正值表示内缩，负值表示外扩。输入多边形必须是简单的、无重合顶点和共线边。可选返回原始顶点到新顶点的索引映射。

### `SkComputeRadialSteps(offset0, offset1, offset, rotSin, rotCos, n) -> bool`

计算两个偏移向量之间的圆弧接合所需的步数和旋转参数。线段长度约为 4 像素。

### `SkGetPolygonWinding(polygonVerts, polygonSize) -> int`

计算多边形绕向。返回 1（顺时针）、-1（逆时针）或 0（退化/自交叉）。假设 y 轴向下。

### `SkIsConvexPolygon(polygonVerts, polygonSize) -> bool`

检测多边形是否为凸多边形。

### `SkIsSimplePolygon(polygonVerts, polygonSize) -> bool`

检测多边形是否为简单多边形（不自交叉）。要求无重合顶点。

### `SkTriangulateSimplePolygon(polygonVerts, indexMap, polygonSize, triangleIndices) -> bool`

对简单多边形执行三角化。输入多边形必须无重合顶点和共线边。输出三角形索引列表。`indexMap` 提供输入索引到最终三角化索引的映射。

## 内部实现细节

实现文件（~1890 行）包含大量的计算几何算法：
- 使用有符号面积公式计算多边形绕向
- 内缩/偏移使用边法线的交点计算
- 简单性检测使用扫描线 + 边交叉判定
- 三角化使用耳剪法（ear clipping）的变体
- 圆弧接合通过旋转步进模拟

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkPoint` / `SkVector` | 2D 点和向量 |
| `SkScalar` | 标量数学 |
| `SkRect` | 多边形边界框 |
| `SkTDArray` | 动态数组（输出顶点和索引） |

## 设计模式与设计决策

1. **条件编译**：被 `SK_ENABLE_OPTIMIZE_SIZE` 守卫，在大小优化构建中完全移除。
2. **坐标精度要求**：输入要求钳位到 1/16，确保浮点比较的稳定性。
3. **纯函数接口**：所有函数都是无状态的纯函数，输出通过参数返回。
4. **索引映射**：`SkOffsetSimplePolygon` 可选返回索引映射，支持追踪新旧顶点关系。

## 性能考量

- 凸多边形内缩为 O(n) 线性算法。
- 简单多边形偏移和三角化为 O(n log n) 扫描线算法。
- 简单性检测使用扫描线交叉判定，复杂度 O(n log n)。
- 圆弧步进计算约 4 像素分段，平衡精度和三角形数量。

## 相关文件

- `src/utils/SkShadowUtils.cpp` — 主要调用者（阴影渲染）
- `include/core/SkPoint.h` — 点/向量类型
