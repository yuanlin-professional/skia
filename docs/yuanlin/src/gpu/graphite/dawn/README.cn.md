# Dawn (WebGPU) 后端 - Skia Graphite 渲染引擎的 Dawn/WebGPU 实现

## 概述

本目录 (`src/gpu/graphite/dawn/`) 包含 Skia Graphite 渲染引擎的 **Dawn/WebGPU 后端**实现。Dawn 是 Google 开发的开源 WebGPU 实现，提供了跨平台的现代图形 API 抽象层。该后端使 Skia 能够通过 WebGPU 标准接口驱动底层图形硬件（Vulkan、Metal、Direct3D 12、OpenGL 等），同时还支持在浏览器环境中通过 Emscripten/WASM 运行。

Graphite 是 Skia 的下一代 GPU 渲染架构，旨在取代旧版 Ganesh 后端。与 Ganesh 不同，Graphite 采用了更现代的设计理念：预编译管线状态对象（PSO）、显式资源管理、以及工作负载的录制与回放分离。Dawn 后端是 Graphite 中最重要的后端之一，因为它能够同时服务于原生桌面应用（通过 Dawn Native）和 Web 应用（通过 WebGPU/Emscripten）。

该后端总共包含约 29 个源文件（14 个 `.cpp` 实现文件、13 个 `.h` 头文件、1 个 `BUILD.bazel` 构建文件、以及 1 个 `DawnTextureInfo.cpp` 纯实现文件），涵盖了从上下文初始化、能力查询、资源创建、管线构建、命令录制到工作提交的完整 GPU 渲染管线。代码中大量使用了 `#if defined(__EMSCRIPTEN__)` 条件编译，以处理 Dawn Native 和 WebGPU/WASM 之间的 API 差异。

本后端的核心设计目标是将 Skia Graphite 的抽象 GPU 接口映射到 WebGPU API（`wgpu::*` 类型），同时针对 Dawn 的特性进行优化，例如异步管线创建、瞬态附件（transient attachments）、以及 MSAA 解析纹理加载等。

## 架构图

```
                        ┌─────────────────────────────────────────────┐
                        │          Skia Graphite 公共 API              │
                        │   (Context, Recorder, Surface, Image)       │
                        └────────────────────┬────────────────────────┘
                                             │
                        ┌────────────────────▼────────────────────────┐
                        │       Graphite 核心抽象层                    │
                        │  SharedContext / ResourceProvider /          │
                        │  CommandBuffer / Caps / QueueManager        │
                        └────────────────────┬────────────────────────┘
                                             │ 继承与实现
                ┌────────────────────────────▼────────────────────────────┐
                │              Dawn 后端实现 (本目录)                       │
                │                                                         │
                │  ┌──────────────────┐    ┌──────────────────────┐      │
                │  │ DawnSharedContext │───▶│ DawnCaps             │      │
                │  │ (设备/队列/实例)   │    │ (能力查询/格式表)     │      │
                │  └────────┬─────────┘    └──────────────────────┘      │
                │           │                                             │
                │  ┌────────▼─────────┐    ┌──────────────────────┐      │
                │  │DawnResourceProvider│──▶│ DawnTexture          │      │
                │  │ (资源创建/缓存)    │   │ DawnBuffer           │      │
                │  │                    │   │ DawnSampler          │      │
                │  └────────┬──────────┘   │ DawnGraphicsPipeline │      │
                │           │              │ DawnComputePipeline   │      │
                │  ┌────────▼──────────┐   └──────────────────────┘      │
                │  │DawnCommandBuffer  │                                  │
                │  │ (命令录制/编码)    │   ┌──────────────────────┐      │
                │  └────────┬──────────┘   │ DawnAsyncWait        │      │
                │           │              │ DawnErrorChecker      │      │
                │  ┌────────▼──────────┐   │ DawnGraphiteUtils    │      │
                │  │ DawnQueueManager  │   └──────────────────────┘      │
                │  │ (工作提交/同步)    │                                  │
                │  └───────────────────┘                                  │
                └─────────────────────────────────────────────────────────┘
                                             │
                        ┌────────────────────▼────────────────────────┐
                        │           Dawn / WebGPU API 层               │
                        │   wgpu::Device, wgpu::Queue, wgpu::Buffer,  │
                        │   wgpu::Texture, wgpu::RenderPipeline ...   │
                        └────────────────────┬────────────────────────┘
                                             │
                ┌────────────────────────────▼────────────────────────────┐
                │              底层图形驱动                                │
                │     Vulkan / Metal / Direct3D 12 / OpenGL              │
                │     (Dawn Native) 或 浏览器 WebGPU (Emscripten)        │
                └─────────────────────────────────────────────────────────┘
```

## 目录结构

```
src/gpu/graphite/dawn/
├── BUILD.bazel                  # Bazel 构建规则定义
│
├── DawnSharedContext.h/.cpp      # 共享上下文：持有 wgpu::Device/Queue/Instance
├── DawnCaps.h/.cpp               # 能力查询：格式支持、特性检测、管线键生成
├── DawnResourceProvider.h/.cpp   # 资源提供者：创建和缓存 GPU 资源
├── DawnQueueManager.h/.cpp       # 队列管理：命令缓冲区提交和 GPU 工作同步
├── DawnCommandBuffer.h/.cpp      # 命令缓冲区：录制渲染/计算/拷贝命令
│
├── DawnGraphicsPipeline.h/.cpp   # 图形管线：渲染管线状态对象管理
├── DawnComputePipeline.h/.cpp    # 计算管线：计算着色器管线管理
│
├── DawnTexture.h/.cpp            # 纹理资源：wgpu::Texture 封装与视图管理
├── DawnBuffer.h/.cpp             # 缓冲区资源：wgpu::Buffer 封装与映射管理
├── DawnSampler.h/.cpp            # 采样器资源：wgpu::Sampler 封装
├── DawnBackendTexture.cpp        # 后端纹理数据：BackendTexture 的 Dawn 特化
├── DawnTextureInfo.cpp           # 纹理信息：DawnTextureInfo 方法实现
│
├── DawnAsyncWait.h/.cpp          # 异步等待工具：封装 Dawn 的异步操作同步
├── DawnErrorChecker.h/.cpp       # 错误检查工具：作用域内 Dawn 错误捕获
└── DawnGraphiteUtils.h/.cpp      # 工具函数：Context 工厂、着色器编译、格式转换
```

## 关键类与函数

### 1. DawnSharedContext (共享上下文)

**文件**: `DawnSharedContext.h` / `DawnSharedContext.cpp`

`DawnSharedContext` 继承自 `SharedContext`，是整个 Dawn 后端的核心入口。它持有 Dawn 设备相关的全局状态，在所有 `Recorder` 之间共享。

```cpp
class DawnSharedContext final : public SharedContext {
public:
    static sk_sp<SharedContext> Make(const DawnBackendContext&, const ContextOptions&);

    const wgpu::Device& device() const;    // WebGPU 逻辑设备
    const wgpu::Queue& queue() const;      // 默认 GPU 命令队列
    const wgpu::Instance& instance() const; // WebGPU 实例（用于事件处理）
    const wgpu::ShaderModule& noopFragment() const; // 空操作片段着色器

    void tick() const;      // 推进 Dawn 事件循环
    void deviceTick(Context*) override; // 设备级别 tick

    // 预创建的 BindGroupLayout（全局共享以减少管线创建开销）
    const wgpu::BindGroupLayout& getUniformBuffersBindGroupLayout() const;
    const wgpu::BindGroupLayout& getSingleTextureSamplerBindGroupLayout() const;
};
```

**关键设计要点**:
- 持有一个 "noop" 空片段着色器 (`fNoopFragment`)，用于解决 Dawn 的验证错误——Dawn 不允许管线有颜色附件但没有片段着色器。
- 预创建并缓存了两个 `wgpu::BindGroupLayout`：一个用于 Uniform 缓冲区（包含固有常量、合并 uniform、渐变缓冲区三个绑定），另一个用于单纹理+采样器对。
- `DawnTickFunction` 机制允许调用者自定义事件循环推进方式。在 Dawn Native 环境下默认调用 `instance.ProcessEvents()`；在 Emscripten 环境下可通过异步 JS 实现。
- 同时管理一个 `DawnThreadSafeResourceProvider`，用于线程安全的资源访问。

### 2. DawnCaps (能力查询)

**文件**: `DawnCaps.h` / `DawnCaps.cpp`

`DawnCaps` 继承自 `Caps`，负责查询和缓存 Dawn 设备的能力信息。它是后端决策的核心依据。

```cpp
class DawnCaps final : public Caps {
public:
    DawnCaps(const DawnBackendContext&, const ContextOptions&);

    bool supportsHalfPrecision() const;        // 半精度浮点支持
    bool useAsyncPipelineCreation() const;     // 异步管线创建
    bool allowScopedErrorChecks() const;       // 作用域错误检查
    bool supportsCommandBufferTimestamps() const; // 时间戳查询
    bool emulateLoadStoreResolve() const;      // 模拟 MSAA 加载/存储/解析

    std::optional<wgpu::LoadOp> resolveTextureLoadOp() const; // MSAA 解析纹理加载操作

    UniqueKey makeGraphicsPipelineKey(...) const; // 生成图形管线缓存键
    UniqueKey makeComputePipelineKey(...) const;  // 生成计算管线缓存键
};
```

**内部数据结构**:
- `FormatInfo` 结构体：为每种 `wgpu::TextureFormat` 存储标志位（可纹理采样、可渲染、支持 MSAA、支持解析、支持存储）和颜色类型映射表。
- `fFormatTable`：包含 31 种纹理格式的查询表，通过 `GetFormatIndex()` 进行快速索引。
- 初始化分三步：`initCaps()`（通用能力）、`initShaderCaps()`（着色器能力）、`initFormatTable()`（格式支持表）。

### 3. DawnCommandBuffer (命令缓冲区)

**文件**: `DawnCommandBuffer.h` / `DawnCommandBuffer.cpp`

`DawnCommandBuffer` 继承自 `CommandBuffer`，是 Dawn 后端中最复杂的类之一（约 58K 代码），负责将 Graphite 的高层渲染命令翻译为 WebGPU 命令。

```cpp
class DawnCommandBuffer final : public CommandBuffer {
public:
    static std::unique_ptr<DawnCommandBuffer> Make(const DawnSharedContext*,
                                                    DawnResourceProvider*);
    wgpu::CommandBuffer finishEncoding(); // 完成编码，返回可提交的命令缓冲区

private:
    // 渲染通道相关
    bool beginRenderPass(...);   // 开始渲染通道
    bool endRenderPass();        // 结束渲染通道
    bool addDrawPass(DrawPass*); // 添加绘制通道

    // 绘制命令
    void draw(PrimitiveType, unsigned int baseVertex, unsigned int vertexCount);
    void drawIndexed(...);
    void drawInstanced(...);
    void drawIndexedInstanced(...);
    void drawIndirect(...);

    // 计算通道相关
    void beginComputePass();
    void bindComputePipeline(const ComputePipeline*);
    void dispatchWorkgroups(const WorkgroupSize&);
    void endComputePass();

    // 数据拷贝
    bool onCopyBufferToBuffer(...);
    bool onCopyTextureToBuffer(...);
    bool onCopyBufferToTexture(...);
    bool onCopyTextureToTexture(...);
};
```

**关键实现细节**:
- 内部维护 `wgpu::CommandEncoder`、`wgpu::RenderPassEncoder` 和 `wgpu::ComputePassEncoder` 三级编码器。
- 支持 MSAA 解析纹理的模拟加载 (`emulateLoadMSAAFromResolveAndBeginRenderPassEncoder`)：当 Dawn 不原生支持从解析纹理加载时，使用绘制调用进行 Blit 操作。
- 支持 GPU 时间戳查询 (`fTimestampQuerySet`, `fTimestampQueryBuffer`) 用于性能统计。
- 通过 `syncUniformBuffers()` 在绘制前同步 Uniform 缓冲区的绑定状态，采用延迟绑定策略减少冗余操作。
- Uniform 缓冲区绑定组包含 3 个缓冲区：固有常量（索引 0）、合并 uniform（索引 1）、渐变缓冲区（索引 2）。

### 4. DawnResourceProvider (资源提供者)

**文件**: `DawnResourceProvider.h` / `DawnResourceProvider.cpp`

`DawnResourceProvider` 继承自 `ResourceProvider`，负责创建和缓存所有 Dawn 后端的 GPU 资源。

```cpp
class DawnResourceProvider final : public ResourceProvider {
public:
    // Blit 绘制编码器，用于 MSAA 解析模拟
    class BlitWithDrawEncoder { ... };

    // 资源查找与创建
    sk_sp<DawnTexture> findOrCreateDiscardableMSAALoadTexture(...);
    sk_sp<DawnBuffer> findOrCreateDawnBuffer(...);
    BlitWithDrawEncoder findOrCreateBlitWithDrawEncoder(...);

    // 绑定组缓存
    const wgpu::BindGroup& findOrCreateUniformBuffersBindGroup(...);
    const wgpu::BindGroup& findOrCreateSingleTextureSamplerBindGroup(...);

    // 固有常量管理
    BindBufferInfo findOrCreateIntrinsicBindBufferInfo(...);
    void releasePendingIntrinsicBuffers();
};
```

**缓存机制**:
- `fUniformBufferBindGroupCache`：基于 LRU 策略的 Uniform 绑定组缓存，键由缓冲区指针和绑定大小的组合构成。
- `fSingleTextureSamplerBindGroups`：单纹理+采样器绑定组的 LRU 缓存。
- `fBlitWithDrawPipelines`：Blit 渲染管线的哈希映射缓存，键由渲染通道描述生成。
- `fNullBuffer`：一个空缓冲区，用于填充未使用的绑定槽位以满足 WebGPU 验证要求。
- `IntrinsicConstantsManager`：管理固有常量缓冲区的分配与复用。

### 5. DawnGraphicsPipeline (图形管线)

**文件**: `DawnGraphicsPipeline.h` / `DawnGraphicsPipeline.cpp`

`DawnGraphicsPipeline` 继承自 `GraphicsPipeline`，封装了 `wgpu::RenderPipeline` 对象。

```cpp
class DawnGraphicsPipeline final : public GraphicsPipeline {
public:
    // 绑定组和缓冲区布局常量
    static constexpr unsigned int kUniformBufferBindGroupIndex = 0;
    static constexpr unsigned int kTextureBindGroupIndex = 1;
    static constexpr unsigned int kBindGroupCount = 2;

    static constexpr unsigned int kIntrinsicUniformBufferIndex = 0;
    static constexpr unsigned int kCombinedUniformIndex = 1;
    static constexpr unsigned int kGradientBufferIndex = 2;
    static constexpr unsigned int kNumUniformBuffers = 3;

    static constexpr unsigned int kIntrinsicUniformSize = 32;

    static sk_sp<DawnGraphicsPipeline> Make(...);

    const wgpu::RenderPipeline& dawnRenderPipeline() const;
    std::optional<std::string> didAsyncCompilationFail() const override;
};
```

**管线布局设计**:
- **绑定组 0** (`kUniformBufferBindGroupIndex`): 包含 3 个 Uniform/Storage 缓冲区，全部使用动态偏移。
- **绑定组 1** (`kTextureBindGroupIndex`): 纹理和采样器绑定。
- **顶点缓冲区**: 使用 2 个槽位——静态数据缓冲区（索引 0）和追加数据缓冲区（索引 1）。
- 支持**异步管线创建** (`AsyncPipelineCreation`)：在管线编译完成前可以检查失败状态。
- 支持**不可变采样器** (`fImmutableSamplers`)：持有不可变采样器的引用以管理生命周期。

### 6. DawnTexture (纹理)

**文件**: `DawnTexture.h` / `DawnTexture.cpp`

```cpp
class DawnTexture : public Texture {
public:
    static sk_sp<Texture> Make(...);           // 创建新纹理
    static sk_sp<Texture> MakeWrapped(...);    // 包装外部 WGPUTexture
    static sk_sp<Texture> MakeWrapped(...);    // 包装外部 WGPUTextureView

    const wgpu::Texture& dawnTexture() const;
    const wgpu::TextureView& sampleTextureView() const;  // 采样用视图
    const wgpu::TextureView& renderTextureView() const;   // 渲染用视图
};
```

**双视图设计**: 每个 `DawnTexture` 维护两个 `wgpu::TextureView`——一个用于着色器采样（`fSampleTextureView`），一个用于作为渲染目标附件（`fRenderTextureView`）。这两个视图的格式可能不同（例如 sRGB 视图 vs 线性视图）。

### 7. DawnBuffer (缓冲区)

**文件**: `DawnBuffer.h` / `DawnBuffer.cpp`

```cpp
class DawnBuffer final : public Buffer {
public:
    static sk_sp<DawnBuffer> Make(const DawnSharedContext*, size_t,
                                   BufferType, AccessPattern, std::string_view label);
    bool isUnmappable() const override;
    const wgpu::Buffer& dawnBuffer() const;

private:
    void onAsyncMap(GpuFinishedProc, GpuFinishedContext) override;  // 异步映射
    void onMap() override;       // 同步映射
    void onUnmap() override;     // 取消映射
};
```

**映射策略**: 支持创建时映射（`MapAtCreation`）以及异步映射回调。在 Emscripten 环境和 Dawn Native 环境使用不同的回调 API。通过 `fAsyncMapCallbacks` 管理异步映射回调链，使用 `SingleOwner` 保证线程安全。

### 8. DawnAsyncWait (异步等待)

**文件**: `DawnAsyncWait.h` / `DawnAsyncWait.cpp`

```cpp
class DawnAsyncWait {
public:
    bool yieldAndCheck() const;  // 让出执行权并检查是否完成
    bool mayBusyWait() const;    // 是否允许忙等待
    void busyWait() const;       // 忙等待直到信号
    void signal();               // 标记完成
    void reset();                // 重置状态
};

template <typename T>
class DawnAsyncResult {
public:
    void set(const T& result);        // 设置结果并发出信号
    const T* getIfReady() const;      // 非阻塞获取
    const T& waitAndGet() const;      // 阻塞等待并获取
};
```

`DawnAsyncWait` 是一个轻量级同步原语，封装了 Dawn 的异步操作等待逻辑。`yieldAndCheck()` 会调用 `tick()` 推进事件循环后检查信号状态；`busyWait()` 则持续循环直到操作完成。`DawnAsyncResult<T>` 模板类在此基础上增加了结果值的存储。

### 9. DawnErrorChecker (错误检查器)

**文件**: `DawnErrorChecker.h` / `DawnErrorChecker.cpp`

```cpp
enum class DawnErrorType : uint32_t {
    kNoError     = 0b00000000,
    kValidation  = 0b00000001,
    kOutOfMemory = 0b00000010,
    kInternal    = 0b00000100,
};

class DawnErrorChecker {
public:
    explicit DawnErrorChecker(const DawnSharedContext*);
    ~DawnErrorChecker();  // 析构时断言无错误
    SkEnumBitMask<DawnErrorType> popErrorScopes();
};
```

**RAII 模式**: 构造时自动推入三个错误作用域（Validation、OutOfMemory、Internal），析构时自动弹出并断言没有未处理的错误。在 Emscripten 环境下使用旧式回调 API，在 Dawn Native 环境下使用 `wgpu::Future` 机制。

### 10. DawnGraphiteUtils (工具函数)

**文件**: `DawnGraphiteUtils.h` / `DawnGraphiteUtils.cpp`

```cpp
// Context 工厂方法
namespace ContextFactory {
    std::unique_ptr<Context> MakeDawn(const DawnBackendContext&, const ContextOptions&);
}

// SkSL -> WGSL 着色器编译
bool SkSLToWGSL(const SkSL::ShaderCaps*, const std::string& sksl, ...);
bool DawnCompileWGSLShaderModule(const DawnSharedContext*, const char* label,
                                  const SkSL::NativeShader& wgsl, wgpu::ShaderModule*,
                                  ShaderErrorHandler*);

// 纹理格式转换
TextureFormat DawnFormatToTextureFormat(wgpu::TextureFormat);
wgpu::TextureFormat TextureFormatToDawnFormat(TextureFormat);
SkTextureCompressionType DawnFormatToCompressionType(wgpu::TextureFormat);

// YCbCr 描述符工具（仅 Dawn Native）
bool DawnDescriptorIsValid(const wgpu::YCbCrVkDescriptor&);
ImmutableSamplerInfo DawnDescriptorToImmutableSamplerInfo(const wgpu::YCbCrVkDescriptor&);
```

## 依赖关系

### 上游依赖（本目录被以下模块使用）

| 模块 | 关系说明 |
|------|---------|
| `include/gpu/graphite/dawn/` | 公共 API 头文件，定义 `DawnBackendContext`、`DawnTextureInfo`、`DawnGraphiteTypes` |
| `src/gpu/graphite/` | Graphite 核心框架，通过虚函数表调用 Dawn 后端实现 |
| Skia 用户代码 | 通过 `ContextFactory::MakeDawn()` 创建 Dawn 上下文 |

### 下游依赖（本目录依赖以下模块）

| 模块 | 关系说明 |
|------|---------|
| `src/gpu/graphite/SharedContext.h` | 基类 `SharedContext` |
| `src/gpu/graphite/Caps.h` | 基类 `Caps` |
| `src/gpu/graphite/CommandBuffer.h` | 基类 `CommandBuffer` |
| `src/gpu/graphite/ResourceProvider.h` | 基类 `ResourceProvider` |
| `src/gpu/graphite/QueueManager.h` | 基类 `QueueManager` |
| `src/gpu/graphite/GraphicsPipeline.h` | 基类 `GraphicsPipeline` |
| `src/gpu/graphite/ComputePipeline.h` | 基类 `ComputePipeline` |
| `src/gpu/graphite/Texture.h` | 基类 `Texture` |
| `src/gpu/graphite/Buffer.h` | 基类 `Buffer` |
| `src/gpu/graphite/Sampler.h` | 基类 `Sampler` |
| `src/gpu/graphite/DrawPass.h` | 绘制通道命令 |
| `src/gpu/graphite/compute/DispatchGroup.h` | 计算调度组 |
| `src/sksl/` | SkSL 着色器编译器（SkSL -> WGSL） |

### 外部依赖

| 库 | 关系说明 |
|----|---------|
| `webgpu/webgpu_cpp.h` | WebGPU C++ 绑定头文件，提供所有 `wgpu::*` 类型 |
| Dawn Native | 非 Emscripten 环境下的 WebGPU 实现 |
| Emscripten WebGPU | `__EMSCRIPTEN__` 环境下的 WebGPU 绑定 |

## 设计模式分析

### 1. 策略模式 (Strategy Pattern)

整个 Dawn 后端本身就是策略模式的体现。Graphite 核心通过抽象基类（`SharedContext`、`Caps`、`CommandBuffer` 等）定义接口，Dawn 后端作为具体策略提供实现。这使得同一套 Graphite 渲染代码可以无缝切换到 Vulkan、Metal 等其他后端。

### 2. 工厂方法模式 (Factory Method)

- `ContextFactory::MakeDawn()` 是顶层工厂方法，创建完整的 Dawn 渲染上下文。
- `DawnSharedContext::Make()` 使用静态工厂方法创建共享上下文。
- `DawnGraphicsPipeline::Make()`、`DawnComputePipeline::Make()` 等资源类均使用静态工厂方法。
- `DawnSharedContext::makeResourceProvider()` 作为虚工厂方法，创建 Dawn 特化的资源提供者。

### 3. RAII 模式 (Resource Acquisition Is Initialization)

- `DawnErrorChecker`：构造时推入错误作用域，析构时弹出并验证。
- `DawnAsyncResult<T>`：析构时确保异步操作已完成。
- 所有 GPU 资源类通过 `sk_sp<>` 智能指针管理，析构时调用 `freeGpuData()` 释放 GPU 资源。

### 4. 享元模式 (Flyweight Pattern) / 缓存模式

- `DawnResourceProvider` 中的 `BindGroupCache` 通过 LRU 缓存减少重复创建绑定组。
- `DawnSharedContext` 预创建并共享 `BindGroupLayout`，避免每条管线重复创建。
- `fBlitWithDrawPipelines` 缓存 Blit 渲染管线，避免重复编译。

### 5. 模板方法模式 (Template Method)

`CommandBuffer` 基类定义了渲染流程的骨架（`addRenderPass` -> `beginRenderPass` -> `addDrawPass` -> `endRenderPass`），`DawnCommandBuffer` 重写各个钩子方法以实现 Dawn 特定逻辑。

### 6. 适配器模式 (Adapter Pattern)

整个后端可以视为 Graphite API 到 WebGPU API 的适配器。例如：
- `SkFilterMode` / `SkTileMode` 到 `wgpu::FilterMode` / `wgpu::AddressMode` 的转换。
- `TextureFormat` 到 `wgpu::TextureFormat` 的双向映射。
- `DawnBackendTextureData` 将 `WGPUTexture` / `WGPUTextureView` 适配到 Skia 的 `BackendTexture` 体系。

## 数据流

### 渲染帧的完整数据流

```
1. 上下文初始化:
   DawnBackendContext (wgpu::Device, Queue, Instance)
     → ContextFactory::MakeDawn()
       → DawnSharedContext::Make()   [创建 DawnCaps, BindGroupLayouts]
       → DawnQueueManager()         [绑定 wgpu::Queue]
       → Context                    [返回给用户]

2. 资源创建 (录制阶段):
   Recorder
     → DawnResourceProvider::createTexture()     → DawnTexture  [wgpu::Texture + Views]
     → DawnResourceProvider::createBuffer()      → DawnBuffer   [wgpu::Buffer]
     → DawnResourceProvider::createSampler()     → DawnSampler  [wgpu::Sampler]
     → DawnSharedContext::createGraphicsPipeline()
       → DawnGraphicsPipeline::Make()            [SkSL→WGSL→wgpu::ShaderModule→wgpu::RenderPipeline]

3. 命令录制:
   DawnCommandBuffer::Make()
     → wgpu::Device::CreateCommandEncoder()
     → beginRenderPass()
       → wgpu::CommandEncoder::BeginRenderPass()   [创建 wgpu::RenderPassEncoder]
     → addDrawPass()
       → bindGraphicsPipeline()     [SetPipeline]
       → bindUniformBuffer()        [绑定 Uniform 到绑定组 0]
       → bindTextureAndSamplers()   [绑定纹理/采样器到绑定组 1]
       → setScissor() / setViewport()
       → draw() / drawIndexed() / drawInstanced()
     → endRenderPass()
       → wgpu::RenderPassEncoder::End()
     → finishEncoding()
       → wgpu::CommandEncoder::Finish()   [返回 wgpu::CommandBuffer]

4. 提交执行:
   DawnQueueManager::onSubmitToGpu()
     → wgpu::Queue::Submit(commandBuffer)
     → DawnWorkSubmission (跟踪完成状态)
       ├─ Emscripten: DawnWorkSubmissionWithAsyncWait [OnSubmittedWorkDone + 回调]
       └─ Native:     DawnWorkSubmissionWithFuture    [wgpu::Future + WaitAny]

5. 同步等待 (可选):
   DawnWorkSubmission::onIsFinished()
     ├─ Emscripten: DawnAsyncWait::yieldAndCheck() [tick + 检查信号]
     └─ Native:     wgpu::Instance::WaitAny()      [Future 等待]
```

### 着色器编译数据流

```
SkSL 源码
  → SkSLToWGSL()                        [SkSL → WGSL 转译]
    → SkSL::ToWGSL()                    [WGSL 代码生成器]
  → DawnCompileWGSLShaderModule()        [WGSL → wgpu::ShaderModule]
    → wgpu::Device::CreateShaderModule() [提交给 Dawn 编译]
  → wgpu::Device::CreateRenderPipeline() [包含在管线创建中]
```

### 绑定组数据流

```
Uniform 缓冲区绑定组 (组 0):
  ┌─────────────────────────────────────┐
  │ binding 0: 固有常量缓冲区 (32 字节)  │ ← 视口变换、RenderTarget 尺寸等
  │ binding 1: 合并 Uniform 缓冲区       │ ← RenderStep + Paint uniform 合并
  │ binding 2: 渐变数据缓冲区            │ ← 大型渐变色标数据 (仅 SSBO 模式)
  └─────────────────────────────────────┘
  全部使用 hasDynamicOffset = true，允许单个绑定组复用多个偏移。

纹理/采样器绑定组 (组 1):
  ┌─────────────────────────────────────┐
  │ binding 0: wgpu::Sampler            │
  │ binding 1: wgpu::TextureView        │
  │ ... (管线按需定义更多绑定)           │
  └─────────────────────────────────────┘
```

## 平台特定说明

### Emscripten / WebAssembly 环境

代码中大量使用 `#if defined(__EMSCRIPTEN__)` 进行条件编译，主要差异包括：

1. **着色器模块创建**: Emscripten 使用 `wgpu::ShaderModuleWGSLDescriptor`，Dawn Native 使用 `wgpu::ShaderSourceWGSL`。

2. **异步操作**: Emscripten 环境不支持 `wgpu::Future`，需使用旧式回调 API (`OnSubmittedWorkDone` + `void* userData`)。Dawn Native 使用 `wgpu::Future` + `wgpu::Instance::WaitAny()` 实现更高效的等待。

3. **Device Tick**: Emscripten 环境下 `deviceTick()` 不调用 `device.Tick()`（由浏览器事件循环驱动），Dawn Native 环境下显式调用。

4. **YCbCr 支持**: `wgpu::YCbCrVkDescriptor` 及相关功能仅在非 Emscripten 环境下可用，因为这是 Dawn 对 Vulkan 外部纹理的原生扩展。

5. **格式支持差异**: 部分纹理格式仅在 Dawn Native 环境下可用：
   - `R16Unorm`, `RG16Unorm`, `RGBA16Unorm` (非标准 WebGPU 格式)
   - `OpaqueYCbCrAndroid` (Android 平台 Vulkan 扩展)

6. **瞬态附件**: `fSupportedTransientAttachmentUsage` 仅在 Dawn Native 构建中有意义，WebGPU 标准中未定义此用法。

7. **错误处理**: `DawnErrorChecker` 在两种环境下使用完全不同的错误弹出流程——Emscripten 使用同步回调链，Dawn Native 使用 Future 等待。

### 工作提交的平台差异

| 特性 | Dawn Native | Emscripten/WASM |
|------|------------|-----------------|
| 工作完成跟踪 | `wgpu::Future` + `WaitAny` | `OnSubmittedWorkDone` + 回调 |
| 事件循环推进 | `instance.ProcessEvents()` | 浏览器 event loop / `asyncSleep` |
| 忙等待 | 支持（通过 tick 循环） | 需要 `-s ASYNCIFY` |
| CPU 同步 | 支持 `SyncToCpu::kYes` | 受限（需要 tick 函数） |

### Android 特殊支持

通过 Dawn 的 Vulkan 后端，Dawn 后端间接支持 Android 平台特有的功能：
- `wgpu::YCbCrVkDescriptor` 用于 Android 硬件缓冲区（AHardwareBuffer）的 YCbCr 采样。
- `wgpu::TextureFormat::OpaqueYCbCrAndroid` 用于不透明 YCbCr 纹理。
- 多平面纹理（`R8BG8Biplanar420Unorm`, `R10X6BG10X6Biplanar420Unorm`）用于视频帧处理。

## 相关文档与参考

### Skia 内部相关目录

| 路径 | 说明 |
|------|------|
| `include/gpu/graphite/dawn/` | Dawn 后端的公共 API 头文件 |
| `src/gpu/graphite/` | Graphite 核心框架和抽象基类 |
| `src/gpu/graphite/vk/` | Vulkan 后端实现（架构类似的对照参考） |
| `src/gpu/graphite/mtl/` | Metal 后端实现 |
| `src/sksl/codegen/SkSLWGSLCodeGenerator.h` | SkSL 到 WGSL 的代码生成器 |
| `src/gpu/SkSLToBackend.h` | 通用着色器编译框架 |

### 外部参考

| 资源 | 链接/说明 |
|------|----------|
| WebGPU 规范 | https://www.w3.org/TR/webgpu/ |
| WGSL 规范 | https://www.w3.org/TR/WGSL/ |
| Dawn 项目 | https://dawn.googlesource.com/dawn |
| Skia Graphite 文档 | https://skia.org/docs/dev/graphite/ |
| WebGPU C++ API | `webgpu/webgpu_cpp.h` 头文件 |

### 关键构建标志

| 宏定义 | 用途 |
|--------|------|
| `__EMSCRIPTEN__` | 区分 Emscripten/WASM 环境和 Dawn Native 环境 |
| `SK_DEBUG` | 启用调试断言和后端类型检查 |
| `GPU_TEST_UTILS` | 启用测试工具（如 GPU 捕获的 start/stop） |

### 类继承关系总结

```
SharedContext          → DawnSharedContext
Caps                   → DawnCaps
ResourceProvider       → DawnResourceProvider
CommandBuffer          → DawnCommandBuffer
QueueManager           → DawnQueueManager
GraphicsPipeline       → DawnGraphicsPipeline
ComputePipeline        → DawnComputePipeline
Texture                → DawnTexture
Buffer                 → DawnBuffer
Sampler                → DawnSampler
BackendTextureData     → DawnBackendTextureData
GpuWorkSubmission      → DawnWorkSubmissionWithAsyncWait (Emscripten)
                       → DawnWorkSubmissionWithFuture    (Dawn Native)
ThreadSafeResourceProvider → DawnThreadSafeResourceProvider
```
