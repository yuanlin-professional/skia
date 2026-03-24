# DawnQueueManager

> 源文件:
> - `src/gpu/graphite/dawn/DawnQueueManager.h`
> - `src/gpu/graphite/dawn/DawnQueueManager.cpp`

## 概述

`DawnQueueManager` 是 Skia Graphite 渲染引擎 Dawn (WebGPU) 后端的队列管理器实现。它继承自 `QueueManager` 基类，负责管理 GPU 命令缓冲区的创建和提交。该类封装了 `wgpu::Queue`，处理命令缓冲区的编码完成、提交到 GPU 以及工作完成的异步跟踪。针对 Emscripten 和原生 Dawn 环境，分别使用不同的异步等待机制。

## 架构位置

```
Graphite Context
  └── QueueManager (平台无关基类)
        └── DawnQueueManager (Dawn/WebGPU 后端)
              ├── DawnWorkSubmissionWithFuture (原生 Dawn，基于 wgpu::Future)
              └── DawnWorkSubmissionWithAsyncWait (Emscripten，基于 DawnAsyncWait)
```

## 主要类与结构体

### `DawnQueueManager`
- 继承自 `QueueManager`，管理 Dawn 后端的 GPU 命令提交。
- 持有 `wgpu::Queue` 成员，通过 `dawnQueue()` 访问器暴露。

### `DawnWorkSubmissionWithFuture`（原生 Dawn）
- 继承自 `GpuWorkSubmission`，使用 `wgpu::Future` 跟踪提交的工作完成状态。
- `onIsFinished()` 通过 `instance.WaitAny()` 以零超时非阻塞检查。
- `onWaitUntilFinished()` 通过 `instance.WaitAny()` 以无限超时阻塞等待。

### `DawnWorkSubmissionWithAsyncWait`（Emscripten）
- 继承自 `GpuWorkSubmission`，使用 `DawnAsyncWait` 辅助类跟踪工作完成。
- 通过 `OnSubmittedWorkDone` 回调在工作完成时发送信号。
- `onIsFinished()` 使用 `yieldAndCheck()` 非阻塞轮询。
- `onWaitUntilFinished()` 使用 `busyWait()` 忙等待。

## 公共 API 函数

- **`DawnQueueManager(wgpu::Queue, const SharedContext*)`**：构造函数，接收 Dawn 队列和共享上下文。
- **`dawnQueue()`**：返回底层 `wgpu::Queue` 引用。
- **`tick()`**：驱动 Dawn 事件处理循环，委托给 `DawnSharedContext::tick()`。

## 内部实现细节

### 命令缓冲区创建
`getNewCommandBuffer()` 委托给 `DawnCommandBuffer::Make()`，传入 Dawn 共享上下文和资源提供者。

### GPU 提交流程
`onSubmitToGpu()` 执行以下步骤：
1. 将当前命令缓冲区转换为 `DawnCommandBuffer`。
2. 调用 `finishEncoding()` 获取 `wgpu::CommandBuffer`。
3. 编码失败时调用 `callFinishedProcs(false)` 并返回空。
4. 调用 `fQueue.Submit()` 提交命令缓冲区。
5. 根据平台创建对应的 `GpuWorkSubmission` 对象跟踪完成状态。

### 平台差异
- **原生 Dawn**：使用 `wgpu::Future` 和 `WaitAny` API，支持高效的非阻塞/阻塞等待。
- **Emscripten**：`wgpu::Future` 尚不可用，回退使用 `DawnAsyncWait` 的回调 + 轮询机制。

## 依赖关系

- **基类**: `QueueManager`
- **Dawn 后端类**: `DawnSharedContext`、`DawnCommandBuffer`、`DawnResourceProvider`、`DawnAsyncWait`
- **WebGPU API**: `wgpu::Queue`、`wgpu::Future`、`wgpu::FutureWaitInfo`

## 设计模式与设计决策

1. **策略模式**：根据平台在编译期选择不同的 `GpuWorkSubmission` 实现，分别使用 `wgpu::Future`（原生）和 `DawnAsyncWait`（Emscripten）。
2. **命令缓冲区所有权转移**：提交后命令缓冲区的所有权从 `QueueManager` 转移到 `GpuWorkSubmission`，确保资源在 GPU 执行完成前不会被释放。
3. **Tick 机制**：`tick()` 方法驱动 Dawn 实例处理异步回调和事件，是事件循环的关键组成部分。

## 性能考量

- **非阻塞完成检查**：`onIsFinished()` 使用零超时检查，避免不必要的阻塞。
- **最小化提交开销**：每次提交仅包含一个命令缓冲区，与 Dawn 的队列模型匹配。
- **Future vs AsyncWait**：原生 Dawn 的 `wgpu::Future` 比 Emscripten 的轮询方式更高效。

## 相关文件

- `src/gpu/graphite/QueueManager.h` - 基类定义
- `src/gpu/graphite/dawn/DawnCommandBuffer.h` - Dawn 命令缓冲区
- `src/gpu/graphite/dawn/DawnSharedContext.h` - Dawn 共享上下文
- `src/gpu/graphite/dawn/DawnAsyncWait.h` - 异步等待辅助类
- `src/gpu/graphite/dawn/DawnResourceProvider.h` - Dawn 资源提供者
