# tessellate - Skia GPU 通用细分曲面代码

## 概述

`src/gpu/tessellate` 目录包含了 Skia 图形库中 GPU 路径渲染的核心细分曲面(tessellation)算法实现。这些代码是 Ganesh(旧版 GPU 后端)和 Graphite(新一代 GPU 后端)共享的基础设施,位于 `skgpu::tess` 命名空间下。

细分曲面是将参数化曲线(如二次贝塞尔、三次贝塞尔和圆锥曲线)转换为 GPU 可直接光栅化的线段和三角形的过程。Skia 的细分系统基于 Wang 公式来确定每条曲线所需的最小线段数量,以保证渲染结果与真实曲线之间的误差不超过 1/4 像素(精度参数 `kPrecision = 4`)。

该目录的核心设计围绕"Patch"概念展开。一个 Patch 由 4 个控制点加上可选属性组成,可以表示三次贝塞尔曲线、圆锥曲线(通过特殊标记)或三角形。`PatchWriter` 是整个系统的核心模板类,负责将路径几何体转换为 GPU 缓冲区中的 Patch 实例数据。它通过 C++ 模板 trait 系统在编译期和运行期灵活配置属性和行为。

固定计数(Fixed-Count)渲染是另一个关键架构决策。与硬件细分曲面不同,Skia 使用预先构建的静态顶点/索引缓冲区作为模板,通过实例化渲染(instanced rendering)来绘制所有曲线 Patch。这种方式兼容性更广,不依赖于硬件细分曲面着色器支持。

该模块还包含了针对描边(stroke)路径的专用迭代器和参数计算,能够正确处理连接(join)、端帽(cap)以及不同的描边宽度。中点外出(Middle-Out)三角化算法用于高效地将多边形扇形区域分解为三角形,相比线性三角条带能显著减少光栅化器的工作量。

## 架构图

```
                    +--------------------------+
                    |     SkPath (输入路径)     |
                    +-----------+--------------+
                                |
                    +-----------v--------------+
                    |    PreChopPathCurves()    |
                    |  (预切分超长曲线,裁剪)    |
                    +-----------+--------------+
                                |
              +-----------------v------------------+
              |          PatchWriter<Alloc, Traits> |
              |  (核心模板类: 曲线->Patch转换)      |
              |                                     |
              |  +-------------------------------+  |
              |  | WangsFormula (Wang公式计算)    |  |
              |  | - quadratic_p4()              |  |
              |  | - cubic_p4()                  |  |
              |  | - conic_p2()                  |  |
              |  +-------------------------------+  |
              |                                     |
              |  +-------------------------------+  |
              |  | LinearTolerances (线性容差)    |  |
              |  | - requiredResolveLevel()      |  |
              |  | - requiredStrokeEdges()       |  |
              |  +-------------------------------+  |
              |                                     |
              |  +-------------------------------+  |
              |  | AffineMatrix (SIMD仿射变换)   |  |
              |  | CullTest    (视口裁剪测试)    |  |
              |  +-------------------------------+  |
              |                                     |
              |  writeCubic / writeConic / writeLine |
              |  writeQuadratic / writeTriangle     |
              +-----------------+-------------------+
                                |
          +---------------------+---------------------+
          |                     |                     |
+---------v--------+  +---------v--------+  +---------v--------+
| FixedCountCurves |  | FixedCountWedges |  | FixedCountStrokes|
| (曲线填充模式)   |  | (扇形填充模式)   |  | (描边模式)       |
+------------------+  +------------------+  +------------------+
          |                     |                     |
          +---------+-----------+---------+-----------+
                    |                     |
        +-----------v------+  +-----------v-----------+
        | MiddleOutPolygon |  |    StrokeIterator     |
        | Triangulator     |  | (描边迭代器: 处理     |
        | (中点外出三角化) |  |  cap/join/close)      |
        +------------------+  +-----------------------+
                    |
          +---------v---------+
          |  GPU 缓冲区输出   |
          |  (实例化渲染数据) |
          +-------------------+
```

## 目录结构

```
src/gpu/tessellate/
|-- BUILD.bazel                          # Bazel 构建配置
|-- AffineMatrix.h                       # SIMD 优化的 2D 仿射变换矩阵
|-- CullTest.h                           # 视口裁剪测试(SIMD 加速)
|-- FixedCountBufferUtils.h              # 固定计数缓冲区工具类声明
|-- FixedCountBufferUtils.cpp            # 固定计数缓冲区数据写入实现
|-- LinearTolerances.h                   # 线性容差追踪(分段数计算)
|-- MiddleOutPolygonTriangulator.h       # 中点外出多边形三角化器
|-- MidpointContourParser.h             # 轮廓中点解析器
|-- PatchWriter.h                        # 核心Patch写入器模板类(~900行)
|-- StrokeIterator.h                     # 描边路径迭代器
|-- Tessellation.h                       # 公共常量、枚举和工具函数
|-- Tessellation.cpp                     # 曲线预切分和凸180度切分实现
|-- WangsFormula.h                       # Wang公式各曲线类型实现
```

## 关键类与函数

### `PatchWriter<PatchAllocator, ...Traits>` (PatchWriter.h)

整个细分系统中最核心的模板类,约 900 行代码。它接收路径动词(verb)并输出 GPU 可用的 Patch 实例数据。

**模板 Trait 支持:**
- `Required<PatchAttribs::A>` - 编译期必须启用的属性
- `Optional<PatchAttribs::A>` - 运行期可选属性
- `TrackJoinControlPoints` - 自动追踪描边连接控制点
- `AddTrianglesWhenChopping` - 切分曲线时自动填充三角形
- `DiscardFlatCurves` - 丢弃平坦曲线(单线段即可表示)
- `ReplicateLineEndPoints` - 以 `{a,a,b,b}` 方式编码直线

**关键写入方法:**
- `writeCubic()` - 写入三次贝塞尔曲线
- `writeConic()` - 写入圆锥曲线(带权重 w)
- `writeQuadratic()` - 写入二次曲线(自动转为等价三次)
- `writeLine()` - 写入直线(转为退化三次)
- `writeTriangle()` - 写入三角形(用 `w=Inf` 的圆锥标记)
- `writeCircle()` / `writeSquare()` - 写入圆形/方形端帽

### `wangs_formula` 命名空间 (WangsFormula.h)

实现 Wang 公式,计算贝塞尔曲线在保证精度下所需的最小均匀参数分段数。

```cpp
// Wang 公式核心: n = sqrt(maxLength * precision * n*(n-1)/8)
// 针对不同曲线类型的特化:
float quadratic_p4(precision, p0, p1, p2, xform);  // 二次曲线, n^4
float cubic_p4(precision, p0, p1, p2, p3, xform);  // 三次曲线, n^4
float conic_p2(precision, p0, p1, p2, w, xform);   // 圆锥曲线, n^2
```

**`VectorXform` 类** - 表示 2x2 仿射变换矩阵的上半部分,用于在 Wang 公式中近似设备空间变换。

### `LinearTolerances` (LinearTolerances.h)

追踪参数分段和径向分段的最坏情况容差值:
- `fNumParametricSegments_p4` - 参数分段数的四次方
- `fNumRadialSegmentsPerRadian` - 每弧度径向分段数(描边用)
- `fEdgesInJoins` - 连接处的固定边数

### `FixedCountCurves` / `FixedCountWedges` / `FixedCountStrokes` (FixedCountBufferUtils.h)

三种固定计数渲染模式的缓冲区工具:
- **Curves**: 仅细分曲线,需额外机制填充内部
- **Wedges**: 曲线 + 扇形中心点三角形(配合 `kFanPoint` 属性)
- **Strokes**: 描边模式,包含径向分段和连接几何

### `MiddleOutPolygonTriangulator` (MiddleOutPolygonTriangulator.h)

使用中点外出策略的 O(N) 多边形三角化器。与线性三角条带相比,中点外出方式产生的三角形覆盖面积更均匀,显著减少光栅化器的工作量。使用 O(log N) 的栈空间,无需预先知道所有顶点。

### `StrokeIterator` (StrokeIterator.h)

描边路径迭代器,自动处理:
- 关闭动词转换为直线
- 方形端帽转换为直线
- 圆形端帽转换为圆
- 退化笔画(零长度子路径)的端帽生成

### `CullTest` / `AffineMatrix` (CullTest.h / AffineMatrix.h)

SIMD 优化的几何工具:
- **CullTest**: 使用 `float4` 同时测试多点是否在视口内
- **AffineMatrix**: 使用 `float4` 同时变换两个点

## 依赖关系

```
tessellate 模块依赖:
  +-- include/core/SkPath, SkMatrix, SkPoint, SkRect, SkPaint
  +-- include/core/SkStrokeRec (描边参数)
  +-- src/base/SkVx.h (SIMD向量运算)
  +-- src/base/SkUtils.h (位转换工具)
  +-- src/core/SkGeometry.h (几何切分: SkChopQuadAtHalf, SkChopCubicAtHalf)
  +-- src/core/SkPathPriv.h (路径内部迭代)
  +-- src/gpu/BufferWriter.h (GPU缓冲区写入)

被以下模块使用:
  +-- src/gpu/ganesh/ (Ganesh GPU后端)
  +-- src/gpu/graphite/ (Graphite GPU后端)
```

## 设计模式分析

### 1. 策略模式 (Strategy Pattern) + 编译期多态

`PatchWriter` 通过模板 Trait 参数实现编译期策略选择。不同的 GPU 后端和渲染算法通过不同的 Trait 组合来配置行为,避免了运行时虚函数调用的开销:

```cpp
// Graphite 填充示例
PatchWriter<GraphiteAlloc, Required<PatchAttribs::kFanPoint>,
            AddTrianglesWhenChopping, DiscardFlatCurves>

// Ganesh 描边示例
PatchWriter<GaneshAlloc, Required<PatchAttribs::kJoinControlPoint>,
            Required<PatchAttribs::kStrokeParams>, TrackJoinControlPoints>
```

### 2. RAII 与惰性求值

`MiddleOutPolygonTriangulator::PoppedTriangleStack` 是一个 RAII 对象,支持范围 for 循环迭代弹出的三角形,在析构时完成栈更新。这种设计将遍历和状态变更分离:

```cpp
for (auto [p0, p1, p2] : middleOut.pushVertex(pt)) {
    vertexWriter << p0 << p1 << p2;
}
// 析构时自动更新栈状态
```

### 3. 条件编译优化

`AttribValue` 通过模板特化实现属性的三态管理(必须启用/可选/禁用),禁用的属性在编译后不占用任何存储或写入开销:

```cpp
template <PatchAttribs A, typename T, bool Required, bool Optional>
struct AttribValue {
    using DataType = std::conditional_t<Required, T,
                     std::conditional_t<Optional, std::pair<T, bool>,
                                        std::monostate>>;
};
```

### 4. 数值精度优化

系统大量使用 n^4 形式存储 Wang 公式结果,延迟开四次方运算到最终需要时。`nextlog16()` 函数直接从 n^4 计算 ceil(log2(n)),利用浮点数 IEEE 754 位表示巧妙避免了开方运算。

## 数据流

```
1. 输入: SkPath + SkMatrix + 渲染参数(填充/描边)
       |
2. PreChopPathCurves(): 预切分曲线使所有子曲线 <= 1024 段
       |                 视口外的曲线被平坦化为直线
       |
3. PatchWriter 接收路径动词:
       |
       +---> writeCubic(p0,p1,p2,p3)
       |       |-- WangsFormula::cubic_p4() 计算所需分段数 n^4
       |       |-- 如果 n^4 > maxSegments^4: 切分为多个子曲线
       |       |     +-- chopAndWriteCubics() 参数均匀切分
       |       |     +-- 可选: writeTriangle() 填充切分间隙
       |       |-- writePatch() 输出4控制点 + 属性到GPU缓冲区
       |
       +---> writeConic(p0,p1,p2,w) -> 类似流程
       +---> writeQuadratic(p0,p1,p2) -> 转为等价三次 -> 类似流程
       +---> writeLine(p0,p1) -> 编码为退化三次
       |
4. LinearTolerances 累积最坏情况容差
       |
5. FixedCount{Curves|Wedges|Strokes}::VertexCount(tolerances)
       |  计算所需的总顶点数/索引数
       |
6. GPU 使用预构建的静态顶点/索引缓冲区模板
   进行实例化渲染(instanced draw)
```

## 相关文档与参考

- **Wang 公式原始文献**: Goldman, Ron. (2003). "5.6.3 Wang's Formula." in *Pyramid Algorithms: A Dynamic Programming Approach to Curves and Surfaces for Geometric Modeling*. Morgan Kaufmann Publishers.
- **圆锥曲线分段公式**: Zheng, J. & Sederberg, T. (2000). "Estimating Tessellation Parameter Intervals for Rational Curves and Surfaces." ACM Transactions on Graphics 19(1).
- **Loop-Blinn 曲线分类**: Microsoft Research. (2005). "Resolution Independent Curve Rendering using Programmable Graphics Hardware."
- **Skia GPU 后端 Ganesh**: `src/gpu/ganesh/tessellate/` - Ganesh 特定的细分渲染管线
- **Skia GPU 后端 Graphite**: `src/gpu/graphite/` - Graphite 中使用 PatchWriter 的渲染器
- **中点外出三角化**: 相比线性扇形三角化,能减少约 50% 的光栅化负载
- **Chromium Bug 1472747**: PreChopPathCurves 必须保留输入路径的填充类型
