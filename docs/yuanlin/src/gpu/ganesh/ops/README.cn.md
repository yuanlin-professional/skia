# ops - Ganesh GPU 延迟绘制操作系统

## 概述

`src/gpu/ganesh/ops/` 目录是 Skia 图形库 Ganesh GPU 后端的核心绘制操作(Op)系统所在地,包含约 82 个源文件。该目录实现了 Ganesh 的**延迟绘制架构**——Ganesh 不会在 draw 调用时立即生成几何体,而是先捕获绘制参数,在刷新(flush)时才生成实际的几何数据并提交给 GPU。这种延迟执行模式允许 Op 子类在生成最终绘制命令之前,自由决定如何合并(merge)或链接(chain)多个操作,从而最大限度地减少绘制调用次数和 GPU 状态切换。

本目录的核心设计围绕 `GrOp` 基类展开,形成了一个层次化的类继承体系。`GrOp` 定义了所有 GPU 操作的公共接口——包括边界框管理、操作合并策略、以及 `prePrepare/prepare/execute` 三阶段执行模型。在此之上,`GrDrawOp` 添加了绘制操作特有的裁剪和处理器集(ProcessorSet)终结化逻辑;`GrMeshDrawOp` 进一步为基于网格的绘制提供了顶点缓冲区管理、模式化索引缓冲区以及四边形辅助器(QuadHelper)等基础设施。

除了核心基类,本目录还包含丰富的具体 Op 实现,覆盖了矩形填充(`FillRectOp`)、圆角矩形(`FillRRectOp`)、椭圆与弧形(`GrOvalOpFactory`)、纹理绘制(`TextureOp`)、文本渲染(`AtlasTextOp`)、路径曲面细分(`PathTessellateOp`、`StrokeTessellateOp`)等各种图元类型。此外还包含多种路径渲染器(PathRenderer),如 `DefaultPathRenderer`、`AAConvexPathRenderer`、`TessellationPathRenderer`、`AtlasPathRenderer` 和 `SoftwarePathRenderer`,它们为不同复杂度和特征的路径选择最优的渲染策略。

操作调度的核心枢纽是 `OpsTask` 类,它继承自 `GrRenderTask`,负责收集、排序和执行一个渲染目标上的所有 Op 链。OpsTask 支持 Op 的前向合并(forward combine)、操作链(OpChain)管理,以及加载操作(load op)优化等高级功能。

## 架构图

```
                        +-----------+
                        |   GrOp    |  (基类: 边界框, 合并策略, 执行生命周期)
                        +-----+-----+
                              |
                +-------------+-------------+
                |                           |
          +-----+------+            +-------+--------+
          |  GrDrawOp  |            |    ClearOp     |  (非绘制类 Op)
          +-----+------+            +-------+--------+
                |                           |
                |                    +------+-------+
                |                    |  DrawableOp  |
                |                    +--------------+
          +-----+---------+
          | GrMeshDrawOp  |  (网格绘制基类: 顶点/索引缓冲区管理)
          +-----+---------+
                |
    +-----------+-----------+-----------+-----------+
    |           |           |           |           |
+---+---+  +---+---+  +----+----+ +----+----+ +----+------+
|FillRect|  |Texture|  |AtlasText| |DrawMesh | |LatticeOp |
|  Op    |  |  Op   |  |  Op    | |   Op    | |           |
+--------+  +-------+  +--------+ +---------+ +-----------+

          +------------------+
          |  GrDrawOp 直接子类 |
          +--------+---------+
                   |
     +-------------+-------------+-------------+
     |             |             |             |
+----+-----+ +----+------+ +---+------+ +----+------+
|PathStencil| |PathTesse- | |StrokeTe-| |DrawAtlas- |
|CoverOp   | |llateOp    | |ssellate | |PathOp     |
+-----------+ +-----------+ |Op       | +-----------+
                            +---------+

  +-----------+          +-----------------+
  |  OpsTask  | -------> |  OpChain (链表) |
  +-----------+          +--------+--------+
       |                          |
       v                     +----+----+
  GrRenderTask               | GrOp 1  |
  (渲染任务DAG)               +----+----+
                                  |
                             +----+----+
                             | GrOp 2  | (链接/合并后的 Op)
                             +---------+

  路径渲染器选择策略:
  +---------------------+     +----------------------------+
  | PathRenderer (基类)  | <---| AAConvexPathRenderer       |
  +---------------------+     | AAHairLinePathRenderer     |
                              | AALinearizingConvexPath-   |
                              |   Renderer                 |
                              | AtlasPathRenderer          |
                              | DashLinePathRenderer       |
                              | DefaultPathRenderer        |
                              | SmallPathRenderer          |
                              | SoftwarePathRenderer       |
                              | TessellationPathRenderer   |
                              | TriangulatingPathRenderer  |
                              +----------------------------+
```

## 文件分类索引

### 1. Op 基础设施 — 基类与调度

| 文件 | 说明 |
|------|------|
| GrOp.h / GrOp.cpp | Op 基类，所有 GPU 操作的根（边界框、合并策略、执行生命周期） |
| GrDrawOp.h | 绘制 Op 基类，添加裁剪与 ProcessorSet 终结化 |
| GrMeshDrawOp.h / GrMeshDrawOp.cpp | 网格绘制 Op 基类，顶点/索引缓冲区管理 |
| OpsTask.h / OpsTask.cpp | Op 调度与执行任务，管理 OpChain 和加载操作优化 |
| FillPathFlags.h | 路径填充标志枚举 |
| GrPathStencilSettings.h | 路径模板缓冲区设置常量 |

### 2. 网格绘制辅助 — Helper 与四边形工具

| 文件 | 说明 |
|------|------|
| GrSimpleMeshDrawOpHelper.h / GrSimpleMeshDrawOpHelper.cpp | 简化网格绘制 Op 的辅助类（Pipeline/ProgramInfo 创建） |
| GrSimpleMeshDrawOpHelperWithStencil.h / GrSimpleMeshDrawOpHelperWithStencil.cpp | 带模板缓冲区支持的辅助类 |
| QuadPerEdgeAA.h / QuadPerEdgeAA.cpp | 逐边抗锯齿四边形工具 |

### 3. 矩形与圆角矩形 — Rect/RRect Op

| 文件 | 说明 |
|------|------|
| FillRectOp.h / FillRectOp.cpp | 矩形填充（最常用的 Op 之一） |
| FillRRectOp.h / FillRRectOp.cpp | 圆角矩形填充 |
| StrokeRectOp.h / StrokeRectOp.cpp | 矩形描边 |

### 4. 椭圆/圆形 — Oval Op

| 文件 | 说明 |
|------|------|
| GrOvalOpFactory.h / GrOvalOpFactory.cpp | 椭圆/圆形/弧形/RRect 绘制工厂 |

### 5. 虚线与笔画 — Dash Op

| 文件 | 说明 |
|------|------|
| DashOp.h / DashOp.cpp | 虚线绘制 Op |
| DashLinePathRenderer.h / DashLinePathRenderer.cpp | 虚线路径渲染器 |

### 6. 路径镶嵌 Op — Path Tessellation

| 文件 | 说明 |
|------|------|
| PathTessellateOp.h / PathTessellateOp.cpp | 路径直接曲面细分（凸路径） |
| StrokeTessellateOp.h / StrokeTessellateOp.cpp | 描边路径曲面细分 |
| PathInnerTriangulateOp.h / PathInnerTriangulateOp.cpp | 路径内部三角化 |
| PathStencilCoverOp.h / PathStencilCoverOp.cpp | 模板-覆盖路径（Red Book 方法） |
| TessellationPathRenderer.h / TessellationPathRenderer.cpp | GPU 曲面细分路径渲染器 |

### 7. AA 路径渲染器 — Anti-Aliased PathRenderer

| 文件 | 说明 |
|------|------|
| AAConvexPathRenderer.h / AAConvexPathRenderer.cpp | 抗锯齿凸路径渲染 |
| AAHairLinePathRenderer.h / AAHairLinePathRenderer.cpp | 抗锯齿细线路径渲染 |
| AALinearizingConvexPathRenderer.h / AALinearizingConvexPathRenderer.cpp | 线性化凸路径抗锯齿渲染 |

### 8. 小路径渲染 — SmallPath Atlas

| 文件 | 说明 |
|------|------|
| SmallPathRenderer.h / SmallPathRenderer.cpp | 小路径图集渲染器 |
| SmallPathAtlasMgr.h / SmallPathAtlasMgr.cpp | 小路径图集管理器 |
| SmallPathShapeData.h / SmallPathShapeData.cpp | 小路径形状数据 |

### 9. 软件路径 — Software PathRenderer

| 文件 | 说明 |
|------|------|
| SoftwarePathRenderer.h / SoftwarePathRenderer.cpp | 软件回退路径渲染器 |

### 10. 默认/通用路径 — Default/Triangulating PathRenderer

| 文件 | 说明 |
|------|------|
| DefaultPathRenderer.h / DefaultPathRenderer.cpp | 默认路径渲染器（模板缓冲区方式） |
| TriangulatingPathRenderer.h / TriangulatingPathRenderer.cpp | CPU 三角化路径渲染器 |

### 11. 文本渲染 — Atlas Text

| 文件 | 说明 |
|------|------|
| AtlasTextOp.h / AtlasTextOp.cpp | 文本图集渲染 Op（含 SDF 距离场文本） |
| AtlasInstancedHelper.h / AtlasInstancedHelper.cpp | 图集实例化渲染辅助 |

### 12. 图集路径渲染 — Atlas PathRenderer

| 文件 | 说明 |
|------|------|
| AtlasPathRenderer.h / AtlasPathRenderer.cpp | 图集路径渲染器 |
| AtlasRenderTask.h / AtlasRenderTask.cpp | 图集渲染任务 |
| DrawAtlasPathOp.h / DrawAtlasPathOp.cpp | 图集路径绘制 Op |

### 13. 纹理操作 — Texture/Atlas Op

| 文件 | 说明 |
|------|------|
| TextureOp.h / TextureOp.cpp | 纹理绘制（drawImage 核心） |
| DrawAtlasOp.h / DrawAtlasOp.cpp | 图集精灵绘制 |

### 14. 网格操作 — DrawMesh Op

| 文件 | 说明 |
|------|------|
| DrawMeshOp.h / DrawMeshOp.cpp | 自定义 SkMesh/Vertices 绘制 |

### 15. 区域操作 — Region Op

| 文件 | 说明 |
|------|------|
| RegionOp.h / RegionOp.cpp | 区域绘制 |

### 16. 阴影与特效 — Shadow Op

| 文件 | 说明 |
|------|------|
| ShadowRRectOp.h / ShadowRRectOp.cpp | 圆角矩形阴影绘制 |

### 17. 清除与 Drawable — Clear/Drawable Op

| 文件 | 说明 |
|------|------|
| ClearOp.h / ClearOp.cpp | 渲染目标清除操作 |
| DrawableOp.h / DrawableOp.cpp | 自定义 Drawable 绘制操作 |

### 18. 网格图操作 — Lattice Op

| 文件 | 说明 |
|------|------|
| LatticeOp.h / LatticeOp.cpp | 九宫格（Lattice）拉伸绘制 |

## 关键类与函数

### 1. GrOp (GrOp.h / GrOp.cpp) -- 所有 GPU 操作的基类

**职责**: 定义所有延迟 GPU 操作的公共接口和生命周期管理。

**关键成员与方法**:
- `Owner` -- `std::unique_ptr<GrOp>` 类型别名,用于 Op 的所有权管理
- `Make<Op>(GrRecordingContext*, Args...)` -- 模板工厂方法,创建 Op 实例
- `MakeWithProcessorSet<Op>(...)` -- 创建带处理器集的 Op,将 GrProcessorSet 与 Op 一起分配
- `combineIfPossible(GrOp*, SkArenaAlloc*, const GrCaps&)` -- 尝试合并两个 Op
- `CombineResult` -- 合并结果枚举: `kMerged`(合并)、`kMayChain`(可链接)、`kCannotCombine`(不可合并)
- `prePrepare(...)` -- 可选的预准备阶段,在排序后、prepare 前调用
- `prepare(GrOpFlushState*)` -- 准备阶段,创建资源和传输数据
- `execute(GrOpFlushState*, const SkRect&)` -- 执行阶段,向 GPU 发出命令
- `chainConcat(GrOp::Owner)` -- 将 Op 链接到当前链的末尾
- `ChainRange<T>` -- 用于遍历 Op 链的范围迭代器
- `bounds()` -- 返回 Op 在设备空间中的边界框
- `DEFINE_OP_CLASS_ID` -- 宏,为每个 Op 子类生成唯一的类标识符

### 2. GrDrawOp (GrDrawOp.h) -- 绘制操作基类

**职责**: 在 GrOp 基础上添加绘制操作专有的裁剪、MSAA 和处理器终结化逻辑。

**关键方法**:
- `usesMSAA()` -- 是否使用多重采样抗锯齿
- `usesStencil()` -- 是否使用模板缓冲区
- `clipToShape(SurfaceDrawContext*, SkClipOp, ...)` -- 尝试将裁剪直接应用到几何体上
- `ClipResult` -- 裁剪结果: `kFail`、`kClippedGeometrically`、`kClippedInShader`、`kClippedOut`
- `finalize(const GrCaps&, const GrAppliedClip*, GrClampType)` -- 终结处理器集,确定是否需要目标纹理

### 3. GrMeshDrawOp (GrMeshDrawOp.h / .cpp) -- 网格绘制操作基类

**职责**: 为基于网格的绘制提供顶点/索引缓冲区管理和公共辅助工具。

**关键内部类**:
- `PatternHelper` -- 使用模式化索引缓冲区渲染重复网格的辅助类
- `QuadHelper` -- PatternHelper 的特化,专用于四边形渲染

**关键方法**:
- `createProgramInfo(...)` -- 创建绘制所需的 GrProgramInfo
- `onPrepareDraws(GrMeshDrawTarget*)` -- 子类实现的纯虚方法,准备绘制数据
- `onCreateProgramInfo(...)` -- 子类实现的纯虚方法,创建着色器程序
- `CanUpgradeAAOnMerge(GrAAType, GrAAType)` -- 判断合并时能否升级抗锯齿

### 4. OpsTask (OpsTask.h / OpsTask.cpp) -- 操作调度与执行任务

**职责**: 管理一个渲染目标上所有 Op 的收集、排序、合并与执行。继承自 `GrRenderTask`,是渲染任务 DAG 的一部分。

**关键内部类**:
- `OpChain` -- 包含 Op 链表、处理器分析结果、裁剪信息和目标代理视图
- `OpChain::List` -- Op 链的双向链表实现

**关键方法**:
- `addOp(GrDrawingManager*, GrOp::Owner, ...)` -- 添加非绘制 Op
- `addDrawOp(GrDrawingManager*, GrOp::Owner, ...)` -- 添加绘制 Op
- `onPrePrepare(GrRecordingContext*)` -- 预准备所有 Op
- `onPrepare(GrOpFlushState*)` -- 准备所有 Op
- `onExecute(GrOpFlushState*)` -- 执行所有 Op 链
- `resetForFullscreenClear(CanDiscardPreviousOps)` -- 处理全屏清除优化
- `setColorLoadOp(GrLoadOp, ...)` -- 设置颜色加载操作 (清除/加载/不关心)
- `forwardCombine(const GrCaps&)` -- 前向合并相邻可合并的 Op 链
- `canMerge(const OpsTask*)` / `mergeFrom(...)` -- OpsTask 间的合并

### 5. FillRectOp (FillRectOp.h / FillRectOp.cpp) -- 矩形填充操作

**职责**: 绘制填充矩形,支持覆盖率抗锯齿(Coverage AA)和非抗锯齿模式。是 Ganesh 中最常用的 Op 之一。

**关键方法**:
- `Make(GrRecordingContext*, GrPaint&&, GrAAType, DrawQuad*, ...)` -- 创建单个矩形填充 Op
- `MakeNonAARect(...)` -- 创建非抗锯齿矩形的便捷方法
- `AddFillRectOps(SurfaceDrawContext*, ...)` -- 批量 API,一次性添加多个四边形

### 6. TextureOp (TextureOp.h / TextureOp.cpp) -- 纹理绘制操作

**职责**: 绘制纹理四边形,是 `drawImage`/`drawImageRect` 的核心实现。与 `FillRectOp` 类似但将 GrPaint 解构为纹理、过滤器、调制颜色和混合模式。

**关键方法**:
- `Make(GrRecordingContext*, GrSurfaceProxyView, ...)` -- 创建单个纹理绘制 Op
- `AddTextureSetOps(SurfaceDrawContext*, ...)` -- 批量绘制纹理集
- `FilterAndMipmapHaveNoEffect(...)` -- 判断过滤和 mipmap 是否对绘制有实际影响

### 7. AtlasTextOp (AtlasTextOp.h / AtlasTextOp.cpp) -- 文本图集渲染操作

**职责**: 使用字形图集渲染文本,支持灰度覆盖率、LCD 覆盖率、彩色位图和签名距离场(SDF)等多种遮罩类型。

**关键内部类型**:
- `Geometry` -- 包含子运行(SubRun)、绘制矩阵、原点、裁剪矩形和颜色
- `MaskType` -- 遮罩类型枚举: `kGrayscaleCoverage`、`kLCDCoverage`、`kColorBitmap`、`kAliasedDistanceField`、`kGrayscaleDistanceField`、`kLCDDistanceField`

### 8. QuadPerEdgeAA (QuadPerEdgeAA.h / QuadPerEdgeAA.cpp) -- 逐边抗锯齿四边形工具

**职责**: 提供逐边(per-edge)抗锯齿四边形的顶点规格定义、曲面细分(Tessellation)和几何处理器创建。被 `FillRectOp` 和 `TextureOp` 广泛使用。

**关键类型**:
- `VertexSpec` -- 顶点配置描述,包含设备四边形类型、颜色类型、本地坐标、子集信息等
- `Tessellator` -- 负责将设备/本地 GrQuad 转换为 VBO 数据
- `IndexBufferOption` -- 索引缓冲区策略: `kPictureFramed`(8 顶点 AA)、`kIndexedRects`(4 顶点索引)、`kTriStrips`(4 顶点条带)

**关键方法**:
- `MakeProcessor(SkArenaAlloc*, const VertexSpec&)` -- 创建非纹理几何处理器
- `MakeTexturedProcessor(...)` -- 创建带纹理的几何处理器
- `GetIndexBuffer(...)` -- 获取对应索引缓冲区
- `IssueDraw(...)` -- 发出绘制命令

### 9. GrSimpleMeshDrawOpHelper (GrSimpleMeshDrawOpHelper.h / .cpp) -- 网格绘制辅助类

**职责**: 减少简单网格绘制 Op 的样板代码,管理 GrProcessorSet 的分配和 GrPipeline 的创建。

**关键方法**:
- `FactoryHelper<Op>(GrRecordingContext*, GrPaint&&, ...)` -- 模板工厂,自动处理 ProcessorSet 分配
- `isCompatible(...)` -- 判断两个 Helper 是否兼容(可合并)
- `finalizeProcessors(...)` -- 终结处理器,确定是否需要目标纹理
- `createPipeline(GrOpFlushState*)` -- 创建渲染管线
- `CreateProgramInfo(...)` -- 静态方法,创建 GrProgramInfo

### 10. PathStencilCoverOp (PathStencilCoverOp.h / .cpp) -- 模板-覆盖路径操作

**职责**: 使用标准的 Red Book "先模板后覆盖"方法渲染路径。曲线通过 GPU 曲面细分着色器或间接绘制进行线性化。需要 MSAA 实现抗锯齿。

**关键特性**:
- 三个阶段的程序: `fStencilFanProgram`(扇形模板)、`fStencilPathProgram`(路径模板)、`fCoverBBoxProgram`(覆盖边界框)
- 使用 `PathTessellator` 进行路径曲面细分

## 依赖关系

### 上游依赖 (本目录依赖的模块)

| 模块 | 路径 | 用途 |
|------|------|------|
| GrCaps | `src/gpu/ganesh/GrCaps.h` | GPU 能力查询,决定渲染策略 |
| GrPaint | `src/gpu/ganesh/GrPaint.h` | 绘制参数封装 (颜色、混合、处理器) |
| GrProcessorSet | `src/gpu/ganesh/GrProcessorSet.h` | 片段处理器集合管理 |
| GrPipeline | `src/gpu/ganesh/GrPipeline.h` | 完整渲染管线描述 |
| GrGeometryProcessor | `src/gpu/ganesh/GrGeometryProcessor.h` | 顶点处理着色器 |
| GrOpFlushState | `src/gpu/ganesh/GrOpFlushState.h` | Op 执行时的 GPU 状态 |
| GrMeshDrawTarget | `src/gpu/ganesh/GrMeshDrawTarget.h` | 网格绘制目标接口 |
| GrRecordingContext | `include/gpu/ganesh/GrRecordingContext.h` | 录制上下文 |
| GrDrawingManager | `src/gpu/ganesh/GrDrawingManager.h` | 绘制管理器 (DAG 调度) |
| GrSurfaceProxy | `src/gpu/ganesh/GrSurfaceProxy.h` | GPU 表面代理 |
| GrQuad / GrQuadBuffer | `src/gpu/ganesh/geometry/` | 四边形几何工具 |
| PathTessellator | `src/gpu/ganesh/tessellate/` | 路径曲面细分器 |
| StrokeTessellator | `src/gpu/ganesh/tessellate/` | 描边曲面细分器 |
| GrTessellationShader | `src/gpu/ganesh/tessellate/` | 曲面细分着色器 |
| SurfaceDrawContext | `src/gpu/ganesh/SurfaceDrawContext.h` | 表面绘制上下文 |
| PathRenderer | `src/gpu/ganesh/PathRenderer.h` | 路径渲染器基类 |
| GrDynamicAtlas | `src/gpu/ganesh/GrDynamicAtlas.h` | 动态图集管理 |
| SkPath / SkRRect / SkMatrix | `include/core/` | 核心几何类型 |

### 下游使用者 (依赖本目录的模块)

| 模块 | 用途 |
|------|------|
| `SurfaceDrawContext` | 调用各种 Op 工厂方法创建绘制操作 |
| `GrDrawingManager` | 管理 OpsTask 的生命周期和 DAG 调度 |
| `GrOpFlushState` | 驱动 Op 的 prepare 和 execute 阶段 |
| `GrPathRendererChain` | 选择和调用适当的路径渲染器 |

### 外部依赖

- C++ 标准库: `<atomic>`、`<memory>`、`<cstdint>`
- Skia 核心: `SkRect`、`SkMatrix`、`SkPath`、`SkStrokeRec`、`SkArenaAlloc`

## 设计模式分析

### 1. 工厂方法模式 (Factory Method)

几乎所有具体 Op 都通过静态 `Make(...)` 工厂方法创建,而非直接暴露构造函数。这允许工厂在参数无效时返回 `nullptr`,同时保持构造函数为 `private`。

```cpp
// FillRectOp::Make -- 典型的工厂方法
static GrOp::Owner Make(GrRecordingContext*,
                        GrPaint&&,
                        GrAAType,
                        DrawQuad*,
                        const GrUserStencilSettings* = nullptr,
                        InputFlags = InputFlags::kNone);
```

`GrSimpleMeshDrawOpHelper::FactoryHelper<Op>()` 进一步泛化了工厂模式,自动处理 `GrProcessorSet` 的内存分配策略——当 paint 是"trivial"时不分配处理器集,否则通过 `MakeWithProcessorSet` 将处理器集与 Op 在同一块内存中分配。

### 2. 模板方法模式 (Template Method)

`GrOp` 定义了 `prePrepare -> prepare -> execute` 的三阶段执行生命周期,具体行为由子类通过重写 `onPrePrepare()`、`onPrepare()`、`onExecute()` 来实现。

```
GrOp::prePrepare()  -->  onPrePrepare()   [可选, 排序后调用]
GrOp::prepare()     -->  onPrepare()      [资源创建和数据传输]
GrOp::execute()     -->  onExecute()      [向 GPU 发出命令]
```

`GrMeshDrawOp` 进一步细化了模板方法,将 `onPrepare` 固定,内部调用 `onPrepareDraws(GrMeshDrawTarget*)`,将 `onPrePrepare` 固定,内部调用 `onPrePrepareDraws(...)`。

### 3. 策略模式 (Strategy Pattern)

路径渲染器体系是策略模式的典型应用。`PathRenderer` 基类定义了 `onCanDrawPath()` 和 `onDrawPath()` 接口,各种具体渲染器实现不同的渲染策略:

| 渲染器 | 策略 |
|--------|------|
| `AAConvexPathRenderer` | 解析式抗锯齿,仅凸路径 |
| `AAHairLinePathRenderer` | 细线(1px)抗锯齿路径 |
| `AALinearizingConvexPathRenderer` | 将凸路径曲线线性化后进行抗锯齿 |
| `TessellationPathRenderer` | GPU 硬件曲面细分 + Red Book 模板/覆盖 |
| `AtlasPathRenderer` | 先渲染到离屏图集,再采样覆盖率 |
| `SmallPathRenderer` | 小路径渲染到图集缓存 |
| `DefaultPathRenderer` | 基于模板缓冲区的通用路径渲染 |
| `SoftwarePathRenderer` | CPU 软件渲染后上传到 GPU |
| `TriangulatingPathRenderer` | CPU 三角化后 GPU 绘制 |

`GrPathRendererChain` 按优先级依次查询各渲染器的 `onCanDrawPath()`,选择第一个支持当前路径的渲染器。

### 4. 组合模式 / 链式模式 (Chain Pattern)

`GrOp` 支持将同类型的 Op 组成链(chain)。链中的头 Op 负责执行整个链的工作:

```cpp
// ChainRange 用于遍历链
for (const MyOp& op : ChainRange<MyOp>(headOp)) {
    // 访问链中每个 op 的数据
}
```

`OpsTask::OpChain` 进一步封装了 Op 链的管理,包括尝试合并(`tryConcat`)、追加(`appendOp`)和前置(`prependChain`)操作。

### 5. 享元模式 (Flyweight) -- 索引缓冲区共享

`QuadPerEdgeAA::GetIndexBuffer()` 方法返回可被多个 Op 共享的索引缓冲区,避免了重复创建。`QuadLimit()` 则返回特定索引缓冲区选项的最大四边形数量,确保不会溢出。

## 数据流

### Op 生命周期数据流

```
                      录制阶段                         刷新阶段
                      --------                         --------

  SkCanvas::drawRect()
        |
        v
  SurfaceDrawContext::drawFilledRect()
        |
        v
  FillRectOp::Make(context, paint, aaType, quad)  ----> 创建 Op 实例
        |                                                (捕获绘制参数)
        v
  OpsTask::addDrawOp(op)
        |
        |---> finalize(caps, clip, clampType)      ----> 终结处理器集
        |---> OpChain::appendOp() / tryConcat()    ----> 尝试与已有 Op 合并
        |
        v
  [Op 存储在 OpsTask::fOpChains 中]
        |
        |================== flush 边界 ==================
        |
        v
  OpsTask::onPrePrepare(context)
        |
        v
  每个 Op: prePrepare(context, dstView, clip, ...)  ----> 可选: 预创建程序信息
        |
        v
  OpsTask::onPrepare(flushState)
        |
        v
  每个 Op: prepare(flushState)
        |---> GrMeshDrawOp::onPrepareDraws(target)
        |     |---> 分配顶点/索引缓冲区
        |     |---> 写入顶点数据
        |     |---> recordDraw(target, gp)
        |
        v
  OpsTask::onExecute(flushState)
        |
        v
  每个 OpChain: 遍历 Op 链
        |---> head->execute(flushState, chainBounds)
              |---> onExecute(flushState, chainBounds)
                    |---> 绑定管线/着色器
                    |---> 发出绘制命令 (draw/drawIndexed)
```

### Op 合并数据流

```
  新 Op 进入 OpsTask
       |
       v
  遍历现有 OpChain, 比较 classID
       |
       |--- classID 不同 --> 跳过, 创建新 OpChain
       |
       |--- classID 相同
            |
            v
       比较 GrAppliedClip, GrDstProxyView 是否兼容
            |
            |--- 不兼容 --> 跳过
            |
            |--- 兼容
                 |
                 v
            调用 combineIfPossible(existingOp, arena, caps)
                 |
                 |--- kMerged --------> 合并数据到现有 Op, 销毁新 Op
                 |
                 |--- kMayChain ------> 链接新 Op 到现有 Op 链尾
                 |
                 |--- kCannotCombine -> 继续尝试下一个 OpChain
```

### 路径渲染选择数据流

```
  SurfaceDrawContext::drawPath(path, paint, style)
       |
       v
  GrPathRendererChain::getPathRenderer(canDrawArgs)
       |
       |--- 依次查询每个注册的 PathRenderer:
       |
       |    1. TessellationPathRenderer::onCanDrawPath()
       |       |--- 支持 --> 使用 PathStencilCoverOp 或 PathTessellateOp
       |
       |    2. AAConvexPathRenderer::onCanDrawPath()
       |       |--- 凸路径且需要 AA --> 使用解析式抗锯齿
       |
       |    3. AAHairLinePathRenderer::onCanDrawPath()
       |       |--- 细线路径 --> 使用细线渲染
       |
       |    4. AtlasPathRenderer::onCanDrawPath()
       |       |--- 小且简单路径 --> 渲染到图集
       |
       |    5. SmallPathRenderer::onCanDrawPath()
       |       |--- 小路径 --> 渲染到小路径图集
       |
       |    6. DefaultPathRenderer::onCanDrawPath()
       |       |--- 通用路径 --> 使用模板缓冲区
       |
       |    7. SoftwarePathRenderer::onCanDrawPath()
       |       |--- 最终回退 --> CPU 渲染后上传
       |
       v
  选中的 PathRenderer::onDrawPath() --> 创建相应的 Op
```

## 平台特定说明

### GPU 曲面细分着色器 (Tessellation Shaders)

`TessellationPathRenderer` 和相关的 `PathTessellateOp`、`PathStencilCoverOp`、`StrokeTessellateOp` 依赖于 GPU 硬件曲面细分着色器支持。不是所有 GPU 都支持此功能:

- `TessellationPathRenderer::IsSupported(const GrCaps&)` 检查 GPU 是否具备所需能力
- 不支持时将回退到其他路径渲染策略(如 `DefaultPathRenderer` 或 `TriangulatingPathRenderer`)
- OpenGL ES 和部分移动端 GPU 可能不支持硬件曲面细分

### MSAA 与 DMSAA

- `OpsTask` 跟踪 `fUsesMSAASurface` 来管理多重采样状态
- `setCannotMergeBackward()` 用于 DMSAA(延迟多重采样抗锯齿)场景,当非多重采样的 OpsTask 无法提升为 MSAA 时阻止向后合并
- 部分 Op(如 `PathStencilCoverOp`、`StrokeTessellateOp`)要求 MSAA 才能实现抗锯齿,因为它们不使用解析式 AA

### 模板缓冲区 (Stencil Buffer)

- `GrPathStencilSettings.h` 定义了 Even/Odd 和 Winding 两种填充规则的模板设置
- `OpsTask::StencilContent` 枚举控制渲染通道开始时模板缓冲区的内容: `kDontCare`、`kUserBitsCleared`、`kPreserved`
- `caps.performStencilClearsAsDraws()` 为 `true` 时不能使用加载操作清除模板,需要通过绘制命令清除

### AtlasPathRenderer 限制

- 仅在 `GrDirectContext` 上可用,不兼容 DDL(显示列表延迟)
- 路径尺寸限制: 每个维度不超过 `fAtlasMaxSize`,总像素不超过 256x256(MSAA/DMSAA 情况下为 128x128)
- 不支持透视变换的路径

### 条件编译

- `SK_ENABLE_OPTIMIZE_SIZE` -- 启用时会排除 `GrOvalOpFactory` 和 `SmallPathRenderer` 等大型模块以减小二进制体积
- `SK_DISABLE_SDF_TEXT` -- 禁用签名距离场文本渲染,影响 `AtlasTextOp` 的 MaskType
- `GPU_TEST_UTILS` -- 启用测试工具方法如 `dumpInfo()`、`numQuads()` 等
- `GR_OP_SPEW` / `GR_FLUSH_TIME_OP_SPEW` -- 调试宏,控制 Op 信息的输出

## 相关文档与参考

### 相关源码目录

| 目录 | 说明 |
|------|------|
| `src/gpu/ganesh/` | Ganesh GPU 后端根目录 |
| `src/gpu/ganesh/tessellate/` | 路径/描边曲面细分器实现 |
| `src/gpu/ganesh/geometry/` | GrQuad、GrQuadBuffer 等几何工具 |
| `src/gpu/ganesh/effects/` | 片段处理器效果 |
| `src/gpu/ganesh/glsl/` | GLSL 着色器代码生成 |
| `src/gpu/` | 跨后端共享的 GPU 工具 (BufferWriter, Tessellation 等) |
| `include/gpu/ganesh/` | Ganesh 公共 API 头文件 |

### 核心设计文档

- **Red Book 算法**: `PathStencilCoverOp` 实现了 OpenGL 编程指南(Red Book)中经典的"模板后覆盖"路径渲染方法。该方法先在模板缓冲区中标记路径内部区域,然后用覆盖通道填充颜色。
- **Per-Edge AA**: `QuadPerEdgeAA` 实现了 Skia 独特的逐边覆盖率抗锯齿方案,每条四边形边可以独立控制是否启用 AA,这对于相邻共享边的矩形避免双重 AA 至关重要。
- **SDF 文本渲染**: `AtlasTextOp` 支持的签名距离场(Signed Distance Field)文本渲染技术允许在不同缩放级别下保持文本边缘清晰,避免了传统位图文本在缩放时的模糊问题。

### 命名空间

本目录中的大部分现代代码都位于 `skgpu::ganesh` 命名空间下(如 `skgpu::ganesh::FillRectOp`、`skgpu::ganesh::OpsTask`),而较早的核心基类(如 `GrOp`、`GrDrawOp`、`GrMeshDrawOp`)仍使用全局 `Gr` 前缀的命名约定。部分工厂函数(如 `skgpu::ganesh::DashOp::MakeDashLineOp`)使用命名空间嵌套的函数式 API。
