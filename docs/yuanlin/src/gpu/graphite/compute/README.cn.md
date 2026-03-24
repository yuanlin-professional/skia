# compute - Graphite 计算管线

## 概述

`src/gpu/graphite/compute/` 目录实现了 Skia Graphite 的 GPU 计算管线（Compute Pipeline）框架。该模块
提供了一套通用的计算步骤（ComputeStep）抽象和调度分组（DispatchGroup）机制，使得 Graphite 能够在 GPU
上执行通用计算任务，包括路径光栅化、几何处理和图像处理等。

该模块的核心设计围绕三个层次展开：`ComputeStep` 定义单个计算内核的资源绑定和着色器逻辑；`DispatchGroup`
将多个顺序执行的 ComputeStep 组装为一组带有屏障（barrier）的调度序列，并管理步骤间的数据流动；而 `VelloRenderer`
则是基于上述框架构建的一个完整的 GPU 路径光栅化实现，集成了 Google 的 Vello 项目的计算着色器。

Vello 是一个完全基于 GPU 计算的 2D 矢量图形渲染器，其核心算法大量使用并行前缀和（Parallel Prefix Sum）
和幺半群（Monoid）技术来处理可变长度的路径编码流。Skia 通过 `VelloComputeSteps.h` 中定义的 20 多个
计算步骤将 Vello 的渲染管线完整集成到 Graphite 中，支持从路径编码到最终像素光栅化的全 GPU 执行流程。

整个计算管线的设计兼顾了跨平台兼容性，支持 SkSL 和原生着色器（WGSL、MSL）两种模式。资源管理采用槽位
（Slot）机制实现 ComputeStep 之间的数据共享，同时支持私有资源（Private）和共享资源（Shared）两种
数据流模式。`DispatchGroup::Builder` 提供了类型安全的构建器模式来验证资源兼容性并自动分配底层 GPU 资源。

## 架构图

```
+================================================================+
|                    VelloRenderer (高层渲染器)                     |
|                                                                  |
|  VelloScene (场景编码)                                            |
|    |                                                             |
|    v                                                             |
|  renderScene() --> DispatchGroup::Builder                        |
|    |                                                             |
|    +-- 阶段 I:   路径标签处理 (PathTag Monoid)                    |
|    |     pathtag_reduce -> pathtag_scan_small/large              |
|    +-- 阶段 II:  路径展平与边界框 (Flatten + BBox)                 |
|    |     bbox_clear -> flatten                                   |
|    +-- 阶段 III: 绘制对象流 (Draw Monoid)                         |
|    |     draw_reduce -> draw_leaf                                |
|    +-- 阶段 IV:  裁剪处理 (Clip Stack)                            |
|    |     clip_reduce -> clip_leaf                                |
|    +-- 阶段 V:   分箱与瓦片分配 (Binning + Tile Alloc)            |
|    |     binning -> tile_alloc -> path_count -> path_tiling      |
|    +-- 阶段 VI:  粗光栅化 (Coarse Rasterization)                  |
|    |     backdrop_dyn -> coarse                                  |
|    +-- 阶段 VII: 精细光栅化 (Fine Rasterization)                  |
|          fine_area / fine_msaa16 / fine_msaa8                    |
|                                                                  |
+================================================================+
         |                          |
         v                          v
+------------------+    +-------------------------+
| DispatchGroup    |    | ComputeStep (抽象基类)   |
| (调度序列容器)    |    |                         |
|                  |    | + computeSkSL()         |
| Dispatch[]       |    | + nativeShaderSource()  |
| Pipeline[]       |    | + calculateBufferSize() |
| Texture[]        |    | + prepareStorageBuffer()|
| Sampler[]        |    | + resources()           |
+------------------+    +-------------------------+
         |                          |
         v                          v
+------------------+    +-------------------------+
| CommandBuffer    |    |  ResourceDesc           |
| (GPU 命令编码)    |    |  - ResourceType         |
+------------------+    |  - DataFlow (Private/   |
                        |    Shared + Slot)       |
                        |  - ResourcePolicy       |
                        +-------------------------+
```

## 目录结构

```
src/gpu/graphite/compute/
|-- BUILD.bazel                  # Bazel 构建规则
|
|-- ComputeStep.h                # 计算步骤抽象基类
|-- ComputeStep.cpp              # ComputeStep 基础实现
|
|-- DispatchGroup.h              # 调度分组容器与构建器
|-- DispatchGroup.cpp            # DispatchGroup 资源管理与命令编码
|
|-- VelloComputeSteps.h          # Vello 全部计算步骤声明与资源槽位定义
|-- VelloComputeSteps.cpp        # Vello 计算步骤的资源绑定实现
|
|-- VelloRenderer.h              # Vello 高层渲染器（场景编码与管线调度）
|-- VelloRenderer.cpp            # VelloRenderer 完整管线组装实现
```

## 关键类与函数

### ComputeStep

计算管线的核心抽象基类，代表一个 GPU 计算内核调度。关键接口：

- `computeSkSL()` -- 返回完整的 SkSL 计算着色器代码
- `nativeShaderSource(NativeShaderFormat)` -- 返回原生着色器源码（WGSL/MSL）
- `calculateBufferSize(int resourceIndex, const ResourceDesc&)` -- 计算缓冲区大小
- `calculateTextureParameters(int resourceIndex, const ResourceDesc&)` -- 计算纹理参数
- `calculateGlobalDispatchSize()` -- 计算全局调度大小（工作组数量）
- `prepareStorageBuffer(int, const ResourceDesc&, BufferWriter&&)` -- CPU 端填充存储缓冲区
- `prepareUniformBuffer(int, const ResourceDesc&, UniformManager*)` -- CPU 端填充 Uniform 缓冲区
- `resources()` -- 返回资源描述列表
- `localDispatchSize()` -- 本地工作组大小

关键内部类型：

- `DataFlow` 枚举：`kPrivate`（私有资源）和 `kShared`（共享资源，带槽位号）
- `ResourceType` 枚举：`kUniformBuffer`、`kStorageBuffer`、`kReadOnlyStorageBuffer`、
  `kIndirectBuffer`、`kWriteOnlyStorageTexture`、`kReadOnlyTexture`、`kSampledTexture`
- `ResourcePolicy` 枚举：`kNone`、`kClear`（零初始化）、`kMapped`（CPU 预填充）
- `ResourceDesc` 结构体：完整描述一个资源的类型、数据流、策略和 SkSL 声明
- `WorkgroupBufferDesc` 结构体：工作组共享内存描述（用于 Metal 的后期绑定）

### DispatchGroup

调度分组容器，将一系列需要顺序执行（带屏障）的计算调度组织在一起：

- `Dispatch` 结构体 -- 单次调度的完整信息：本地/全局工作组大小、资源绑定列表、管线索引
- `prepareResources(ResourceProvider*)` -- 实例化计算管线和纹理资源
- `addResourceRefs(CommandBuffer*)` -- 向命令缓冲区注册资源引用
- `snapChildTask()` -- 获取前置依赖任务（如缓冲区清零）

### DispatchGroup::Builder

类型安全的调度分组构建器：

- `appendStep(const ComputeStep*, optional<WorkgroupSize>)` -- 添加计算步骤
- `appendStepIndirect(const ComputeStep*, BindBufferInfo)` -- 添加间接调度步骤
- `assignSharedBuffer(BindBufferInfo, slot, cleared)` -- 手动绑定共享缓冲区
- `assignSharedTexture(sk_sp<TextureProxy>, slot)` -- 手动绑定共享纹理
- `finalize()` -- 完成构建并返回不可变的 DispatchGroup
- `OutputTable` -- 跟踪最近一次 ComputeStep 的输出资源句柄

### VelloScene

Vello 场景编码器，将高层绘制命令编码为 Vello 内部的编码流：

- `solidFill(SkPath, SkColor4f, SkPathFillType, Transform)` -- 纯色填充路径
- `solidStroke(SkPath, SkColor4f, SkStrokeRec, Transform)` -- 纯色描边路径
- `pushClipLayer(SkPath, Transform)` / `popClipLayer()` -- 裁剪层管理
- `append(const VelloScene&)` -- 合并另一个场景
- `reset()` -- 重置编码状态

### VelloRenderer

Vello 完整渲染管线的编排器，专用于生成覆盖遮罩（coverage mask）：

- `renderScene(RenderParams, VelloScene, TextureProxy, Recorder*)` -- 执行完整管线
- `RenderParams` 结构体：目标宽高、背景色、AA 配置（AnalyticArea/MSAA16/MSAA8）
- 内部持有全部 20+ 个 Vello 计算步骤实例和 3 种精细光栅化变体

### VelloStep<S> 模板类与 VelloComputeSteps

`VelloStep<S>` 是所有 Vello 计算步骤的基类模板，模板参数 `S` 是 `vello_cpp::ShaderStage` 枚举值。
通过 `VELLO_COMPUTE_STEP` 宏批量生成 20 个具体步骤类：

- 路径标签处理：`VelloPathtagReduceStep`、`VelloPathtagReduce2Step`、`VelloPathtagScan1Step`、
  `VelloPathtagScanLargeStep`、`VelloPathtagScanSmallStep`
- 路径展平：`VelloBboxClearStep`、`VelloFlattenStep`
- 绘制流处理：`VelloDrawReduceStep`、`VelloDrawLeafStep`
- 裁剪处理：`VelloClipReduceStep`、`VelloClipLeafStep`
- 分箱与瓦片：`VelloBinningStep`、`VelloTileAllocStep`、`VelloPathCountStep`、
  `VelloPathCountSetupStep`、`VelloPathTilingStep`、`VelloPathTilingSetupStep`
- 粗光栅化：`VelloBackdropDynStep`、`VelloCoarseStep`
- 精细光栅化：`VelloFineAreaStep`、`VelloFineAreaAlpha8Step`、`VelloFineMsaa16Step`、
  `VelloFineMsaa16Alpha8Step`、`VelloFineMsaa8Step`、`VelloFineMsaa8Alpha8Step`

### 资源槽位常量 (kVelloSlot_*)

28 个共享资源槽位定义了 Vello 管线中所有步骤间的数据流：

| 槽位范围 | 用途 |
|----------|------|
| 0-1 | 配置 Uniform 和场景编码 |
| 2-5 | 路径标签幺半群流（PathTag Monoid） |
| 6-7 | 路径边界框和线段汤（Line Soup） |
| 8-11 | 绘制幺半群和分箱信息 |
| 12-14 | 裁剪双循环半群和边界框 |
| 15-22 | 分箱、瓦片、段计数、PTCL |
| 23-25 | 输出图像、渐变图像、图像图集 |
| 26-27 | 间接计数和 MSAA 掩码 LUT |

## 依赖关系

```
compute/ 依赖:
  +-- src/gpu/graphite/ComputeTypes.h        (WorkgroupSize, IndirectDispatchArgs)
  +-- src/gpu/graphite/ComputePipelineDesc.h (计算管线描述)
  +-- src/gpu/graphite/ComputePipeline.h     (计算管线对象)
  +-- src/gpu/graphite/ResourceTypes.h       (BindBufferInfo, SamplerDesc)
  +-- src/gpu/graphite/CommandBuffer.h       (GPU 命令编码)
  +-- src/gpu/graphite/TextureProxy.h        (纹理代理)
  +-- src/gpu/graphite/BufferManager.h       (缓冲区分配)
  +-- src/gpu/graphite/Caps.h               (GPU 能力查询)
  +-- src/gpu/graphite/UniformManager.h      (Uniform 布局管理)
  +-- src/gpu/graphite/geom/Transform.h      (几何变换)
  +-- src/gpu/BufferWriter.h                 (类型安全缓冲区写入)
  +-- third_party/vello/cpp/vello.h          (Vello Rust FFI 绑定)
  +-- include/core/SkPath.h                  (路径数据)
  +-- include/core/SkStrokeRec.h             (描边参数)
```

## 设计模式分析

### 策略模式 (Strategy Pattern)

`ComputeStep` 基类定义了计算内核的统一接口，每个子类代表一个具体的计算阶段。
`DispatchGroup::Builder` 通过 `appendStep()` 将不同的 ComputeStep 策略组合成完整的
计算流水线。VelloRenderer 将 20+ 个步骤按照固定顺序组装，体现了策略模式的灵活组合能力。

### 构建器模式 (Builder Pattern)

`DispatchGroup::Builder` 是典型的构建器模式实现。它通过逐步添加 ComputeStep 来构建
DispatchGroup，在添加过程中验证资源兼容性、自动分配 GPU 资源，最终通过 `finalize()`
生成不可变的 DispatchGroup 对象。`OutputTable` 跟踪中间状态以支持增量构建。

### 槽位共享机制 (Slot-based Data Flow)

ComputeStep 之间的数据传递通过编号的共享槽位实现，类似于管道/过滤器架构模式。
多个 ComputeStep 声明相同槽位号的资源将自动绑定到同一个底层 GPU 资源。这种机制
解耦了各计算阶段，使得管线的组装和资源管理对单个步骤透明。

### 模板方法模式 (Template Method Pattern)

`VelloStep<S>` 模板类通过 C++ 模板参数化实现了编译时多态。所有 Vello 步骤共享
相同的原生着色器加载逻辑（`nativeShaderSource()`），而资源绑定和工作组配置通过
模板参数 `S` 自动从 Vello 元数据中获取。`VELLO_COMPUTE_STEP` 宏进一步减少了
样板代码。

### 资源所有权模式

`DispatchGroup` 持有所有管线、纹理和采样器的强引用（`sk_sp`），确保在 GPU 执行
期间资源不会被释放。资源实例化延迟到 `prepareResources()` 调用时进行，
实现了惰性初始化。

## 数据流

```
CPU 端场景构建:
+---------------+     +------------------+
| VelloScene    | --> | Rust Encoding    |
| solidFill()   |     | (vello_cpp)      |
| solidStroke() |     +------------------+
+---------------+              |
                               v
管线组装 (VelloRenderer::renderScene):
+------------------+     +------------------------+
| DispatchGroup    | <-- | DispatchGroup::Builder |
| ::Builder        |     |                        |
+------------------+     | 1. 写入 ConfigUniform  |
         |               | 2. 上传 Scene 编码     |
         |               | 3. appendStep() x 20+  |
         |               | 4. finalize()          |
         |               +------------------------+
         v
GPU 执行序列 (顺序调度，步骤间带屏障):
+----------------+    +----------------+    +----------------+
| PathTag Reduce | -> | PathTag Scan   | -> | BBox Clear     |
+----------------+    +----------------+    +----------------+
         |                                          |
         v                                          v
+----------------+    +----------------+    +----------------+
| Flatten        | -> | Draw Reduce    | -> | Draw Leaf      |
+----------------+    +----------------+    +----------------+
         |                                          |
         v                                          v
+----------------+    +----------------+    +----------------+
| Clip Reduce    | -> | Clip Leaf      | -> | Binning        |
+----------------+    +----------------+    +----------------+
         |                                          |
         v                                          v
+----------------+    +----------------+    +----------------+
| Tile Alloc     | -> | Path Count     | -> | Path Tiling    |
+----------------+    +----------------+    +----------------+
         |                                          |
         v                                          v
+----------------+    +----------------+    +----------------+
| Backdrop       | -> | Coarse         | -> | Fine Raster    |
+----------------+    +----------------+    +----------------+
                                                    |
                                                    v
                                            +----------------+
                                            | 输出纹理       |
                                            | (覆盖遮罩)     |
                                            +----------------+
```

## 相关文档与参考

- **ComputeTypes.h** (`src/gpu/graphite/ComputeTypes.h`) -- WorkgroupSize、IndirectDispatchArgs 等类型定义
- **ComputePipeline.h** (`src/gpu/graphite/ComputePipeline.h`) -- 计算管线对象
- **Renderer.h** (`src/gpu/graphite/Renderer.h`) -- RenderStep 基类，与计算管线配合使用
- **geom/Transform.h** (`src/gpu/graphite/geom/Transform.h`) -- Vello 使用的几何变换
- **Vello 项目** (https://github.com/linebender/vello) -- Google/Linebender 的 GPU 矢量图形渲染器
- **"Prefix Sums and Their Applications"** (Blelloch, 1993) -- 并行前缀和算法的经典论文
- **"Fast GPU Path Rendering"** (https://arxiv.org/pdf/2205.11659.pdf) -- 基于栈幺半群的 GPU 裁剪算法
- **幺半群 (Monoid)** (https://en.wikipedia.org/wiki/Monoid) -- Vello 核心代数结构
