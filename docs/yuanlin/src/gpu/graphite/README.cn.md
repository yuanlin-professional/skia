# src/gpu/graphite - Graphite 下一代 GPU 渲染后端核心

## 目录

- [概述](#概述)
- [架构图](#架构图)
- [目录结构](#目录结构)
- [关键类与函数](#关键类与函数)
  - [1. Context](#1-context-contextcpp-contextprivh)
  - [2. Recorder](#2-recorder-recordercpp-recorderprivh)
  - [3. Device](#3-device-deviceh-devicecpp)
  - [4. DrawContext](#4-drawcontext-drawcontexth-drawcontextcpp)
  - [5. DrawList 与 DrawPass](#5-drawlist-drawlisth-与-drawpass-drawpassh)
  - [6. SharedContext](#6-sharedcontext-sharedcontexth)
  - [7. CommandBuffer](#7-commandbuffer-commandbufferh)
  - [8. Renderer 与 RenderStep](#8-renderer-与-renderstep-rendererh)
  - [9. Caps](#9-caps-capsh)
  - [10. ResourceProvider](#10-resourceprovider-resourceproviderh)
  - [11. TextureProxy](#11-textureproxy-textureproxyh)
  - [12. QueueManager](#12-queuemanager-queuemanagerh)
- [依赖关系](#依赖关系)
- [设计模式分析](#设计模式分析)
- [数据流](#数据流)
- [平台特定说明](#平台特定说明)
- [相关文档与参考](#相关文档与参考)

## 概述

Graphite 是 Skia 图形库的下一代 GPU 渲染后端,旨在替代旧版的 Ganesh (GrContext) 后端。与 Ganesh 采用的即时模式(immediate mode)渲染不同,Graphite 采用了**延迟记录(deferred recording)**架构,将绘制命令的记录与 GPU 命令的提交完全解耦。这种设计使得 Graphite 能够更好地利用现代 GPU API(如 Metal、Vulkan、Dawn/WebGPU)的特性,实现更高效的命令批处理、资源管理和多线程录制。

`src/gpu/graphite` 目录是 Graphite 后端的核心实现,包含约 168 个文件,涵盖了从高层 API 接口(Context、Recorder)到底层 GPU 资源管理(Texture、Buffer、Pipeline)的完整渲染管线。该目录定义了 Graphite 的核心抽象层,各个后端(Metal、Vulkan、Dawn)通过继承这些抽象类来提供具体的 GPU API 实现。

Graphite 的核心设计理念包括:**(1)** 录制-快照-提交(Record-Snap-Submit)的三阶段工作流;**(2)** 基于任务图(Task Graph)的 GPU 工作调度;**(3)** 画家深度排序(Painter's Depth Ordering)与模板缓冲区相结合的裁剪机制;**(4)** 通过 SharedContext 实现跨 Recorder 的资源共享与线程安全。

该目录还包含了完整的着色器代码字典(ShaderCodeDictionary)和管线预编译(Precompile)系统,允许应用程序在绘制之前预编译可能用到的图形管线,从而消除运行时的管线编译卡顿(jank)。Graphite 同时集成了基于计算着色器的路径图集(Compute Path Atlas)渲染,以及传统的 MSAA 曲面细分(Tessellation)渲染路径,可根据硬件能力自动选择最佳渲染策略。

## 架构图

```
                         +-----------------------+
                         |      Application      |
                         +-----------+-----------+
                                     |
                    +----------------v-----------------+
                    |           Context (Context.cpp)  |
                    |  - 管理 GPU 设备生命周期          |
                    |  - 提交 Recording 到 GPU          |
                    |  - 异步读回像素                    |
                    +----+-------------+---------------+
                         |             |
              +----------v---+    +----v--------------+
              |   Recorder   |    |   QueueManager    |
              | (Recorder.cpp)|   | (QueueManager.h)  |
              | - 录制绘制命令 |   | - 管理 CommandBuffer|
              | - 生成快照    |   | - 提交到 GPU       |
              +------+-------+   +---------+----------+
                     |                      |
           +---------v----------+  +--------v----------+
           |   Device           |  |  CommandBuffer     |
           |  (Device.h)        |  | (CommandBuffer.h)  |
           | - SkCanvas 后端    |  | - 封装 GPU 命令    |
           | - 绘制调用分发     |  | - 资源追踪         |
           +--------+-----------+  +--------+-----------+
                    |                       |
           +--------v-----------+  +--------v----------+
           |    DrawContext      |  |  RenderPassTask   |
           |  (DrawContext.h)    |  | (RenderPassTask.h)|
           | - 管理绘制列表     |  | - 执行渲染通道    |
           | - 刷新到 DrawTask  |  +--------+----------+
           +--------+-----------+           |
                    |              +--------v----------+
           +--------v-----------+  |     DrawPass      |
           |   DrawList         |  |   (DrawPass.h)    |
           |  (DrawList.h)      |  | - 排序绘制命令    |
           | - 积累绘制命令     |  | - 生成 GPU 命令   |
           | - 排序键(SortKey) |  +-------------------+
           +--------------------+

    +-----------------------------------------------------------+
    |                    共享层 (SharedContext)                   |
    |  +-------------+ +---------------+ +-------------------+  |
    |  | GlobalCache | | PipelineManager| | ShaderCodeDict   |  |
    |  | 管线缓存    | | 管线创建/复用  | | 着色器代码字典    |  |
    |  +-------------+ +---------------+ +-------------------+  |
    |  +-------------+ +---------------+ +-------------------+  |
    |  |    Caps      | |RendererProvider| | ResourceProvider |  |
    |  | GPU 能力查询 | | 渲染器注册表   | | 资源创建/管理    |  |
    |  +-------------+ +---------------+ +-------------------+  |
    +-----------------------------------------------------------+

    +-----------------------------------------------------------+
    |              后端实现 (Backend Implementations)             |
    |  +--------+  +-----------+  +------+                      |
    |  |  mtl/  |  |   dawn/   |  |  vk/ |                     |
    |  | Metal  |  | Dawn/WebGPU|  |Vulkan|                     |
    |  +--------+  +-----------+  +------+                      |
    +-----------------------------------------------------------+
```

## 目录结构

```
src/gpu/graphite/
|-- Context.cpp / ContextPriv.h        # GPU 上下文,管理设备生命周期和提交
|-- Recorder.cpp / RecorderPriv.h      # 绘制命令录制器
|-- Device.cpp / Device.h              # SkCanvas 的 Graphite 后端实现
|-- SharedContext.cpp / SharedContext.h # 跨 Recorder 共享的 GPU 上下文
|
|-- DrawContext.cpp / DrawContext.h     # 单个渲染目标的绘制管理
|-- DrawList.cpp / DrawList.h          # 绘制命令列表及排序
|-- DrawListLayer.cpp / DrawListLayer.h # 实验性分层绘制列表
|-- DrawPass.cpp / DrawPass.h          # 已排序的绘制通道
|-- DrawWriter.cpp / DrawWriter.h      # 顶点/实例数据写入器
|-- DrawCommands.h / DrawOrder.h       # 绘制命令与排序类型定义
|
|-- CommandBuffer.cpp / CommandBuffer.h # GPU 命令缓冲区抽象
|-- QueueManager.cpp / QueueManager.h  # 命令队列管理与提交
|-- Recording.cpp / RecordingPriv.h    # 录制快照,包含所有任务
|
|-- Caps.cpp / Caps.h                  # GPU 硬件能力查询
|-- Renderer.cpp / Renderer.h          # 渲染器与渲染步骤(RenderStep)
|-- RendererProvider.cpp               # 渲染器注册与管理
|
|-- GraphicsPipeline.cpp               # 图形管线抽象
|-- GraphicsPipelineDesc.h             # 管线描述符
|-- PipelineManager.cpp / .h           # 管线创建任务管理
|-- PipelineData.h                     # 管线 uniform/texture 数据
|-- ComputePipeline.cpp                # 计算管线抽象
|
|-- ShaderCodeDictionary.cpp / .h      # 着色器代码片段字典
|-- ShaderInfo.cpp / .h                # SkSL 着色器信息组合
|-- KeyContext.cpp / KeyHelpers.cpp     # 管线键生成辅助
|-- PaintParams.cpp / PaintParamsKey.cpp # 绘制参数与管线键
|
|-- Texture.cpp / Texture.h            # GPU 纹理资源
|-- TextureProxy.cpp / TextureProxy.h  # 纹理代理(延迟实例化)
|-- TextureFormat.cpp / TextureFormat.h # 纹理格式定义
|-- TextureInfo.cpp / TextureInfoPriv.h # 纹理信息封装
|-- Sampler.cpp / Sampler.h            # 采样器资源
|
|-- Buffer.cpp / Buffer.h              # GPU 缓冲区抽象
|-- BufferManager.cpp / BufferManager.h # 绘制/静态缓冲区管理
|-- UploadBufferManager.cpp / .h       # 上传缓冲区管理
|
|-- Resource.cpp / Resource.h          # GPU 资源基类
|-- ResourceCache.cpp / ResourceCache.h # 资源缓存(LRU/预算)
|-- ResourceProvider.cpp / .h          # 资源创建工厂
|-- GlobalCache.cpp / GlobalCache.h    # 全局共享缓存(管线/采样器)
|-- ScratchResourceManager.cpp / .h    # 临时资源复用管理
|
|-- ClipStack.cpp / ClipStack.h        # 裁剪栈实现
|-- ClipAtlasManager.cpp / .h          # 裁剪图集管理
|-- AtlasProvider.cpp / .h             # 图集提供器(文字/路径/裁剪)
|-- DrawAtlas.cpp / DrawAtlas.h        # 绘制图集(纹理图集)
|-- PathAtlas.cpp / PathAtlas.h        # 路径图集抽象
|-- RasterPathAtlas.cpp / .h           # 软件光栅化路径图集
|-- ComputePathAtlas.cpp / .h          # 计算着色器路径图集
|
|-- Image_Graphite.cpp / .h            # Graphite 图像实现
|-- Image_YUVA_Graphite.cpp / .h       # YUVA 图像支持
|-- Surface_Graphite.cpp / .h          # Graphite 表面实现
|-- SpecialImage_Graphite.cpp / .h     # 特殊图像(滤镜中间产物)
|
|-- RenderPassDesc.cpp / .h            # 渲染通道描述符
|-- RuntimeEffectDictionary.cpp / .h   # 运行时效果字典
|-- UniformManager.cpp / .h            # Uniform 数据布局管理
|
|-- compute/                           # 计算着色器调度
|   |-- ComputeStep.cpp / .h          # 计算步骤基类
|   |-- DispatchGroup.cpp / .h        # 计算调度组
|   |-- VelloRenderer.cpp / .h        # Vello 向量渲染器
|   |-- VelloComputeSteps.cpp / .h    # Vello 计算步骤
|
|-- dawn/                              # Dawn/WebGPU 后端实现
|-- mtl/                               # Metal 后端实现
|-- vk/                                # Vulkan 后端实现
|
|-- geom/                              # 几何工具类
|   |-- Shape.cpp / Shape.h           # 几何形状抽象
|   |-- Transform.cpp / Transform.h   # 变换矩阵封装
|   |-- Rect.h                        # 浮点矩形(SIMD 优化)
|   |-- BoundsManager.h              # 绘制边界管理
|   |-- IntersectionTree.cpp / .h     # 相交树(模板索引)
|
|-- render/                            # 各类 RenderStep 实现
|   |-- AnalyticRRectRenderStep.cpp   # 解析圆角矩形
|   |-- AnalyticBlurRenderStep.cpp    # 解析模糊
|   |-- TessellateCurvesRenderStep.cpp# 曲线细分
|   |-- TessellateStrokesRenderStep.cpp# 描边细分
|   |-- TessellateWedgesRenderStep.cpp# 楔形细分
|   |-- CoverageMaskRenderStep.cpp    # 覆盖度蒙版
|   |-- BitmapTextRenderStep.cpp      # 位图文字
|   |-- SDFTextRenderStep.cpp         # SDF 文字
|   |-- VerticesRenderStep.cpp        # 自定义顶点
|   |-- PerEdgeAAQuadRenderStep.cpp   # 逐边抗锯齿四边形
|
|-- task/                              # 任务图系统
|   |-- Task.h                        # 任务基类
|   |-- TaskList.cpp / .h            # 任务列表
|   |-- DrawTask.cpp / .h            # 绘制任务
|   |-- RenderPassTask.cpp / .h      # 渲染通道任务
|   |-- UploadTask.cpp / .h          # 上传任务
|   |-- ComputeTask.cpp / .h         # 计算任务
|   |-- CopyTask.cpp / .h            # 拷贝任务
|   |-- SynchronizeToCpuTask.cpp / .h# CPU 同步任务
|   |-- ClearBuffersTask.cpp / .h    # 缓冲区清除任务
|
|-- text/                              # 文字渲染支持
|   |-- TextAtlasManager.cpp / .h    # 文字图集管理
|   |-- TextStrike.cpp / .h          # 文字 Strike 缓存
|   |-- GlyphData.cpp / .h           # 字形数据
|
|-- surface/                           # 平台特定 Surface 工厂
|   |-- Surface_AndroidFactories.cpp  # Android Surface 创建
|
|-- precompile/                        # 管线预编译系统
```

## 关键类与函数

### 1. Context (`Context.cpp`, `ContextPriv.h`)

**职责**: Graphite 的顶层入口,管理 GPU 设备生命周期,负责将 Recording 提交到 GPU 执行。

**关键方法**:
- `makeRecorder(const RecorderOptions&)` - 创建客户端拥有的 Recorder
- `makeInternalRecorder()` - 创建内部短生命周期 Recorder(共享资源预算)
- `insertRecording(const InsertRecordingInfo&)` - 将录制的 Recording 插入命令队列
- `submit(SubmitInfo)` - 提交所有待处理的 GPU 工作
- `asyncRescaleAndReadPixels()` - 异步缩放并读回像素数据
- `transferPixels()` - 从纹理传输像素到缓冲区
- `freeGpuResources()` / `performDeferredCleanup()` - GPU 资源清理
- `finishInitialization()` - 初始化 RendererProvider 和静态缓冲区

**关键成员**:
- `fSharedContext` - 共享上下文(Caps、GlobalCache、ShaderCodeDictionary)
- `fQueueManager` - 命令队列管理器
- `fResourceProvider` - Context 自有的资源提供器
- `fMappedBufferManager` - 异步映射缓冲区管理

### 2. Recorder (`Recorder.cpp`, `RecorderPriv.h`)

**职责**: 录制绘制命令的核心对象。每个 Recorder 拥有自己的资源预算和绘制状态,可在不同线程上独立使用。

**关键方法**:
- `snap()` - 将所有累积的工作快照为一个不可变的 Recording
- `makeDeferredCanvas()` - 创建延迟绘制画布(用于延迟绑定纹理)
- `registerDevice(sk_sp<Device>)` - 注册需要追踪的 Device
- `createBackendTexture()` / `updateBackendTexture()` - 后端纹理操作
- `freeGpuResources()` / `performDeferredCleanup()` - 资源管理

**关键成员**:
- `fSharedContext` - 共享上下文引用
- `fResourceProvider` - 资源提供器(自有或 Context 共享)
- `fRootTaskList` / `fRootUploads` - 根任务列表与上传列表
- `fDrawBufferManager` / `fUploadBufferManager` - 缓冲区管理
- `fAtlasProvider` - 图集管理(文字/路径/裁剪)
- `fTrackedDevices` - 已注册的 Device 列表

### 3. Device (`Device.h`, `Device.cpp`)

**职责**: `SkDevice` 的 Graphite 实现,是 `SkCanvas` 与 Graphite 之间的桥梁,将所有 SkCanvas 绘制调用转换为 Graphite 内部的绘制命令。

**关键方法**:
- `Make()` - 静态工厂方法,创建关联到纹理代理的 Device
- `drawRect()`, `drawPath()`, `drawRRect()` 等 - 各种图元绘制
- `drawGeometry()` - 所有绘制的最终落点,记录到 DrawContext
- `chooseRenderer()` - 根据形状和样式选择最佳 Renderer
- `flushPendingWork()` - 刷新挂起工作到 DrawTask
- `clipRect()`, `clipPath()` 等 - 裁剪操作

**关键成员**:
- `fRecorder` - 关联的 Recorder
- `fDC` (DrawContext) - 管理当前目标的绘制列表
- `fClip` (ClipStack) - 裁剪栈
- `fColorDepthBoundsManager` - 颜色/深度边界管理器
- `fCurrentDepth` - 画家深度计数器

### 4. DrawContext (`DrawContext.h`, `DrawContext.cpp`)

**职责**: 管理面向单个渲染目标(TextureProxy)的绘制记录。将绘制、上传和依赖任务组织到 DrawTask 中。

**关键方法**:
- `recordDraw()` - 记录一次绘制(Renderer、变换、几何、裁剪、排序、颜料)
- `recordUpload()` - 记录纹理上传
- `recordDependency()` - 记录任务依赖
- `flush()` - 将挂起的绘制和上传刷新到 DrawTask
- `snapDrawTask()` - 获取当前 DrawTask
- `getComputePathAtlas()` - 获取/创建计算路径图集

**关键成员**:
- `fTarget` - 渲染目标纹理代理
- `fCurrentDrawTask` - 正在构建的 DrawTask
- `fPendingDraws` (DrawListBase) - 挂起的绘制列表
- `fPendingUploads` - 挂起的上传
- `fComputePathAtlas` - 计算路径图集

### 5. DrawList (`DrawList.h`) 与 DrawPass (`DrawPass.h`)

**DrawList 职责**: 收集任意顺序的绘制命令,支持排序和优化。每个绘制命令包含形状、变换、裁剪、着色描述和排序键。

**DrawPass 职责**: DrawList 排序优化后的不可变绘制通道,尽可能直接对应 GPU 命令缓冲区内容。

**DrawList 关键方法**:
- `recordDraw()` - 记录一个完整的绘制操作
- `snapDrawPass()` - 将 DrawList 排序优化后转换为 DrawPass

**DrawPass 关键方法**:
- `prepareResources()` - 实例化管线、纹理、采样器等资源
- `addResourceRefs()` - 将资源引用添加到 CommandBuffer
- `commands()` - 获取排序后的命令列表迭代器

### 6. SharedContext (`SharedContext.h`)

**职责**: 所有 Recorder 共享的 GPU 上下文,持有只读/长生命周期的共享资源。

**关键方法**:
- `caps()` - 获取硬件能力查询对象
- `globalCache()` - 获取全局缓存(管线、采样器)
- `pipelineManager()` - 获取管线管理器
- `rendererProvider()` - 获取渲染器注册表
- `shaderCodeDictionary()` - 获取着色器代码字典
- `findOrCreateGraphicsPipeline()` - 查找或创建图形管线
- `makeResourceProvider()` - 创建后端特定的资源提供器(纯虚)

### 7. CommandBuffer (`CommandBuffer.h`)

**职责**: GPU 命令缓冲区的抽象基类,封装渲染通道、计算通道和数据传输操作。

**关键方法**:
- `addRenderPass()` - 添加渲染通道(颜色/深度模板/解析纹理 + DrawPass 列表)
- `addComputePass()` - 添加计算通道
- `copyTextureToBuffer()` / `copyBufferToTexture()` - 纹理-缓冲区拷贝
- `copyTextureToTexture()` - 纹理间拷贝
- `trackResource()` - 追踪资源引用直到命令执行完毕
- `setReplayTranslationAndClip()` - 设置重放平移和裁剪

### 8. Renderer 与 RenderStep (`Renderer.h`)

**Renderer 职责**: 定义将高级绘制操作分解为一系列 RenderStep 的技术方案。每个 Renderer 是单例,通过 RendererProvider 访问。

**RenderStep 职责**: 渲染技术的单个步骤,定义顶点布局、SkSL 着色器代码、深度模板设置和 uniform 数据。

**RenderStep 关键方法**:
- `writeVertices()` - 写入顶点/实例数据
- `writeUniformsAndTextures()` - 写入 uniform 值和纹理绑定
- `vertexSkSL()` - 返回顶点着色器 SkSL 代码
- `fragmentCoverageSkSL()` / `fragmentColorSkSL()` - 片段着色器覆盖度/颜色代码

**内置 RenderStep 类型**: `AnalyticRRect`, `AnalyticBlur`, `TessellateCurves`, `TessellateStrokes`, `TessellateWedges`, `CoverageMask`, `BitmapText`, `SDFText`, `PerEdgeAAQuad`, `Vertices` 等。

### 9. Caps (`Caps.h`)

**职责**: GPU 硬件能力抽象,各后端子类化提供具体能力信息。

**关键能力查询**:
- `maxTextureSize()` - 最大纹理尺寸
- `isTexturable()` / `isRenderable()` / `isCopyableSrc()` - 纹理能力
- `storageBufferSupport()` / `computeSupport()` - 存储缓冲区/计算支持
- `blendEquationSupport()` - 混合方程支持级别
- `getDstReadStrategy()` - 目标纹理读取策略
- `makeGraphicsPipelineKey()` - 生成管线唯一键(纯虚)
- `resourceBindingRequirements()` - 资源绑定需求

### 10. ResourceProvider (`ResourceProvider.h`)

**职责**: GPU 资源的创建与缓存工厂,每个 Recorder 和 Context 拥有独立实例。

**关键方法**:
- `findOrCreateShareableTexture()` / `findOrCreateNonShareableTexture()` - 查找或创建纹理
- `findOrCreateNonShareableBuffer()` / `findOrCreateScratchBuffer()` - 缓冲区管理
- `createGraphicsPipelineHandle()` / `resolveHandle()` - 管线创建与解析
- `findOrCreateCompatibleSampler()` - 采样器管理
- `createWrappedTexture()` - 包装外部纹理

### 11. TextureProxy (`TextureProxy.h`)

**职责**: 纹理的代理对象,支持延迟实例化(lazy instantiation)和临时(scratch)资源复用。

**关键特性**:
- 支持三种创建模式: 立即实例化 (`Make`)、延迟实例化 (`MakeLazy`)、完全延迟 (`MakeFullyLazy`)
- `instantiate()` / `lazyInstantiate()` - 按需实例化实际纹理
- `InstantiateIfNotLazy(ScratchResourceManager*)` - 通过临时资源管理器实例化
- `Wrap()` - 包装已有纹理

### 12. QueueManager (`QueueManager.h`)

**职责**: 管理命令缓冲区的创建、复用和按序提交。支持受保护(Protected)和非受保护命令缓冲区。

**关键方法**:
- `addRecording()` - 将 Recording 中的任务添加到当前命令缓冲区
- `addTask()` - 直接添加单个任务
- `submitToGpu()` - 将命令缓冲区提交到 GPU
- `checkForFinishedWork()` - 检查已完成的 GPU 工作

## 依赖关系

### 上游依赖 (被调用方)

| 模块 | 路径 | 说明 |
|------|------|------|
| Skia Core | `include/core/` | SkCanvas, SkPaint, SkImage, SkSurface 等核心类型 |
| GPU 公共头 | `include/gpu/graphite/` | Context, Recorder, Recording 的公共 API 定义 |
| GPU 通用层 | `src/gpu/` | ResourceKey, Swizzle, RefCntedCallback, Token 等通用工具 |
| SkSL | `src/sksl/` | 着色器编译,通过 SkSL::Compiler 和 Graphite 模块数据 |
| Text 渲染 | `src/text/gpu/` | SubRunContainer, StrikeCache, TextBlobRedrawCoordinator |
| 图像滤镜 | `src/core/` | SkDevice 基类, SkConvertPixels 等核心实现 |
| Capture | `src/capture/` | SkCaptureManager 渲染捕获系统 |

### 下游依赖 (调用方)

| 模块 | 路径 | 说明 |
|------|------|------|
| Metal 后端 | `src/gpu/graphite/mtl/` | MtlCaps, MtlCommandBuffer, MtlTexture 等 |
| Vulkan 后端 | `src/gpu/graphite/vk/` | VulkanCaps, VulkanCommandBuffer 等 |
| Dawn 后端 | `src/gpu/graphite/dawn/` | DawnCaps, DawnCommandBuffer 等 |
| 测试代码 | `tests/graphite/` | 单元测试和集成测试 |
| Benchmark | `bench/` | 性能基准测试 |

### 外部依赖

| 依赖 | 说明 |
|------|------|
| Metal Framework | Apple 平台 GPU API (mtl/ 子目录) |
| Vulkan SDK | 跨平台 GPU API (vk/ 子目录) |
| Dawn (WebGPU) | Chrome 的 WebGPU 实现 (dawn/ 子目录) |
| Vello | 基于计算着色器的 2D 向量渲染 (compute/ 子目录) |

## 设计模式分析

### 1. 延迟记录模式 (Deferred Recording Pattern)

Graphite 的核心设计模式。绘制命令不会立即执行,而是经过三个阶段:

```
记录阶段 (Recorder)  -->  快照阶段 (snap)  -->  提交阶段 (Context::submit)
  - Device 记录绘制       - 排序/优化绘制      - 生成 GPU 命令
  - DrawList 积累命令      - 实例化资源          - 提交到 GPU 队列
  - 上传纹理数据           - 生成 DrawPass       - 等待/轮询完成
```

### 2. 代理模式 (Proxy Pattern)

`TextureProxy` 是经典的代理模式应用。纹理在录制时只创建代理(描述尺寸、格式等元信息),实际 GPU 纹理在 `prepareResources()` 阶段按需实例化。这允许:
- 延迟资源分配到真正需要的时刻
- 临时(scratch)纹理的高效复用
- 懒加载(lazy)纹理的回调机制

### 3. 任务图模式 (Task Graph Pattern)

GPU 工作通过 `Task` 基类组织为有向无环图(DAG):
- `DrawTask` - 封装一组 RenderPassTask 和依赖
- `RenderPassTask` - 封装一个渲染通道中的 DrawPass 集合
- `UploadTask` - 封装数据上传操作
- `ComputeTask` - 封装计算着色器调度
- `CopyTask` - 封装纹理/缓冲区拷贝
- `SynchronizeToCpuTask` - 封装 CPU 同步操作

每个 Task 有两阶段执行:
- `prepareResources()` - 在 Recorder 上下文中准备资源
- `addCommands()` - 将命令写入 CommandBuffer

### 4. 策略模式 (Strategy Pattern)

`Renderer` 和 `RenderStep` 使用策略模式。`Device::chooseRenderer()` 根据形状类型、描边样式和硬件能力,在运行时选择最优的渲染策略:
- 解析渲染 (Analytic): `AnalyticRRectRenderStep` - GPU 内解析计算覆盖度
- 曲面细分 (Tessellation): `TessellateCurvesRenderStep` - 将曲线细分为三角形
- 覆盖度蒙版 (Coverage Mask): `CoverageMaskRenderStep` - 通过图集纹理渲染
- 计算路径 (Compute Path): 通过 `ComputePathAtlas` 用计算着色器生成覆盖度

### 5. 享元模式 (Flyweight Pattern)

`ShaderCodeDictionary` 和 `PaintParamsKey` 使用享元模式:
- 着色器代码片段通过全局字典去重,以整数 ID 引用
- 绘制参数组合(着色器、颜色滤镜、混合模式)编码为紧凑的键
- `UniformDataCache` 和 `TextureDataCache` 对 uniform/纹理数据去重

### 6. 模板方法模式 (Template Method Pattern)

后端抽象层广泛使用模板方法模式:
- `CommandBuffer::addRenderPass()` 调用 `onAddRenderPass()` (子类实现)
- `ResourceProvider::findOrCreateTexture()` 调用 `createTexture()` (子类实现)
- `SharedContext::findOrCreateGraphicsPipeline()` 调用 `createGraphicsPipeline()` (子类实现)
- `Task::prepareResources()` 和 `Task::addCommands()` 由各 Task 子类实现

### 7. 观察者/回调模式

- `TextureProxy::LazyInstantiateCallback` - 延迟纹理实例化回调
- `GpuFinishedProc` - GPU 工作完成回调
- `ContextOptions::PipelineCachingCallback` - 管线缓存事件回调

## 数据流

### 绘制命令数据流 (从 SkCanvas 到 GPU)

```
1. SkCanvas::drawRect()
   |
   v
2. Device::drawRect()
   |-- 应用路径效果 (drawGeometryWithPathEffect)
   |
   v
3. Device::drawGeometry()
   |-- chooseRenderer() -> 选择 Renderer + 可选 PathAtlas
   |-- ClipStack::applyClipToDraw() -> 确定裁剪
   |-- DrawOrder 分配 (深度、模板索引、画家顺序)
   |
   v
4. DrawContext::recordDraw()
   |-- DrawList::recordDraw() -> 存储 Draw 结构体
   |-- 生成 PaintParamsKey (着色器组合键)
   |-- 收集 Uniform/Texture 数据
   |
   v
5. Device::flushPendingWork()
   |-- DrawContext::flush()
   |     |-- DrawList::snapDrawPass() -> 排序 + 生成 DrawPass
   |     |-- 添加到 DrawTask
   |-- DrawContext::snapDrawTask() -> 返回 DrawTask
   |-- 添加到 Recorder 根任务列表
   |
   v
6. Recorder::snap()
   |-- 刷新所有跟踪的 Device
   |-- DrawBufferManager::transferToRecording()
   |-- 创建 Recording (包含 TaskList)
   |-- Task::prepareResources() -> 实例化管线/纹理/缓冲区
   |
   v
7. Context::insertRecording()
   |-- QueueManager::addRecording()
   |     |-- Task::addCommands() -> 写入 CommandBuffer
   |     |-- CommandBuffer::addRenderPass()
   |
   v
8. Context::submit()
   |-- QueueManager::submitToGpu()
   |-- GPU 执行命令
```

### 管线创建数据流

```
1. DrawList 排序阶段
   |-- 对每个 (Draw, RenderStep) 对:
   |     |-- GraphicsPipelineDesc = RenderStep 信息 + PaintParamsKey
   |     |-- RenderPassDesc = 目标格式 + 加载/存储操作 + MSAA
   |
   v
2. DrawPass::prepareResources()
   |-- ResourceProvider::createGraphicsPipelineHandle()
   |     |-- PipelineManager::createHandle()
   |     |     |-- Caps::makeGraphicsPipelineKey() -> UniqueKey
   |     |     |-- GlobalCache::findGraphicsPipeline() -> 缓存查询
   |     |     |-- 若未命中: 创建 PipelineCreationTask
   |
   v
3. ResourceProvider::startPipelineCreationTask()
   |-- PipelineManager::startPipelineCreationTask()
   |     |-- SharedContext::createGraphicsPipeline() (可能异步/线程化)
   |
   v
4. ResourceProvider::resolveHandle()
   |-- PipelineManager::resolveHandle()
   |     |-- 等待编译完成, 返回 sk_sp<GraphicsPipeline>
   |     |-- GlobalCache::addGraphicsPipeline() -> 加入全局缓存
```

### 纹理代理实例化流程

```
1. 录制阶段: TextureProxy::Make() 或 MakeLazy()
   |-- 仅记录尺寸、格式等元信息
   |-- 不分配 GPU 资源
   |
   v
2. snap() -> prepareResources()
   |-- TextureProxy::InstantiateIfNotLazy(ScratchResourceManager*)
   |     |-- 尝试复用临时纹理 (ScratchResourceManager)
   |     |-- 或 ResourceProvider::findOrCreateShareableTexture()
   |     |-- 或执行 LazyInstantiateCallback
   |
   v
3. addCommands()
   |-- TextureProxy::texture() 返回已实例化的 Texture
   |-- CommandBuffer::trackResource() 追踪资源引用
```

## 平台特定说明

### Metal (mtl/)

Metal 后端是 Graphite 最成熟的实现,位于 `src/gpu/graphite/mtl/` 目录。主要特点:
- NDC Y 轴朝下 (`ndcYAxisPointsDown() == true`),与 Skia 约定一致
- 原生支持存储缓冲区(Storage Buffer),使用 Metal 内存布局
- 支持 `msaaRenderToSingleSampled`(Metal 3+ 设备)
- 不支持 clamp-to-border 采样(需回退方案)
- Metal Shader 通过 SkSL -> MSL 转译生成

### Vulkan (vk/)

Vulkan 后端位于 `src/gpu/graphite/vk/` 目录。主要特点:
- 支持动态状态(`useBasicDynamicState`, `useVertexInputDynamicState`)
- 支持管线库(`usePipelineLibraries` via VK_EXT_graphics_pipeline_library)
- 支持推送常量(Push Constants)用于内置常量
- 支持 AHardwareBuffer 导入(Android)
- 支持受保护内容(Protected Content)
- Vulkan Shader 通过 SkSL -> SPIR-V 转译生成

### Dawn / WebGPU (dawn/)

Dawn 后端位于 `src/gpu/graphite/dawn/` 目录,用于 Chrome 浏览器和 WebGPU。主要特点:
- 缓冲区映射为异步操作 (`bufferMapsAreAsync() == true`)
- 不支持 CPU 同步 (`allowCpuSync()` 可能为 false)
- 需要特殊的异步工作完成检查 (`deviceTick`)
- 要求有序录制 (`requireOrderedRecordings` 默认为 true)
- Dawn Shader 通过 SkSL -> WGSL 转译生成

### Android 特定支持

- `Surface_AndroidFactories.cpp` - Android 专用 Surface 创建
- AHardwareBuffer 纹理导入支持 (仅 Vulkan 后端)
- 受保护内容支持(Protected Content)

### 计算着色器路径渲染

- `ComputePathAtlas` - 使用计算着色器生成路径覆盖度蒙版
- `RasterPathAtlas` - 回退方案,使用 CPU 光栅化生成路径蒙版
- `VelloRenderer` / `VelloComputeSteps` - 基于 Vello 的计算着色器向量渲染
- 仅在硬件支持计算着色器时可用 (`Caps::computeSupport()`)

## 相关文档与参考

### 源码中的相关目录

| 路径 | 说明 |
|------|------|
| `include/gpu/graphite/` | Graphite 公共 API 头文件 |
| `src/gpu/graphite/mtl/` | Metal 后端实现 |
| `src/gpu/graphite/vk/` | Vulkan 后端实现 |
| `src/gpu/graphite/dawn/` | Dawn/WebGPU 后端实现 |
| `src/gpu/graphite/precompile/` | 管线预编译系统 |
| `src/gpu/` | GPU 通用工具(ResourceKey, Swizzle 等) |
| `src/sksl/` | SkSL 着色器语言编译器 |
| `src/text/gpu/` | GPU 文字渲染通用层 |
| `tests/graphite/` | Graphite 测试套件 |

### 核心概念术语表

| 术语 | 说明 |
|------|------|
| Recording | 通过 `Recorder::snap()` 产生的不可变工作快照 |
| DrawPass | 排序优化后的绘制命令集,对应 GPU 子通道 |
| RenderStep | 渲染技术的单个步骤(顶点布局 + 着色器代码) |
| PaintersDepth | 画家深度值,用于深度测试实现画家算法排序 |
| CompressedPaintersOrder | 压缩的画家顺序,排序键的最高位 |
| DisjointStencilIndex | 不相交模板索引,确保多步骤渲染的正确性 |
| ScratchDevice | 临时 Device,在 Recorder snap 前必须释放 |
| TextureProxy | 纹理代理,支持延迟实例化和资源复用 |
| PaintParamsKey | 绘制参数键,编码着色器/混合/滤镜组合 |
| DstReadStrategy | 目标纹理读取策略(纹理拷贝/输入附件/无需读取) |
| DrawTask | 对应单个渲染目标的完整任务(含依赖和渲染通道) |

### Graphite 与 Ganesh 的主要区别

| 特性 | Ganesh (旧) | Graphite (新) |
|------|-------------|---------------|
| 命令模式 | 即时提交 | 延迟录制 + 批量提交 |
| 线程模型 | 单 Recorder | 多 Recorder 并行 |
| 裁剪实现 | 模板缓冲区 | 深度排序 + 模板/图集混合 |
| 管线管理 | 即时编译 | 预编译 + 全局缓存 |
| 资源模型 | GrContext 集中管理 | SharedContext + 每 Recorder 预算 |
| API 覆盖 | GL/Vulkan/Metal/D3D | Metal/Vulkan/Dawn(WebGPU) |
| 排序策略 | Op 批次合并 | 画家深度 + SortKey 全局排序 |
