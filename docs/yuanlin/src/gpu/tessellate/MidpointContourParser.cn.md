# MidpointContourParser - 轮廓中点解析器

> 源文件: `src/gpu/tessellate/MidpointContourParser.h`

## 概述

MidpointContourParser 是 Skia GPU 细分系统中用于解析路径轮廓并计算每个轮廓中点的实用类。它逐个解析路径中的轮廓（contour），在遍历过程中累积各曲线段端点的加权平均值作为轮廓的"中点"（midpoint）。

中点是多边形三角化（如 middle-out 三角化）的常用扇形中心点。通过在解析阶段同步计算中点，避免了对路径进行两次遍历（一次求中点，一次处理几何）。

## 架构位置

```
Skia GPU 曲线细分
  -> MidpointContourParser (轮廓解析 + 中点计算)
    -> SkPath 原始路径数据
  -> PatchWriter (使用中点作为扇形中心)
```

MidpointContourParser 在细分管线的路径解析阶段使用，为后续的三角化提供几何中心点。

## 主要类与结构体

### `MidpointContourParser`
- **职责**: 逐轮廓解析路径，同时计算每个轮廓的近似中点
- **使用模式**: 外层循环调用 `parseNextContour()`，内层循环用 `currentContour()` 遍历动词

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MidpointContourParser(const SkPath&)` | 构造函数，初始化路径迭代器 |
| `parseNextContour()` | 解析下一个轮廓，返回 false 表示无更多轮廓 |
| `currentContour()` | 返回当前轮廓的可迭代视图（SkPathPriv::Iterate） |
| `currentMidpoint()` | 返回当前轮廓的中点 |

## 内部实现细节

### 中点计算方法
中点是轮廓中所有曲线段端点的简单算术平均值。对于每个非 Move 动词，将其最后一个控制点（端点）累加到 `fMidpoint`，并递增 `fMidpointWeight`。最终中点为 `fMidpoint * (1/fMidpointWeight)`。

### 隐式关闭处理
如果轮廓的最后一个点与起点不同，说明存在隐式关闭线段。此时将起点也加入中点计算，确保中点考虑了完整的轮廓形状。

### 动词处理与索引推进
```
kMove:   fPtsIdx = 1（跳过 moveTo 点）
kLine:   fPtsIdx += 1
kQuad:   fPtsIdx += 2
kConic:  fPtsIdx += 2, fWtsIdx += 1
kCubic:  fPtsIdx += 3
kClose:  不增加索引（continue）
```

### advance() 方法
在遇到新的 kMove 时（即新轮廓开始），`advance()` 将内部指针前移到当前位置，重置局部索引。这使得 `currentContour()` 可以返回仅包含当前轮廓动词的视图。

### 数据组织
解析器直接操作路径的原始数组（`verbs`、`points`、`conicWeights`），使用索引而非迭代器，这允许在不同轮廓之间高效地分割数组视图。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `include/core/SkPath.h` | 路径数据源 |
| `include/core/SkPoint.h` | SkPoint 点类型 |
| `src/core/SkPathPriv.h` | 路径内部迭代（SkPathPriv::Iterate） |

## 设计模式与设计决策

1. **单遍处理**: 在解析轮廓结构的同时计算中点，避免了对路径的二次遍历。

2. **端点平均**: 使用端点（而非所有控制点）的平均值作为中点，这对大多数形状是合理的近似。对于极度不对称的曲线，中点可能偏离几何中心，但作为三角化的扇形中心点仍然有效。

3. **原始指针访问**: 直接使用原始指针和索引访问路径数据，避免了 SkPath 迭代器的额外开销。

4. **轮廓视图**: `currentContour()` 返回 `SkPathPriv::Iterate`，允许调用者使用 range-for 语法遍历当前轮廓。

## 性能考量

1. **O(n) 时间复杂度**: 整个路径只遍历一次，每个动词的处理为 O(1)。
2. **零内存分配**: 解析器不分配额外内存，仅存储指针和索引。
3. **缓存友好**: 顺序访问路径的连续数组数据，缓存利用率高。
4. **中点计算开销**: 每个动词仅需一次点加法和一次整数递增。

## 相关文件

- `src/gpu/tessellate/MiddleOutPolygonTriangulator.h` - 使用中点进行三角化
- `src/gpu/tessellate/PatchWriter.h` - 使用中点作为扇形属性
- `src/core/SkPathPriv.h` - 路径内部迭代工具
- `include/core/SkPath.h` - 路径数据结构
