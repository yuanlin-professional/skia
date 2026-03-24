# CommandBuffer (命令缓冲区)

> 源文件：[src/gpu/graphite/CommandBuffer.h](../../../../src/gpu/graphite/CommandBuffer.h)、[src/gpu/graphite/CommandBuffer.cpp](../../../../src/gpu/graphite/CommandBuffer.cpp)

## 概述

`CommandBuffer` 是 Graphite 中 GPU 命令录制的核心抽象类，封装了渲染通道、计算通道、缓冲区/纹理拷贝、同步等 GPU 操作的录制接口。后端子类（Metal、Vulkan、Dawn）实现具体的 GPU API 调用。

`CommandBuffer` 管理资源跟踪（通过命令缓冲区引用保持资源存活）、完成回调（finish procs）、信号量同步、以及重放变换（replay translation）等功能。

## 架构位置

`CommandBuffer` 位于 GPU 命令提交管线的核心：

- **上游**：`QueueManager` 管理命令缓冲区的生命周期和提交。
- **数据来源**：`DrawPass`（渲染命令）和 `DispatchGroup`（计算命令）提供具体的 GPU 操作。
- **下游**：后端子类将命令转换为 GPU API 调用并提交给 GPU。

## 主要类与结构体

### `CommandBuffer` (抽象基类)

**核心成员：**
- `fCommandBufferResources`：跟踪的资源列表（使用 `gr_cb<Resource>` 持有命令缓冲区引用）。
- `fFinishedProcs`：命令完成后的回调列表。
- `fBuffersToAsyncMap`：提交时需异步映射的缓冲区。
- `fRenderTargetBounds / fRenderAreaBounds`：渲染区域边界。
- `fReplayTranslation`：重放变换偏移。
- `fDstCopy`：DstRead 策略的纹理拷贝信息。
- `fIsProtected`：是否为受保护内容的命令缓冲区。

## 公共 API 函数

### 资源跟踪
- `trackResource(sk_sp<Resource>)`：添加命令缓冲区引用，资源在命令完成前保持存活。
- `resetCommandBuffer()`：释放所有跟踪的资源。

### 渲染与计算
- `addRenderPass(RenderPassDesc, colorTex, resolveTex, dsTex, dstCopy, ..., DrawPassList) -> bool`：录制渲染通道。
- `addComputePass(DispatchGroupSpan) -> bool`：录制计算通道。

### 缓冲区/纹理操作
- `copyBufferToBuffer / copyTextureToBuffer / copyBufferToTexture / copyTextureToTexture`：各种复制操作。
- `synchronizeBufferToCpu`：GPU -> CPU 缓冲区同步。
- `clearBuffer`：清零缓冲区。

### 完成回调与信号量
- `addFinishedProc(sk_sp<RefCntedCallback>)`：注册完成回调。
- `callFinishedProcs(bool success)`：调用所有完成回调。
- `addWaitSemaphores / addSignalSemaphores`：信号量同步。

### 重放
- `setReplayTranslationAndClip(translation, clip, rtBounds) -> bool`：设置重放变换和裁剪。

### 统计
- `startStatsQuery / endStatsQuery / gpuStats`：GPU 统计查询。

## 内部实现细节

### 资源生命周期管理
`trackResource()` 通过 `gr_cb<Resource>` 持有命令缓冲区引用（`refCommandBuffer`），确保资源在 GPU 执行完成前不被释放。`resetCommandBuffer()` 在命令完成后释放所有引用。

### 渲染通道的 DST 读取
`addRenderPass` 接受可选的 `dstCopy` 纹理参数，用于实现 `DstReadStrategy::kTextureCopy`。`fDstReadBounds` 已包含重放变换。

### 后端子类纯虚方法
所有 GPU 操作都通过 `on*` 前缀的纯虚方法委托给后端实现：
- `onAddRenderPass`：后端渲染通道录制。
- `onAddComputePass`：后端计算通道录制。
- `onCopy*`：各种后端复制操作。
- `resourceProvider()`：后端特定的资源提供者。

### 重放变换
`setReplayTranslationAndClip` 允许以不同的偏移和裁剪重放同一 Recording，用于 Surface 的变换重放。视口会自动应用变换偏移。

## 依赖关系

- `Resource`：GPU 资源基类（资源跟踪）。
- `DrawPass`：渲染命令来源。
- `DispatchGroup`：计算命令来源。
- `RenderPassDesc`：渲染通道描述。
- `Texture / Buffer / Sampler`：GPU 资源。

## 设计模式与设计决策

1. **模板方法模式**：公共方法处理通用逻辑（资源跟踪、边界计算），委托后端实现。
2. **资源跟踪与引用分离**：命令缓冲区引用独立于使用引用，允许资源被缓存复用的同时保持 GPU 安全。
3. **命令缓冲区池化**：`QueueManager` 维护可用命令缓冲区池，避免重复创建。
4. **重放变换支持**：单次录制可以多次以不同变换提交。

## 性能考量

- 初始资源跟踪容量为 32（`kInitialTrackedResourcesCount`），减少小型命令缓冲区的内存分配。
- 异步缓冲区映射（`fBuffersToAsyncMap`）允许在提交时启动异步映射，避免阻塞。

## 相关文件

- `src/gpu/graphite/QueueManager.h/.cpp`：命令缓冲区管理。
- `src/gpu/graphite/DrawPass.h/.cpp`：渲染命令生成。
- `src/gpu/graphite/RenderPassDesc.h`：渲染通道描述。
- `src/gpu/graphite/Resource.h`：资源基类。
- 后端实现：`MtlCommandBuffer`、`VulkanCommandBuffer`、`DawnCommandBuffer`。
