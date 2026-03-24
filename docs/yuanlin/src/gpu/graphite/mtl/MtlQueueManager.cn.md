# MtlQueueManager -- Metal 队列管理器

> 源文件:
> - `src/gpu/graphite/mtl/MtlQueueManager.h`
> - `src/gpu/graphite/mtl/MtlQueueManager.mm`

## 概述

MtlQueueManager 是 Graphite Metal 后端的队列管理器实现,继承自 `QueueManager` 基类。它管理 Metal 命令队列,负责命令缓冲区的创建和 GPU 工作提交。与 Vulkan 后端不同,Metal 的提交通过命令缓冲区的 `commit` 方法完成,队列本身主要用于创建命令缓冲区。

## 架构位置

```
QueueManager (抽象基类)
  -> MtlQueueManager  <-- 本模块
       -> id<MTLCommandQueue> (Metal 命令队列)
       -> MtlCommandBuffer (命令缓冲区)
       -> MtlWorkSubmission (提交追踪)
```

## 主要类与结构体

### MtlQueueManager

```cpp
class MtlQueueManager : public QueueManager {
    sk_cfp<id<MTLCommandQueue>> fQueue;  // 持有引用计数的队列
};
```

### MtlWorkSubmission (内部类)

封装已提交的命令缓冲区,委托 `MtlCommandBuffer` 查询完成状态。

## 公共 API 函数

### 构造函数
```cpp
MtlQueueManager(sk_cfp<id<MTLCommandQueue>> queue, const SharedContext*);
```
接管命令队列的引用计数（与 Vulkan 不同,这里持有所有权）。

## 内部实现细节

### getNewCommandBuffer
将 `ResourceProvider` 转型为 `MtlResourceProvider`,创建 `MtlCommandBuffer`。

### onSubmitToGpu
调用 `MtlCommandBuffer::commit()` 提交命令缓冲区,成功后包装为 `MtlWorkSubmission`。

### GPU 捕获（测试专用）
```cpp
void startCapture() override;
void stopCapture() override;
```
使用 `MTLCaptureManager` 和 `MTLCaptureDescriptor` 实现 GPU 命令捕获,用于调试和测试。捕获目标设为命令队列。

## 依赖关系

- `QueueManager` -- 基类
- `MtlCommandBuffer` -- 命令缓冲区
- `MtlResourceProvider` -- 资源管理
- `MtlSharedContext` -- 共享上下文
- `GpuWorkSubmission` -- 提交追踪基类

## 设计模式与设计决策

1. **引用计数队列**: 使用 `sk_cfp` 持有队列引用,确保队列在 QueueManager 生命周期内有效。
2. **commit 模型**: Metal 的提交通过命令缓冲区的 `commit` 方法直接完成,不需要显式队列提交。
3. **捕获隔离**: GPU 捕获功能仅在 `GPU_TEST_UTILS` 编译模式下可用。

## 性能考量

- 队列创建是一次性开销,通过外部提供的 `MtlBackendContext` 完成。
- 命令缓冲区提交是异步的,`MtlWorkSubmission` 通过轮询或等待追踪完成状态。

## 相关文件

- `src/gpu/graphite/QueueManager.h` -- 队列管理基类
- `src/gpu/graphite/mtl/MtlCommandBuffer.h` -- Metal 命令缓冲区
- `src/gpu/graphite/mtl/MtlSharedContext.h` -- Metal 共享上下文
- `src/gpu/graphite/GpuWorkSubmission.h` -- GPU 工作提交基类
