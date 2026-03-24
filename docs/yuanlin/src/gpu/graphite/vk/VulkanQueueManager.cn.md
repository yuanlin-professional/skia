# VulkanQueueManager -- Vulkan 队列管理器

> 源文件:
> - `src/gpu/graphite/vk/VulkanQueueManager.h`
> - `src/gpu/graphite/vk/VulkanQueueManager.cpp`

## 概述

VulkanQueueManager 是 Skia Graphite Vulkan 后端的队列管理器,继承自 `QueueManager` 基类。它负责管理 Vulkan 命令缓冲区的创建和 GPU 工作的提交,是 Graphite 将渲染命令发送到 GPU 的核心调度组件。

## 架构位置

```
Context
  -> QueueManager (抽象基类)
    -> VulkanQueueManager (Vulkan 实现)  <-- 本模块
       -> VulkanCommandBuffer (命令缓冲区)
       -> VulkanWorkSubmission (提交追踪)
```

`VulkanQueueManager` 在 `ContextFactory::MakeVulkan` 中创建,与 `VulkanSharedContext` 一同构成 Context 的核心组件。

## 主要类与结构体

### VulkanQueueManager

```cpp
class VulkanQueueManager final : public QueueManager {
    VkQueue fQueue;  // Vulkan 队列句柄
};
```

### VulkanWorkSubmission (内部类)

```cpp
class VulkanWorkSubmission final : public GpuWorkSubmission {
    bool onIsFinished(const SharedContext*) override;
    void onWaitUntilFinished(const SharedContext*) override;
};
```
封装已提交的命令缓冲区,委托给 `VulkanCommandBuffer` 查询完成状态。

## 公共 API 函数

### 构造函数

```cpp
VulkanQueueManager(VkQueue queue, const SharedContext*);
```
接收外部提供的 `VkQueue` 句柄（来自 `VulkanBackendContext`）。

## 内部实现细节

### getNewCommandBuffer

```cpp
std::unique_ptr<CommandBuffer> getNewCommandBuffer(ResourceProvider*, Protected) override;
```
将 `ResourceProvider` 向下转型为 `VulkanResourceProvider`,调用 `VulkanCommandBuffer::Make` 创建新的命令缓冲区。

### onSubmitToGpu

```cpp
OutstandingSubmission onSubmitToGpu(const SubmitInfo& submitInfo) override;
```
1. 将当前命令缓冲区转型为 `VulkanCommandBuffer`
2. 调用 `submit(fQueue, submitInfo)` 将命令提交到 Vulkan 队列
3. 成功时创建 `VulkanWorkSubmission` 包装并返回
4. 失败时调用 `callFinishedProcs(false)` 通知上层并返回 nullptr

## 依赖关系

- `QueueManager` -- 基类
- `VulkanCommandBuffer` -- 命令缓冲区实现
- `VulkanResourceProvider` -- 资源管理
- `VulkanSharedContext` -- 共享上下文
- `GpuWorkSubmission` -- GPU 工作提交基类

## 设计模式与设计决策

1. **队列句柄外部所有**: `VkQueue` 由客户端通过 `VulkanBackendContext` 提供,QueueManager 不拥有也不销毁它,这符合 Vulkan 中队列生命周期与设备绑定的特性。

2. **简洁的提交模型**: 每次提交创建一个 `VulkanWorkSubmission` 对象,通过其 `isFinished()` 和 `waitUntilFinished()` 方法追踪 GPU 工作完成状态。

## 性能考量

- 提交操作本身是轻量的,主要开销在 `VulkanCommandBuffer::submit` 中。
- 测试捕获功能 (`startCapture`/`stopCapture`) 仅在 `GPU_TEST_UTILS` 编译模式下存在,目前为空实现。

## 相关文件

- `src/gpu/graphite/QueueManager.h` -- 队列管理基类
- `src/gpu/graphite/vk/VulkanCommandBuffer.h` -- Vulkan 命令缓冲区
- `src/gpu/graphite/vk/VulkanSharedContext.h` -- Vulkan 共享上下文
- `src/gpu/graphite/GpuWorkSubmission.h` -- GPU 工作提交基类
