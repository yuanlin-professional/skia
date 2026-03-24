# task - GPU 任务管理系统

## 概述

`src/gpu/graphite/task/` 目录实现了 Skia Graphite 后端的 GPU 任务管理子系统。任务系统是 Graphite 渲染架构的执行核心，它将高层的绘制操作分解为离散的、可调度的任务单元，这些任务单元被组织成有向无环图（DAG），并按照依赖顺序提交到 GPU 命令缓冲区执行。

任务系统的设计围绕 `Task` 基类构建。每个任务都有一个两阶段的生命周期：首先是 `prepareResources()` 阶段，在此阶段任务实例化和准备 GPU 资源（如纹理、缓冲区）；然后是 `addCommands()` 阶段，在此阶段任务将具体的 GPU 命令（如渲染通道、数据拷贝、计算调度）记录到命令缓冲区中。任务的状态返回值（`Status`）支持三种结果：`kSuccess`（成功并可重放）、`kDiscard`（成功但为一次性操作，应从任务列表中移除）和 `kFail`（失败，整个 Recording 无效）。

`TaskList` 是任务的容器类，管理一组任务的有序执行。它支持自动清理返回 `kDiscard` 状态的任务，并通过 `ScratchResourceManager` 的作用域机制管理临时 GPU 资源的分配和回收。任务列表的 `prepareResources()` 方法会将每次调用包裹在一个新的 scratch 作用域中，确保子任务使用的临时资源能够在不再需要时被正确归还。

该子系统支持任务图中的资源共享与去重机制。`DrawTask` 通过实现 `ScratchResourceManager::PendingUseListener` 接口，追踪其目标纹理的待处理读取计数，避免同一任务在任务图中被多次引用时重复准备资源。当所有待处理的读取完成后，临时纹理会被归还给 `ScratchResourceManager` 以供复用。

任务系统还包含了对 Recording 重放（Replay）的支持。`ReplayTargetData` 结构体携带重放目标纹理、坐标偏移和裁剪区域信息，使得同一组命令可以被渲染到不同的目标位置。

## 架构图

```
                    +-------------------+
                    |    Recording      |
                    +--------+----------+
                             |
                             v
                    +-------------------+
                    |    TaskList       |  <-- 顶层任务列表
                    |  fTasks: TArray   |
                    +--------+----------+
                             |
              +---------+----+----+---------+
              |         |         |         |
              v         v         v         v
         +--------+ +--------+ +--------+ +--------+
         |DrawTask| |Upload  | |Copy    | |Compute |
         |        | |Task    | |Task    | |Task    |
         +---+----+ +--------+ +--------+ +--------+
             |
             v
        +----------+
        | TaskList |  <-- 子任务列表
        +----+-----+
             |
    +--------+--------+
    |        |        |
    v        v        v
+-------+ +------+ +------+
|Render | |Upload| |Clear |
|Pass   | |Task  | |Buff  |
|Task   | |      | |Task  |
+-------+ +------+ +------+

  Task 基类继承体系:
  +-------------------+
  |    Task (基类)     |
  | + prepareResources|
  | + addCommands     |
  | + visitPipelines  |
  | + visitProxies    |
  +-------------------+
       |
       +-- DrawTask              绘制任务（包含子任务列表）
       +-- RenderPassTask        渲染通道任务
       +-- ComputeTask           计算任务
       +-- UploadTask            数据上传任务
       +-- CopyBufferToBuffer    缓冲区拷贝
       +-- CopyTextureToBuffer   纹理到缓冲区拷贝
       +-- CopyTextureToTexture  纹理到纹理拷贝
       +-- ClearBuffersTask      缓冲区清零
       +-- SynchronizeToCpuTask  GPU->CPU 同步
```

## 目录结构

```
src/gpu/graphite/task/
|-- BUILD.bazel                  # Bazel 构建配置
|-- Task.h                       # Task 基类定义
|-- TaskList.h                   # 任务列表容器
|-- TaskList.cpp                 # 任务列表实现
|-- DrawTask.h                   # 绘制任务（子任务容器）
|-- DrawTask.cpp                 # 绘制任务实现
|-- RenderPassTask.h             # 渲染通道任务
|-- RenderPassTask.cpp           # 渲染通道任务实现（核心，14KB+）
|-- ComputeTask.h                # 计算任务
|-- ComputeTask.cpp              # 计算任务实现
|-- CopyTask.h                   # 拷贝任务集合
|-- CopyTask.cpp                 # 拷贝任务实现
|-- UploadTask.h                 # 上传任务
|-- UploadTask.cpp               # 上传任务实现（最大文件，25KB+）
|-- ClearBuffersTask.h           # 缓冲区清零任务
|-- ClearBuffersTask.cpp         # 缓冲区清零实现
|-- SynchronizeToCpuTask.h       # CPU 同步任务
|-- SynchronizeToCpuTask.cpp     # CPU 同步实现
```

## 关键类与函数

### Task
所有 GPU 任务的抽象基类，定义了任务的两阶段生命周期接口。

```cpp
class Task : public SkRefCnt {
public:
    struct ReplayTargetData {
        const Texture* fTarget;
        SkIVector fTranslation;
        SkIRect fClip;
    };

    enum class Status { kSuccess, kDiscard, kFail };

    virtual Status prepareResources(ResourceProvider*,
                                    ScratchResourceManager*,
                                    sk_sp<const RuntimeEffectDictionary>) = 0;
    virtual Status addCommands(Context*, CommandBuffer*, ReplayTargetData) = 0;
    virtual bool visitPipelines(const std::function<bool(const GraphicsPipeline*)>&);
    virtual bool visitProxies(const std::function<bool(const TextureProxy*)>&, bool readsOnly);
};
```

### TaskList
任务容器，管理任务的有序执行，自动清理已丢弃的任务。

```cpp
class TaskList {
public:
    void add(TaskList&& tasks);
    void add(sk_sp<Task> task);
    void reset();
    int size() const;
    bool hasTasks() const;

    Task::Status prepareResources(ResourceProvider*, ScratchResourceManager*,
                                  sk_sp<const RuntimeEffectDictionary>);
    Task::Status addCommands(Context*, CommandBuffer*, Task::ReplayTargetData);
    bool visitPipelines(const std::function<bool(const GraphicsPipeline*)>&);
    bool visitProxies(const std::function<bool(const TextureProxy*)>&, bool readsOnly);
};
```

### DrawTask
绘制任务，作为子任务的容器。管理目标纹理代理和 scratch 资源的生命周期。

```cpp
class DrawTask final : public Task, private ScratchResourceManager::PendingUseListener {
public:
    explicit DrawTask(sk_sp<TextureProxy> target);
    Status prepareResources(ResourceProvider*, ScratchResourceManager*,
                            sk_sp<const RuntimeEffectDictionary>) override;
    Status addCommands(Context*, CommandBuffer*, ReplayTargetData) override;
private:
    friend class DrawContext;  // 允许 DrawContext 直接添加子任务
    void addTask(sk_sp<Task> task);
    void onUseCompleted(ScratchResourceManager*) override;  // scratch 纹理回收

    sk_sp<TextureProxy> fTarget;
    TaskList fChildTasks;
    bool fPrepared = false;
};
```

### RenderPassTask
渲染通道任务，将 DrawPass 列表打包到单个 GPU 渲染通道中执行。

```cpp
class RenderPassTask final : public Task {
public:
    using DrawPassList = skia_private::STArray<1, std::unique_ptr<DrawPass>>;

    static sk_sp<RenderPassTask> Make(DrawPassList, const RenderPassDesc&,
                                      sk_sp<TextureProxy> target,
                                      sk_sp<TextureProxy> dstCopy,
                                      SkIRect dstReadBounds);
private:
    DrawPassList fDrawPasses;
    RenderPassDesc fRenderPassDesc;
    sk_sp<TextureProxy> fTarget;
    sk_sp<TextureProxy> fDstCopy;
    SkIRect fDstReadBounds;
};
```

### UploadTask 与 UploadInstance
管理从 CPU 内存到 GPU 纹理的数据上传。支持条件上传（`ConditionalUploadContext`）和批量上传。

```cpp
class UploadInstance {
public:
    static UploadInstance Make(Recorder*, sk_sp<TextureProxy>, const SkColorInfo& src,
                               const SkColorInfo& dst, const UploadSource&, const SkIRect&,
                               std::unique_ptr<ConditionalUploadContext>);
    bool prepareResources(ResourceProvider*);
    Task::Status addCommand(Context*, CommandBuffer*, Task::ReplayTargetData) const;
};

class UploadTask final : public Task {
public:
    static sk_sp<UploadTask> Make(UploadList*);
    static sk_sp<UploadTask> Make(UploadInstance);
};
```

### ComputeTask
计算任务，将 DispatchGroup 记录为一系列计算调度命令。

```cpp
class ComputeTask final : public Task {
public:
    using DispatchGroupList = skia_private::STArray<1, std::unique_ptr<DispatchGroup>>;
    static sk_sp<ComputeTask> Make(DispatchGroupList dispatchGroups);
};
```

### CopyTask 系列
提供三种拷贝操作：`CopyBufferToBufferTask`（缓冲区间拷贝）、`CopyTextureToBufferTask`（纹理到缓冲区回读）和 `CopyTextureToTextureTask`（纹理间拷贝）。

### ClearBuffersTask
将一组缓冲区区域清零的任务。

### SynchronizeToCpuTask
确保 GPU 对缓冲区的修改对 CPU 可见的同步任务。

## 依赖关系

### 上游依赖（本目录依赖的模块）

| 模块 | 说明 |
|------|------|
| `src/gpu/graphite/CommandBuffer.h` | GPU 命令缓冲区接口 |
| `src/gpu/graphite/DrawPass.h` | 绘制通道，包含排序后的绘制命令 |
| `src/gpu/graphite/RenderPassDesc.h` | 渲染通道描述（附件格式、采样数等） |
| `src/gpu/graphite/ResourceProvider.h` | GPU 资源分配（纹理、缓冲区） |
| `src/gpu/graphite/ScratchResourceManager.h` | 临时资源管理与复用 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理，延迟实例化 |
| `src/gpu/graphite/Texture.h` | GPU 纹理对象 |
| `src/gpu/graphite/Caps.h` | GPU 能力查询 |
| `src/gpu/graphite/Context.h` | Graphite 上下文 |
| `src/gpu/graphite/compute/DispatchGroup.h` | 计算调度组 |
| `src/gpu/graphite/RuntimeEffectDictionary.h` | 运行时效果字典 |

### 下游依赖（依赖本目录的模块）

| 模块 | 说明 |
|------|------|
| `src/gpu/graphite/DrawContext.h` | 绘制上下文，生成和组织 DrawTask |
| `src/gpu/graphite/Recording.h` | 记录对象，持有顶层 TaskList |
| `src/gpu/graphite/QueueManager.h` | 队列管理器，调度 Recording 执行 |

## 设计模式分析

### 1. 命令模式（Command Pattern）
整个任务系统是命令模式的典型应用。每个 `Task` 子类封装了一个具体的 GPU 操作（渲染通道、数据上传、拷贝等），将请求封装为对象，使得可以对请求进行排队、记录和重放。`addCommands()` 方法对应命令的执行操作。

### 2. 组合模式（Composite Pattern）
`DrawTask` 和 `TaskList` 构成了经典的组合模式。`DrawTask` 包含一个 `TaskList` 子任务列表，可以嵌套其他任务（包括其他 `DrawTask`）。这使得复杂的渲染操作可以被递归地分解为更小的任务单元。

### 3. 两阶段初始化（Two-Phase Initialization）
任务执行分为 `prepareResources()` 和 `addCommands()` 两个阶段。第一阶段在 Recorder 线程上完成资源实例化（可能涉及共享资源分配），第二阶段在命令缓冲区构建时执行。这种分离允许资源准备和命令生成在不同的时机进行，提高了灵活性。

### 4. 观察者模式（Observer Pattern）
`DrawTask` 实现了 `ScratchResourceManager::PendingUseListener` 接口，当所有对 scratch 纹理的待处理读取完成时，`onUseCompleted()` 回调被触发，从而将纹理归还给 `ScratchResourceManager`。这是观察者模式在资源生命周期管理中的应用。

### 5. 模板方法模式（Template Method Pattern）
`TaskList::visitTasks()` 是一个私有模板方法，定义了遍历任务列表并处理状态返回值的算法骨架。`prepareResources()` 和 `addCommands()` 等公共方法通过传入不同的 lambda 来复用这个遍历逻辑。

### 6. 条件策略模式（Conditional Strategy）
`ConditionalUploadContext` 允许上传任务根据运行时条件决定是否执行上传。`ImageUploadContext` 是一个具体策略，它始终执行上传但之后立即丢弃（一次性上传）。

## 数据流

```
1. 绘制记录阶段（Recorder 线程）:
   DrawContext 创建和组织任务
     |-- 创建 DrawTask(targetProxy)
     |-- 添加子任务:
     |     |-- UploadTask (纹理数据上传)
     |     |-- RenderPassTask (渲染通道)
     |     |-- CopyTextureToTextureTask (Dst 拷贝)
     |
     v
2. 资源准备阶段:
   TaskList.prepareResources()
     |-- ScratchResourceManager.pushScope()
     |-- for each task:
     |     |-- DrawTask.prepareResources()
     |     |     |-- 检查 pendingReadCount (scratch 去重)
     |     |     |-- 标记资源使用: markResourceInUse()
     |     |     |-- fChildTasks.prepareResources()
     |     |           |-- RenderPassTask.prepareResources()
     |     |           |     |-- 实例化目标纹理 (InstantiateIfNotLazy)
     |     |           |     |-- DrawPass.prepareResources()
     |     |           |     |-- 通知资源消费完成
     |     |           |-- UploadTask.prepareResources()
     |     |                 |-- 实例化上传目标纹理
     |-- ScratchResourceManager.popScope()
     |
     v
3. 命令生成阶段:
   TaskList.addCommands(context, commandBuffer, replayData)
     |-- for each task:
     |     |-- DrawTask.addCommands()
     |     |     |-- fChildTasks.addCommands()
     |     |           |-- RenderPassTask.addCommands()
     |     |           |     |-- 创建/获取 MSAA 附件
     |     |           |     |-- 创建/获取 深度/模板附件
     |     |           |     |-- 设置重放坐标变换与裁剪
     |     |           |     |-- CommandBuffer.addRenderPass()
     |     |           |-- UploadTask.addCommands()
     |     |           |     |-- 检查 ConditionalUploadContext
     |     |           |     |-- CommandBuffer.copyBufferToTexture()
     |     |           |-- CopyTask.addCommands()
     |     |                 |-- CommandBuffer.copyTextureToTexture()
     |
     v
4. GPU 提交与执行:
   CommandBuffer 被提交到 GPU 队列执行
```

## 相关文档与参考

- `src/gpu/graphite/DrawContext.h` - 绘制上下文，任务图的生产者
- `src/gpu/graphite/Recording.h` - 记录对象，持有最终的任务图
- `src/gpu/graphite/CommandBuffer.h` - GPU 命令缓冲区抽象
- `src/gpu/graphite/DrawPass.h` - 绘制通道，排序后的绘制命令
- `src/gpu/graphite/RenderPassDesc.h` - 渲染通道描述
- `src/gpu/graphite/ResourceProvider.h` - 资源提供者
- `src/gpu/graphite/ScratchResourceManager.h` - 临时资源管理
- `src/gpu/graphite/TextureProxy.h` - 纹理代理
- `src/gpu/graphite/compute/DispatchGroup.h` - 计算调度组
