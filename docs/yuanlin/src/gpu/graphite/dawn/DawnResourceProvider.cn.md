# DawnResourceProvider

> 源文件:
> - `src/gpu/graphite/dawn/DawnResourceProvider.h`
> - `src/gpu/graphite/dawn/DawnResourceProvider.cpp`

## 概述

`DawnResourceProvider` 是 Skia Graphite 渲染引擎中面向 Dawn (WebGPU) 后端的资源提供者实现。它继承自 `ResourceProvider` 基类，负责创建和管理 Dawn 后端所需的各类 GPU 资源，包括纹理、缓冲区、采样器、计算管线以及绑定组（Bind Group）等。该类还包含一套复杂的内部常量（intrinsic constants）缓冲区管理系统和 Blit-with-Draw 编码器机制。

## 架构位置

`DawnResourceProvider` 位于 Graphite 渲染引擎的 Dawn 后端层：

```
Graphite (平台无关层)
  └── ResourceProvider (基类，定义资源创建接口)
        └── DawnResourceProvider (Dawn/WebGPU 后端实现)
              ├── IntrinsicConstantsManager (内部常量缓冲区管理)
              ├── IntrinsicBuffer (单个内部常量缓冲区封装)
              └── BlitWithDrawEncoder (Blit 操作编码器)
```

它通过 `DawnSharedContext` 获取底层 `wgpu::Device`，并与 `DawnTexture`、`DawnBuffer`、`DawnSampler`、`DawnComputePipeline`、`DawnGraphicsPipeline` 等 Dawn 后端类紧密协作。

## 主要类与结构体

### `DawnResourceProvider`
- 继承自 `ResourceProvider`，是 Dawn 后端资源创建与管理的核心类。
- 拥有绑定组缓存（`fUniformBufferBindGroupCache`、`fSingleTextureSamplerBindGroups`）和 Blit 管线缓存（`fBlitWithDrawPipelines`）。
- 模板别名 `BindGroupKey<NumEntries>` 用于生成固定大小的缓存键。
- `kNumUniformEntries = 3`：统一缓冲区绑定组包含 3 个条目（内部常量、渲染步骤 uniform、绘制 uniform）。

### `DawnResourceProvider::IntrinsicBuffer`
- 封装一个 `DawnBuffer`，用于存储内部常量数据块。
- 每个缓冲区最多包含 `kNumSlots = 8` 个常量槽位。
- 使用 `THashMap` 缓存已写入的 `UniformDataBlock` 到其偏移量的映射，避免重复写入。
- 包含 LRU 访问时间戳用于资源回收。

### `DawnResourceProvider::IntrinsicConstantsManager`
- 管理内部常量缓冲区的旋转使用策略。
- 由于 Dawn 目前不支持推送常量（push constants），此管理器通过轮换缓冲区并使用 `WriteBuffer()` 来模拟类似功能。
- 维护一个 LRU 链表（最多 `kMaxNumBuffers = 16` 个缓冲区），在缓冲区用尽时创建新的并淘汰最久未使用的。
- 被淘汰的缓冲区放入 `fPendingIntrinsicBuffers` 链表，待命令缓冲区完成后释放。

### `DawnResourceProvider::BlitWithDrawEncoder`
- 用于在渲染过程中执行 Blit（像素复制）操作的编码器。
- 支持普通纹理和 MSAA 纹理的采样。
- 使用全屏三角形绘制方式实现 Blit，通过 `instanceIndex` 编码源偏移量（将 x、y 各编码为 16 位整数打包到 32 位）。

## 公共 API 函数

### 构造与析构
- **`DawnResourceProvider(SharedContext*, SingleOwner*, uint32_t recorderID, size_t resourceBudget)`**：构造函数，初始化绑定组缓存和内部常量管理器。
- **`~DawnResourceProvider()`**：析构函数，默认实现。

### 纹理相关
- **`findOrCreateDiscardableMSAALoadTexture(SkISize, const TextureInfo&)`**：查找或创建用于 MSAA 加载阶段的可丢弃纹理。该纹理为单采样，带有纹理绑定用途，且不可为 transient attachment。

### Blit 操作
- **`findOrCreateBlitWithDrawEncoder(const RenderPassDesc&, SampleCount)`**：查找或创建用于 Blit 的渲染管线和编码器。根据渲染通道描述和源采样数生成缓存键。内联 WGSL 着色器用于执行纹理采样或 MSAA 解析。

### 缓冲区相关
- **`findOrCreateDawnBuffer(size_t, BufferType, AccessPattern, std::string_view)`**：查找或创建指定大小和类型的 Dawn 缓冲区。

### 绑定组管理
- **`findOrCreateUniformBuffersBindGroup(...)`**：根据绑定的缓冲区及其大小查找或创建统一缓冲区绑定组。使用 LRU 缓存（最多 1024 个条目）。未使用的槽位绑定到空缓冲区（null buffer）。
- **`findOrCreateSingleTextureSamplerBindGroup(const DawnSampler*, const DawnTexture*)`**：查找或创建单纹理+采样器的绑定组。使用 LRU 缓存（最多 4096 个条目）。

### 内部常量管理
- **`findOrCreateIntrinsicBindBufferInfo(DawnCommandBuffer*, UniformDataBlock)`**：查找或创建给定内部常量值的绑定缓冲区信息。代理到 `IntrinsicConstantsManager::add()`。
- **`releasePendingIntrinsicBuffers()`**：释放已完成的待处理内部常量缓冲区。

### BlitWithDrawEncoder 方法
- **`EncodeBlit(const wgpu::Device&, const wgpu::RenderPassEncoder&, const wgpu::TextureView&, const SkIPoint&, const SkIRect&)`**：编码一次 Blit 绘制调用，设置管线、绑定组、裁剪矩形和视口，然后执行 Draw 调用。

## 内部实现细节

### Blit-with-Draw 管线
由于 Dawn 不直接支持在渲染通道中执行 Blit，`DawnResourceProvider` 采用绘制调用方式模拟 Blit 操作：
1. 使用 WGSL 着色器定义一个全屏三角形顶点着色器和两个片段着色器（普通采样和 MSAA 解析）。
2. 源偏移量通过 `instanceIndex` 参数传递：低 16 位存 x 偏移，高 16 位存 y 偏移。顶点着色器进行 16 位到 32 位的符号扩展。
3. 管线按 `(renderPassDesc, srcIsMSAA)` 组合缓存到 `fBlitWithDrawPipelines` 哈希表中。

### 内部常量缓冲区管理
- 每个 `IntrinsicBuffer` 包含 8 个槽位，每个槽位存储一组对齐后的 uniform 数据。
- 写入时先遍历 LRU 链表查找已有的相同数据，命中则直接返回偏移量。
- 未命中时，若当前缓冲区已满或不存在，则创建新缓冲区。
- 通过 `wgpu::Queue::WriteBuffer()` 将数据写入 GPU 缓冲区。注意该方法不能在活动渲染通道期间调用。

### 空缓冲区（Null Buffer）
- 用于填充绑定组中未使用的槽位，满足 Dawn 对绑定组完整性的要求。
- 大小为 `kBufferBindingSizeAlignment`（16 字节），使用 `CopyDst | Uniform | Storage` 用途。

### 资源清理
- `onFreeGpuResources()`：释放内部常量管理器资源并重置绑定组缓存。
- `onPurgeResourcesNotUsedSince()`：按时间戳清理过期的内部常量缓冲区。

## 依赖关系

- **基类**: `ResourceProvider`（Graphite 平台无关资源管理接口）
- **Dawn 后端类**: `DawnSharedContext`、`DawnTexture`、`DawnBuffer`、`DawnSampler`、`DawnComputePipeline`、`DawnGraphicsPipeline`、`DawnCommandBuffer`、`DawnErrorChecker`
- **Graphite 核心**: `ComputePipeline`、`RenderPassDesc`、`TextureInfo`、`BackendTexture`、`PipelineData`
- **Skia 基础设施**: `SkLRUCache`、`SkTHash`、`SkArenaAlloc`、`SkTInternalLList`、`SkAlignTo`
- **WebGPU API**: `wgpu::Device`、`wgpu::Buffer`、`wgpu::Texture`、`wgpu::BindGroup`、`wgpu::RenderPipeline` 等

## 设计模式与设计决策

1. **LRU 缓存模式**：绑定组和内部常量缓冲区均使用 LRU 缓存策略，在内存占用和创建开销之间取得平衡。绑定组缓存上限分别为 1024（uniform）和 4096（纹理）。

2. **缓冲区旋转策略**：`IntrinsicConstantsManager` 使用缓冲区池和旋转机制，避免每帧重新创建缓冲区。由于 Dawn 不支持推送常量，这是性能关键路径上的重要优化。

3. **延迟释放**：被淘汰的内部常量缓冲区不立即释放，而是放入待处理链表，等待关联的命令缓冲区执行完毕后再释放，确保 GPU 端不会访问已释放的资源。

4. **Blit-via-Draw 方案**：使用绘制调用模拟 Blit 操作，通过 `instanceIndex` 编码偏移量以绕过 Dawn 当前缺乏推送常量的限制。

5. **线程安全**：使用 `SingleOwner` 和 `SKGPU_ASSERT_SINGLE_OWNER` 宏确保关键操作在正确的线程上执行。另提供 `DawnThreadSafeResourceProvider` 用于跨线程场景。

## 性能考量

- **绑定组缓存**：避免每帧重复创建 `wgpu::BindGroup` 对象，减少 Dawn API 调用开销。缓存键设计紧凑（使用 buffer ID 和 binding size 组合），查找效率高。
- **内部常量去重**：同一帧中重复出现的内部常量值会被 `IntrinsicBuffer` 内的哈希表拦截，避免重复写入 GPU。
- **对齐约束**：缓冲区绑定大小需对齐到 `kBufferBindingSizeAlignment`（16 字节），内部常量按 `requiredUniformBufferAlignment()` 对齐。
- **MSAA 性能**：Blit-with-Draw 的 MSAA 片段着色器在 GPU 端循环对每个采样点进行采样后求均值，相当于手动 Resolve。
- **按需创建**：空缓冲区、Blit 管线等资源均为惰性创建，首次使用时才分配。

## 相关文件

- `src/gpu/graphite/ResourceProvider.h` - 基类定义
- `src/gpu/graphite/dawn/DawnSharedContext.h` - Dawn 共享上下文
- `src/gpu/graphite/dawn/DawnTexture.h` - Dawn 纹理实现
- `src/gpu/graphite/dawn/DawnBuffer.h` - Dawn 缓冲区实现
- `src/gpu/graphite/dawn/DawnSampler.h` - Dawn 采样器实现
- `src/gpu/graphite/dawn/DawnComputePipeline.h` - Dawn 计算管线
- `src/gpu/graphite/dawn/DawnGraphicsPipeline.h` - Dawn 图形管线
- `src/gpu/graphite/dawn/DawnCommandBuffer.h` - Dawn 命令缓冲区
- `src/gpu/graphite/dawn/DawnErrorChecker.h` - Dawn 错误检查器
- `src/gpu/graphite/PipelineData.h` - 管线数据定义（含 UniformDataBlock）
