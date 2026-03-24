# VulkanCommandBuffer

> 源文件: `src/gpu/graphite/vk/VulkanCommandBuffer.h`, `src/gpu/graphite/vk/VulkanCommandBuffer.cpp`

## 概述

`VulkanCommandBuffer` 是 Skia Graphite Vulkan 后端的命令缓冲区实现，继承自通用的 `CommandBuffer` 基类。它封装了 `VkCommandBuffer` 和 `VkCommandPool`，负责记录所有 GPU 命令——包括渲染通道、绘制调用、资源复制、管线状态绑定、描述符集管理和同步操作。

该类是 Graphite 的绘制命令最终转换为 Vulkan API 调用的地方，将抽象的 `DrawPass` 命令翻译为具体的 Vulkan 绘制、绑定和状态设置操作。

## 架构位置

- **上层**: 继承自 `CommandBuffer`，由 `QueueManager` 管理
- **核心角色**: 将 Graphite 的抽象绘制命令翻译为 Vulkan API 调用
- **协作**: 使用 `VulkanResourceProvider` 获取资源，操作 `VulkanTexture`、`VulkanBuffer` 等

## 主要类与结构体

### `VulkanCommandBuffer` 类

**核心状态**:
- `fPool` — `VkCommandPool` 句柄
- `fPrimaryCommandBuffer` — `VkCommandBuffer` 句柄
- `fActive` — 是否已调用 begin() 但未调用 end()
- `fActiveRenderPass` — 是否在活跃的渲染通道中
- `fTargetTexture` — 当前渲染目标纹理
- `fActiveGraphicsPipeline` — 当前绑定的图形管线
- `fSubmitFence` — 提交栅栏，用于检测完成状态

**同步状态**:
- `fWaitSemaphores` / `fSignalSemaphores` — 等待和信号信号量
- `fBufferBarriers` / `fImageBarriers` — 待提交的内存屏障
- `fSrcStageMask` / `fDstStageMask` — 管线阶段掩码

**描述符绑定跟踪**:
- `fBindUniformBuffers` / `fBindTextureSamplers` — 是否需要重新绑定
- `fUniformBuffersToBind` — 待绑定的 uniform 缓冲区
- `fTextureSamplerDescSetToBind` — 待绑定的纹理/采样器描述符集

**PushConstantInfo 结构体**: 封装推送常量的偏移、大小、着色器阶段和值指针。

## 公共 API 函数

### 生命周期

- **`Make(VulkanSharedContext*, VulkanResourceProvider*, Protected)`** — 静态工厂方法
- **`setNewCommandBufferResources()`** — 重置命令缓冲区资源
- **`submit(VkQueue, SubmitInfo)`** — 提交到队列
- **`isFinished()`** — 检查是否执行完毕
- **`waitUntilFinished()`** — 等待执行完成

### 内存屏障

- **`addBufferMemoryBarrier(...)`** — 添加缓冲区内存屏障
- **`addImageMemoryBarrier(...)`** — 添加图像内存屏障

### GPU 统计

- **`startStatsQuery(GpuStatsFlags)`** — 开始时间戳/遮挡查询
- **`endStatsQuery(GpuStatsFlags)`** — 结束查询
- **`gpuStats()`** — 获取 GPU 统计数据

## 内部实现细节

### 渲染通道流程

1. **`onAddRenderPass()`**: 入口点，设置渲染通道
2. **`beginRenderPass()`**: 查找/创建 VkRenderPass 和 VkFramebuffer，发出 vkCmdBeginRenderPass
3. **`performOncePerRPUpdates()`**: 设置视口、推送常量、绑定输入附件
4. **`addDrawPass()`**: 遍历 DrawPass 命令并翻译
5. **`endRenderPass()`**: 结束渲染通道

### 绘制命令翻译

`addDrawPass()` 遍历 DrawPassCommands 并翻译为 Vulkan 调用：
- `BindGraphicsPipeline` → `vkCmdBindPipeline`
- `SetBlendConstants` → `vkCmdSetBlendConstants`
- `BindUniformBuffer` → 记录待绑定缓冲区
- `BindDrawBuffers` → `vkCmdBindVertexBuffers` / `vkCmdBindIndexBuffer`
- `BindTexturesAndSamplers` → 记录描述符集
- `SetScissor` → `vkCmdSetScissor`
- `Draw/DrawIndexed/DrawInstanced/DrawIndexedInstanced` → 对应的 vkCmdDraw* 调用

### 描述符集同步

`syncDescriptorSets()` 在绘制前检查是否需要更新 uniform 缓冲区或纹理/采样器的描述符集绑定，确保所有资源在绘制时已正确绑定。

### 内存屏障批处理

内存屏障不会立即提交，而是累积在 `fBufferBarriers` 和 `fImageBarriers` 中，在 `submitPipelineBarriers()` 时一次性通过 `vkCmdPipelineBarrier` 提交。

### MSAA 加载

`loadMSAAFromResolve()` 处理从解析附件加载多采样数据的特殊子通道，用于保留先前帧的内容。

## 依赖关系

- `CommandBuffer` — 基类
- `VulkanSharedContext` — Vulkan 设备和接口
- `VulkanResourceProvider` — 资源查找和创建
- `VulkanGraphicsPipeline` — 图形管线
- `VulkanDescriptorSet` — 描述符集
- `VulkanTexture` / `VulkanBuffer` — GPU 资源
- `DrawPass` / `DrawPassCommands` — 抽象绘制命令

## 设计模式与设计决策

### 延迟绑定

描述符集的绑定被延迟到绘制调用前的 `syncDescriptorSets()` 中执行，减少不必要的绑定操作。

### 屏障批处理

内存屏障累积后批量提交，减少 Vulkan API 调用次数。

### 模拟管线布局

使用 `VulkanResourceProvider` 提供的模拟管线布局在渲染通道开始时更新推送常量，避免了对实际管线绑定顺序的依赖。

### 间接绘制追踪

间接缓冲区绑定被追踪（`fBoundIndirectBuffer`），避免在未改变时重复绑定。

## 性能考量

- **屏障批处理**: 减少 vkCmdPipelineBarrier 调用次数
- **描述符集缓存**: 通过 VulkanResourceProvider 的缓存避免重复创建
- **管线状态追踪**: 仅在管线变化时更新绑定
- **混合常量缓存**: `fCachedBlendConstant` 避免重复设置相同的混合常量

## 相关文件

- `src/gpu/graphite/CommandBuffer.h` — 基类
- `src/gpu/graphite/DrawPass.h` — 绘制通道
- `src/gpu/graphite/vk/VulkanResourceProvider.h` — 资源提供者
- `src/gpu/graphite/vk/VulkanGraphicsPipeline.h` — 图形管线
- `src/gpu/graphite/vk/VulkanSharedContext.h` — Vulkan 共享上下文
