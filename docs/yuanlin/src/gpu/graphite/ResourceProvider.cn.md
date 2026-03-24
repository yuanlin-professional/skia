# ResourceProvider (资源提供者)

> 源文件：[src/gpu/graphite/ResourceProvider.h](../../../../src/gpu/graphite/ResourceProvider.h)、[src/gpu/graphite/ResourceProvider.cpp](../../../../src/gpu/graphite/ResourceProvider.cpp)

## 概述

`ResourceProvider` 是 Graphite 中负责创建、查找和管理 GPU 资源的核心抽象类。它充当客户端代码与底层资源缓存（`ResourceCache`）之间的中介，提供统一的接口来获取纹理、缓冲区、采样器和管线资源。`ResourceProvider` 封装了"先查找缓存再创建新资源"的逻辑，并通过后端子类实现具体的 GPU API 调用。

每个 `Recorder` 和 `Context` 都持有自己的 `ResourceProvider` 实例，各自关联一个 `ResourceCache`。

## 架构位置

`ResourceProvider` 位于资源管理系统的最上层：

- **上游**：`Recorder`、`DrawContext`、`TextureProxy` 等通过 ResourceProvider 获取资源。
- **下游**：通过 `ResourceCache` 查找可复用资源，通过后端子类创建新资源。
- **全局协作**：图形管线的创建通过 `GlobalCache` 在 Context 级别共享。

## 主要类与结构体

### `ResourceProvider` (抽象基类)

**核心成员：**
- `fSharedContext`：共享上下文，提供后端 API 和能力查询。
- `fResourceCache`：本地资源缓存。

## 公共 API 函数

### 管线资源
- `createGraphicsPipelineHandle(...) -> GraphicsPipelineHandle`：创建图形管线句柄。
- `startPipelineCreationTask(...)`：启动异步管线创建任务。
- `resolveHandle(...) -> sk_sp<GraphicsPipeline>`：解析管线句柄为实际管线。
- `findOrCreateComputePipeline(ComputePipelineDesc) -> sk_sp<ComputePipeline>`：查找或创建计算管线。

### 纹理资源
- `findOrCreateShareableTexture(SkISize, TextureInfo, label)`：查找或创建可共享纹理。
- `findOrCreateNonShareableTexture(SkISize, TextureInfo, label, Budgeted)`：查找或创建独占纹理。
- `findOrCreateScratchTexture(SkISize, TextureInfo, label, unavailable)`：查找或创建 scratch 纹理。
- `createWrappedTexture(BackendTexture, label)`：包装外部纹理。

### 缓冲区资源
- `findOrCreateNonShareableBuffer(size, BufferType, AccessPattern, label)`：查找或创建独占缓冲区。
- `findOrCreateScratchBuffer(size, BufferType, AccessPattern, label, unavailable)`：查找或创建 scratch 缓冲区。

### 采样器
- `findOrCreateCompatibleSampler(SamplerDesc)`：查找或创建兼容的采样器。

### 后端纹理
- `createBackendTexture(SkISize, TextureInfo) -> BackendTexture`：创建后端纹理。
- `deleteBackendTexture(BackendTexture)`：删除后端纹理。

### 缓存管理
- `setResourceCacheLimit / getResourceCacheLimit`：预算限制。
- `freeGpuResources() / purgeResourcesNotUsedSince(...)`：资源清除。
- `proxyCache() -> ProxyCache*`：纹理代理缓存。

## 内部实现细节

### 资源查找与创建流程
对纹理和缓冲区，通用的内部流程：
1. 根据资源参数生成 `GraphiteResourceKey`。
2. 调用 `fResourceCache->findAndRefResource(key, ...)` 查找缓存。
3. 如果缓存未命中，调用后端子类的纯虚创建函数（`createTexture`、`createBuffer` 等）。
4. 将新创建的资源通过 `fResourceCache->insertResource(...)` 注册到缓存。

### 后端子类纯虚函数
- `createComputePipeline(ComputePipelineDesc) -> sk_sp<ComputePipeline>`
- `createTexture(SkISize, TextureInfo, label) -> sk_sp<Texture>`
- `createBuffer(size, BufferType, AccessPattern, label) -> sk_sp<Buffer>`
- `createSampler(SamplerDesc) -> sk_sp<Sampler>`

## 依赖关系

### 上游依赖
- `SharedContext`：共享上下文和后端 API。
- `ResourceCache`：资源缓存。
- `Caps`：能力查询。

### 下游使用者
- `Recorder`、`DrawContext`：获取资源。
- `TextureProxy`：通过 ResourceProvider 实例化纹理。
- `DrawBufferManager`：获取缓冲区。

## 设计模式与设计决策

1. **模板方法模式**：`findOrCreate*` 方法封装了查找-创建-注册的通用逻辑，子类只需实现 `create*` 纯虚方法。

2. **共享性分级**：资源可以是 `Shareable::kNo`（独占）、`Shareable::kYes`（共享）或 `Shareable::kScratch`（临时），不同级别有不同的缓存和复用策略。

3. **分层缓存**：本地 `ResourceCache` + 全局 `GlobalCache`，图形管线在全局级别共享。

## 性能考量

- 资源查找优先于创建，最大化缓存复用。
- Scratch 资源使用 `unavailable` 集合避免同一 Recording 内的资源冲突。
- 管线创建可以异步执行，不阻塞录制。

## 相关文件

- `src/gpu/graphite/ResourceCache.h/.cpp`：资源缓存。
- `src/gpu/graphite/Resource.h/.cpp`：资源基类。
- `src/gpu/graphite/GraphiteResourceKey.h`：资源键。
- `src/gpu/graphite/SharedContext.h`：共享上下文。
