# QueueManager (命令队列管理器)

> 源文件：[src/gpu/graphite/QueueManager.h](../../../../src/gpu/graphite/QueueManager.h)、[src/gpu/graphite/QueueManager.cpp](../../../../src/gpu/graphite/QueueManager.cpp)

## 概述

`QueueManager` 管理 Graphite 中所有命令缓冲区的创建、复用、录制和提交，确保 GPU 工作以正确的顺序提交执行。后端子类实现获取新命令缓冲区和提交到 GPU 的具体逻辑。

该类还支持受保护（protected）和非受保护命令缓冲区的分离管理。在受保护 Context 中，大部分命令使用受保护命令缓冲区，但某些操作（如顶点缓冲区上传）需要非受保护命令缓冲区，因为受保护内存不能在顶点着色器中访问。

## 架构位置

`QueueManager` 位于 GPU 命令提交管线的最顶层：

- **上游**：`Context` 通过 `insertRecording()` 将 Recording 提交到队列。
- **下游**：管理 `CommandBuffer` 的生命周期，通过 `GpuWorkSubmission` 跟踪已提交的工作。
- **协作**：`ResourceProvider` 用于创建命令缓冲区所需的资源。

## 主要类与结构体

### `QueueManager` (抽象基类)

**核心成员：**
- `fSharedContext`：共享上下文。
- `fCurrentCommandBuffer`：当前正在录制的命令缓冲区。
- `fOutstandingSubmissions`：已提交但未完成的 GPU 工作（`SkDeque`）。
- `fAvailableCommandBuffers / fAvailableProtectedCommandBuffers`：可复用的命令缓冲区池。
- `fLastAddedRecordingIDs`：每个 Recorder 最后添加的 Recording ID（防止乱序插入）。

## 公共 API 函数

### 录制与提交
- `addRecording(InsertRecordingInfo, Context*) -> InsertStatus`：将 Recording 中的命令添加到当前命令缓冲区。
- `addTask(Task*, Context*, Protected) -> bool`：直接添加单个任务（可指定保护级别）。
- `addFinishInfo(InsertFinishInfo, ResourceProvider*, buffers) -> bool`：注册完成回调和异步映射缓冲区。
- `submitToGpu(SubmitInfo) -> bool`：将当前命令缓冲区提交到 GPU 执行。

### 工作状态查询
- `hasUnfinishedGpuWork() -> bool`：是否有未完成的 GPU 工作。
- `hasPendingGPUWork() -> bool`：当前命令缓冲区是否有待提交的工作。
- `checkForFinishedWork(SyncToCpu)`：检查已完成的 GPU 工作，释放资源。

### 命令缓冲区管理
- `returnCommandBuffer(unique_ptr<CommandBuffer>)`：归还命令缓冲区到复用池。

## 内部实现细节

### 命令缓冲区池化
- 已完成的命令缓冲区通过 `returnCommandBuffer` 归还到复用池。
- `setupCommandBuffer` 优先从池中获取，仅在池为空时创建新命令缓冲区。
- 受保护和非受保护命令缓冲区使用独立的池。

### 提交跟踪
- 使用 `SkDeque` 存储 `OutstandingSubmission`（`GpuWorkSubmission`），按 FIFO 顺序。
- `checkForFinishedWork` 从前端检查完成状态，释放资源和回调。
- 分配块大小为 8（`kDefaultOutstandingAllocCnt`），平衡内存和分配频率。

### Recording ID 顺序验证
`fLastAddedRecordingIDs` 使用哈希映射跟踪每个 Recorder 的最后 Recording ID，防止同一 Recorder 的 Recording 被乱序插入。

### 受保护内容处理
在受保护 Context 中切换命令缓冲区的保护级别前，必须先提交当前工作（`submitToGpu`）。混合使用不同保护级别的命令缓冲区会报错。

## 依赖关系

- `CommandBuffer`：命令缓冲区。
- `GpuWorkSubmission`：GPU 工作提交跟踪。
- `SharedContext`：共享上下文。
- `ResourceProvider`：资源提供。
- `Recording`：录制的命令来源。
- `Task`：任务抽象。

## 设计模式与设计决策

1. **命令缓冲区池化**：避免频繁创建/销毁 GPU 命令缓冲区。
2. **FIFO 提交跟踪**：确保按提交顺序检查完成状态。
3. **保护级别分离**：受保护和非受保护命令缓冲区使用独立的池和生命周期。
4. **Recording ID 验证**：防止客户端错误地乱序插入同一 Recorder 的 Recording。

## 性能考量

- 命令缓冲区复用减少了 GPU API 调用。
- 延迟检查完成状态（`checkForFinishedWork`）避免不必要的同步。
- 批量提交（累积多个 Recording 到同一命令缓冲区）减少提交次数。

## 相关文件

- `src/gpu/graphite/CommandBuffer.h/.cpp`：命令缓冲区。
- `src/gpu/graphite/GpuWorkSubmission.h/.cpp`：GPU 工作提交。
- `include/gpu/graphite/Context.h`：Context 管理。
- `include/gpu/graphite/Recording.h`：Recording。
- 后端实现：`MtlQueueManager`、`VulkanQueueManager`、`DawnQueueManager`。
