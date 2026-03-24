# geometry - Ganesh GPU 几何处理模块

## 概述

`src/gpu/ganesh/geometry/` 目录是 Skia Ganesh GPU 渲染后端中负责几何图形处理的核心模块。该模块提供了从高层图形基元（路径、矩形、圆角矩形等）到 GPU 可直接消费的三角形网格之间的桥梁。在 GPU 渲染管线中，所有非矩形的复杂几何形状最终都需要被分解（镶嵌/三角化）为三角形才能被光栅化硬件处理，而这个模块正是完成这一关键转换的地方。

该模块涵盖了多种几何处理能力：路径三角化（包括抗锯齿和非抗锯齿版本）、凸多边形的抗锯齿镶嵌、四边形（Quad）表示与操作、贝塞尔曲线的线性化近似，以及通用的形状抽象。这些功能共同构成了 Ganesh 渲染器将 SkPath、SkRect、SkRRect 等 Skia 核心图形对象高效转化为 GPU 绘制命令的基础设施。

模块中的代码大量使用了计算几何算法，包括 Bentley-Ottmann 扫描线算法用于简化自交多边形、基于活动边列表（Active Edge List）的单调多边形镶嵌算法、以及递归曲线细分算法。这些算法的正确性和效率直接影响 Skia 的 GPU 渲染质量和性能。

该模块设计上注重内存效率和可复用性。例如 `GrQuadBuffer` 使用紧凑的变长编码存储四边形数据，`GrAAConvexTessellator` 支持 `rewind()` 以在多次镶嵌间复用实例，`GrTriangulator` 使用 `SkArenaAlloc` 进行高效的竞技场分配以减少内存碎片。

形状抽象层（`GrShape` 和 `GrStyledShape`）则为上层渲染操作提供了统一的几何表示，使得不同类型的形状（点、线段、矩形、圆角矩形、弧、路径）能够以一致的方式进行简化、缓存键生成和样式应用。

## 架构图

```
+-------------------------------------------------------------------+
|                      上层绘制操作 (GrOps)                          |
+-------------------------------------------------------------------+
        |                    |                    |
        v                    v                    v
+----------------+  +------------------+  +----------------+
| GrStyledShape  |  |    GrQuad /      |  |  GrPathUtils   |
| (形状+样式抽象)|  | GrQuadBuffer     |  | (路径工具函数) |
+----------------+  | (四边形处理)     |  +----------------+
        |           +------------------+          |
        v                    |                    v
+----------------+           |           +------------------+
|   GrShape      |           |           | QuadUVMatrix     |
| (纯几何抽象)   |           |           | (UV 坐标计算)    |
+----------------+           |           +------------------+
        |                    |
        v                    v
+-------------------------------------------------------------------+
|                    三角化引擎 (Triangulation)                       |
+-------------------------------------------------------------------+
|                                                                     |
|  +---------------------+  +---------------------+                   |
|  | GrTriangulator      |  | GrAAConvex          |                   |
|  | (通用路径三角化)    |  | Tessellator         |                   |
|  |   |                 |  | (凸多边形AA镶嵌)    |                   |
|  |   +-> GrAATriang.   |  +---------------------+                   |
|  |   |   (AA三角化)    |                                            |
|  |   +-> GrInnerFan    |  +---------------------+                   |
|  |       Triangulator   |  | GrQuadUtils         |                   |
|  |       (内扇三角化)  |  | TessellationHelper  |                   |
|  +---------------------+  | (四边形镶嵌辅助)    |                   |
|                            +---------------------+                   |
+-------------------------------------------------------------------+
                             |
                             v
                   +-------------------+
                   |  GPU 顶点缓冲区   |
                   | (三角形列表)       |
                   +-------------------+
```

## 文件分类索引

### 1. 四边形表示 — Quad Representation

| 文件 | 说明 |
|------|------|
| GrQuad.h / GrQuad.cpp | 四边形几何表示（设备空间 + 局部空间坐标） |
| GrQuadBuffer.h | 四边形紧凑存储缓冲区（变长编码模板类） |
| GrQuadUtils.h / GrQuadUtils.cpp | 四边形操作工具（裁剪、镶嵌辅助） |

### 2. 矩形工具 — Rect Utilities

| 文件 | 说明 |
|------|------|
| GrRect.h | 矩形工具函数（重叠检测、坐标映射等） |

### 3. 路径/形状处理 — Path/Shape Abstraction

| 文件 | 说明 |
|------|------|
| GrShape.h / GrShape.cpp | 通用几何形状抽象（点、线段、矩形、RRect、弧、路径） |
| GrStyledShape.h / GrStyledShape.cpp | 带样式的形状抽象（几何 + 描边/填充样式） |
| GrPathUtils.h / GrPathUtils.cpp | 路径处理工具函数集（曲线细分、控制点计算） |

### 4. 三角剖分 — Triangulation Engines

| 文件 | 说明 |
|------|------|
| GrTriangulator.h / GrTriangulator.cpp | 通用路径三角化引擎（Bentley-Ottmann 扫描线算法） |
| GrAATriangulator.h / GrAATriangulator.cpp | 抗锯齿路径三角化器 |
| GrInnerFanTriangulator.h | 内扇三角化器（Redbook stencil-then-cover 方法） |
| GrAAConvexTessellator.h / GrAAConvexTessellator.cpp | 凸多边形抗锯齿镶嵌器 |

## 关键类与函数

### GrTriangulator - 路径三角化引擎

这是整个模块最复杂的类，实现了将任意 `SkPath` 转换为三角形列表的完整管线。算法分为六个阶段：

1. **路径线性化** (`pathToContours`)：将曲线段近似为折线段
2. **网格构建** (`contoursToMesh`)：将顶点连接为边的网格
3. **顶点排序** (`SortMesh`)：按 Y 坐标（及 X 坐标）归并排序
4. **网格简化** (`simplify`)：基于 Bentley-Ottmann 算法处理自交
5. **单调多边形镶嵌** (`tessellate`)：分解为单调多边形
6. **三角化** (`polysToTriangles`)：将单调多边形转换为三角形

```cpp
// 核心静态接口
static int PathToTriangles(const SkPath& path, SkScalar tolerance,
                           const SkRect& clipBounds,
                           GrEagerVertexAllocator* vertexAllocator,
                           bool* isLinear);
```

内部数据结构包括 `Vertex`（顶点）、`Edge`（边）、`EdgeList`（活动边列表）、`MonotonePoly`（单调多边形）、`Poly`（多边形）和 `Line`（隐式直线方程）。

### GrAATriangulator - 抗锯齿三角化

继承自 `GrTriangulator`，在标准三角化的基础上增加了抗锯齿处理。核心思想是将多边形边界向内外各偏移半个像素，生成 alpha 渐变带：

```cpp
static int PathToAATriangles(const SkPath& path, SkScalar tolerance,
                              const SkRect& clipBounds,
                              GrEagerVertexAllocator* vertexAllocator);
```

额外阶段包括：边界提取 (`extractBoundary`)、边界简化 (`simplifyBoundary`)、边界描边 (`strokeBoundary`)。

### GrAAConvexTessellator - 凸多边形抗锯齿镶嵌

专门针对凸多边形的优化镶嵌器。通过"环缩"（ring inset）算法逐层向内收缩多边形轮廓来生成覆盖率渐变，支持填充和描边样式：

```cpp
class GrAAConvexTessellator {
    bool tessellate(const SkMatrix& m, const SkPath& path);
    int numPts() const;
    int numIndices() const;
    const SkPoint& point(int index) const;
    SkScalar coverage(int index) const;
};
```

内部使用 `Ring`（环）和 `CandidateVerts`（候选顶点）辅助类管理逐层收缩过程。

### GrQuad - 四边形表示

表示 GPU 渲染中的任意四边形。四个顶点按 CCW 三角条带顺序排列（左上、左下、右上、右下）。支持四种类型分类：

```cpp
enum class Type {
    kAxisAligned,   // 轴对齐矩形
    kRectilinear,   // 直角四边形（旋转后的矩形）
    kGeneral,       // 一般2D四边形
    kPerspective    // 透视四边形（w != 1）
};
```

`DrawQuad` 结构体将设备空间四边形、局部坐标四边形和 AA 边标志组合在一起，作为绘制操作的基本工作单元。

### GrQuadBuffer<T> - 四边形缓冲区

使用变长编码的紧凑缓冲区，存储设备四边形、可选局部四边形和元数据。每个条目的存储结构为：

```
[Header: 4字节] [Metadata: sizeof(T)] [Device XY(W): 8或12个float] [Local XY(W): 0/8/12个float]
```

提供只读迭代器 `Iter` 和可变元数据迭代器 `MetadataIter`。

### GrShape 和 GrStyledShape - 形状抽象

`GrShape` 是纯几何数据的联合体表示，支持七种类型：Empty、Point、Rect、RRect、Path、Arc、Line。提供无损简化、包含检测和路径转换功能。

`GrStyledShape` 在 `GrShape` 基础上组合了 `GrStyle`（描边、路径效果等），提供带样式的形状表示。支持缓存键生成、样式应用和形状简化。

### GrPathUtils - 路径工具函数

```cpp
namespace GrPathUtils {
    // 将容差从设备空间缩放到源空间
    SkScalar scaleToleranceToSrc(SkScalar devTol, const SkMatrix& viewM,
                                  const SkRect& pathBounds);
    // 二次贝塞尔曲线线性化
    uint32_t generateQuadraticPoints(...);
    // 三次贝塞尔曲线线性化
    uint32_t generateCubicPoints(...);
    // 三次曲线转二次曲线序列
    void convertCubicToQuads(...);
    // 圆锥曲线的 KLM 隐式方程计算
    void getConicKLM(const SkPoint p[3], SkScalar weight, SkMatrix* klm);
}
```

### GrRect - 矩形工具

提供矩形重叠检测和坐标映射的内联工具函数：

```cpp
static inline bool GrRectsOverlap(const SkRect& a, const SkRect& b);
static inline bool GrRectsTouchOrOverlap(const SkRect& a, const SkRect& b);
static inline void GrMapRectPoints(const SkRect& inRect, const SkRect& outRect,
                                    const SkPoint inPts[], SkPoint outPts[], size_t ptCount);
```

## 依赖关系

### 内部依赖（模块内）

- `GrAATriangulator` 继承自 `GrTriangulator`
- `GrInnerFanTriangulator` 继承自 `GrTriangulator`
- `GrStyledShape` 包含 `GrShape` 和 `GrStyle`
- `GrQuadUtils` 依赖 `GrQuad`
- `GrQuadBuffer` 依赖 `GrQuad`

### 外部依赖（Skia 核心）

- `include/core/SkPath` - 路径定义
- `include/core/SkRRect` - 圆角矩形
- `include/core/SkMatrix` - 变换矩阵
- `include/core/SkPoint` / `SkRect` - 基础几何类型
- `src/base/SkArenaAlloc` - 竞技场内存分配器
- `src/gpu/BufferWriter` - GPU 缓冲区写入器

### 被依赖关系

该模块被以下 Ganesh 组件广泛使用：

- `GrOps` 系列操作类（如 `AAConvexPathOp`、`TriangulatingPathOp` 等）
- `GrSurfaceDrawContext` 的形状绘制路径
- Tessellation 着色器管线

## 设计模式分析

### 模板方法模式 (Template Method)

`GrTriangulator` 使用模板方法模式定义三角化管线的骨架。`tessellate()` 是虚函数，允许 `GrAATriangulator` 重写第5步以插入 AA 边界处理逻辑，而保持其余步骤不变。

### 策略模式 (Strategy)

`GrShape` 通过类型枚举和联合体实现了一种轻量级的策略模式。不同几何类型有不同的 `simplify`、`bounds`、`contains` 实现，通过类型标记进行分派。

### 享元模式 (Flyweight)

`GrQuadBuffer` 实现了紧凑的四边形存储，通过变长编码避免了为每个四边形分配独立对象，节省内存开销。Header 中的位字段精确控制存储的数据量。

### 环缩算法 (Ring Inset)

`GrAAConvexTessellator` 使用独特的环缩算法：初始多边形作为"第0环"，沿法线向内偏移生成后续环，每环之间连接三角形条带。这种方法对于凸多边形特别高效，能生成平滑的覆盖率渐变。

## 数据流

```
SkPath / SkRect / SkRRect
            |
            v
    +------------------+
    | GrStyledShape    |  <-- 应用样式简化，生成缓存键
    | - 简化 (simplify)|
    | - 样式应用       |
    +------------------+
            |
            v
    +------------------+
    | GrShape          |  <-- 纯几何表示
    | - asPath()       |
    +------------------+
            |
            +------------------+-------------------+
            |                  |                   |
            v                  v                   v
    +--------------+  +----------------+   +----------------+
    | GrTriang.    |  | GrAAConvex     |   | GrQuad         |
    | PathToTri()  |  | Tessellator    |   | MakeFromRect() |
    +--------------+  | tessellate()   |   +----------------+
            |         +----------------+           |
            |                  |                   v
            v                  v           +----------------+
    +-------------------------------+      | GrQuadUtils    |
    |   顶点缓冲区                  |      | CropToRect()   |
    |   (position, coverage, UV)    |      | inset/outset   |
    +-------------------------------+      +----------------+
            |                                      |
            v                                      v
    +----------------------------------------------+
    |        GPU 光栅化管线                         |
    +----------------------------------------------+
```

### 典型三角化流程

1. 上层 Op 将 `SkPath` 传入 `GrTriangulator::PathToTriangles()`
2. 路径被线性化为折线轮廓（曲线用递归细分近似）
3. 轮廓顶点按归并排序
4. 扫描线算法检测并处理边交叉
5. 生成单调多边形集合
6. 每个单调多边形被三角化为三角扇
7. 三角形顶点写入 `GrEagerVertexAllocator` 分配的顶点缓冲区

## 相关文档与参考

- Skia 官方文档：https://skia.org/docs/dev/design/
- Fournier, A. and Montuno, D. "Triangulating Simple Polygons and Equivalent Problems" - `GrTriangulator` 中镶嵌算法的理论基础
- Bentley-Ottmann 扫描线算法 - `GrTriangulator::simplify()` 中使用的交点检测算法
- `src/gpu/ganesh/ops/` - 使用本模块的绘制操作类
- `src/gpu/ganesh/GrStyle.h` - `GrStyledShape` 依赖的样式定义
- `src/gpu/ganesh/tessellate/` - 更现代的硬件镶嵌路径（使用镶嵌着色器）
- `include/core/SkPath.h` - 路径定义与操作
- `src/core/SkPointPriv.h` - 点操作的内部扩展
