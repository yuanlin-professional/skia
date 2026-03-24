# render - Graphite 渲染步骤与渲染通道

## 概述

`src/gpu/graphite/render/` 目录是 Skia Graphite 渲染后端的核心渲染步骤（RenderStep）实现集合。每一个 RenderStep 子类
都代表了一种特定的几何图元绘制策略，负责将上层的绘图命令（如矩形、圆角矩形、路径、文本等）转换为 GPU 可执行的顶点数据、
着色器代码和深度/模板状态。所有 RenderStep 子类都继承自定义在 `src/gpu/graphite/Renderer.h` 中的 `RenderStep` 基类。

Graphite 采用了一种基于深度缓冲（Depth Buffer）和画家算法排序的渲染架构，与传统的即时模式 GPU 渲染不同。RenderStep 的
设计使得 Graphite 可以将不同类型的几何图元批量化（batching），通过实例化绘制（instanced drawing）实现高效的 GPU 提交。
每个 RenderStep 生成自己的 SkSL 顶点着色器和覆盖度（coverage）/颜色片段着色器代码，并通过 `DrawWriter` 将实例数据写入
GPU 缓冲区。

该目录中的 RenderStep 实现覆盖了 Graphite 所支持的全部图元类型，包括：解析式几何图元（矩形、圆角矩形、弧线）、
基于细分（tessellation）的路径绘制、文本渲染（位图和 SDF）、覆盖遮罩（coverage mask）、顶点网格、以及模糊效果。
这些实现充分利用了 Graphite 的 stencil-then-cover 多通道算法和单通道直接绘制两种模式，配合
`CommonDepthStencilSettings.h` 中预定义的深度/模板配置完成正确的像素覆盖和排序。

目录还包含辅助工具类 `DynamicInstancesPatchAllocator`，用于在细分通道中动态分配 patch 实例数据，
它是 `DrawWriter::DynamicInstances` 和 `skgpu::tess::PatchWriter` 之间的适配器。

## 架构图

```
                         +-----------------------+
                         |     Renderer 系统      |
                         |  (Renderer.h 定义)     |
                         +-----------+-----------+
                                     |
                                     | 包含多个
                                     v
                         +-----------------------+
                         |    RenderStep 基类     |
                         |  writeVertices()      |
                         |  vertexSkSL()         |
                         |  fragmentCoverageSkSL()|
                         +----------+------------+
                                    |
              +---------------------+---------------------+
              |                     |                     |
    +---------v--------+  +---------v--------+  +---------v--------+
    |  直接绘制步骤     |  | Stencil-Cover   |  |  文本/遮罩步骤    |
    | (单通道)         |  | (多通道)         |  | (纹理采样)       |
    +------------------+  +------------------+  +------------------+
    | AnalyticRRect    |  | MiddleOutFan     |  | BitmapText       |
    | PerEdgeAAQuad    |  | TessellateCurves |  | SDFText          |
    | CircularArc      |  | TessellateWedges |  | SDFTextLCD       |
    | AnalyticBlur     |  | TessellateStrokes|  | CoverageMask     |
    | Vertices         |  | CoverBounds      |  |                  |
    +------------------+  +------------------+  +------------------+
              |                     |                     |
              v                     v                     v
    +------------------------------------------------------------+
    |              DrawWriter (缓冲区写入)                        |
    |         DynamicInstancesPatchAllocator (Patch 分配)         |
    +------------------------------------------------------------+
              |
              v
    +------------------------------------------------------------+
    |          CommonDepthStencilSettings (深度/模板配置)          |
    |  kDirectDepthLessPass | kWindingStencilPass | kCoverPass   |
    +------------------------------------------------------------+
```

## 目录结构

```
src/gpu/graphite/render/
|-- BUILD.bazel                          # Bazel 构建规则
|
|-- CommonDepthStencilSettings.h         # 预定义的深度/模板状态常量
|-- DynamicInstancesPatchAllocator.h     # Tessellation patch 实例动态分配器
|
|-- AnalyticRRectRenderStep.h/.cpp       # 解析式圆角矩形/矩形/四边形渲染
|-- AnalyticBlurRenderStep.h/.cpp        # 解析式模糊效果渲染
|-- CircularArcRenderStep.h/.cpp         # 圆弧渲染
|-- PerEdgeAAQuadRenderStep.h/.cpp       # 逐边抗锯齿四边形渲染
|
|-- MiddleOutFanRenderStep.h/.cpp        # Middle-out 扇形三角剖分（模板通道）
|-- TessellateCurvesRenderStep.h/.cpp    # 曲线细分渲染（模板通道）
|-- TessellateWedgesRenderStep.h/.cpp    # 楔形细分渲染（模板/凸面通道）
|-- TessellateStrokesRenderStep.h/.cpp   # 描边细分渲染
|-- CoverBoundsRenderStep.h/.cpp         # 包围盒覆盖渲染（Cover 通道）
|
|-- BitmapTextRenderStep.h/.cpp          # 位图文本渲染（字形图集）
|-- SDFTextRenderStep.h/.cpp             # SDF 文本渲染（有符号距离场）
|-- SDFTextLCDRenderStep.h/.cpp          # SDF LCD 子像素文本渲染
|-- CoverageMaskRenderStep.h/.cpp        # 覆盖遮罩纹理渲染
|
|-- VerticesRenderStep.h/.cpp            # SkVertices 自定义顶点网格渲染
```

## 关键类与函数

### RenderStep 基类 (定义在 Renderer.h)

所有渲染步骤的抽象基类，定义了标准接口：

- `writeVertices(DrawWriter*, const DrawParams&, uint32_t ssboIndex)` -- 将几何实例数据写入 GPU 缓冲区
- `vertexSkSL()` -- 返回顶点着色器 SkSL 代码
- `fragmentCoverageSkSL()` -- 返回覆盖度片段着色器代码
- `fragmentColorSkSL()` -- 返回颜色片段着色器代码
- `texturesAndSamplersSkSL()` -- 返回纹理和采样器声明代码
- `writeUniformsAndTextures(const DrawParams&, PipelineDataGatherer*)` -- 写入 uniform 数据和纹理绑定

### AnalyticRRectRenderStep

最核心的渲染步骤之一，支持填充矩形、带逐边 AA 的四边形、任意圆角的圆角矩形（填充/描边/发丝线）、描边矩形、
描边线段等。使用实例化绘制，每个图元一个实例。通过 `float4 xRadiiOrFlags`、`float4 radiiOrQuadXs`、
`float4 ltrbOrQuadYs` 三个实例属性灵活编码所有图元类型。使用静态索引顶点缓冲区模板
（`fVertexBuffer` / `fIndexBuffer`）。

### TessellateCurvesRenderStep / TessellateWedgesRenderStep

基于 GPU 细分的路径渲染步骤，使用 `DynamicInstancesPatchAllocator` 分配 patch 实例。
支持 winding（非零）和 even-odd（奇偶）填充规则，作为 stencil-then-cover 算法的模板通道。
`TessellateCurvesRenderStep` 处理曲线段，`TessellateWedgesRenderStep` 处理楔形区域。
两者均依赖 `FixedCountCurves` / `FixedCountWedges` 计算顶点数量。

### TessellateStrokesRenderStep

描边路径的细分渲染步骤，将描边转换为填充几何体。支持无穷远点（infinity support）
以处理描边的端点和连接。

### BitmapTextRenderStep / SDFTextRenderStep / SDFTextLCDRenderStep

文本渲染步骤族。`BitmapTextRenderStep` 直接从字形图集纹理采样位图字形，支持
灰度、LCD 和彩色掩码格式。`SDFTextRenderStep` 使用有符号距离场实现可缩放的文本渲染。
`SDFTextLCDRenderStep` 在 SDF 基础上增加 LCD 子像素渲染支持。

### CommonDepthStencilSettings

预定义的 `DepthStencilSettings` 常量集合，包括：

- `kDirectDepthLessPass` / `kDirectDepthLEqualPass` -- 单通道直接绘制
- `kWindingStencilPass` / `kEvenOddStencilPass` -- Redbook 算法模板通道
- `kRegularCoverPass` / `kInverseCoverPass` -- Redbook 算法覆盖通道

模板面配置包括 `kIncrementCW`（顺时针递增）、`kDecrementCCW`（逆时针递减）、
`kToggle`（奇偶切换）、`kPassNonZero`（非零通过）、`kPassZero`（零值通过）。

### DynamicInstancesPatchAllocator<FixedCountVariant>

`DrawWriter::DynamicInstances` 的适配器模板，满足 `skgpu::tess::PatchWriter` 的
`PatchAllocator` 接口要求。模板参数 `FixedCountVariant` 可以是 `FixedCountCurves`、
`FixedCountWedges` 或 `FixedCountStrokes`，用于根据线性容差计算每个 patch 的顶点数。

## 依赖关系

```
render/ 依赖:
  +-- src/gpu/graphite/Renderer.h          (RenderStep 基类)
  +-- src/gpu/graphite/DrawWriter.h        (GPU 缓冲区写入)
  +-- src/gpu/graphite/DrawParams.h        (绘制参数封装)
  +-- src/gpu/graphite/DrawOrder.h         (绘制排序/深度值)
  +-- src/gpu/graphite/DrawTypes.h         (深度模板设置类型)
  +-- src/gpu/graphite/PipelineData.h      (Pipeline 数据收集)
  +-- src/gpu/graphite/Attribute.h         (顶点属性定义)
  +-- src/gpu/graphite/BufferManager.h     (缓冲区管理)
  +-- src/gpu/graphite/ResourceTypes.h     (资源绑定信息)
  +-- src/gpu/graphite/geom/              (几何工具: Shape, Transform, Rect 等)
  +-- src/gpu/tessellate/                 (细分工具: PatchWriter, LinearTolerances)
  +-- src/gpu/BufferWriter.h              (类型安全的缓冲区写入)
```

## 设计模式分析

### 策略模式 (Strategy Pattern)

`RenderStep` 基类定义了统一的渲染接口，每个子类实现特定的几何图元绘制策略。上层的
`Renderer` 通过组合一个或多个 `RenderStep` 来完成完整的绘制操作（例如 stencil-then-cover
需要两个步骤：一个模板步骤 + 一个覆盖步骤）。这种设计使得新的图元类型可以通过添加新的
`RenderStep` 子类来支持，无需修改渲染管线的其他部分。

### 模板方法模式 (Template Method Pattern)

`RenderStep` 基类的 `getScissor()` 提供默认实现，子类通过覆写 `writeVertices()`、
`vertexSkSL()`、`fragmentCoverageSkSL()` 等虚函数来定制行为。框架代码按固定顺序
调用这些方法来完成着色器编译和数据写入。

### 适配器模式 (Adapter Pattern)

`DynamicInstancesPatchAllocator` 将 `DrawWriter::DynamicInstances` 的 API 适配为
`PatchWriter::PatchAllocator` 所需的接口，使得细分系统可以无缝地将 patch 数据
写入 Graphite 的绘制缓冲区。内部通过 `LinearToleranceProxy` 代理类将线性容差
转换为固定顶点数计数。

### 实例化绘制模式

大多数 RenderStep（如 `AnalyticRRectRenderStep`、`PerEdgeAAQuadRenderStep`、
`CircularArcRenderStep`）使用固定的静态顶点/索引缓冲区模板配合实例数据进行绘制。
每个图元对应一个实例，通过 `StaticBufferManager` 管理共享的顶点模板缓冲区。
这极大地减少了 CPU 到 GPU 的数据传输量。

## 数据流

```
应用层绘制命令 (SkCanvas API)
        |
        v
+-------------------+
| Device::drawGeometry() -- 确定 Renderer 和 RenderStep
+-------------------+
        |
        v
+-------------------+
| DrawParams 封装   | -- 包含 Geometry, Transform, DrawOrder, Clip 等
+-------------------+
        |
        v
+-------------------+
| RenderStep::      |
| writeVertices()   | -- 将实例数据写入 DrawWriter
+-------------------+     |
        |                 v
        |           +-------------------+
        |           | DrawWriter 缓冲区  | -- 顶点/实例数据
        |           +-------------------+
        v
+-------------------+
| RenderStep::      |
| vertexSkSL()      | -- 生成顶点着色器代码
| fragmentCoverage  |
| SkSL()            | -- 生成片段着色器代码
+-------------------+
        |
        v
+-------------------+
| Pipeline 编译     | -- SkSL -> GPU 原生着色器
+-------------------+
        |
        v
+-------------------+
| GPU 执行          | -- 深度/模板测试 + 光栅化
| (使用 CommonDepth |
|  StencilSettings) |
+-------------------+
        |
        v
    最终像素输出
```

## 相关文档与参考

- **Renderer.h** (`src/gpu/graphite/Renderer.h`) -- `RenderStep` 基类定义和 `Renderer` 类
- **DrawWriter.h** (`src/gpu/graphite/DrawWriter.h`) -- GPU 绘制缓冲区写入工具
- **DrawParams.h** (`src/gpu/graphite/DrawParams.h`) -- 绘制参数封装
- **geom/ 目录** (`src/gpu/graphite/geom/`) -- 几何工具类（Shape, Transform, Rect 等）
- **tessellate/ 目录** (`src/gpu/tessellate/`) -- GPU 细分算法（PatchWriter, FixedCount 系列）
- **Redbook 算法** -- 经典的 stencil-then-cover 路径渲染技术，参见 OpenGL "红宝书"
- **SDF 文本渲染** -- 基于有符号距离场的可缩放文本技术（Valve 2007 SIGGRAPH）
- **Graphite 架构文档** -- Skia 官方文档中关于 Graphite 渲染后端的设计说明
