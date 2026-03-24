# Graphite Metal 后端 - Apple Metal GPU 渲染实现

## 概述

`src/gpu/graphite/mtl` 目录是 Skia Graphite 渲染引擎的 Apple Metal 后端实现。Graphite 是 Skia 的下一代 GPU 渲染架构，旨在替代旧的 Ganesh 后端，提供更现代、更高效的 GPU 加速渲染能力。本目录包含约 28 个源文件，全面实现了通过 Apple Metal API 进行 2D 图形渲染所需的全部基础设施。

Metal 是 Apple 专有的低级 GPU 编程框架，适用于 macOS、iOS 和 tvOS 平台。与 Vulkan 和 DirectX 12 类似，Metal 提供了对 GPU 硬件的低开销、细粒度控制。Graphite Metal 后端利用 Metal 的能力实现了高效的图形管线创建、命令缓冲区录制与提交、GPU 资源管理以及着色器编译等核心功能。

该后端遵循 Graphite 的统一后端抽象架构，所有 Metal 特定的类均继承自 `src/gpu/graphite` 中定义的基类。这种设计使得上层的绘制逻辑与底层 GPU API 完全解耦，同时又能充分利用 Metal API 的特性，如 Memoryless 存储模式、Framebuffer Fetch 等 Apple 平台独有的优化。

当前代码要求的最低系统版本为 macOS 10.15 和 iOS/tvOS 13.0。MSL（Metal Shading Language）版本支持范围从 1.2 到 2.3，其中 MSL 2.3 需要 macOS 11.0+ 或 iOS 14.0+ 才能使用 Framebuffer Fetch 等高级特性。编译时通过 `SKGPU_GRAPHITE_METAL_SDK_VERSION` 宏根据目标平台 SDK 版本自动选择合适的 MSL 版本。

## 架构图

```
+-------------------------------------------------------------------+
|                      Graphite 上层接口                              |
|  Context / Recorder / Surface / DrawPass / DispatchGroup           |
+-------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+------------------+  +----------------+  +------------------+
|  SharedContext   |  | QueueManager   |  | ResourceProvider |
|  (基类)          |  | (基类)          |  | (基类)            |
+------------------+  +----------------+  +------------------+
         |                    |                    |
         v                    v                    v
+------------------+  +----------------+  +------------------+
| MtlSharedContext |  | MtlQueueManager|  |MtlResourceProvider|
| - MTLDevice      |  | - MTLCommandQ  |  | - 创建纹理/缓冲区 |
| - MemoryAllocator|  | - 提交命令     |  | - 创建管线/采样器 |
| - DepthStencil缓存|  | - GPU捕获     |  | - MSAA管线缓存   |
+------------------+  +----------------+  +------------------+
         |                                         |
         v                                         v
+------------------+                    +---------------------+
|    MtlCaps       |                    |  GPU 资源对象         |
| - GPU族检测       |                    |                     |
| - 格式表初始化     |                    | MtlTexture          |
| - 能力查询        |                    | MtlBuffer           |
| - Pipeline Key   |                    | MtlSampler          |
+------------------+                    | MtlGraphicsPipeline |
                                        | MtlComputePipeline  |
                                        +---------------------+
+-------------------------------------------------------------------+
|                      命令录制层                                     |
|                                                                   |
|  MtlCommandBuffer                                                 |
|  +-------------------------------------------------------------+  |
|  | MtlRenderCommandEncoder  (渲染通道编码)                       |  |
|  | MtlComputeCommandEncoder (计算通道编码)                       |  |
|  | MtlBlitCommandEncoder    (数据拷贝编码)                       |  |
|  +-------------------------------------------------------------+  |
+-------------------------------------------------------------------+
         |
         v
+-------------------------------------------------------------------+
|                   Apple Metal Framework                            |
|  MTLDevice / MTLCommandQueue / MTLCommandBuffer / MTLLibrary      |
+-------------------------------------------------------------------+
```

## 目录结构

```
src/gpu/graphite/mtl/
|
|-- BUILD.bazel                    # Bazel 构建配置，定义 graphite_native_metal 目标
|
|-- 核心上下文与管理 ────────────────
|   |-- MtlSharedContext.h/.mm     # Metal 共享上下文，持有 MTLDevice 和全局状态
|   |-- MtlQueueManager.h/.mm     # 命令队列管理器，负责命令提交与 GPU 捕获
|   |-- MtlResourceProvider.h/.mm # 资源提供者，工厂方法创建各种 GPU 资源
|   |-- MtlCaps.h/.mm             # Metal 能力查询，GPU 族检测与格式支持表
|   |-- MtlGraphiteUtils.h/.mm    # 工具函数：Context 创建、着色器编译、格式转换
|
|-- 命令缓冲区与编码器 ────────────────
|   |-- MtlCommandBuffer.h/.mm    # 命令缓冲区，协调三种编码器的录制与提交
|   |-- MtlRenderCommandEncoder.h # 渲染命令编码器，封装 MTLRenderCommandEncoder
|   |-- MtlComputeCommandEncoder.h# 计算命令编码器，封装 MTLComputeCommandEncoder
|   |-- MtlBlitCommandEncoder.h   # 数据传输编码器，封装 MTLBlitCommandEncoder
|
|-- 管线对象 ────────────────────────
|   |-- MtlGraphicsPipeline.h/.mm # 图形管线：着色器编译、PSO 创建、混合/深度模板状态
|   |-- MtlComputePipeline.h/.mm  # 计算管线：计算着色器编译与 PSO 创建
|
|-- GPU 资源 ────────────────────────
|   |-- MtlTexture.h/.mm          # 纹理资源，支持创建与包装外部纹理
|   |-- MtlBuffer.h/.mm           # 缓冲区资源，支持多种存储模式
|   |-- MtlSampler.h/.mm          # 采样器资源，支持各种过滤与寻址模式
|
|-- 后端互操作 ──────────────────────
|   |-- MtlBackendTexture.mm      # BackendTexture 的 Metal 实现
|   |-- MtlBackendSemaphore.mm    # BackendSemaphore 的 Metal 实现（MTLEvent）
|   |-- MtlTextureInfo.mm         # MtlTextureInfo 实现，纹理格式与属性查询
```

## 关键类与函数

### MtlSharedContext（核心共享上下文）

**文件**: `MtlSharedContext.h` / `MtlSharedContext.mm`

`MtlSharedContext` 是整个 Metal 后端的核心入口点，继承自 `SharedContext`。它持有与所有录制器（Recorder）共享的全局状态：

```cpp
class MtlSharedContext final : public SharedContext {
public:
    static sk_sp<SharedContext> Make(const MtlBackendContext&, const ContextOptions&);

    id<MTLDevice> device() const;                    // Metal 设备对象
    skgpu::MtlMemoryAllocator* memoryAllocator() const; // GPU 内存分配器
    const MtlCaps& mtlCaps() const;                  // Metal 能力查询

    sk_cfp<id<MTLDepthStencilState>> getCompatibleDepthStencilState(
        const DepthStencilSettings&) const;          // 深度模板状态缓存

private:
    sk_cfp<id<MTLDevice>> fDevice;
    sk_sp<skgpu::MtlMemoryAllocator> fMemoryAllocator;
    THashMap<DepthStencilSettings, sk_cfp<id<MTLDepthStencilState>>> fDepthStencilStates;
};
```

关键设计要点：
- 在构造函数中预创建所有常见的深度模板状态（`kDirectDepthLessPass`、`kWindingStencilPass` 等），避免运行时的并发创建问题。
- 通过 `createGraphicsPipeline()` 虚函数委托给 `MtlGraphicsPipeline::Make()` 实现管线创建。
- 要求 macOS 10.15+ / iOS 13.0+，低于此版本会返回 nullptr。

### MtlCaps（能力查询）

**文件**: `MtlCaps.h` / `MtlCaps.mm`（44KB，目录中最大的文件）

`MtlCaps` 继承自 `Caps`，负责检测 GPU 硬件能力并构建像素格式支持表：

```cpp
class MtlCaps final : public Caps {
public:
    MtlCaps(const id<MTLDevice>, const ContextOptions&);

    bool isMac() const;    // Mac GPU（包括 Intel）
    bool isApple() const;  // Apple Silicon GPU
    bool isIntel() const;  // Intel GPU

private:
    enum class GPUFamily { kApple, kMac, kMacIntel };
    GPUFamily fGPUFamily;
    int fFamilyGroup;

    struct FormatInfo {
        enum { kTexturable_Flag, kRenderable_Flag, kMSAA_Flag, kResolve_Flag, kStorage_Flag };
        uint16_t fFlags;
        std::unique_ptr<ColorTypeInfo[]> fColorTypeInfos;
    };
    FormatInfo fFormatTable[kNumMtlFormats]; // Mac: 23 种格式, iOS: 21 种
};
```

GPU 族检测层次（由高到低）：
1. `MTLGPUFamilyApple7`（Apple Silicon M1/A14+）
2. `MTLGPUFamilyApple1-6`（iOS 专有）
3. `MTLGPUFamilyMac2` / `MTLGPUFamilyMac1`（旧款 Mac）
4. Intel GPU 通过设备名称字符串检测

### MtlCommandBuffer（命令缓冲区）

**文件**: `MtlCommandBuffer.h` / `MtlCommandBuffer.mm`（42KB）

`MtlCommandBuffer` 继承自 `CommandBuffer`，是命令录制的核心协调者。它管理三种命令编码器的生命周期并确保同一时间只有一个编码器处于活动状态：

```cpp
class MtlCommandBuffer final : public CommandBuffer {
public:
    static std::unique_ptr<MtlCommandBuffer> Make(id<MTLCommandQueue>,
                                                  const MtlSharedContext*,
                                                  MtlResourceProvider*);
    bool commit();
    bool isFinished();
    void waitUntilFinished();

private:
    // 渲染通道
    bool onAddRenderPass(const RenderPassDesc&, ...);
    void bindGraphicsPipeline(const GraphicsPipeline*);
    void draw(PrimitiveType, unsigned int baseVertex, unsigned int vertexCount);
    void drawIndexed(...);
    void drawInstanced(...);
    void drawIndexedInstanced(...);
    void drawIndirect(...);

    // 计算通道
    bool onAddComputePass(DispatchGroupSpan);
    void dispatchThreadgroups(const WorkgroupSize& global, const WorkgroupSize& local);

    // 数据拷贝
    bool onCopyBufferToBuffer(...);
    bool onCopyTextureToBuffer(...);
    bool onCopyBufferToTexture(...);
    bool onCopyTextureToTexture(...);

    sk_cfp<id<MTLCommandBuffer>> fCommandBuffer;
    sk_sp<MtlRenderCommandEncoder> fActiveRenderCommandEncoder;
    sk_sp<MtlComputeCommandEncoder> fActiveComputeCommandEncoder;
    sk_sp<MtlBlitCommandEncoder> fActiveBlitCommandEncoder;
};
```

### MtlRenderCommandEncoder（渲染命令编码器）

**文件**: `MtlRenderCommandEncoder.h`

该类封装 `MTLRenderCommandEncoder`，实现了智能状态缓存以减少冗余的 GPU 状态切换：

```cpp
class MtlRenderCommandEncoder : public Resource {
    // 状态缓存 - 仅在状态变化时才发送命令到 GPU
    void setRenderPipelineState(id<MTLRenderPipelineState> pso);  // 缓存 PSO
    void setFragmentTexture(id<MTLTexture> texture, NSUInteger index); // 缓存纹理绑定
    void setFragmentSamplerState(id<MTLSamplerState>, NSUInteger);     // 缓存采样器
    void setDepthStencilState(id<MTLDepthStencilState>);               // 缓存深度模板
    void setScissorRect(const MTLScissorRect&);                        // 缓存裁剪矩形
    void setTriangleFillMode(MTLTriangleFillMode);                     // 缓存填充模式

private:
    static constexpr int kMaxExpectedBuffers = 6;
    static constexpr int kMaxExpectedTextures = 16;
    id<MTLRenderPipelineState> fCurrentRenderPipelineState = nil;
    id<MTLTexture> fCurrentTexture[kMaxExpectedTextures];
    id<MTLSamplerState> fCurrentSampler[kMaxExpectedTextures];
};
```

### MtlComputeCommandEncoder（计算命令编码器）

**文件**: `MtlComputeCommandEncoder.h`

封装 `MTLComputeCommandEncoder`，同样实现了状态缓存优化。支持直接调度和间接调度两种模式：

```cpp
class MtlComputeCommandEncoder : public Resource {
    void setComputePipelineState(id<MTLComputePipelineState> pso);
    void setBuffer(id<MTLBuffer>, NSUInteger offset, NSUInteger index);
    void setTexture(id<MTLTexture>, NSUInteger index);
    void setSamplerState(id<MTLSamplerState>, NSUInteger index);
    void setThreadgroupMemoryLength(NSUInteger length, NSUInteger index); // 16字节对齐
    void dispatchThreadgroups(const WorkgroupSize& global, const WorkgroupSize& local);
    void dispatchThreadgroupsWithIndirectBuffer(...); // 间接调度
};
```

### MtlBlitCommandEncoder（数据传输编码器）

**文件**: `MtlBlitCommandEncoder.h`

封装 `MTLBlitCommandEncoder`，提供纹理与缓冲区之间的数据拷贝操作：

```cpp
class MtlBlitCommandEncoder : public Resource {
    void copyFromTexture(id<MTLTexture>, SkIRect srcRect, id<MTLBuffer>, ...);
    void copyFromBuffer(id<MTLBuffer>, ..., id<MTLTexture>, SkIRect dstRect, unsigned dstLevel);
    void copyTextureToTexture(id<MTLTexture> src, SkIRect, id<MTLTexture> dst, SkIPoint, int mip);
    void copyBufferToBuffer(id<MTLBuffer> src, size_t srcOffset, id<MTLBuffer> dst, ...);
    void fillBuffer(id<MTLBuffer>, size_t offset, size_t bytes, uint8_t value);
#ifdef SK_BUILD_FOR_MAC
    void synchronizeResource(id<MTLBuffer>);  // Mac 上的 Managed 模式同步
#endif
};
```

### MtlGraphicsPipeline（图形管线）

**文件**: `MtlGraphicsPipeline.h` / `MtlGraphicsPipeline.mm`（21KB）

图形管线的创建是一个多步骤过程：SkSL -> MSL 转换 -> 着色器库编译 -> PSO 创建。

```cpp
class MtlGraphicsPipeline final : public GraphicsPipeline {
public:
    // 标准图形管线缓冲区索引布局
    static constexpr unsigned int kIntrinsicUniformBufferIndex = 0;  // 内置 Uniform
    static constexpr unsigned int kCombinedUniformIndex = 1;         // Paint + RenderStep
    static constexpr unsigned int kStaticDataBufferIndex = 2;        // 静态顶点数据
    static constexpr unsigned int kAppendDataBufferIndex = 3;        // 追加顶点数据
    static constexpr unsigned int kGradientBufferIndex = 4;          // 渐变数据

    static sk_sp<MtlGraphicsPipeline> Make(const MtlSharedContext*, ...);
    static sk_sp<MtlGraphicsPipeline> MakeLoadMSAAPipeline(const MtlSharedContext*,
                                                           const RenderPassDesc&);

    id<MTLRenderPipelineState> mtlPipelineState() const;
    id<MTLDepthStencilState> mtlDepthStencilState() const;
    uint32_t stencilReferenceValue() const;

private:
    using MSLFunction = std::pair<id<MTLLibrary>, std::string>;
    sk_cfp<id<MTLRenderPipelineState>> fPipelineState;
    sk_cfp<id<MTLDepthStencilState>> fDepthStencilState;
    uint32_t fStencilReferenceValue;
};
```

`MakeLoadMSAAPipeline()` 方法创建一个特殊的内部管线，用于从 Resolve 纹理加载 MSAA 内容，其着色器以硬编码 MSL 字符串形式内嵌在源码中。

### MtlResourceProvider（资源提供者）

**文件**: `MtlResourceProvider.h` / `MtlResourceProvider.mm`

作为工厂类，负责创建所有 Metal 特定的 GPU 资源：

```cpp
class MtlResourceProvider final : public ResourceProvider {
public:
    sk_sp<MtlGraphicsPipeline> findOrCreateLoadMSAAPipeline(const RenderPassDesc&);

private:
    sk_sp<Texture> createTexture(SkISize, const TextureInfo&, std::string_view label);
    sk_sp<Texture> onCreateWrappedTexture(const BackendTexture&, std::string_view label);
    sk_sp<Buffer> createBuffer(size_t, BufferType, AccessPattern, std::string_view label);
    sk_sp<Sampler> createSampler(const SamplerDesc&);
    sk_sp<ComputePipeline> createComputePipeline(const ComputePipelineDesc&);

    THashMap<uint32_t, sk_sp<MtlGraphicsPipeline>> fLoadMSAAPipelines; // MSAA管线缓存
};
```

### MtlGraphiteUtils（工具函数）

**文件**: `MtlGraphiteUtils.h` / `MtlGraphiteUtils.mm`

提供全局工具函数：

```cpp
// 创建 Metal Graphite 上下文的入口
namespace ContextFactory {
    std::unique_ptr<Context> MakeMetal(const MtlBackendContext&, const ContextOptions&);
}

// 编译 MSL 着色器代码为 MTLLibrary
sk_cfp<id<MTLLibrary>> MtlCompileShaderLibrary(const MtlSharedContext*,
                                               std::string_view label,
                                               std::string_view msl,
                                               ShaderErrorHandler*);

// 像素格式双向转换
TextureFormat MTLPixelFormatToTextureFormat(MTLPixelFormat);
MTLPixelFormat TextureFormatToMTLPixelFormat(TextureFormat);
```

格式转换表 `MTL_FORMAT_MAPPING` 涵盖了 30 多种像素格式的映射关系，包括颜色格式（R8、RGBA8、BGRA8 等）、压缩格式（ETC2、BC1）、深度模板格式（D16、D32F、D24_S8 等）以及扩展格式（BGR10_XR、BGRA10_XR 等）。

## 依赖关系

### 内部依赖（Graphite 基类）

| Metal 类                  | 基类                       | 所在目录                    |
|---------------------------|----------------------------|-----------------------------|
| `MtlSharedContext`        | `SharedContext`            | `src/gpu/graphite/`        |
| `MtlCommandBuffer`       | `CommandBuffer`            | `src/gpu/graphite/`        |
| `MtlQueueManager`        | `QueueManager`             | `src/gpu/graphite/`        |
| `MtlResourceProvider`    | `ResourceProvider`         | `src/gpu/graphite/`        |
| `MtlCaps`                | `Caps`                     | `src/gpu/graphite/`        |
| `MtlGraphicsPipeline`    | `GraphicsPipeline`         | `src/gpu/graphite/`        |
| `MtlComputePipeline`     | `ComputePipeline`          | `src/gpu/graphite/`        |
| `MtlTexture`             | `Texture`                  | `src/gpu/graphite/`        |
| `MtlBuffer`              | `Buffer`                   | `src/gpu/graphite/`        |
| `MtlSampler`             | `Sampler`                  | `src/gpu/graphite/`        |
| `MtlRenderCommandEncoder`| `Resource`                 | `src/gpu/graphite/`        |
| `MtlComputeCommandEncoder`| `Resource`                | `src/gpu/graphite/`        |
| `MtlBlitCommandEncoder`  | `Resource`                 | `src/gpu/graphite/`        |

### 外部依赖

- **Apple Metal Framework** (`<Metal/Metal.h>`) - Metal GPU API
- **Apple Foundation Framework** - 基础对象管理
- **SkSL 编译器** (`src/sksl/`) - 着色器从 SkSL 编译到 MSL
- **`src/gpu/mtl/`** - 共享的 Metal 工具代码（`MtlUtilsPriv.h`、`MtlMemoryAllocatorImpl.h`）
- **`include/ports/SkCFObject.h`** - Core Foundation 对象的智能指针 `sk_cfp<>`
- **`include/gpu/graphite/mtl/`** - 公共 Metal 类型定义（`MtlBackendContext`、`MtlGraphiteTypes`）

### 构建依赖（BUILD.bazel）

```
sdk_frameworks = ["Foundation", "Metal"]
copts = ["-fno-objc-arc"]    # 禁用 ARC，使用手动引用计数管理
defines = ["SK_METAL"]
deps = ["//:core", "//src/gpu", "//src/gpu/graphite", "//src/gpu/mtl:gpu_mtl"]
```

注意：所有 `.mm` 文件使用 Objective-C++ 编写，通过 `-fno-objc-arc` 编译标志禁用自动引用计数。Metal 对象的生命周期通过 `sk_cfp<>` 智能指针和 `sk_ret_cfp()` 辅助函数手动管理。

## 设计模式分析

### 1. 工厂方法模式（Factory Method）

所有 GPU 资源类均使用静态 `Make()` 工厂方法创建实例，而非公开构造函数：

```cpp
// MtlTexture 提供两种工厂方法
static sk_sp<Texture> Make(const MtlSharedContext*, SkISize, const TextureInfo&, std::string_view);
static sk_sp<Texture> MakeWrapped(const MtlSharedContext*, SkISize, const TextureInfo&,
                                  sk_cfp<id<MTLTexture>>, std::string_view);
```

这种模式允许在对象创建失败时返回 `nullptr`，而不是抛出异常。

### 2. 模板方法模式（Template Method）

基类定义算法框架，Metal 子类实现具体步骤：

- `SharedContext::createGraphicsPipeline()` -> `MtlSharedContext` 调用 `MtlGraphicsPipeline::Make()`
- `ResourceProvider::createTexture()` -> `MtlResourceProvider` 调用 `MtlTexture::Make()`
- `CommandBuffer::onAddRenderPass()` -> `MtlCommandBuffer` 使用 `MtlRenderCommandEncoder`
- `QueueManager::onSubmitToGpu()` -> `MtlQueueManager` 调用 `MtlCommandBuffer::commit()`

### 3. 适配器模式（Adapter）

三种命令编码器类将 Objective-C 的 Metal API 适配为 C++ 接口：

```cpp
// MtlRenderCommandEncoder 将 Metal Objective-C 消息封装为 C++ 方法
void setRenderPipelineState(id<MTLRenderPipelineState> pso) {
    if (fCurrentRenderPipelineState != pso) {
        [(*fCommandEncoder) setRenderPipelineState:pso];
        fCurrentRenderPipelineState = pso;
    }
}
```

### 4. 状态缓存模式（State Caching / Dirty Tracking）

`MtlRenderCommandEncoder` 和 `MtlComputeCommandEncoder` 均维护当前绑定状态的缓存，仅在状态实际变更时才向 Metal 发送命令。这对于避免冗余的 GPU 状态切换至关重要：

- 管线状态（`fCurrentRenderPipelineState` / `fCurrentComputePipelineState`）
- 纹理绑定（`fCurrentTexture[]`，最多 16 个槽位）
- 采样器绑定（`fCurrentSampler[]`，最多 16 个槽位）
- 深度模板状态（`fCurrentDepthStencilState`）
- 裁剪矩形（`fCurrentScissorRect`）
- 模板参考值（`fCurrentStencilReferenceValue`）
- 三角形填充模式（`fCurrentTriangleFillMode`）

### 5. 享元模式（Flyweight）

`MtlSharedContext` 中的深度模板状态通过 `THashMap` 缓存，以 `DepthStencilSettings` 作为键。由于常见的深度模板配置数量有限，在构造时预创建所有配置可以避免运行时分配和并发问题：

```cpp
for (const DepthStencilSettings& dss : { kDirectDepthLessPass,
                                         kDirectDepthLEqualPass,
                                         kWindingStencilPass,
                                         kEvenOddStencilPass,
                                         kRegularCoverPass,
                                         kInverseCoverPass,
                                         kIgnoreDSS }) {
    this->createCompatibleDepthStencilState(dss);
}
```

### 6. 后端数据封装模式（Type Erasure + PIMPL）

`MtlBackendTextureData` 和 `MtlBackendSemaphoreData` 通过基类指针的方式将 Metal 特定数据嵌入到后端无关的 `BackendTexture` 和 `BackendSemaphore` 中：

```cpp
class MtlBackendTextureData final : public BackendTextureData {
    CFTypeRef fMtlTexture;
    void copyTo(AnyBackendTextureData& dstData) const override;
    bool equal(const BackendTextureData* that) const override;
};
```

## 数据流

### 1. 上下文初始化流程

```
ContextFactory::MakeMetal(backendContext, options)
    |
    +-> MtlSharedContext::Make(backendContext, options)
    |       |-> 检查 macOS 10.15+ / iOS 13.0+ 系统版本
    |       |-> new MtlCaps(device, options)
    |       |       |-> initGPUFamily(device)     // 检测 Apple/Mac/Intel GPU
    |       |       |-> initCaps(device)           // 初始化通用能力
    |       |       |-> initShaderCaps()           // 初始化着色器能力
    |       |       |-> initFormatTable(device)    // 构建像素格式支持表
    |       |
    |       |-> MtlMemoryAllocatorImpl::Make(device)
    |       |-> 构造 MtlSharedContext
    |       |       |-> 创建 MtlThreadSafeResourceProvider
    |       |       |-> 预创建 7 种深度模板状态
    |
    +-> new MtlQueueManager(queue, sharedContext)
    |
    +-> ContextCtorAccessor::MakeContext(sharedContext, queueManager, options)
```

### 2. 图形管线创建流程

```
MtlGraphicsPipeline::Make(sharedContext, runtimeDict, pipelineKey, pipelineDesc, renderPassDesc, ...)
    |
    +-> ShaderInfo::Make(caps, dictionary, runtimeDict, renderPassDesc, step, paintID)
    |       |-> 生成顶点着色器 SkSL
    |       |-> 生成片元着色器 SkSL
    |
    +-> SkSLToMSL(shaderCaps, fsSkSL, kGraphiteFragment, ...) -> fsMSL
    +-> SkSLToMSL(shaderCaps, vsSkSL, kGraphiteVertex, ...)   -> vsMSL
    |
    +-> MtlCompileShaderLibrary(sharedContext, vsLabel, vsMSL, errorHandler) -> vsLibrary
    +-> MtlCompileShaderLibrary(sharedContext, fsLabel, fsMSL, errorHandler) -> fsLibrary
    |
    +-> sharedContext->getCompatibleDepthStencilState(depthStencilSettings) -> dss
    |
    +-> Make(sharedContext, label, pipelineInfo, {vsLibrary, "vertexMain"}, ...,
    |        {fsLibrary, "fragmentMain"}, dss, stencilRefValue, blendInfo, renderPassDesc)
    |       |-> create_vertex_descriptor(appendStepFunc, staticAttrs, appendAttrs)
    |       |-> create_color_attachment(colorFormat, blendInfo)
    |       |-> [device newRenderPipelineStateWithDescriptor:desc error:&error] -> PSO
    |
    +-> return MtlGraphicsPipeline(sharedContext, pipelineInfo, label, pso, dss, stencilRefValue)
```

### 3. 渲染命令录制与提交流程

```
MtlQueueManager::getNewCommandBuffer(resourceProvider, Protected)
    |-> MtlCommandBuffer::Make(queue, sharedContext, resourceProvider)
        |-> createNewMTLCommandBuffer()
            |-> [queue commandBufferWithDescriptor:desc] (macOS 11.0+)
            |-> 或 [queue commandBufferWithUnretainedReferences] (较旧版本)

MtlCommandBuffer::onAddRenderPass(renderPassDesc, colorTex, resolveTex, dsTex, drawPasses)
    |-> beginRenderPass(renderPassDesc, colorTex, resolveTex, dsTex)
    |       |-> 配置 MTLRenderPassDescriptor（颜色/深度模板附件、load/store 动作）
    |       |-> MtlRenderCommandEncoder::Make(sharedContext, commandBuffer, descriptor)
    |
    |-> 对于每个 DrawPass:
    |       |-> addDrawPass(drawPass)
    |           |-> 遍历绘制命令列表
    |           |-> bindGraphicsPipeline() -> setRenderPipelineState / setDepthStencilState
    |           |-> bindUniformBuffer() -> setVertexBuffer / setFragmentBuffer
    |           |-> bindTextureAndSampler() -> setFragmentTexture / setFragmentSamplerState
    |           |-> setScissor() -> setScissorRect
    |           |-> draw() / drawIndexed() / drawInstanced() -> drawPrimitives / drawIndexedPrimitives
    |
    |-> endRenderPass()
        |-> [encoder endEncoding]

MtlQueueManager::onSubmitToGpu(submitInfo)
    |-> mtlCmdBuffer->commit()
    |       |-> endBlitCommandEncoder()  // 确保所有编码器已结束
    |       |-> [commandBuffer commit]
    |
    |-> return MtlWorkSubmission(cmdBuffer, queueManager)
```

### 4. 缓冲区内存管理流程

```
MtlBuffer::Make(sharedContext, size, type, accessPattern, label)
    |
    |-> 根据 accessPattern 和平台选择存储模式:
    |   |-> AccessPattern::kHostVisible + Mac GPU:
    |   |       MTLResourceStorageModeManaged (CPU/GPU 各一份，需手动同步)
    |   |-> AccessPattern::kHostVisible + Apple Silicon / iOS:
    |   |       MTLResourceStorageModeShared (统一内存，CPU/GPU 共享)
    |   |-> AccessPattern::kGpuOnly:
    |           MTLResourceStorageModePrivate (仅 GPU 可见)
    |
    |-> [device newBufferWithLength:size options:options]
    |
    |-> onMap():  fMapPtr = fBuffer.contents  (Private 模式下不可映射)
    |-> onUnmap(): Mac Managed 模式下调用 [fBuffer didModifyRange:] 同步
```

## 平台特定说明

### macOS 与 iOS/tvOS 的差异

| 特性                       | macOS                    | iOS / tvOS              |
|----------------------------|--------------------------|-------------------------|
| 最低支持版本                | 10.15                    | 13.0                    |
| GPU 族                     | Mac / MacIntel / Apple   | Apple                   |
| 像素格式数量                | 23 种                    | 21 种                   |
| BC1 压缩纹理               | 支持                     | 不支持                  |
| D24_S8 深度模板格式          | 部分设备支持              | 不支持                  |
| 缓冲区 Managed 存储模式     | 支持（Intel/AMD GPU）    | 不适用                  |
| Memoryless 存储模式         | macOS 11.0+（Apple GPU） | iOS 10.0+               |
| `synchronizeResource()`    | 需要（Managed 模式）      | 不需要                  |

### 条件编译宏

- **`SK_BUILD_FOR_MAC`**: 启用 Mac 特定代码路径（BC1 纹理、Managed 存储模式、资源同步）
- **`SK_BUILD_FOR_IOS`**: 启用 iOS 特定的 GPU 族检测（Apple1-6 系列）
- **`SK_METAL`**: 全局 Metal 后端启用标志
- **`SK_ENABLE_MTL_DEBUG_INFO`**: 启用 Metal 资源的调试标签设置
- **`GPU_TEST_UTILS`**: 启用 GPU 捕获功能（`startCapture()` / `stopCapture()`）
- **`SKGPU_GRAPHITE_METAL_SDK_VERSION`**: 根据目标平台 SDK 版本自动定义的 Metal SDK 版本号

### MSL 版本选择策略

着色器编译时根据系统版本选择 MSL 版本：

```
macOS 11.0+ / iOS 14.0+ -> MTLLanguageVersion2_3 (支持 Framebuffer Fetch)
macOS 10.13+ / iOS 11.0+ -> MTLLanguageVersion2_0 (支持 array<>)
iOS 10.0+ (仅 iOS) -> MTLLanguageVersion1_2 (array<> 基础支持)
```

### Apple Silicon 统一内存架构

在 Apple Silicon (Apple GPU 族) 设备上，CPU 与 GPU 共享统一内存（Unified Memory），因此：
- 缓冲区默认使用 `MTLStorageModeShared`，无需显式的 CPU-GPU 同步
- 支持 `MTLStorageModeMemoryless` 用于瞬态纹理（如 MSAA Resolve 中间纹理），可节省内存带宽

### 非 ARC 内存管理

Metal 后端使用 `-fno-objc-arc` 编译，通过 `sk_cfp<>` 模板和 `sk_ret_cfp()` 函数进行手动引用计数管理。这是 Skia 在 Objective-C 环境中的一贯做法，确保与 C++ RAII 模式的兼容性。典型用法如下：

```objc
// 对 autorelease 返回的对象显式 retain
sk_cfp<id<MTLRenderCommandEncoder>> encoder =
    sk_ret_cfp([commandBuffer renderCommandEncoderWithDescriptor:descriptor]);

// @autoreleasepool 确保中间 autorelease 对象及时释放
@autoreleasepool {
    sk_cfp<id<MTLBlitCommandEncoder>> encoder =
        sk_ret_cfp<id<MTLBlitCommandEncoder>>([commandBuffer blitCommandEncoder]);
}
```

## 相关文档与参考

### Skia 内部文档

- `src/gpu/graphite/` - Graphite 渲染引擎核心框架（基类定义）
- `src/gpu/graphite/dawn/` - Dawn/WebGPU 后端实现（对比参考）
- `src/gpu/graphite/vk/` - Vulkan 后端实现（对比参考）
- `src/gpu/mtl/` - 共享的 Metal 工具代码（Ganesh 和 Graphite 共用）
- `include/gpu/graphite/mtl/` - Metal 后端的公共 API 头文件
- `src/sksl/codegen/` - SkSL 到 MSL 的代码生成器

### Apple 官方文档

- [Metal Programming Guide](https://developer.apple.com/metal/) - Metal 编程指南
- [Metal Shading Language Specification](https://developer.apple.com/metal/Metal-Shading-Language-Specification.pdf) - MSL 规范
- [Metal Best Practices Guide](https://developer.apple.com/library/archive/documentation/3DDrawing/Conceptual/MTLBestPracticesGuide/) - Metal 最佳实践
- [Metal Feature Set Tables](https://developer.apple.com/metal/Metal-Feature-Set-Tables.pdf) - Metal 特性支持表
- [GPU Family 支持列表](https://developer.apple.com/documentation/metal/mtlgpufamily) - GPU 族与设备对应关系

### 关键概念

- **Graphite vs Ganesh**: Graphite 是 Skia 的下一代 GPU 后端架构，旨在提供更好的多线程支持和更低的 CPU 开销。Ganesh 是旧的 GPU 后端，位于 `src/gpu/ganesh/`。
- **SharedContext**: 跨线程共享的上下文，持有 GPU 设备和全局缓存。
- **Recorder**: 线程本地的命令录制器，可以在多个线程上并行录制绘制命令。
- **DrawPass**: 一组共享相同渲染目标配置的绘制命令集合。
- **RenderStep**: 定义特定几何类型渲染方式的步骤描述。
- **SkSL**: Skia 的着色器语言，会被编译为目标平台的原生着色器语言（本后端为 MSL）。
