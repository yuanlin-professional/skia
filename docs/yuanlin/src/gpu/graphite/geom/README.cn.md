# geom - Graphite 几何工具库

## 概述

`src/gpu/graphite/geom/` 目录是 Skia Graphite 渲染后端的几何数据基础设施层。该模块提供了一组类型安全、
高性能的几何数据结构和空间管理工具，为 Graphite 的整个渲染管线提供几何输入的统一抽象。从简单的矩形和
变换矩阵到复杂的形状变体容器和空间查询加速结构，这些类构成了 Graphite 处理所有 2D 图形数据的基础。

该模块的核心设计理念是 **SIMD 优先**。`Rect` 类将矩形数据存储为 `[left, top, -right, -bottom]` 的
取反格式，使得交集、并集、内缩、外扩等常见运算只需单条 SIMD 指令即可完成。`Shape` 类作为几何形状的
variant 容器，统一了直线、矩形、圆角矩形、弧线和路径的表示，使上层代码无需关心具体的几何类型。
`Transform` 类封装了 4x4 矩阵及其逆矩阵、类型分类和缓存的缩放因子，避免了重复的矩阵求逆和类型判断。

`Geometry` 类是更高层的变体容器，将 `Shape`、`SkVertices`、`SubRunData`（文本子运行）、
`EdgeAAQuad`（逐边 AA 四边形）、`CoverageMaskShape`（覆盖遮罩）和 `AnalyticBlurMask`（解析模糊）
统一为单一类型。这使得 Graphite 的绘制记录和排序系统可以用统一的方式处理所有可能的几何输入。

空间管理方面，`BoundsManager` 提供了一套从暴力搜索到网格加速再到混合策略的边界查询层次结构，
用于高效判断绘制命令之间的重叠关系，从而优化画家排序和遮挡剔除。`IntersectionTree` 则维护了一组
非重叠矩形的集合，支持高效的插入与碰撞检测。

## 架构图

```
+================================================================+
|                     上层 Graphite 系统                           |
|  Device / DrawContext / DrawList / RenderStep                   |
+================================================================+
         |                    |                    |
         v                    v                    v
+------------------+  +------------------+  +------------------+
|    Geometry      |  |   Transform      |  |  BoundsManager   |
|  (变体容器)      |  |  (矩阵与逆矩阵)  |  |  (空间查询)      |
|                  |  |                  |  |                  |
| Shape            |  | SkM44 fM         |  | Naive            |
| SkVertices       |  | SkM44 fInvM      |  | BruteForce       |
| SubRunData       |  | Type 分类        |  | Grid             |
| EdgeAAQuad       |  | ScaleFactors     |  | Hybrid           |
| CoverageMask     |  |                  |  |                  |
| AnalyticBlur     |  +------------------+  +------------------+
+------------------+           |
         |                     |
         v                     v
+------------------+  +------------------+
|     Shape        |  |      Rect        |
|  (形状变体)      |  |  (SIMD 矩形)     |
|                  |  |                  |
| Empty            |  | [l, t, -r, -b]  |
| Line  -> Rect    |  | intersect()     |
| Rect  -> Rect    |  | makeJoin()      |
| RRect -> SkRRect |  | contains()      |
| Arc   -> SkArc   |  | makeInset()     |
| Path  -> SkPath  |  | makeOutset()    |
+------------------+  +------------------+
         |
         v
+------------------------------------------+
|           其他几何工具类                    |
|  EdgeAAQuad        - 逐边 AA 四边形       |
|  CoverageMaskShape - 覆盖遮罩形状         |
|  SubRunData        - 文本字形子运行        |
|  AnalyticBlurMask  - 解析式模糊遮罩       |
|  NonMSAAClip       - 非 MSAA 裁剪        |
|  IntersectionTree  - 非重叠矩形集合       |
+------------------------------------------+
```

## 目录结构

```
src/gpu/graphite/geom/
|-- BUILD.bazel                  # Bazel 构建规则
|
|-- Rect.h                       # SIMD 加速矩形类
|-- Shape.h / Shape.cpp          # 几何形状变体容器
|-- Transform.h / Transform.cpp  # 矩阵变换封装
|-- Geometry.h                   # 高层几何变体容器
|
|-- EdgeAAQuad.h                 # 逐边抗锯齿四边形
|-- CoverageMaskShape.h          # 覆盖遮罩形状
|-- SubRunData.h                 # 文本字形子运行数据
|-- AnalyticBlurMask.h/.cpp      # 解析式模糊遮罩
|-- NonMSAAClip.h                # 非 MSAA 裁剪结构
|
|-- BoundsManager.h              # 空间边界查询加速结构
|-- IntersectionTree.h/.cpp      # 非重叠矩形碰撞检测树
```

## 关键类与函数

### Rect

SIMD 加速的矩形类，内部存储格式为 `[left, top, -right, -bottom]`（取反右下角），使常见运算高效执行：

- 构造：`Rect(l, t, r, b)`、`Rect(topLeft, botRight)`、`Rect(SkRect)`、`LTRB()`、`XYWH()`、`WH()`、`Point()`
- 特殊值：`Infinite()`（用于累积交集）、`InfiniteInverted()`（用于累积并集）
- 访问器：`left()`、`top()`、`right()`、`bot()`、`topLeft()`、`botRight()`、`ltrb()`
- 几何运算：`makeIntersect()`（交集）、`makeJoin()`（并集）、`makeInset()`/`makeOutset()`（内缩/外扩）
- 空间查询：`intersects(ComplementRect)`、`contains(Rect)`
- 取整：`makeRoundIn()`（向内取整）、`makeRoundOut()`（向外取整）、`makeRound()`
- 属性：`size()`、`center()`、`area()`、`isEmptyNegativeOrNaN()`
- `ComplementRect` 内部类：存储 `[right, bottom, -left, -top]` 格式，用于加速多次相交测试

取反存储的关键优势：交集运算变为 `max(a, b)`，并集变为 `min(a, b)`，内缩变为加法，
外扩变为减法 -- 全部是单条 SIMD 指令。

### Shape

几何形状的变体容器（类似 `std::variant`），支持以下类型：

- `Type::kEmpty` -- 空形状
- `Type::kLine` -- 线段（使用 Rect 存储两端点）
- `Type::kRect` -- 矩形（使用 Rect 存储）
- `Type::kRRect` -- 圆角矩形（使用 SkRRect 存储）
- `Type::kArc` -- 弧线（使用 SkArc 存储）
- `Type::kPath` -- 任意路径（使用 SkPath 存储）

关键方法：
- `setLine()` / `setRect()` / `setRRect()` / `setArc()` / `setPath()` -- 设置形状数据
- `bounds()` -- 获取包围盒
- `convex(bool simpleFill)` -- 判断凸性
- `conservativeContains(Rect/point)` -- 保守包含测试
- `fillType()` -- 获取填充类型（winding/even-odd/inverse）
- `inverted()` / `setInverted()` -- 反转填充管理
- `asPath()` -- 转换为 SkPath
- `keySize()` / `writeKey()` -- 用于管线缓存的序列化键

内部使用匿名 union 存储不同类型的几何数据，手动管理 SkPath 的构造/析构。
`kDefaultPixelTolerance` (0.0039) 定义了设备空间中的模糊比较容差。

### Transform

矩阵变换封装，预计算并缓存逆矩阵和分类信息：

- 类型枚举 `Type`：`kIdentity`、`kSimpleRectStaysRect`、`kRectStaysRect`、
  `kAffine`、`kPerspective`、`kInvalid`
- 静态工厂：`Identity()`、`Invalid()`、`Translate(x, y)`、`Inverse(Transform)`
- 矩阵访问：`matrix()` -> `SkM44`、`inverse()` -> `SkM44`
- 类型查询：`type()`、`valid()`
- 缩放分析：`scaleFactors(SkV2)` -> `pair<min, max>`、`maxScaleFactor()`
- 抗锯齿：`localAARadius(Rect)` -- 计算本地空间中确保 1px 设备空间偏移的最小距离
- 矩形映射：`mapRect()`、`inverseMapRect()`
- 点映射：`mapPoints()` -- 支持 `SkV2 -> SkV4` 和 `SkV4 -> SkV4` 两种变体
- 组合：`concat()`、`concatInverse()`、`preTranslate()`、`postTranslate()`

缩放因子对于非透视变换是预缓存的常量，对于透视变换则忽略并按需计算。

### Geometry

最高层的变体容器，统一所有可绘制的几何类型：

- `Type::kEmpty` -- 空
- `Type::kShape` -- 任意形状（Shape）
- `Type::kVertices` -- 顶点网格（SkVertices）
- `Type::kSubRun` -- 文本子运行（SubRunData）
- `Type::kEdgeAAQuad` -- 逐边 AA 四边形（EdgeAAQuad）
- `Type::kCoverageMaskShape` -- 覆盖遮罩形状（CoverageMaskShape）
- `Type::kAnalyticBlur` -- 解析模糊（AnalyticBlurMask）

支持移动和拷贝语义，通过 placement new 和手动析构管理 union 成员。
提供统一的 `bounds()` 接口返回 `Rect` 类型的包围盒。

### EdgeAAQuad

存储四边形的四个顶点坐标和每条边的抗锯齿标记：

- 内部用 `skvx::float4 fXs` 和 `skvx::float4 fYs` 分别存储 X/Y 坐标
- `Flags` 枚举标记每条边是否需要 AA：`kLeft`、`kTop`、`kRight`、`kBottom`
- `isRect()` 标记是否为轴对齐矩形（可走快速路径）
- `bounds()` 计算包围盒

### CoverageMaskShape

表示从纹理获取逐像素覆盖数据的形状：

- `MaskInfo` 结构体：纹理原点（`fTextureOrigin`）和遮罩尺寸（`fMaskSize`）
- 持有 `TextureProxy` 引用保持纹理存活
- `deviceToLocal()` -- 从设备空间到遮罩本地空间的逆变换
- `inverted()` -- 是否使用反转填充

### SubRunData

文本字形图集的子运行数据：

- `subRun()` -- `AtlasSubRun` 指针
- `startGlyphIndex()` / `glyphCount()` -- 字形范围
- `deviceToLocal()` -- 逆变换矩阵
- `luminanceColor()` -- SDF 文本亮度色
- `pixelGeometry()` -- LCD 子像素几何
- `recorder()` -- 关联的 Recorder（图集归属）
- `rendererData()` -- 渲染器特定数据

### AnalyticBlurMask

解析式模糊遮罩的着色器输入数据：

- `ShapeType` 枚举：`kRect`、`kRRect`、`kCircle`
- `Make(Recorder*, Transform, sigma, SkRRect)` -- 静态工厂方法
- `drawBounds()` -- 本地空间绘制边界
- `deviceToScaledShape()` -- 设备到缩放形状空间的变换
- `shapeData()` -- 形状参数数据
- `blurData()` -- 模糊参数（含义因 ShapeType 而异）
- `refProxy()` -- 关联的纹理代理（模糊积分查找表）

### NonMSAAClip

非 MSAA 裁剪的组合结构：

- `AnalyticClip` -- 解析式裁剪（矩形/圆角矩形，统一圆角半径）
- `AtlasClip` -- 基于图集纹理的裁剪遮罩
- `NonMSAAClip` -- 两者的组合

### BoundsManager

空间边界查询加速结构的抽象基类和多种实现：

- **`NaiveBoundsManager`** -- 最简实现，假设所有绘制都重叠，返回全局最大序号
- **`BruteForceBoundsManager`** -- 暴力搜索实现，精确查询但 O(n) 复杂度
- **`GridBoundsManager`** -- 均匀网格实现，将设备空间划分为单元格，O(1) 查询
- **`HybridBoundsManager`** -- 混合策略，小 N 用暴力搜索，超过阈值自动切换到网格

核心接口：
- `getMostRecentDraw(Rect)` -> `CompressedPaintersOrder` -- 查询与给定矩形重叠的最近绘制
- `recordDraw(Rect, CompressedPaintersOrder)` -- 记录一次绘制的边界和排序值
- `reset()` -- 重置状态

### IntersectionTree

基于二叉空间分割的非重叠矩形集合：

- `add(Rect)` -> `bool` -- 尝试添加矩形，若与已有矩形相交则返回 false
- 内部使用 `SkArenaAlloc` 进行内存分配，`TreeNode` 和 `LeafNode` 构成树结构
- 按 X 或 Y 轴交替分割空间（`SplitType::kX` / `SplitType::kY`）

## 依赖关系

```
geom/ 依赖:
  +-- include/core/SkM44.h              (4x4 矩阵)
  +-- include/core/SkMatrix.h           (3x3 矩阵)
  +-- include/core/SkPath.h             (路径)
  +-- include/core/SkRRect.h            (圆角矩形)
  +-- include/core/SkArc.h              (弧线)
  +-- include/core/SkRect.h             (SkRect 互操作)
  +-- include/core/SkVertices.h         (顶点网格)
  +-- include/core/SkRefCnt.h           (引用计数)
  +-- src/base/SkVx.h                   (SIMD 向量操作)
  +-- src/base/SkArenaAlloc.h           (内存池分配)
  +-- src/base/SkTBlockList.h           (块链表)
  +-- src/gpu/graphite/DrawOrder.h      (CompressedPaintersOrder)
  +-- src/gpu/graphite/TextureProxy.h   (纹理代理)
  +-- src/text/gpu/SubRunContainer.h    (文本子运行)

被依赖:
  <-- src/gpu/graphite/render/          (所有 RenderStep 使用几何类型)
  <-- src/gpu/graphite/compute/         (VelloRenderer 使用 Transform)
  <-- src/gpu/graphite/Device.cpp       (设备层几何处理)
  <-- src/gpu/graphite/DrawList.h       (绘制列表存储 Geometry)
  <-- src/gpu/graphite/DrawPass.cpp     (绘制通道排序)
```

## 设计模式分析

### 变体容器模式 (Variant/Tagged Union)

`Shape` 和 `Geometry` 都采用了手动管理的 tagged union 模式（而非 `std::variant`），
通过 `Type` 枚举标记当前存储的类型，使用 placement new 和手动析构来管理非平凡类型
（如 `SkPath`、`sk_sp<SkVertices>`）的生命周期。这种设计避免了 `std::variant` 的
编译时开销和异常处理要求，同时保持了类型安全性。

### SIMD 优先设计

`Rect` 类是 SIMD 优先设计的典范。通过将右下角坐标取反存储（`[l, t, -r, -b]`），
常见的几何运算被转化为简单的 SIMD 操作：

- 交集 = `max(a, b)` （分量取最大值）
- 并集 = `min(a, b)` （分量取最小值）
- 内缩 = `vals + inset` （加法）
- 外扩 = `vals - outset` （减法）
- 包含测试 = `all(a <= b)` （分量比较）

`ComplementRect` 进一步优化了一对多的相交测试场景。

### 策略模式 (Strategy Pattern) -- BoundsManager

`BoundsManager` 抽象基类定义了空间查询接口，四个实现提供了不同的性能特征：
`NaiveBoundsManager`（O(1) 但保守）、`BruteForceBoundsManager`（O(n) 但精确）、
`GridBoundsManager`（O(k) 其中 k 为覆盖单元格数）、`HybridBoundsManager`（自适应切换）。
`HybridBoundsManager` 特别有趣 -- 它在小 N 时利用暴力搜索的精确性和低内存开销，
超过阈值后自动迁移到网格方案，并重放之前的绘制历史。

### 预计算缓存模式

`Transform` 类将矩阵的逆矩阵、类型分类和缩放因子在构造时一次性计算并缓存。
这避免了在渲染管线中频繁重复的矩阵求逆操作，尤其是 `localAARadius()` 和
`scaleFactors()` 这类在每个绘制命令中都可能调用的方法。

### 工厂方法模式

`AnalyticBlurMask::Make()` 是工厂方法模式的典型应用，根据输入的 `SkRRect` 形状自动
选择内部的 `MakeRect()`、`MakeCircle()` 或 `MakeRRect()` 路径，对调用者隐藏了
模糊参数计算的复杂性。返回 `std::optional` 处理不支持的情况。

## 数据流

```
应用层 (SkCanvas API)
        |
        | drawRect / drawRRect / drawPath / drawVertices / drawText ...
        v
+-------------------+
| Device::draw*()   | -- 将绘制参数转换为 Geometry 对象
+-------------------+
        |
        v
+-------------------+     +-------------------+
| Geometry 创建     | --> | Shape / Vertices  |
| (类型标记 union)   |     | SubRunData /      |
|                   |     | EdgeAAQuad / ...   |
+-------------------+     +-------------------+
        |
        v
+-------------------+
| Transform 变换    | -- 本地到设备空间变换，预计算逆矩阵
| localToDevice     |    类型分类 (Identity/Affine/Perspective)
+-------------------+
        |
        v
+-------------------+
| BoundsManager     | -- 设备空间边界查询
| recordDraw()      |    判断绘制重叠，优化画家排序
| getMostRecentDraw()|
+-------------------+
        |
        v
+-------------------+
| DrawList 记录     | -- 存储 (Geometry, Transform, DrawOrder, ...)
+-------------------+
        |
        v
+-------------------+
| RenderStep 消费   | -- 从 Geometry 提取具体类型
| writeVertices()   |    使用 Transform 计算设备坐标
|                   |    使用 Rect 进行边界计算
+-------------------+
        |
        v
    GPU 缓冲区
```

## 相关文档与参考

- **Renderer.h** (`src/gpu/graphite/Renderer.h`) -- RenderStep 基类，消费 Geometry/Transform
- **DrawList.h** (`src/gpu/graphite/DrawList.h`) -- 绘制列表，存储 Geometry 对象
- **DrawParams.h** (`src/gpu/graphite/DrawParams.h`) -- 绘制参数，封装 Geometry + Transform + Clip
- **DrawOrder.h** (`src/gpu/graphite/DrawOrder.h`) -- CompressedPaintersOrder 定义
- **render/ 目录** (`src/gpu/graphite/render/`) -- 所有 RenderStep 实现，是 geom/ 的主要消费者
- **compute/ 目录** (`src/gpu/graphite/compute/`) -- VelloRenderer 使用 Transform
- **SkVx.h** (`src/base/SkVx.h`) -- SIMD 向量库，Rect 的底层实现基础
- **SkPath.h** (`include/core/SkPath.h`) -- 路径数据结构
- **SkRRect.h** (`include/core/SkRRect.h`) -- 圆角矩形数据结构
- **SIMD 优化参考** -- Rect 的取反存储技巧源自 GPU 图形学中常见的 AABB 优化技术
