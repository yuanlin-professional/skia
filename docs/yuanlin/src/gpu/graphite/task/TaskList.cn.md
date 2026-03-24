# TaskList

> 源文件
> - src/gpu/graphite/task/TaskList.h
> - src/gpu/graphite/task/TaskList.cpp

## 概述

`TaskList` 是 Skia Graphite 任务系统中的核心容器类，用于管理和执行一系列 `Task` 对象。它提供统一的接口来添加、遍历和执行任务，支持资源准备、命令录制、管线访问等操作。该类实现了任务的批量处理逻辑，包括自动丢弃无用任务、错误传播、作用域化资源管理等关键功能。

`TaskList` 的主要职责包括：维护任务的存储和顺序、统一调用任务接口、处理任务返回状态（成功、丢弃、失败）、与临时资源管理器协作管理资源作用域。它是任务图执行的基础组件，被 `DrawTask`、`Recording` 等上层对象广泛使用。

## 架构位置

`TaskList` 在任务系统架构中处于容器层：

- **被使用者**: `DrawTask` 使用 `TaskList` 存储子任务，`Recording` 使用它管理顶层任务列表
- **管理对象**: 存储各类 `Task` 子类实例（`RenderPassTask`、`ComputeTask`、`DrawTask` 等）
- **资源协作**: 与 `ScratchResourceManager` 配合实现作用域化资源管理
- **命令流转**: 将任务序列转换为 `CommandBuffer` 中的命令序列

它是任务系统的"容器适配器"，提供统一的批量操作接口，隐藏任务列表的内部实现细节。

## 主要类与结构体

### TaskList 类

值类型容器，核心成员和方法：

**成员变量**:
- `skia_private::TArray<sk_sp<Task>> fTasks`: 任务智能指针数组，自动管理任务生命周期

**添加与重置**:
```cpp
void add(TaskList&& tasks)
```
移动另一个任务列表的所有任务到当前列表末尾，使用移动语义避免拷贝。

```cpp
void add(sk_sp<Task> task)
```
添加单个任务到列表末尾，转移所有权。

```cpp
void reset()
```
清空任务列表，释放所有任务对象。

**查询接口**:
```cpp
int size() const
```
返回任务数量（包括已丢弃的空指针）。

```cpp
bool hasTasks() const
```
检查列表是否为空。

**执行接口**:
```cpp
Task::Status prepareResources(ResourceProvider*,
                              ScratchResourceManager*,
                              sk_sp<const RuntimeEffectDictionary>)
```
准备所有任务的资源，自动管理临时资源作用域。

```cpp
Task::Status addCommands(Context*, CommandBuffer*, Task::ReplayTargetData)
```
录制所有任务的命令到命令缓冲区。

**访问者接口**:
```cpp
bool visitPipelines(const std::function<bool(const GraphicsPipeline*)>& visitor)
```
遍历所有任务使用的图形管线。

```cpp
bool visitProxies(const std::function<bool(const TextureProxy*)>& visitor, bool readsOnly)
```
遍历所有任务引用的纹理代理。

**调试接口**:
```cpp
void visit(const std::function<void(const Task* task, bool isLast)>& visitor) const
```
遍历任务用于调试输出（仅在 `SK_DUMP_TASKS` 宏启用时可用）。

## 公共 API 函数

### 添加操作

```cpp
void add(TaskList&& tasks)
```
批量添加任务，通过 `move_back` 高效移动整个数组内容，避免逐个转移。适用于合并多个任务列表。

```cpp
void add(sk_sp<Task> task)
```
添加单个任务，使用 `emplace_back` 在数组末尾原地构造，避免临时对象。

### 资源准备

```cpp
Task::Status prepareResources(ResourceProvider* resourceProvider,
                              ScratchResourceManager* scratchManager,
                              sk_sp<const RuntimeEffectDictionary> runtimeDict)
```
执行流程：
1. 记录跟踪事件（任务数量）
2. 推入新的资源作用域到 `ScratchResourceManager`
3. 调用 `visitTasks` 遍历所有任务，调用其 `prepareResources()` 方法
4. 弹出资源作用域，自动回收本作用域内分配的临时资源
5. 返回整体状态

**返回值语义**:
- `kSuccess`: 至少一个任务成功，无任务失败
- `kDiscard`: 所有任务都被丢弃（列表实际为空）
- `kFail`: 至少一个任务失败

**作用域意义**: 确保子任务使用的临时资源在父任务完成后自动回收，防止资源泄漏。

### 命令录制

```cpp
Task::Status addCommands(Context* context,
                        CommandBuffer* commandBuffer,
                        Task::ReplayTargetData replayData)
```
遍历所有任务，调用其 `addCommands()` 方法录制命令。不管理资源作用域（命令录制阶段资源已准备好）。

**参数说明**:
- `context`: 全局上下文，提供设备信息和功能查询
- `commandBuffer`: 命令缓冲区，接收录制的命令
- `replayData`: 重放目标数据，用于离屏渲染等场景

**返回值**: 与 `prepareResources` 相同的语义

### 访问者模式

```cpp
bool visitPipelines(const std::function<bool(const GraphicsPipeline*)>& visitor)
```
递归遍历所有任务的图形管线，允许访问者检查或收集管线对象。访问者返回 `false` 时中止遍历。

**返回值**:
- `true`: 所有管线都被访问，或无管线可访问
- `false`: 访问者中止了遍历

**用途**: 预编译管线、依赖分析、性能统计等。

```cpp
bool visitProxies(const std::function<bool(const TextureProxy*)>& visitor, bool readsOnly)
```
遍历任务引用的纹理代理，`readsOnly` 参数控制是否只访问只读纹理。

**返回值**: 与 `visitPipelines` 相同

**用途**: 资源跟踪、依赖图构建、内存分析等。

## 内部实现细节

### visitTasks 模板方法

```cpp
template <typename Fn>
Status TaskList::visitTasks(Fn fn)
```
核心遍历逻辑，接受函数对象或 lambda 表达式，对每个任务调用：

**实现细节**:
1. 初始化丢弃计数器 `discardCount = 0`
2. 遍历 `fTasks` 数组：
   - 跳过空指针（已丢弃的任务），增加丢弃计数
   - 调用 `fn(task.get())` 获取状态
   - 遇到 `kFail` 立即返回失败
   - 遇到 `kDiscard` 重置任务指针为空，增加丢弃计数
3. 返回 `kDiscard` 如果所有任务都被丢弃，否则返回 `kSuccess`

**关键特性**:
- **原地丢弃**: 通过 `task.reset()` 置空指针，不改变数组大小
- **延迟清理**: 空指针保留在数组中，避免遍历时重新分配
- **全局判断**: 只有全部丢弃才返回 `kDiscard`，一个有效任务即为成功

### 作用域管理

`prepareResources()` 中的作用域推入/弹出机制：
```cpp
scratchManager->pushScope();
// ... 准备任务资源 ...
scratchManager->popScope();
```

**作用域栈**: `ScratchResourceManager` 维护作用域栈，每个作用域跟踪分配的临时纹理
**自动回收**: `popScope()` 时，将本作用域分配但未被标记"仍在使用"的纹理归还池中
**嵌套支持**: 子任务的 `prepareResources()` 可能推入更深层作用域，形成栈式管理

### 跟踪事件

使用 `TRACE_EVENT1` 宏记录性能跟踪信息：
```cpp
TRACE_EVENT1("skia.gpu", TRACE_FUNC, "# tasks", fTasks.size())
```

**参数说明**:
- `"skia.gpu"`: 事件类别
- `TRACE_FUNC`: 当前函数名（宏自动展开）
- `"# tasks"`: 参数名
- `fTasks.size()`: 参数值

这些信息可被 Chrome tracing 工具捕获，用于性能分析。

### 调试遍历

```cpp
void visit(const std::function<void(const Task* task, bool isLast)>& visitor) const
```

**实现逻辑**:
1. 反向遍历数组，找到最后一个非空任务 `lastNonNullTask`
2. 正向遍历数组，对每个非空任务调用访问者
3. 传递 `isLast` 参数，指示是否为最后一个任务（用于绘制树形结构）

**用途**: `DrawTask` 的 `dump()` 方法使用此接口正确绘制 Unicode 树形分支。

## 依赖关系

### 直接依赖

**头文件依赖**:
- `include/core/SkRefCnt.h`: 智能指针类型
- `include/private/base/SkTArray.h`: 动态数组容器
- `src/gpu/graphite/task/Task.h`: 任务基类和状态枚举

**实现文件依赖**:
- `src/core/SkTraceEvent.h`: 性能跟踪宏
- `src/gpu/graphite/ScratchResourceManager.h`: 临时资源管理器

### 被使用者

- **DrawTask**: 使用 `TaskList` 存储子任务并执行
- **Recording**: 管理顶层任务列表
- **任务生成器**: 各种上层 API 构建任务列表

### 协作对象

- **Task**: 所有任务类型的基类
- **ResourceProvider**: 提供资源分配服务
- **ScratchResourceManager**: 管理临时资源作用域
- **CommandBuffer**: 接收录制的命令
- **Context**: 提供全局上下文
- **RuntimeEffectDictionary**: 运行时效果字典
- **GraphicsPipeline**: 图形管线对象
- **TextureProxy**: 纹理代理对象

## 设计模式与设计决策

### 模板方法模式 (Template Method)

`visitTasks` 模板函数定义遍历骨架：
- 统一的错误处理和丢弃逻辑
- 灵活的任务操作（通过函数对象参数化）
- 代码复用，避免重复的遍历逻辑

### 访问者模式 (Visitor Pattern)

`visitPipelines` 和 `visitProxies` 实现访问者模式：
- 解耦数据结构和操作
- 支持多种遍历目的（检查、收集、统计等）
- 允许外部代码控制遍历流程（返回 false 中止）

### 值语义容器

`TaskList` 是值类型而非引用计数对象：
- 支持移动语义，高效转移所有权
- 简化生命周期管理（无需引用计数）
- 自然支持栈上分配和 RAII

### 智能指针管理

使用 `sk_sp<Task>` 而非裸指针：
- 自动引用计数，防止内存泄漏
- 支持空指针表示丢弃的任务
- 线程安全的引用计数（如果需要）

### 原地丢弃策略

丢弃任务时置空指针而不删除数组元素：
- **优点**: 避免遍历时数组重新分配，保证迭代器有效性
- **缺点**: 保留空洞，轻微浪费空间
- **权衡**: 性能优先（遍历频繁），空间开销可接受（指针大小）

### 作用域化资源管理

推入/弹出作用域的设计：
- **RAII 风格**: 通过函数调用栈管理资源生命周期
- **嵌套支持**: 子任务可创建更深层作用域
- **自动回收**: 无需手动跟踪每个临时资源

### 状态聚合逻辑

返回值决策：
- **失败传播**: 任何子任务失败则整体失败（悲观策略）
- **部分丢弃容忍**: 部分任务丢弃不影响整体成功（乐观策略）
- **全部丢弃**: 所有任务都无用时才返回丢弃（避免空操作）

## 性能考量

### 批量操作效率

- **单次遍历**: `visitTasks` 一次遍历完成所有任务操作，最小化循环开销
- **移动语义**: `add(TaskList&&)` 使用移动避免拷贝智能指针数组
- **原地构造**: `emplace_back` 避免临时对象

### 内存布局

- **紧凑数组**: `TArray` 连续存储智能指针，缓存友好
- **智能指针开销**: 每个指针 16 字节（64 位系统，指针+控制块），可接受
- **空洞保留**: 丢弃的任务留空洞，空间开销 = 指针大小 × 丢弃数

### 错误处理

- **快速失败**: 遇到失败立即返回，不继续处理后续任务
- **延迟清理**: 不立即删除丢弃的任务，避免数组重新分配
- **状态传播**: 使用枚举返回值而非异常，零开销错误处理

### 作用域开销

- **栈式管理**: 推入/弹出作用域仅操作栈和哈希表，O(1) 复杂度
- **延迟回收**: 资源实际回收在弹出时批量进行，减少碎片化操作
- **嵌套支持**: 多层嵌套不增加额外开销，每层独立管理

### 跟踪事件开销

- **条件编译**: 跟踪宏在发布版本中通常为空操作
- **最小信息**: 仅记录任务数量，避免昂贵的序列化
- **异步记录**: 跟踪数据异步写入，不阻塞任务执行

### 访问者模式开销

- **虚函数调用**: 每个任务的访问方法为虚函数，小开销
- **函数对象**: `std::function` 可能有间接调用开销，但灵活性价值更高
- **提前中止**: 访问者返回 false 立即停止，避免不必要的遍历

## 相关文件

### 任务系统

- `src/gpu/graphite/task/Task.h`: 任务基类
- `src/gpu/graphite/task/DrawTask.h`: 绘制任务
- `src/gpu/graphite/task/RenderPassTask.h`: 渲染通道任务
- `src/gpu/graphite/task/ComputeTask.h`: 计算任务
- `src/gpu/graphite/task/CopyTask.h`: 拷贝任务
- `src/gpu/graphite/task/UploadTask.h`: 上传任务

### 资源管理

- `src/gpu/graphite/ScratchResourceManager.h`: 临时资源管理器
- `src/gpu/graphite/ResourceProvider.h`: 资源提供者
- `src/gpu/graphite/TextureProxy.h`: 纹理代理

### 上下文与命令

- `src/gpu/graphite/Recording.h`: 录制对象
- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区
- `src/gpu/graphite/Context.h`: 全局上下文

### 管线与效果

- `src/gpu/graphite/GraphicsPipeline.h`: 图形管线
- `src/gpu/graphite/RuntimeEffectDictionary.h`: 运行时效果字典

### 工具与基础

- `include/private/base/SkTArray.h`: 动态数组容器
- `src/core/SkTraceEvent.h`: 性能跟踪工具
