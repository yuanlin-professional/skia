# PipelineCreationTask

> 源文件
> - src/gpu/graphite/PipelineCreationTask.h

## 概述

`PipelineCreationTask` 是 Skia Graphite 渲染引擎中用于异步管线创建的任务类。该类封装了图形管线编译所需的所有信息，支持将管线编译工作委托给线程池，并在完成后锁定管线在缓存中的位置。

与 Graphite 的其他 `Task` 类（如 `RenderPassTask`）不同，`PipelineCreationTask` 不会被添加到 `TaskList`，而是由 `PipelineManager` 专门管理和调度。完成后的任务持有编译好的 `GraphicsPipeline` 引用，防止其在任务存活期间被驱逐。

## 架构位置

```
PipelineManager
  └── PipelineCreationTask (管线编译任务)
      ├── GraphicsPipelineDesc (管线描述)
      ├── RenderPassDesc (渲染通道描述)
      └── GraphicsPipeline (编译结果)
```

该类位于管线编译系统的核心，连接管线描述和实际的 GPU 管线对象。

## 主要类与结构体

### PipelineCreationTask

```cpp
class PipelineCreationTask : public SkRefCnt {
private:
    friend class PipelineManager;  // 仅 PipelineManager 可访问

    PipelineCreationTask(const UniqueKey& pipelineKey,
                         const GraphicsPipelineDesc& graphicsPipelineDesc,
                         const RenderPassDesc& renderPassDesc,
                         SkEnumBitMask<PipelineCreationFlags> pipelineCreationFlags);

    const UniqueKey fPipelineKey;
    const GraphicsPipelineDesc fGraphicsPipelineDesc;
    const RenderPassDesc fRenderPassDesc;
    const SkEnumBitMask<PipelineCreationFlags> fPipelineCreationFlags;

    sk_sp<GraphicsPipeline> fPipeline;  // 编译完成后填充
    std::atomic<bool> fCompleted = false;
};
```

**核心职责**：
- 存储管线编译所需的描述信息
- 跟踪编译状态（`fCompleted`）
- 持有编译结果并锁定缓存

**关键成员说明**：

#### fPipelineKey

```cpp
const UniqueKey fPipelineKey;
```

**用途**：在 `PipelineManager` 中跟踪此任务的唯一标识

**类型**：`UniqueKey`（唯一键）

#### fGraphicsPipelineDesc

```cpp
const GraphicsPipelineDesc fGraphicsPipelineDesc;
```

**用途**：图形管线的完整描述

**包含信息**：
- 渲染步骤（RenderStep）
- 着色器键（PaintParamsKey）
- 原始顶点属性
- 混合模式
- 等等

#### fRenderPassDesc

```cpp
const RenderPassDesc fRenderPassDesc;
```

**用途**：渲染通道的描述

**包含信息**：
- 颜色附件格式
- 深度/模板附件格式
- MSAA 样本数
- 加载/存储操作

#### fPipelineCreationFlags

```cpp
const SkEnumBitMask<PipelineCreationFlags> fPipelineCreationFlags;
```

**用途**：控制管线创建的标志

**可能的标志**（举例）：
- 启用调试信息
- 跳过某些优化
- 强制重新编译

#### fPipeline

```cpp
sk_sp<GraphicsPipeline> fPipeline;
```

**用途**：存储编译完成的管线对象

**生命周期**：
- 初始为空
- 编译成功后填充
- 任务存活期间锁定管线在缓存中

**缓存锁定**：
- `sk_sp` 持有引用计数
- 防止管线被驱逐
- 任务销毁时自动释放

#### fCompleted

```cpp
std::atomic<bool> fCompleted = false;
```

**用途**：原子标志，指示编译是否完成

**线程安全**：使用 `std::atomic` 确保多线程访问安全

## 公共 API 函数

**注意**：该类没有公共 API，所有接口都是 `private`，仅 `PipelineManager` 可访问。

### 构造函数（private）

```cpp
PipelineCreationTask(const UniqueKey& pipelineKey,
                     const GraphicsPipelineDesc& graphicsPipelineDesc,
                     const RenderPassDesc& renderPassDesc,
                     SkEnumBitMask<PipelineCreationFlags> pipelineCreationFlags);
```

**调用者**：`PipelineManager::createPipelineTask`

**参数验证**：假设所有参数已验证

## 内部实现细节

### 编译流程（由 PipelineManager 管理）

1. **任务创建**：
   ```cpp
   sk_sp<PipelineCreationTask> task = sk_make_sp<PipelineCreationTask>(key, desc, ...);
   ```

2. **提交到线程池**：
   ```cpp
   threadPool->submit([task]() {
       task->fPipeline = compileGraphicsPipeline(task->fGraphicsPipelineDesc, task->fRenderPassDesc);
       task->fCompleted.store(true, std::memory_order_release);
   });
   ```

3. **等待完成**（可选）：
   ```cpp
   while (!task->fCompleted.load(std::memory_order_acquire)) {
       // 等待或执行其他工作
   }
   ```

4. **使用管线**：
   ```cpp
   if (task->fPipeline) {
       // 编译成功，使用管线
   } else {
       // 编译失败，处理错误
   }
   ```

### 线程安全

#### 原子操作

```cpp
std::atomic<bool> fCompleted;
```

**内存顺序**：
- **写入**（编译线程）：`memory_order_release`
- **读取**（主线程）：`memory_order_acquire`
- **效果**：确保 `fPipeline` 的写入对读取 `fCompleted` 的线程可见

#### 引用计数

```cpp
class PipelineCreationTask : public SkRefCnt
```

**线程安全性**：
- `SkRefCnt` 提供线程安全的引用计数
- 多个线程可以同时持有 `sk_sp<PipelineCreationTask>`

### 缓存锁定机制

```cpp
sk_sp<GraphicsPipeline> fPipeline;
```

**工作原理**：
1. 管线缓存使用弱引用或引用计数跟踪管线
2. `PipelineCreationTask` 持有 `sk_sp`，增加引用计数
3. 缓存驱逐时检查引用计数，跳过被锁定的管线
4. 任务销毁时，`sk_sp` 析构，释放引用

**好处**：
- 防止正在使用的管线被驱逐
- 自动管理，无需手动解锁

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `SkRefCnt` | 引用计数基类 |
| `GraphicsPipeline` | 编译后的图形管线 |
| `GraphicsPipelineDesc` | 管线描述 |
| `RenderPassDesc` | 渲染通道描述 |
| `UniqueKey` | 唯一键 |
| `PipelineCreationFlags` | 创建标志 |

### 管理者

| 类型 | 关系 |
|------|------|
| `PipelineManager` | 创建、调度和管理任务 |

## 设计模式与设计决策

### 1. 任务对象模式

将编译工作封装为对象，支持异步执行：

```cpp
task = createTask(params);
submit(task);
// ... 稍后 ...
use(task->result());
```

### 2. RAII 资源管理

通过 `sk_sp<GraphicsPipeline>` 自动管理缓存锁定：

```cpp
{
    sk_sp<PipelineCreationTask> task = ...;
    // 管线被锁定
}  // task 销毁，管线自动解锁
```

### 3. 友元访问控制

通过 `friend class PipelineManager` 限制访问：
- 所有成员和构造函数都是 `private`
- 仅 `PipelineManager` 可以创建和操作任务
- 防止外部代码直接操作

### 4. 原子状态标志

使用 `std::atomic<bool>` 而非互斥锁：
- 轻量级（仅一个标志）
- 无锁等待（可选）
- 适合简单的完成状态

### 5. 不可变描述

所有描述字段都是 `const`：
- 创建后不可修改
- 线程安全（无竞争）
- 清晰的语义

## 性能考量

### 异步编译

1. **并行化**：多个管线可同时编译
2. **非阻塞**：不阻塞渲染线程
3. **预编译**：可以提前编译预期需要的管线

### 缓存锁定开销

1. **引用计数**：原子操作（较低开销）
2. **内存占用**：一个 `sk_sp`（8 字节）
3. **驱逐检查**：轻量级引用计数检查

### 完成检查

```cpp
task->fCompleted.load(std::memory_order_acquire);
```

**开销**：单个原子加载（非常快）

**优化**：可以批量检查多个任务，避免频繁轮询

### 内存顺序

使用 `release-acquire` 而非 `seq_cst`：
- 更轻量级
- 足够保证正确性
- 允许更多编译器优化

## 使用模式

### 提交任务（由 PipelineManager）

```cpp
sk_sp<PipelineCreationTask> task = sk_make_sp<PipelineCreationTask>(
    key, desc, renderPassDesc, flags);

fTaskMap.insert(key, task);  // 跟踪任务

fThreadPool->submit([task, this]() {
    this->compilePipeline(task);
});
```

### 编译函数（伪代码）

```cpp
void PipelineManager::compilePipeline(sk_sp<PipelineCreationTask> task) {
    sk_sp<GraphicsPipeline> pipeline = fResourceProvider->createGraphicsPipeline(
        task->fGraphicsPipelineDesc,
        task->fRenderPassDesc);

    task->fPipeline = std::move(pipeline);
    task->fCompleted.store(true, std::memory_order_release);
}
```

### 等待和使用

```cpp
sk_sp<GraphicsPipeline> getPipeline(const UniqueKey& key) {
    sk_sp<PipelineCreationTask>* taskPtr = fTaskMap.find(key);
    if (taskPtr) {
        sk_sp<PipelineCreationTask> task = *taskPtr;
        // 等待完成（可选）
        while (!task->fCompleted.load(std::memory_order_acquire)) {
            // 可以执行其他工作或挂起
        }
        return task->fPipeline;
    }
    return nullptr;
}
```

## 限制和约束

### 私有接口

所有成员都是 `private`，外部代码无法直接创建或操作任务。

### 单次使用

任务创建后，描述字段不可修改，编译结果只能写入一次。

### 依赖 PipelineManager

任务的生命周期和使用完全由 `PipelineManager` 控制。

### 编译失败处理

如果 `fPipeline` 为空（编译失败），调用者需要检测并处理：

```cpp
if (!task->fPipeline) {
    // 编译失败，使用备用管线或报错
}
```

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/GraphicsPipeline.h` | 图形管线对象 |
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 管线描述 |
| `src/gpu/graphite/RenderPassDesc.h` | 渲染通道描述 |
| `src/gpu/ResourceKey.h` | 资源唯一键 |
| `include/core/SkRefCnt.h` | 引用计数基类 |
