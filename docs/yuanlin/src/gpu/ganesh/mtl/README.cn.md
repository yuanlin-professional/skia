# Ganesh Metal 后端 - Apple Metal GPU 渲染实现

## 概述

本目录 (`src/gpu/ganesh/mtl/`) 是 Skia 图形库中 Ganesh GPU 渲染引擎的 **Apple Metal** 后端实现。Metal 是 Apple 专有的低开销图形和计算 API，适用于 macOS、iOS 和 tvOS 平台。本目录包含约 51 个源文件（头文件 `.h` 和 Objective-C++ 实现文件 `.mm`），共同构成了一个完整的 Metal 渲染管线。

Ganesh Metal 后端的核心职责是将 Skia 的跨平台绘图操作翻译为 Metal API 调用。它负责管理 Metal 设备 (`MTLDevice`)、命令队列 (`MTLCommandQueue`)、命令缓冲区 (`MTLCommandBuffer`)、渲染管线状态 (`MTLRenderPipelineState`)、纹理、缓冲区以及各种 GPU 资源的生命周期。所有文件均以 `GrMtl` 前缀命名，遵循 Skia 的 Ganesh 命名规范。

本后端支持完整的 2D 图形渲染功能，包括纹理采样、混合模式、模板测试、MSAA 多重采样抗锯齿、Mipmap 生成、像素读写传输、着色器编译与缓存等。实现上采用 Objective-C++ (`.mm`) 作为源文件格式，以便直接调用 Metal 的 Objective-C API，同时与 Skia 的 C++ 架构无缝集成。

需要特别注意的是，所有 `.mm` 文件均使用 **ARC (Automatic Reference Counting)** 编译（通过 `-fobjc-arc` 标志），并定义了 `GR_NORETAIN` 宏来优化 ARC 环境下的性能。构建时需要链接 `Metal`、`MetalKit` 和 `Foundation` 框架，并定义 `SK_METAL` 宏。

## 架构图

```
+------------------------------------------------------------------+
|                      GrDirectContext                              |
|                  (Skia 图形上下文入口)                              |
+------------------------------------------------------------------+
         |                                      |
         v                                      v
+-------------------+              +-------------------------+
| GrMtlTrampoline   |              |  GrMtlDirectContext.mm  |
| (C++ -> ObjC 桥接) |              |  (MakeMetal 入口函数)     |
+-------------------+              +-------------------------+
         |
         v
+------------------------------------------------------------------+
|                        GrMtlGpu                                  |
|              (Metal GPU 设备核心管理器)                             |
|                                                                  |
|  fDevice: id<MTLDevice>                                          |
|  fQueue: id<MTLCommandQueue>                                     |
|  fCurrentCmdBuffer: sk_sp<GrMtlCommandBuffer>                   |
|  fResourceProvider: GrMtlResourceProvider                        |
|  fStagingBufferManager: GrStagingBufferManager                   |
|  fUniformsRingBuffer: GrRingBuffer                               |
+------------------------------------------------------------------+
         |              |               |               |
         v              v               v               v
+-------------+ +---------------+ +------------+ +----------------+
| GrMtlCaps   | | GrMtlCommand  | | GrMtlOps   | | GrMtlResource  |
| (能力查询)   | | Buffer        | | RenderPass | | Provider       |
|             | | (命令缓冲区)   | | (渲染通道)  | | (资源缓存)     |
+-------------+ +---------------+ +------------+ +----------------+
                       |                |               |
                       v                v               v
              +-----------------+ +-----------+ +------------------+
              | GrMtlRender     | | GrMtl     | | PipelineState    |
              | CommandEncoder  | | Pipeline  | | Cache (LRU)      |
              | (编码器状态追踪) | | State     | |                  |
              +-----------------+ +-----------+ +------------------+
                                       |
                       +---------------+---------------+
                       |               |               |
                       v               v               v
              +-----------+ +-------------+ +------------------+
              | GrMtl     | | GrMtl       | | GrMtlPipeline   |
              | Uniform   | | Varying     | | StateData        |
              | Handler   | | Handler     | | Manager          |
              +-----------+ +-------------+ +------------------+

+------------------------------------------------------------------+
|                       GPU 资源层                                   |
+------------------------------------------------------------------+
|  GrMtlTexture    | GrMtlRenderTarget  | GrMtlTextureRenderTarget |
|  GrMtlAttachment | GrMtlBuffer        | GrMtlFramebuffer         |
|  GrMtlSampler    | GrMtlDepthStencil  | GrMtlSemaphore/Event     |
+------------------------------------------------------------------+
```

## 文件分类索引

### 1. 核心实现 — GPU/Caps/Context

| 文件 | 说明 |
|------|------|
| GrMtlGpu.h / GrMtlGpu.mm | Metal GPU 设备管理器（核心类） |
| GrMtlCaps.h / GrMtlCaps.mm | Metal 能力查询与格式支持 |
| GrMtlDirectContext.mm | GrDirectContext Metal 入口 |
| GrMtlTrampoline.h / GrMtlTrampoline.mm | C++ 到 Objective-C 的桥接层 |

### 2. 命令/渲染 — Command Buffer/RenderPass

| 文件 | 说明 |
|------|------|
| GrMtlCommandBuffer.h / GrMtlCommandBuffer.mm | Metal 命令缓冲区封装 |
| GrMtlRenderCommandEncoder.h | 渲染命令编码器状态追踪 |
| GrMtlOpsRenderPass.h / GrMtlOpsRenderPass.mm | 渲染操作通道实现 |

### 3. 管线管理 — Pipeline

| 文件 | 说明 |
|------|------|
| GrMtlPipeline.h | MTLRenderPipelineState 封装 |
| GrMtlPipelineState.h / GrMtlPipelineState.mm | 完整渲染管线状态 |
| GrMtlPipelineStateBuilder.h / GrMtlPipelineStateBuilder.mm | 管线状态构建器 |
| GrMtlPipelineStateDataManager.h / GrMtlPipelineStateDataManager.mm | Uniform 数据管理 |

### 4. 资源/纹理 — Texture/Buffer/Attachment

| 文件 | 说明 |
|------|------|
| GrMtlTexture.h / GrMtlTexture.mm | Metal 纹理 |
| GrMtlRenderTarget.h / GrMtlRenderTarget.mm | Metal 渲染目标 |
| GrMtlTextureRenderTarget.h / GrMtlTextureRenderTarget.mm | 纹理与渲染目标组合 |
| GrMtlAttachment.h / GrMtlAttachment.mm | 附件（颜色/模板/深度/MSAA） |
| GrMtlBuffer.h / GrMtlBuffer.mm | Metal 缓冲区 |

### 5. 渲染基础设施 — Framebuffer/DepthStencil

| 文件 | 说明 |
|------|------|
| GrMtlFramebuffer.h / GrMtlFramebuffer.mm | 帧缓冲区封装 |
| GrMtlDepthStencil.h / GrMtlDepthStencil.mm | 深度/模板状态 |

### 6. 采样器 — Sampler

| 文件 | 说明 |
|------|------|
| GrMtlSampler.h / GrMtlSampler.mm | Metal 采样器状态 |

### 7. 同步 — Synchronization

| 文件 | 说明 |
|------|------|
| GrMtlSemaphore.h / GrMtlSemaphore.mm | 信号量（基于 MTLEvent） |

### 8. Uniform/Varying — 着色器变量管理

| 文件 | 说明 |
|------|------|
| GrMtlUniformHandler.h / GrMtlUniformHandler.mm | Uniform 变量处理 |
| GrMtlVaryingHandler.h / GrMtlVaryingHandler.mm | Varying 变量处理 |

### 9. 资源提供器 — Resource Provider

| 文件 | 说明 |
|------|------|
| GrMtlResourceProvider.h / GrMtlResourceProvider.mm | 资源缓存与复用 |

### 10. 后端表面/工具 — Backend Surface & Utilities

| 文件 | 说明 |
|------|------|
| GrMtlBackendSemaphore.mm | 后端信号量支持 |
| GrMtlBackendSurface.mm | 后端表面支持 |
| GrMtlUtil.h / GrMtlUtil.mm | 通用工具函数 |
| GrMtlCppUtil.h | 可在 C++ 中使用的工具 |
| GrMtlTypesPriv.h / GrMtlTypesPriv.mm | 私有类型定义与 SDK 版本检测 |

## 关键类与函数

### 1. GrMtlGpu (`GrMtlGpu.h` / `GrMtlGpu.mm`)

**职责**: Metal 后端的核心入口，继承自 `GrGpu`。管理 Metal 设备、命令队列、命令缓冲区的生命周期，并协调所有 GPU 操作。

**关键成员**:
- `fDevice: id<MTLDevice>` - Metal 设备引用
- `fQueue: id<MTLCommandQueue>` - 命令队列
- `fCurrentCmdBuffer: sk_sp<GrMtlCommandBuffer>` - 当前活动的命令缓冲区
- `fResourceProvider: GrMtlResourceProvider` - 资源提供器（管线缓存、采样器缓存等）
- `fStagingBufferManager: GrStagingBufferManager` - 暂存缓冲区管理
- `fUniformsRingBuffer: GrRingBuffer` - Uniform 数据环形缓冲区

**关键方法**:
- `Make(const GrMtlBackendContext&, const GrContextOptions&, GrDirectContext*)` - 静态工厂方法
- `commandBuffer()` - 获取或创建当前命令缓冲区
- `onCreateTexture(...)` - 创建 Metal 纹理
- `onReadPixels(...)` / `onWritePixels(...)` - 像素数据读写
- `onCopySurface(...)` - 表面复制（支持 Blit 和 Resolve 两种模式）
- `submitCommandBuffer(SyncQueue)` - 提交命令缓冲区并可选同步等待
- `copySurfaceAsBlit(...)` / `copySurfaceAsResolve(...)` - 两种表面复制策略
- `loadMSAAFromResolve(...)` - 从解析附件加载 MSAA 数据

### 2. GrMtlCaps (`GrMtlCaps.h` / `GrMtlCaps.mm`)

**职责**: 查询并存储 Metal 设备的能力信息。继承自 `GrCaps`，提供像素格式支持、采样数、渲染能力等查询。

**关键方法**:
- `isFormatTexturable(MTLPixelFormat)` - 查询格式是否可作为纹理
- `isFormatRenderable(MTLPixelFormat, int sampleCount)` - 查询格式是否可渲染
- `getRenderTargetSampleCount(int, MTLPixelFormat)` - 获取支持的采样数
- `preferredStencilFormat()` - 获取首选模板格式
- `canCopyAsBlit(...)` / `canCopyAsResolve(...)` - 判断复制策略可用性
- `makeDesc(...)` - 创建程序描述符（用于着色器缓存键）
- `isMac()` / `isApple()` / `isIntel()` - GPU 家族识别

**内部结构**:
- `GPUFamily` 枚举: `kApple`、`kMac`、`kMacIntel` - 区分不同的 GPU 架构
- `FormatInfo` / `ColorTypeInfo` - 格式信息表，存储各像素格式的能力标志

### 3. GrMtlCommandBuffer (`GrMtlCommandBuffer.h` / `GrMtlCommandBuffer.mm`)

**职责**: 封装 `id<MTLCommandBuffer>`，管理编码器的生命周期和资源追踪。

**关键方法**:
- `Make(id<MTLCommandQueue>)` - 从命令队列创建命令缓冲区
- `commit(bool waitUntilCompleted)` - 提交命令缓冲区
- `getBlitCommandEncoder()` - 获取 Blit 命令编码器
- `getRenderCommandEncoder(MTLRenderPassDescriptor*, ...)` - 获取或复用渲染命令编码器
- `addGrBuffer(...)` / `addGrSurface(...)` - 追踪引用的 GPU 资源
- `encodeSignalEvent(...)` / `encodeWaitForEvent(...)` - 编码同步事件
- `isCompleted()` - 检查命令是否已执行完成

**设计要点**: 命令缓冲区内部维护了活动编码器（`fActiveBlitCommandEncoder` 和 `fActiveRenderCommandEncoder`），并尝试在连续渲染通道间复用编码器以减少开销。

### 4. GrMtlRenderCommandEncoder (`GrMtlRenderCommandEncoder.h`)

**职责**: 封装 `id<MTLRenderCommandEncoder>` 并追踪其状态变化，通过脏检查避免冗余的 Metal API 调用。这是一个纯头文件实现类。

**状态追踪包括**:
- 当前渲染管线状态 (`fCurrentRenderPipelineState`)
- 顶点/片段缓冲区及偏移 (`fCurrentVertexBuffer` / `fCurrentFragmentBuffer`)
- 纹理和采样器绑定 (`fCurrentTexture` / `fCurrentSampler`)
- 深度模板状态 (`fCurrentDepthStencilState`)
- 裁剪矩形 (`fCurrentScissorRect`)
- 三角形填充模式 (`fCurrentTriangleFillMode`)

**关键方法**: 所有的 `setXxx` 方法都包含脏检查逻辑，只在状态真正发生变化时才调用底层 Metal API，显著减少了 CPU 端的 API 调用开销。

### 5. GrMtlPipelineState (`GrMtlPipelineState.h` / `GrMtlPipelineState.mm`)

**职责**: 封装完整的渲染管线状态，包括 `MTLRenderPipelineState`、着色器程序实现、Uniform 数据管理等。

**关键方法**:
- `setData(GrMtlFramebuffer*, const GrProgramInfo&)` - 设置渲染目标和程序数据
- `setTextures(...)` / `bindTextures(...)` - 设置和绑定纹理
- `setDrawState(...)` - 配置绘制状态（混合颜色、深度模板等）
- `SetDynamicScissorRectState(...)` - 设置动态裁剪矩形（静态方法）

### 6. GrMtlPipelineStateBuilder (`GrMtlPipelineStateBuilder.h` / `GrMtlPipelineStateBuilder.mm`)

**职责**: 构建 `GrMtlPipelineState` 对象。继承自 `GrGLSLProgramBuilder`，负责着色器编译和管线状态对象组装。

**关键方法**:
- `CreatePipelineState(...)` - 静态工厂方法，创建管线状态
- `PrecompileShaders(...)` - 预编译着色器（写入 Apple 着色器缓存）
- `compileMtlShaderLibrary(...)` - 将 SkSL/MSL 编译为 `MTLLibrary`
- `storeShadersInCache(...)` - 将着色器存入持久化缓存

### 7. GrMtlResourceProvider (`GrMtlResourceProvider.h` / `GrMtlResourceProvider.mm`)

**职责**: GPU 资源的缓存与复用中心。管理管线状态缓存、采样器缓存、深度模板状态缓存和 MSAA 加载管线。

**关键方法**:
- `findOrCreateCompatiblePipelineState(...)` - 查找或创建兼容的管线状态
- `findOrCreateCompatibleDepthStencilState(...)` - 查找或创建深度模板状态
- `findOrCreateCompatibleSampler(...)` - 查找或创建采样器
- `findOrCreateMSAALoadPipeline(...)` - 查找或创建 MSAA 加载管线
- `precompileShader(...)` - 预编译着色器

**内部缓存结构**:
- `PipelineStateCache` (LRU 缓存) - 基于 `GrProgramDesc` 哈希的管线状态缓存
- `fSamplers` (`SkTDynamicHash`) - 采样器状态哈希表
- `fDepthStencilStates` (`SkTDynamicHash`) - 深度模板状态哈希表
- `fMSAALoadPipelines` - MSAA 加载管线数组

### 8. GrMtlOpsRenderPass (`GrMtlOpsRenderPass.h` / `GrMtlOpsRenderPass.mm`)

**职责**: 实现具体的渲染操作通道。继承自 `GrOpsRenderPass`，负责将 Ganesh 的绘制操作编码为 Metal 渲染命令。

**关键方法**:
- `onBindPipeline(...)` - 绑定渲染管线
- `onBindTextures(...)` - 绑定纹理
- `onBindBuffers(...)` - 绑定顶点/索引/实例缓冲区
- `onDraw(...)` / `onDrawIndexed(...)` / `onDrawInstanced(...)` - 各种绘制调用
- `onDrawIndirect(...)` / `onDrawIndexedIndirect(...)` - 间接绘制
- `onClear(...)` / `onClearStencilClip(...)` - 清除操作
- `submit()` - 提交渲染通道

### 9. GrMtlAttachment (`GrMtlAttachment.h` / `GrMtlAttachment.mm`)

**职责**: 封装 `id<MTLTexture>` 作为渲染附件使用。支持模板附件、MSAA 附件、普通纹理附件和外部包装附件。

**工厂方法**:
- `MakeStencil(...)` - 创建模板附件
- `MakeMSAA(...)` - 创建 MSAA 附件
- `MakeTexture(...)` - 创建纹理附件
- `MakeWrapped(...)` - 包装外部 Metal 纹理

### 10. GrMtlTexture / GrMtlRenderTarget / GrMtlTextureRenderTarget

**GrMtlTexture** (`GrMtlTexture.h`): 继承自 `GrTexture`，封装可采样的 Metal 纹理。内部使用 `GrMtlAttachment` 持有实际的 `id<MTLTexture>`。

**GrMtlRenderTarget** (`GrMtlRenderTarget.h`): 继承自 `GrRenderTarget`，表示可渲染的 Metal 目标。支持颜色附件 (`fColorAttachment`) 和解析附件 (`fResolveAttachment`)，并缓存 4 种帧缓冲区配置。

**GrMtlTextureRenderTarget** (`GrMtlTextureRenderTarget.h`): 通过菱形继承同时继承 `GrMtlTexture` 和 `GrMtlRenderTarget`，表示既可采样又可渲染的资源。

### 11. 其他关键类

| 类名 | 文件 | 职责 |
|------|------|------|
| `GrMtlBuffer` | `GrMtlBuffer.h/.mm` | 封装 `id<MTLBuffer>`，支持动态/静态缓冲区 |
| `GrMtlSampler` | `GrMtlSampler.h/.mm` | 封装 `id<MTLSamplerState>`，支持哈希缓存 |
| `GrMtlDepthStencil` | `GrMtlDepthStencil.h/.mm` | 封装 `id<MTLDepthStencilState>`，支持哈希缓存 |
| `GrMtlFramebuffer` | `GrMtlFramebuffer.h/.mm` | 帧缓冲区抽象，持有颜色/解析/模板附件 |
| `GrMtlRenderPipeline` | `GrMtlPipeline.h` | 封装 `id<MTLRenderPipelineState>`，继承 `GrManagedResource` |
| `GrMtlSemaphore` / `GrMtlEvent` | `GrMtlSemaphore.h/.mm` | 基于 `MTLEvent` 的 GPU 同步原语 |
| `GrMtlPipelineStateDataManager` | `GrMtlPipelineStateDataManager.h/.mm` | Uniform 缓冲区数据管理与上传 |
| `GrMtlUniformHandler` | `GrMtlUniformHandler.h/.mm` | 着色器 Uniform 变量声明与布局 |
| `GrMtlVaryingHandler` | `GrMtlVaryingHandler.h/.mm` | 着色器 Varying 变量处理 |
| `GrMtlTrampoline` | `GrMtlTrampoline.h/.mm` | C++ 与 Objective-C 的桥接跳板 |

## 依赖关系

### 上游依赖 (本目录被以下模块使用)

- `include/gpu/ganesh/mtl/` - 公共 API 头文件（`GrMtlBackendContext.h`、`GrMtlDirectContext.h`、`GrMtlTypes.h` 等）
- `src/gpu/ganesh/surface/` - Metal 表面创建 (`mtl_objc_srcs`)
- Skia 应用层通过 `GrDirectContexts::MakeMetal()` 创建 Metal 上下文

### 下游依赖 (本目录依赖的模块)

- **Ganesh 核心** (`src/gpu/ganesh/`): `GrGpu`、`GrCaps`、`GrOpsRenderPass`、`GrTexture`、`GrRenderTarget`、`GrAttachment`、`GrGpuBuffer`、`GrSemaphore`、`GrManagedResource` 等基类
- **GLSL 程序构建** (`src/gpu/ganesh/glsl/`): `GrGLSLProgramBuilder`、`GrGLSLUniformHandler`、`GrGLSLVaryingHandler`
- **SkSL 编译器** (`src/sksl/codegen/`): Metal 着色器代码生成 (`SkSLNativeShader`)
- **GPU 通用层** (`src/gpu/`): `GpuRefCnt`、暂存缓冲区管理等
- **核心库** (`src/core/` / `src/base/`): `SkLRUCache`、`SkTDynamicHash`、`SkChecksum`、`SkSpinlock` 等

### 外部框架依赖

- **Metal.framework** - Apple Metal 图形 API
- **MetalKit.framework** - Metal 辅助工具
- **Foundation.framework** - Apple 基础框架

## 设计模式分析

### 1. 工厂方法模式 (Factory Method)

几乎所有 GPU 资源类都采用静态工厂方法而非公开构造函数：

```cpp
// GrMtlGpu::Make() - 创建 GPU 设备
static std::unique_ptr<GrGpu> Make(const GrMtlBackendContext&,
                                    const GrContextOptions&,
                                    GrDirectContext*);

// GrMtlCommandBuffer::Make() - 创建命令缓冲区
static sk_sp<GrMtlCommandBuffer> Make(id<MTLCommandQueue> queue);

// GrMtlAttachment::MakeStencil/MakeMSAA/MakeTexture/MakeWrapped
static sk_sp<GrMtlAttachment> MakeStencil(GrMtlGpu*, SkISize, int, MTLPixelFormat);
```

### 2. 策略模式 (Strategy)

`GrMtlGpu` 中的表面复制操作支持多种策略，通过 `GrMtlCaps` 的能力查询在运行时选择最优方案：

- `copySurfaceAsBlit(...)` - 使用 Blit 命令编码器复制
- `copySurfaceAsResolve(...)` - 使用 MSAA 解析复制

### 3. 享元模式 (Flyweight) / 缓存模式

`GrMtlResourceProvider` 大量使用缓存来复用昂贵的 GPU 资源：

- `PipelineStateCache` - 基于 LRU 策略的管线状态缓存 (`SkLRUCache`)
- `fSamplers` - 采样器状态哈希表 (`SkTDynamicHash<GrMtlSampler, Key>`)
- `fDepthStencilStates` - 深度模板状态哈希表 (`SkTDynamicHash<GrMtlDepthStencil, Key>`)

### 4. 代理/包装模式 (Wrapper)

`GrMtlRenderCommandEncoder` 包装了 `id<MTLRenderCommandEncoder>`，在每次状态设置时进行脏检查，仅在状态变化时才真正调用 Metal API：

```cpp
void setRenderPipelineState(id<MTLRenderPipelineState> pso) {
    if (fCurrentRenderPipelineState != pso) {
        [fCommandEncoder setRenderPipelineState:pso];
        fCurrentRenderPipelineState = pso;
    }
}
```

### 5. 桥接模式 (Bridge)

`GrMtlTrampoline` 作为 C++ 代码和 Objective-C++ Metal 实现之间的桥接层。由于 Ganesh 核心是纯 C++ 代码，无法直接包含 `.mm` 头文件，因此通过 `GrMtlTrampoline` 间接调用：

```
GrDirectContext (C++) --> GrMtlTrampoline (C++ 接口) --> GrMtlGpu (ObjC++)
```

### 6. 资源引用计数管理

使用 Skia 的 `sk_sp<>` 智能指针和 `GrManagedResource` 基类进行 GPU 资源生命周期管理。`GrMtlCommandBuffer` 通过 `addGrBuffer()` / `addGrSurface()` 方法追踪命令缓冲区引用的资源，确保在命令执行完成前资源不被释放。

### 7. 模板方法模式 (Template Method)

`GrMtlGpu` 通过覆写 `GrGpu` 基类的虚函数来实现 Metal 特定逻辑。基类定义了 GPU 操作的流程骨架，子类填充具体实现：

```cpp
// 基类 GrGpu 定义接口
virtual sk_sp<GrTexture> onCreateTexture(...) = 0;
virtual bool onReadPixels(...) = 0;

// GrMtlGpu 提供 Metal 实现
sk_sp<GrTexture> onCreateTexture(...) override;
bool onReadPixels(...) override;
```

## 数据流

### 1. 上下文创建流程

```
应用程序
  |
  v
GrDirectContexts::MakeMetal(backendContext, options)
  |
  v
GrDirectContextPriv::Make(GrBackendApi::kMetal, options)
  |
  v
GrMtlTrampoline::MakeGpu(backendContext, options, direct)
  |
  v
GrMtlGpu::Make(backendContext, options, direct)
  |-- 获取 id<MTLDevice> 和 id<MTLCommandQueue>
  |-- 创建 GrMtlCaps（查询设备能力）
  |-- 初始化 GrMtlResourceProvider
  |-- 初始化 GrStagingBufferManager
  |-- 初始化 GrRingBuffer (Uniforms)
  v
返回 sk_sp<GrDirectContext>
```

### 2. 绘制命令执行流程

```
Ganesh 绘制操作
  |
  v
GrMtlGpu::onGetOpsRenderPass(renderTarget, ...)
  |-- 创建 GrMtlOpsRenderPass
  v
GrMtlOpsRenderPass::onBindPipeline(programInfo, drawBounds)
  |-- GrMtlResourceProvider::findOrCreateCompatiblePipelineState(desc, info)
  |   |-- PipelineStateCache::refPipelineState(desc, info)
  |   |   |-- [缓存未命中] GrMtlPipelineStateBuilder::CreatePipelineState(...)
  |   |   |   |-- SkSL 编译为 MSL
  |   |   |   |-- GrCompileMtlShaderLibrary() 编译 MTLLibrary
  |   |   |   |-- 创建 MTLRenderPipelineState
  |   |   |   v
  |   |   |-- [缓存命中] 返回已有 GrMtlPipelineState
  v
GrMtlOpsRenderPass::onDraw(vertexCount, baseVertex)
  |-- GrMtlRenderCommandEncoder::drawPrimitives(...)
  |   |-- [fCommandEncoder drawPrimitives:...]
  v
GrMtlGpu::submit(renderPass)
  |-- GrMtlOpsRenderPass::submit()
  v
GrMtlGpu::submitCommandBuffer(sync)
  |-- GrMtlCommandBuffer::commit(waitUntilCompleted)
  |   |-- [fCmdBuffer commit]
  v
GPU 异步执行
```

### 3. 纹理上传数据流

```
onWritePixels(surface, rect, colorType, texels[], mipLevelCount)
  |
  v
uploadToTexture(mtlTexture, rect, dataColorType, texels[], mipLevels)
  |
  |-- 获取 Blit 命令编码器: commandBuffer()->getBlitCommandEncoder()
  |
  |-- 对每个 mip 级别:
  |   |-- 从 StagingBufferManager 获取暂存缓冲区切片
  |   |-- 将像素数据复制到暂存缓冲区
  |   |-- 编码 copyFromBuffer:toTexture 命令
  |
  v
暂存缓冲区数据 --[GPU 异步]--> Metal 纹理 (Private 存储模式)
```

### 4. 像素回读数据流

```
onReadPixels(surface, rect, surfaceColorType, bufferColorType, buffer, rowBytes)
  |
  v
readOrTransferPixels(surface, rect, dstColorType, transferBuffer, offset, ...)
  |
  |-- GrGetMTLTextureFromSurface(surface) 获取源纹理
  |-- 获取 Blit 命令编码器
  |-- 编码 copyFromTexture:toBuffer 命令
  |-- submitCommandBuffer(kForce_SyncQueue) 同步等待完成
  |
  v
Metal 纹理 --[GPU 同步执行]--> 传输缓冲区 --> CPU 内存
```

## 平台特定说明

### GPU 家族分类

`GrMtlCaps` 将 Metal GPU 分为三个家族，影响能力查询和优化路径：

| GPU 家族 | 枚举值 | 说明 |
|----------|--------|------|
| Apple Silicon | `GPUFamily::kApple` | Apple 自研 GPU (A 系列 / M 系列芯片) |
| Mac (独立 GPU) | `GPUFamily::kMac` | macOS 上的 AMD/其他独立 GPU |
| Mac (Intel 集显) | `GPUFamily::kMacIntel` | macOS 上的 Intel 集成显卡 |

### Metal SDK 版本兼容

`GrMtlTypesPriv.h` 中通过宏检测 Metal SDK 版本：

- **macOS**: 最低要求 10.14 SDK (`GR_METAL_SDK_VERSION 210`)，最高支持 13.0+ (`GR_METAL_SDK_VERSION 300`)
- **iOS/tvOS**: 最低要求 12.0 SDK (`GR_METAL_SDK_VERSION 210`)，最高支持 16.0+ (`GR_METAL_SDK_VERSION 300`)

### 缓冲区对齐要求

不同 GPU 家族有不同的缓冲区对齐要求（来自 `GrMtlCaps::getMinBufferAlignment()`）：

- **Mac GPU (包括 Intel)**: 最小对齐 4 字节
- **Apple GPU (iOS/Apple Silicon)**: 最小对齐 1 字节

### MSAA 支持

- `storeAndMultisampleResolveSupport()` - 检查是否支持 `MTLStoreActionStoreAndMultisampleResolve`，该操作允许在单次存储操作中同时写入和解析 MSAA 附件
- `renderTargetSupportsDiscardableMSAA()` - 检查渲染目标是否支持可丢弃的 MSAA（memoryless 模式），这在 iOS 上特别重要以节省内存

### ARC 与 GR_NORETAIN

所有 `.mm` 文件使用 ARC 编译。为避免 ARC 在 Objective-C 方法调用时产生不必要的 retain/release 开销，使用了 `GR_NORETAIN` 宏（基于 `__attribute__((objc_externally_retained))`），该属性告诉编译器参数的内存管理由外部负责。

### API 可用性检查

代码中广泛使用 `@available` 和 `SK_API_AVAILABLE` 进行运行时 API 可用性检查，例如：

```objc
// MTLEvent 需要 macOS 10.14+ / iOS 12.0+
if (@available(macOS 10.14, iOS 12.0, tvOS 12.0, *)) {
    [fCmdBuffer encodeSignalEvent:event value:value];
}

// setVertexBufferOffset 需要 macOS 10.11+ / iOS 8.3+
if (@available(macOS 10.11, iOS 8.3, tvOS 9.0, *)) {
    [fCommandEncoder setVertexBufferOffset:offset atIndex:index];
}
```

### 着色器编译超时保护

`GrMtlUtil.h` 中的 `GrMtlNewLibraryWithSource()` 和 `GrMtlNewRenderPipelineStateWithDescriptor()` 函数替代了 Metal 标准的同步创建方法，添加了超时保护机制。这是因为 Metal 着色器编译可能在某些设备或驱动上耗时异常，Skia 通过超时避免了无限期阻塞。

## 相关文档与参考

### Skia 内部相关目录

- `include/gpu/ganesh/mtl/` - Metal 后端公共 API 头文件
- `include/gpu/mtl/` - 通用 Metal 类型定义
- `src/gpu/ganesh/` - Ganesh 渲染引擎核心
- `src/gpu/ganesh/glsl/` - GLSL 程序构建基础设施（被 Metal 后端复用）
- `src/sksl/codegen/` - SkSL 到 Metal Shading Language 的代码生成
- `src/gpu/ganesh/vk/` - Vulkan 后端（架构上与 Metal 后端高度对称）
- `src/gpu/ganesh/gl/` - OpenGL 后端
- `src/gpu/ganesh/d3d/` - Direct3D 12 后端

### Apple 官方文档

- [Metal Programming Guide](https://developer.apple.com/metal/)
- [Metal Best Practices Guide](https://developer.apple.com/library/archive/documentation/3DDrawing/Conceptual/MTLBestPracticesGuide/)
- [Metal Feature Set Tables](https://developer.apple.com/metal/Metal-Feature-Set-Tables.pdf)
- [Metal Shading Language Specification](https://developer.apple.com/metal/Metal-Shading-Language-Specification.pdf)

### 构建配置

构建 Metal 后端需要：
1. 在 Bazel 中依赖 `//src/gpu/ganesh/mtl:ganesh_metal`
2. 定义 `SK_METAL` 宏
3. 使用 `-fobjc-arc` 编译标志
4. 链接 `Metal.framework`、`MetalKit.framework`、`Foundation.framework`

### 注意事项

- Metal 后端仅在 Apple 平台（macOS、iOS、tvOS）上可用
- `GrMtlUniformHandler` 的实现基本上是从 `GrVkUniformHandler`（Vulkan 后端）复制而来，因为 SkSL Metal 代码生成器最初被设计为与 Vulkan 风格的 GLSL 兼容
- `GrMtlRenderCommandEncoder` 是纯头文件实现，所有方法都是内联的，以最大化状态追踪的性能
- 命令缓冲区的资源追踪（`addResource()`）当前被禁用（注释掉了），仅追踪 `GrBuffer` 和 `GrSurface`
