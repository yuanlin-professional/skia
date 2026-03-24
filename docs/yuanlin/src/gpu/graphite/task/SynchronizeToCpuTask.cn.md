# SynchronizeToCpuTask -- GPU 到 CPU 同步任务

> 源文件:
> - `src/gpu/graphite/task/SynchronizeToCpuTask.h`
> - `src/gpu/graphite/task/SynchronizeToCpuTask.cpp`

## 概述

SynchronizeToCpuTask 是 Graphite 任务系统中的一个具体任务类型,用于确保 GPU 对缓冲区的修改在 CPU 端可见。典型用例包括像素回读操作,在 GPU 将渲染结果写入缓冲区后,需要同步以便 CPU 读取数据。对于不需要同步的缓冲区（如共享内存缓冲区）,该任务可能不产生实际工作。

## 架构位置

```
Task (抽象基类)
  -> SynchronizeToCpuTask  <-- 本模块
       -> CommandBuffer (命令缓冲区)
       -> Buffer (目标缓冲区)
```

该任务在 Recording 的任务列表中排列,在命令缓冲区构建阶段被调用。

## 主要类与结构体

### SynchronizeToCpuTask

```cpp
class SynchronizeToCpuTask final : public Task {
    sk_sp<Buffer> fBuffer;  // 需要同步的缓冲区
};
```

继承自 `Task`,是一个轻量级任务,持有对目标缓冲区的引用。

## 公共 API 函数

### Make -- 静态工厂方法

```cpp
static sk_sp<SynchronizeToCpuTask> Make(sk_sp<Buffer>);
```
创建同步任务,接管缓冲区的引用计数。

### prepareResources

```cpp
Status prepareResources(ResourceProvider*, ScratchResourceManager*,
                        sk_sp<const RuntimeEffectDictionary>) override;
```
始终返回 `kSuccess`,无需准备额外资源。

### addCommands

```cpp
Status addCommands(Context*, CommandBuffer*, ReplayTargetData) override;
```
调用 `CommandBuffer::synchronizeBufferToCpu()` 添加同步命令。成功返回 `kSuccess`,失败返回 `kFail`。注意:缓冲区通过 `std::move` 转移所有权给命令缓冲区。

## 内部实现细节

- 构造函数为 `explicit private`,仅通过 `Make` 工厂方法创建
- 缓冲区在 `addCommands` 中通过 `std::move(fBuffer)` 转移,任务执行后不再持有缓冲区引用
- 实际的同步操作由各后端的 `CommandBuffer` 实现决定（如 Vulkan 的管线屏障、Metal 的 blitEncoder 同步等）

## 依赖关系

- `Task` -- 任务基类
- `Buffer` -- Graphite 缓冲区抽象
- `CommandBuffer` -- 命令缓冲区（执行实际同步操作）

## 设计模式与设计决策

1. **命令模式**: 将同步操作封装为任务对象,可以与其他任务一起排列、排序和批量执行。
2. **所有权转移**: 在 `addCommands` 中将缓冲区移动给 `CommandBuffer`,确保缓冲区在 GPU 操作完成前保持有效。
3. **后端无关**: 任务本身不包含后端特定逻辑,同步的具体实现委托给各后端的 `CommandBuffer`。

## 性能考量

- 同步操作可能涉及 GPU 管线刷新或内存屏障,这是一个潜在的性能瓶颈点。
- 对于使用共享内存的平台（如统一内存架构），同步可能是无操作。
- `prepareResources` 的空实现避免了不必要的资源查找开销。

## 相关文件

- `src/gpu/graphite/task/Task.h` -- 任务基类
- `src/gpu/graphite/Buffer.h` -- 缓冲区抽象
- `src/gpu/graphite/CommandBuffer.h` -- 命令缓冲区接口
- `src/gpu/graphite/task/CopyTask.h` -- 相关的复制任务
