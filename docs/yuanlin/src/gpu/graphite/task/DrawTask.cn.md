# DrawTask

> 源文件
> - src/gpu/graphite/task/DrawTask.h
> - src/gpu/graphite/task/DrawTask.cpp

## 概述

`DrawTask` 是 Skia Graphite 渲染管线中的核心任务类型，负责组织和管理一系列子任务以生成目标纹理的图像内容。它作为任务列表的容器，将多个渲染、计算或拷贝操作组合在一起，最终输出到指定的纹理代理对象中。该类继承自 `Task` 基类，并实现了 `ScratchResourceManager::PendingUseListener` 接口，以支持临时资源的生命周期管理。

`DrawTask` 的主要职责包括：协调子任务的资源准备、命令录制和执行顺序，管理目标纹理的实例化状态，处理临时设备纹理的引用计数和复用机制。它确保所有子任务按正确顺序执行，并在完成后释放临时资源供后续复用。

## 架构位置

`DrawTask` 位于 Graphite 任务系统的中间层，连接上层的 `DrawContext` 和底层的各种具体任务类型：

- **上层交互**: `DrawContext` 通过友元关系直接向 `DrawTask` 添加子任务，完成绘制命令的组织
- **下层管理**: 内部维护 `TaskList` 容器，存储 `RenderPassTask`、`ComputeTask`、`CopyTask` 等具体任务
- **资源管理**: 与 `ScratchResourceManager` 协作，管理临时纹理的分配、使用和回收
- **命令录制**: 通过 `CommandBuffer` 将所有子任务转换为 GPU 可执行的命令序列

在任务图中，`DrawTask` 通常作为叶子节点或中间节点，其子任务直接操作 GPU 资源，而 `DrawTask` 本身负责整体协调。

## 主要类与结构体

### DrawTask 类

继承自 `Task` 和 `ScratchResourceManager::PendingUseListener`，核心成员包括：

**关键成员变量**:
- `sk_sp<TextureProxy> fTarget`: 目标纹理代理，所有子任务的渲染结果最终输出到此纹理
- `TaskList fChildTasks`: 子任务列表，按顺序存储需要执行的各种任务
- `bool fPrepared`: 标记资源准备状态，防止临时设备任务的重复准备

**核心方法**:
- `explicit DrawTask(sk_sp<TextureProxy> target)`: 构造函数，初始化目标纹理
- `Status prepareResources(...)`: 准备所有子任务所需的 GPU 资源
- `Status addCommands(...)`: 将子任务的命令录制到命令缓冲区
- `void addTask(sk_sp<Task> task)`: 添加子任务（仅 `DrawContext` 可调用）
- `void onUseCompleted(...)`: 资源使用完成回调，处理临时资源回收

### 依赖的关键类型

- `TaskList`: 任务容器，管理子任务的存储和遍历
- `TextureProxy`: 纹理代理对象，延迟纹理的实际分配
- `ScratchResourceManager`: 临时资源管理器，负责纹理复用
- `CommandBuffer`: 命令缓冲区，记录 GPU 命令

## 公共 API 函数

### 构造与析构

```cpp
explicit DrawTask(sk_sp<TextureProxy> target)
```
创建绘制任务，指定目标纹理代理。目标纹理可以是常规纹理或临时设备纹理。

```cpp
~DrawTask() override
```
析构函数，使用默认实现，智能指针自动管理资源释放。

### 任务执行接口

```cpp
Status prepareResources(ResourceProvider* resourceProvider,
                       ScratchResourceManager* scratchManager,
                       sk_sp<const RuntimeEffectDictionary> rteDict) override
```
准备任务执行所需的所有资源。处理逻辑包括：
1. 检查目标纹理的待读计数，判断是否为临时设备
2. 如果已准备过且为临时设备，返回 `kDiscard` 避免重复执行
3. 标记资源为使用中状态，防止过早回收
4. 递归调用子任务的资源准备方法

返回值说明：
- `kSuccess`: 准备成功
- `kDiscard`: 任务已执行，应从图中移除此引用
- `kFail`: 准备失败

```cpp
Status addCommands(Context* ctx,
                  CommandBuffer* commandBuffer,
                  ReplayTargetData replayTarget) override
```
将所有子任务的命令录制到命令缓冲区。要求目标纹理已完成实例化，然后递归调用子任务的命令添加方法。

### 访问者模式接口

```cpp
bool visitPipelines(const std::function<bool(const GraphicsPipeline*)>& visitor) override
```
遍历所有子任务使用的图形管线对象，用于依赖分析和预编译。

```cpp
bool visitProxies(const std::function<bool(const TextureProxy*)>& visitor,
                 bool readsOnly) override
```
遍历所有子任务引用的纹理代理，支持只读或读写模式过滤，用于资源跟踪和依赖图构建。

## 内部实现细节

### 临时资源管理机制

`DrawTask` 实现了精细的临时设备纹理管理：

1. **待读计数跟踪**: 通过 `ScratchResourceManager::pendingReadCount()` 检查目标纹理是否有待处理的读取操作
2. **重复准备检测**: `fPrepared` 标志确保同一任务在图中被多次引用时，只准备一次资源
3. **任务丢弃策略**: 对于已准备的临时设备任务，后续遇到时返回 `kDiscard`，避免重复执行
4. **资源回收触发**: 在 `onUseCompleted()` 中递减待读计数，当计数归零时将纹理归还给管理器

### 资源作用域管理

`prepareResources()` 方法通过 `TaskList` 创建新的资源作用域：
- 子任务的临时资源在该作用域内分配
- 子任务完成后，其使用的临时资源在作用域结束时自动返回
- 父任务的 `markResourceInUse()` 在子任务作用域之外调用，确保在正确的作用域处理待回收资源

### 调试支持

在 `SK_DUMP_TASKS` 宏启用时，提供树状结构的任务转储功能：
- 显示任务指针、目标纹理地址和标签
- 使用 Unicode 字符绘制树形分支（│ ├ └）
- 递归转储所有子任务，形成完整的任务层次结构
- 支持缩进管理，正确显示嵌套关系

### 断言保护

代码中大量使用 `SkASSERT` 确保运行时正确性：
- 临时设备纹理必须不是延迟实例化的
- 已准备的任务必须已完成目标纹理实例化
- 命令录制时目标纹理必须已实例化
- 待读计数必须大于零才能执行递减操作

## 依赖关系

### 直接依赖

**头文件依赖**:
- `include/core/SkRefCnt.h`: 智能指针支持
- `src/gpu/graphite/ScratchResourceManager.h`: 临时资源管理
- `src/gpu/graphite/TextureProxy.h`: 纹理代理类型
- `src/gpu/graphite/task/Task.h`: 任务基类
- `src/gpu/graphite/task/TaskList.h`: 任务列表容器

**实现文件依赖**:
- `include/private/base/SkAssert.h`: 断言宏
- `src/gpu/graphite/Texture.h`: 实际纹理对象（仅保持编译依赖）

### 被依赖关系

- `DrawContext`: 友元类，负责创建和填充 `DrawTask`
- `Recording`: 在录制过程中收集并优化 `DrawTask`
- 各种子任务类型（`RenderPassTask`、`ComputeTask` 等）被添加到任务列表中

### 运行时协作

- **ResourceProvider**: 提供资源分配服务
- **ScratchResourceManager**: 管理临时纹理的生命周期
- **CommandBuffer**: 接收录制的 GPU 命令
- **Context**: 提供全局上下文信息
- **RuntimeEffectDictionary**: 管理运行时着色器效果

## 设计模式与设计决策

### 组合模式 (Composite Pattern)

`DrawTask` 是典型的组合模式实现：
- 本身是 `Task`，同时包含 `TaskList`
- 支持递归的资源准备和命令录制
- 允许构建任意深度的任务树结构

### 访问者模式 (Visitor Pattern)

通过 `visitPipelines` 和 `visitProxies` 方法：
- 解耦任务结构和遍历逻辑
- 支持多种不同的遍历目的（依赖分析、资源统计等）
- 允许客户端代码灵活处理遍历结果

### 监听器模式 (Listener Pattern)

实现 `PendingUseListener` 接口：
- 资源管理器在适当时机回调 `onUseCompleted()`
- 解耦资源生命周期管理和任务执行逻辑
- 支持异步的资源回收机制

### 延迟实例化 (Lazy Instantiation)

通过 `TextureProxy` 实现：
- 任务创建时不立即分配纹理内存
- 在 `prepareResources()` 阶段按需实例化
- 允许资源管理器优化内存分配策略

### 友元类设计决策

`DrawContext` 作为友元类可直接访问 `addTask()` 和 `hasTasks()`：
- 避免公开内部修改接口，保证封装性
- 允许 `DrawContext` 高效构建任务图
- 一旦任务快照完成，任务列表即为不可变

### 任务丢弃机制

针对临时设备的优化设计：
- 同一临时设备的 `DrawTask` 可能被多次引用
- 通过 `kDiscard` 返回值在任务图中去重
- 避免重复执行相同的渲染操作，提升性能

## 性能考量

### 资源复用优化

- **临时纹理池化**: 通过 `ScratchResourceManager` 复用纹理对象，减少分配开销
- **待读计数机制**: 精确跟踪纹理使用状态，最早时机回收资源
- **作用域管理**: 通过嵌套作用域自动管理资源生命周期，避免过早或过晚释放

### 任务去重

- **准备状态缓存**: `fPrepared` 标志避免重复资源准备
- **引用消除**: 多次引用的任务只执行一次，其他引用返回 `kDiscard`
- **减少 GPU 工作量**: 避免重复渲染相同内容

### 内存占用

- **延迟实例化**: 纹理代理延迟实际分配，减少峰值内存
- **智能指针管理**: 自动引用计数，避免内存泄漏
- **任务列表容器**: 高效存储子任务，最小化容器开销

### 命令缓冲区效率

- **批量命令录制**: 一次性录制所有子任务的命令
- **顺序执行保证**: 子任务按添加顺序执行，减少同步开销
- **目标预验证**: 命令录制前断言纹理已实例化，避免运行时检查

## 相关文件

### 核心任务系统

- `src/gpu/graphite/task/Task.h`: 任务基类定义
- `src/gpu/graphite/task/TaskList.h`: 任务列表容器
- `src/gpu/graphite/task/RenderPassTask.h`: 渲染通道任务
- `src/gpu/graphite/task/ComputeTask.h`: 计算任务
- `src/gpu/graphite/task/CopyTask.h`: 拷贝任务

### 资源管理

- `src/gpu/graphite/ScratchResourceManager.h`: 临时资源管理器
- `src/gpu/graphite/ResourceProvider.h`: 资源提供者
- `src/gpu/graphite/TextureProxy.h`: 纹理代理
- `src/gpu/graphite/Texture.h`: 实际纹理对象

### 上下文与命令

- `src/gpu/graphite/DrawContext.h`: 绘制上下文（友元类）
- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区
- `src/gpu/graphite/Context.h`: 全局上下文
- `src/gpu/graphite/Recording.h`: 录制对象

### 着色器支持

- `src/gpu/graphite/RuntimeEffectDictionary.h`: 运行时效果字典
- `src/gpu/graphite/GraphicsPipeline.h`: 图形管线对象
