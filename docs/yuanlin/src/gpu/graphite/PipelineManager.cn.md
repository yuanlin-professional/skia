# PipelineManager

> 源文件
> - src/gpu/graphite/PipelineManager.h
> - src/gpu/graphite/PipelineManager.cpp

## 概述

`PipelineManager` 是 Graphite 渲染引擎中负责管理图形管线（Graphics Pipeline）创建和生命周期的核心组件。它通过任务系统协调管线的异步编译过程，避免重复创建相同的管线，并在多线程环境中提供线程安全的访问机制。

该类的主要职责包括：
1. **管线句柄创建**：为管线描述符生成轻量级句柄，句柄可能指向正在创建的任务或已完成的管线对象
2. **任务去重**：维护活动任务映射表，确保相同的管线键不会触发多次编译
3. **异步编译协调**：启动管线创建任务并在任务完成后清理资源
4. **句柄解析**：将管线句柄解析为实际的管线对象，等待任务完成（如果需要）

`PipelineManager` 使用自旋锁保护内部状态，设计为支持高并发的轻量级同步机制。

## 架构位置

`PipelineManager` 位于 Graphite 渲染管线的编译和缓存层：

```
skgpu::graphite 命名空间
├── SharedContext (共享上下文 - 拥有 PipelineManager)
│   ├── PipelineManager (管线管理器)
│   │   ├── GraphicsPipelineHandle (管线句柄 - 可能包含任务或管线)
│   │   └── PipelineCreationTask (管线创建任务)
│   ├── GlobalCache (全局缓存 - 存储完成的管线)
│   └── Caps (能力抽象 - 生成管线键)
├── GraphicsPipelineDesc (管线描述符)
├── RenderPassDesc (渲染通道描述符)
└── RuntimeEffectDictionary (运行时效果字典)
```

`PipelineManager` 作为 `SharedContext` 的组成部分，在录制和提交阶段协调管线的准备工作。

## 主要类与结构体

### PipelineManager 类

```cpp
class PipelineManager {
public:
    PipelineManager();
    ~PipelineManager();

    GraphicsPipelineHandle createHandle(
        SharedContext*,
        const GraphicsPipelineDesc&,
        const RenderPassDesc&,
        SkEnumBitMask<PipelineCreationFlags>);

    void startPipelineCreationTask(SharedContext*,
                                   sk_sp<const RuntimeEffectDictionary>,
                                   const GraphicsPipelineHandle&);

    sk_sp<GraphicsPipeline> resolveHandle(const GraphicsPipelineHandle&);

private:
    mutable SkSpinlock fSpinLock;
    TaskMap fActiveTasks SK_GUARDED_BY(fSpinLock);
};
```

**核心成员变量：**
- `fSpinLock`: 保护 `fActiveTasks` 的自旋锁
- `fActiveTasks`: 活动任务的哈希表，键为 `UniqueKey`

### GraphicsPipelineHandle 类

```cpp
class GraphicsPipelineHandle {
    std::variant<sk_sp<PipelineCreationTask>, sk_sp<GraphicsPipeline>> fTaskOrPipeline;
};
```

**设计意图：**
- 使用 `std::variant` 持有任务或管线对象
- 轻量级：仅包含一个智能指针的大小
- 延迟求值：句柄创建时管线可能尚未编译完成

### PipelineCreationTask 类

```cpp
class PipelineCreationTask {
    UniqueKey fPipelineKey;
    GraphicsPipelineDesc fGraphicsPipelineDesc;
    RenderPassDesc fRenderPassDesc;
    SkEnumBitMask<PipelineCreationFlags> fPipelineCreationFlags;
    std::atomic<bool> fCompleted;
    sk_sp<GraphicsPipeline> fPipeline;
};
```

**职责：**
- 存储管线编译所需的所有信息
- 使用原子布尔值 `fCompleted` 跟踪任务状态
- 编译完成后持有结果管线对象

### Traits 结构体

```cpp
struct Traits {
    static const UniqueKey& GetKey(const sk_sp<PipelineCreationTask>&);
    static uint32_t Hash(const UniqueKey& pipelineKey);
};
using TaskMap = skia_private::THashTable<sk_sp<PipelineCreationTask>, UniqueKey, Traits>;
```

为 `THashTable` 提供键提取和哈希函数，使用 `UniqueKey` 作为任务的查找键。

### Stats 结构体（测试工具）

```cpp
#if defined(GPU_TEST_UTILS)
struct Stats {
    int fNumPreemptivelyFoundTasks = 0;  // 提前找到已有任务的次数
    int fNumTasksCreated = 0;            // 创建新任务的次数
    int fNumTaskCreationRaces = 0;       // 任务创建竞争的次数
};
#endif
```

用于性能分析和测试验证，跟踪任务去重效果和竞态条件发生频率。

## 公共 API 函数

### createHandle

```cpp
GraphicsPipelineHandle createHandle(
    SharedContext* sharedContext,
    const GraphicsPipelineDesc& pipelineDesc,
    const RenderPassDesc& renderPassDesc,
    SkEnumBitMask<PipelineCreationFlags> pipelineCreationFlags);
```

**功能：**为指定的管线配置创建一个句柄。

**执行流程：**
1. 根据描述符生成 `UniqueKey`（通过 `Caps::makeGraphicsPipelineKey`）
2. 检查是否已有活动任务正在编译该管线
3. 如果没有任务，查找全局缓存中的已编译管线
4. 如果缓存未命中，创建或复用任务

**返回值：**
- 包含 `PipelineCreationTask` 的句柄（如果需要编译）
- 包含 `GraphicsPipeline` 的句柄（如果已缓存）

**实现逻辑：**
```cpp
UniqueKey pipelineKey = caps->makeGraphicsPipelineKey(pipelineDesc, renderPassDesc);

if (sk_sp<PipelineCreationTask> task = this->findTask(pipelineKey)) {
    return GraphicsPipelineHandle(std::move(task));
}

sk_sp<GraphicsPipeline> pipeline = globalCache->findGraphicsPipeline(
    pipelineKey, pipelineCreationFlags);
if (pipeline) {
    return GraphicsPipelineHandle(std::move(pipeline));
}

sk_sp<PipelineCreationTask> task = this->findOrCreateTask(
    pipelineKey, pipelineDesc, renderPassDesc, pipelineCreationFlags);
return GraphicsPipelineHandle(std::move(task));
```

**竞态处理：**注释提到存在竞态窗口：在首次检查任务和检查缓存之间，另一个线程可能已经创建了任务。这由 `findOrCreateTask` 内部再次检查处理。

### startPipelineCreationTask

```cpp
void startPipelineCreationTask(SharedContext* sharedContext,
                               sk_sp<const RuntimeEffectDictionary> runtimeDict,
                               const GraphicsPipelineHandle& handle);
```

**功能：**启动管线创建任务的实际执行。

**前提条件：**句柄必须包含 `PipelineCreationTask`（如果包含 `GraphicsPipeline` 则直接返回）。

**执行流程：**
1. 从句柄中提取任务对象
2. 调用 `SharedContext::findOrCreateGraphicsPipeline` 执行实际编译
3. 使用原子操作设置任务完成状态（`fCompleted.exchange(true)`）
4. 将编译结果存储到任务的 `fPipeline` 成员
5. 从活动任务表中移除任务

**原子操作的作用：**
```cpp
if (!task->fCompleted.exchange(true)) {
    task->fPipeline = pipeline;
    this->removeTask(task.get());
}
```

`exchange(true)` 返回旧值，只有第一个完成任务的线程才会执行清理逻辑，避免重复移除。

**错误处理：**
```cpp
if (!pipeline) {
    SKGPU_LOG_W("Failed to create GraphicsPipeline!");
}
```

即使编译失败，任务也会被标记为完成并清理，避免永久阻塞。

### resolveHandle

```cpp
sk_sp<GraphicsPipeline> resolveHandle(const GraphicsPipelineHandle& handle);
```

**功能：**将句柄解析为实际的管线对象。

**行为：**
- 如果句柄包含管线：直接返回
- 如果句柄包含任务：等待任务完成并返回结果管线

**实现逻辑：**
```cpp
if (std::holds_alternative<sk_sp<GraphicsPipeline>>(handle.fTaskOrPipeline)) {
    return std::get<sk_sp<GraphicsPipeline>>(handle.fTaskOrPipeline);
}

sk_sp<PipelineCreationTask> task =
    std::get<sk_sp<PipelineCreationTask>>(handle.fTaskOrPipeline);

SkASSERT(task->fCompleted);  // 非线程版本假设任务已完成
return task->fPipeline;
```

**非线程版本的特殊性：**注释指出，在非线程版本中，线程在到达这里之前已经在 `DrawPass::prepareResources` 中盲目执行了任务，因此任务必定已完成。

### getStats（测试工具）

```cpp
#if defined(GPU_TEST_UTILS)
Stats getStats() const SK_EXCLUDES(fSpinLock);
#endif
```

**功能：**返回任务管理的统计信息，用于测试和性能分析。

**线程安全：**使用 `SkAutoSpinlock` 保护读取。

## 内部实现细节

### findTask

```cpp
sk_sp<PipelineCreationTask> findTask(const UniqueKey& pipelineKey) SK_EXCLUDES(fSpinLock);
```

**功能：**在活动任务表中查找指定键的任务。

**线程安全：**使用 `SkAutoSpinlock` 保护哈希表访问。

**统计跟踪：**
```cpp
#if defined(GPU_TEST_UTILS)
if (task) {
    fStats.fNumPreemptivelyFoundTasks++;
}
#endif
```

记录成功找到已有任务的次数，用于评估去重效果。

### findOrCreateTask

```cpp
sk_sp<PipelineCreationTask> findOrCreateTask(
    const UniqueKey& pipelineKey,
    const GraphicsPipelineDesc& pipelineDesc,
    const RenderPassDesc& renderPassDesc,
    SkEnumBitMask<PipelineCreationFlags> pipelineCreationFlags) SK_EXCLUDES(fSpinLock);
```

**功能：**查找或创建管线创建任务。

**竞态处理：**
```cpp
sk_sp<PipelineCreationTask>* task = fActiveTasks.find(pipelineKey);
if (task) {
    // 存在竞态：createHandle 中的检查序列允许多个线程同时尝试创建任务
#if defined(GPU_TEST_UTILS)
    fStats.fNumTaskCreationRaces++;
#endif
    return *task;
}
```

这个方法再次检查任务是否存在，处理 `createHandle` 中提到的竞态窗口。

**任务创建：**
```cpp
sk_sp<PipelineCreationTask> newTask = sk_sp<PipelineCreationTask>(
    new PipelineCreationTask(pipelineKey,
                             pipelineDesc,
                             renderPassDesc,
                             pipelineCreationFlags));
fActiveTasks.set(newTask);
return newTask;
```

直接使用 `new` 构造任务（可能 `PipelineCreationTask` 的构造函数是私有的），并插入活动任务表。

### removeTask

```cpp
void removeTask(PipelineCreationTask* task) SK_EXCLUDES(fSpinLock);
```

**功能：**从活动任务表中移除指定任务。

**防御性检查：**
```cpp
// TODO(robertphillips): 这个保护仅在非线程版本的 PipelineManager 中必要
if (fActiveTasks.findOrNull(task->fPipelineKey)) {
    fActiveTasks.remove(task->fPipelineKey);
}
```

在移除前检查任务是否存在，避免在非线程版本中重复移除导致的问题。

### Traits 实现

```cpp
const UniqueKey& PipelineManager::Traits::GetKey(
    const sk_sp<PipelineCreationTask>& task) {
    return task->fPipelineKey;
}

uint32_t PipelineManager::Traits::Hash(const UniqueKey& pipelineKey) {
    return pipelineKey.hash();
}
```

这些静态方法让 `THashTable` 能够使用 `UniqueKey` 作为查找键，即使表中存储的是 `sk_sp<PipelineCreationTask>`。

### GraphicsPipelineHandle 构造函数

```cpp
GraphicsPipelineHandle::GraphicsPipelineHandle(sk_sp<PipelineCreationTask> task)
    : fTaskOrPipeline(std::move(task)) {}

GraphicsPipelineHandle::GraphicsPipelineHandle(sk_sp<GraphicsPipeline> pipeline)
    : fTaskOrPipeline(std::move(pipeline)) {}
```

两个构造函数分别从任务和管线创建句柄，实现在 `PipelineManager.cpp` 中（可能为了避免循环依赖）。

## 依赖关系

### 直接依赖

| 依赖项 | 类型 | 用途 |
|-------|------|------|
| `GraphicsPipeline` | Graphite 管线 | 编译完成的管线对象 |
| `GraphicsPipelineDesc` | Graphite 描述符 | 管线配置描述 |
| `GraphicsPipelineHandle` | Graphite 句柄 | 轻量级管线引用 |
| `PipelineCreationTask` | Graphite 任务 | 管线编译任务 |
| `RenderPassDesc` | Graphite 描述符 | 渲染通道配置 |
| `RuntimeEffectDictionary` | Graphite 着色器 | 运行时效果字典 |
| `SharedContext` | Graphite 上下文 | 共享资源上下文 |
| `GlobalCache` | Graphite 缓存 | 全局管线缓存 |
| `Caps` | Graphite 能力 | 生成管线键 |
| `UniqueKey` | GPU 资源键 | 管线唯一标识 |
| `SkSpinlock` | Skia 并发 | 轻量级锁 |
| `THashTable` | Skia 容器 | 哈希表实现 |

### 被依赖关系

- `SharedContext`: 拥有 `PipelineManager` 实例
- `DrawPass`: 通过 `prepareResources` 触发管线准备
- 各种渲染组件：使用 `createHandle` 获取管线句柄

## 设计模式与设计决策

### 1. 句柄/代理模式（Handle/Proxy Pattern）

`GraphicsPipelineHandle` 是典型的句柄模式实现：
- **延迟求值**：句柄创建时管线可能尚未编译
- **透明性**：使用方无需关心句柄内部是任务还是管线
- **轻量级**：仅包含一个智能指针，可高效传递

**设计优势：**
- 解耦了管线请求和管线编译
- 允许异步编译的同时保持同步接口的简洁性

### 2. 命令模式（Command Pattern）

`PipelineCreationTask` 封装了管线创建的所有参数：
- 任务对象可被存储、传递、延迟执行
- 任务完成后存储执行结果

**设计决策：**
- 任务对象本身不执行编译逻辑（由 `SharedContext` 执行）
- 任务仅作为数据容器和状态跟踪器

### 3. 缓存模式（Cache Pattern）

`PipelineManager` 实现了两级缓存策略：
1. **任务级缓存**：`fActiveTasks` 避免重复创建编译任务
2. **结果级缓存**：`GlobalCache` 存储编译完成的管线

**缓存逻辑：**
```
createHandle 查找顺序：
1. 活动任务表 (PipelineManager::fActiveTasks)
2. 全局管线缓存 (GlobalCache)
3. 创建新任务 (findOrCreateTask)
```

### 4. 双检锁优化（Double-Checked Locking）

`createHandle` 使用了类似双检锁的模式，但存在已知的竞态：
```cpp
// 第一次检查（无锁）
if (sk_sp<PipelineCreationTask> task = this->findTask(pipelineKey)) {
    return GraphicsPipelineHandle(std::move(task));
}

// 检查全局缓存
sk_sp<GraphicsPipeline> pipeline = globalCache->findGraphicsPipeline(...);
if (pipeline) {
    return GraphicsPipelineHandle(std::move(pipeline));
}

// 第二次检查（带锁，在 findOrCreateTask 内部）
sk_sp<PipelineCreationTask> task = this->findOrCreateTask(...);
```

**竞态窗口：**在第一次检查和创建任务之间，另一个线程可能已经创建了任务或管线。

**解决方案：**`findOrCreateTask` 内部再次检查，并通过 `fNumTaskCreationRaces` 统计跟踪竞态发生频率。

### 5. 原子操作的一次性执行保证

```cpp
if (!task->fCompleted.exchange(true)) {
    task->fPipeline = pipeline;
    this->removeTask(task.get());
}
```

使用 `std::atomic<bool>` 的 `exchange` 操作确保只有一个线程执行清理逻辑：
- 多个线程可能同时完成同一个任务（在线程版本中）
- `exchange` 返回旧值，只有第一个调用的线程看到 `false`
- 其他线程看到 `true`，跳过清理逻辑

### 6. 自旋锁的选择

使用 `SkSpinlock` 而非互斥锁：

**理由：**
- 临界区非常短（仅哈希表查找/插入/删除）
- 无阻塞操作或系统调用
- 高并发场景下自旋锁的开销更低

**权衡：**
- 如果临界区变长，自旋锁会浪费 CPU 时间
- 适用于锁竞争不激烈的场景

## 性能考量

### 1. 任务去重效果

**统计指标：**
- `fNumPreemptivelyFoundTasks`: 成功避免重复任务的次数
- `fNumTasksCreated`: 实际创建的任务数量
- `fNumTaskCreationRaces`: 竞态导致的重复检查次数

**理想情况：**`fNumPreemptivelyFoundTasks` 应远大于 `fNumTasksCreated`，表示去重机制工作良好。

### 2. 竞态条件的影响

**竞态场景：**
```
线程 A                    线程 B
findTask(key) -> null
                          findTask(key) -> null
globalCache->find -> null
                          globalCache->find -> null
findOrCreateTask(key)
                          findOrCreateTask(key) -> 发现 A 创建的任务
```

**性能影响：**
- `fNumTaskCreationRaces` 表示检查了两次任务表的频率
- 竞态本身不影响正确性，但会轻微增加锁竞争

**优化思路：**
- 合并第一次 `findTask` 和 `globalCache->find` 的检查
- 但可能需要更复杂的锁策略或更粗粒度的锁

### 3. 自旋锁的性能特征

**优势：**
- 无上下文切换开销
- 临界区极短（~纳秒级）
- 适合多核高并发

**潜在问题：**
- 锁竞争激烈时会浪费 CPU 时间
- 不适合长临界区或可能阻塞的操作

**当前实现：**所有临界区操作都是快速的哈希表查找/修改，自旋锁是合适的选择。

### 4. 管线缓存命中率

`PipelineManager` 的效率依赖于 `GlobalCache` 的命中率：
- 高命中率：大部分 `createHandle` 调用直接返回缓存的管线
- 低命中率：频繁创建任务和编译管线，增加延迟

**影响因素：**
- 管线描述符的多样性
- 缓存大小和清理策略
- 应用的渲染模式（静态 vs 动态）

### 5. 非线程版本的简化

注释提到非线程版本的特殊性：
- 任务在 `DrawPass::prepareResources` 中同步执行
- `resolveHandle` 可以假设任务已完成
- `removeTask` 需要防御性检查避免重复移除

**性能影响：**
- 非线程版本更简单但无法利用异步编译
- 管线编译会阻塞录制线程

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/GraphicsPipeline.h` | 使用 | 编译完成的管线对象 |
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 使用 | 管线配置描述符 |
| `src/gpu/graphite/GraphicsPipelineHandle.h` | 使用 | 管线句柄定义 |
| `src/gpu/graphite/PipelineCreationTask.h` | 使用 | 管线创建任务 |
| `src/gpu/graphite/RenderPassDesc.h` | 使用 | 渲染通道描述符 |
| `src/gpu/graphite/RuntimeEffectDictionary.h` | 使用 | 运行时效果字典 |
| `src/gpu/graphite/SharedContext.h` | 被包含 | 共享上下文拥有管理器 |
| `src/gpu/graphite/GlobalCache.h` | 使用 | 全局管线缓存 |
| `src/gpu/graphite/Caps.h` | 使用 | 生成管线键 |
| `src/gpu/ResourceKey.h` | 使用 | UniqueKey 定义 |
| `src/base/SkSpinlock.h` | 使用 | 自旋锁实现 |
| `src/core/SkTHash.h` | 使用 | 哈希表实现 |
| `src/core/SkTaskGroup.h` | 使用 | 任务组（用于异步执行） |
| `src/gpu/graphite/Log.h` | 使用 | 日志记录 |
