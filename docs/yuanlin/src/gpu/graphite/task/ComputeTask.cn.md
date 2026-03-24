# ComputeTask

> 源文件
> - src/gpu/graphite/task/ComputeTask.h
> - src/gpu/graphite/task/ComputeTask.cpp

## 概述

`ComputeTask` 是 Skia Graphite 中专门用于执行计算着色器（Compute Shader）的任务类型。它负责将一个或多个 `DispatchGroup` 对象转换为 GPU 可执行的计算调度（compute dispatch）命令序列，并将这些命令录制到命令缓冲区中。每个 `DispatchGroup` 代表一组需要顺序执行的计算操作，`ComputeTask` 保证这些操作的执行顺序性。

该类继承自 `Task` 基类，支持资源准备、命令录制等标准任务接口。它还管理与调度组关联的子任务，允许在计算通道之间插入其他类型的任务（如渲染或拷贝任务），从而支持复杂的任务依赖关系。

## 架构位置

`ComputeTask` 在 Graphite 任务系统中扮演计算工作负载的执行者角色：

- **上层输入**: 由高层 API 或绘制上下文创建 `DispatchGroup` 列表，传递给 `ComputeTask`
- **同级任务**: 与 `RenderPassTask`、`DrawTask`、`CopyTask` 等并列，作为任务图的叶子或中间节点
- **下层输出**: 通过 `CommandBuffer` 的计算通道接口，将调度命令编码为后端特定的 GPU 命令
- **子任务管理**: 每个 `DispatchGroup` 可关联前置子任务，在调度前执行必要的准备工作

在计算管线中，`ComputeTask` 连接了高级别的计算抽象（`DispatchGroup`）和底层的命令录制系统，是计算着色器执行路径的核心组件。

## 主要类与结构体

### ComputeTask 类

继承自 `Task`，核心成员包括：

**类型别名**:
```cpp
using DispatchGroupList = skia_private::STArray<1, std::unique_ptr<DispatchGroup>>;
```
调度组列表类型，使用小数组优化（栈上分配 1 个元素）以减少堆分配。

**关键成员变量**:
- `DispatchGroupList fDispatchGroups`: 存储所有调度组，按执行顺序排列
- `skia_private::TArray<sk_sp<Task>> fChildTasks`: 子任务数组，与调度组一一对应，可为空

**核心方法**:
- `static sk_sp<ComputeTask> Make(DispatchGroupList)`: 静态工厂方法，创建计算任务
- `Status prepareResources(...)`: 准备所有子任务和调度组的资源
- `Status addCommands(...)`: 录制计算调度命令到命令缓冲区

### DispatchGroup 类（外部依赖）

封装计算调度的逻辑单元：
- 定义计算管线、工作组大小、绑定资源等
- 提供 `snapChildTask()` 方法获取前置子任务
- 通过 `prepareResources()` 实例化纹理和缓冲区

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<ComputeTask> Make(DispatchGroupList dispatchGroups)
```
创建 `ComputeTask` 实例，接受调度组列表作为参数。内部调用私有构造函数，返回智能指针。

**参数说明**:
- `dispatchGroups`: 调度组列表，移动语义转移所有权

**返回值**: 指向新创建任务的智能指针

### 任务执行接口

```cpp
Status prepareResources(ResourceProvider* provider,
                       ScratchResourceManager* scratchManager,
                       sk_sp<const RuntimeEffectDictionary> rtd) override
```
准备任务执行所需的所有资源，分两个阶段：

1. **子任务准备**: 遍历 `fChildTasks` 数组，递归调用子任务的 `prepareResources()`
   - 遇到 `kFail` 立即返回失败
   - 遇到 `kDiscard` 重置子任务指针为空
2. **调度组准备**: 遍历 `fDispatchGroups`，调用其 `prepareResources()` 实例化资源
   - 任何调度组失败则整体失败

**返回值**:
- `kSuccess`: 所有资源准备成功
- `kFail`: 资源准备失败

**注意**: 代码注释指出未来将支持临时纹理的分配和归还。

```cpp
Status addCommands(Context* ctx,
                  CommandBuffer* commandBuffer,
                  ReplayTargetData rtd) override
```
将计算调度命令录制到命令缓冲区，实现智能分段编码：

1. **空列表检查**: 若调度组为空，返回 `kDiscard`
2. **跨度累积**: 将连续的（无子任务）调度组累积为一个计算通道
3. **子任务插入**: 遇到子任务时，先编码累积的跨度，再执行子任务
4. **最终编码**: 编码剩余的调度组跨度

**返回值**:
- `kSuccess`: 命令录制成功
- `kDiscard`: 无有效调度组
- `kFail`: 命令录制失败

### 调试接口

```cpp
SK_DUMP_TASKS_CODE(const char* getTaskName() const override)
```
返回任务名称 "Compute Task" 用于调试输出。未来将支持遍历子任务（见 TODO 注释）。

## 内部实现细节

### 构造函数逻辑

```cpp
ComputeTask::ComputeTask(DispatchGroupList dispatchGroups)
        : fDispatchGroups(std::move(dispatchGroups)),
          fChildTasks(fDispatchGroups.size())
```
私有构造函数执行以下操作：
1. 移动调度组列表到成员变量
2. 预分配子任务数组，大小等于调度组数量
3. 遍历调度组，调用 `snapChildTask()` 获取子任务并存储

这确保每个调度组都有对应的子任务槽位（可为空）。

### 资源准备策略

采用两阶段准备，先处理依赖再处理调度组：
- **子任务优先**: 确保前置任务的资源先就绪
- **丢弃处理**: 允许子任务被丢弃（如重复的临时设备任务）
- **失败传播**: 任何环节失败则立即中止

### 计算通道分段算法

`addCommands()` 使用跨度（span）累积机制优化编码：

**核心思想**: 将连续的调度组合并到一个计算通道中，减少编码器切换开销。

**算法步骤**:
1. 初始化跨度指针 `currentSpanPtr` 指向第一个调度组
2. 初始化跨度大小 `currentSpanSize` 为 0
3. 遍历每个调度组：
   - 如果有子任务，先编码当前累积的跨度（若非空），执行子任务，重置跨度
   - 否则累积跨度大小
4. 编码最后剩余的跨度

**示例场景**:
```
Groups: [G1, G2(child), G3, G4]
编码过程:
  - 累积 G1
  - 遇到 G2 的子任务，编码 [G1]，执行子任务
  - 累积 G3, G4
  - 编码 [G3, G4]
```

### 数组索引同步

通过 `SkASSERT(fDispatchGroups.size() == fChildTasks.size())` 确保两个数组大小一致，使用相同索引访问对应元素，避免越界和错位。

## 依赖关系

### 直接依赖

**头文件依赖**:
- `include/core/SkRefCnt.h`: 智能指针支持
- `include/private/base/SkTArray.h`: 动态数组容器
- `src/gpu/graphite/compute/DispatchGroup.h`: 调度组封装
- `src/gpu/graphite/task/Task.h`: 任务基类

**实现文件依赖**:
- `include/private/base/SkAssert.h`: 断言宏
- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区
- `src/gpu/graphite/ComputePipeline.h`: 计算管线（编译依赖）
- `src/gpu/graphite/Sampler.h`: 采样器（编译依赖）
- `src/gpu/graphite/TextureProxy.h`: 纹理代理（编译依赖）

### 被依赖关系

- **DrawTask**: 可将 `ComputeTask` 作为子任务添加到任务列表
- **Recording**: 在录制过程中收集计算任务
- **调度组生成器**: 高层 API 生成 `DispatchGroup` 列表并创建 `ComputeTask`

### 运行时协作

- **ResourceProvider**: 提供纹理、缓冲区等资源的分配服务
- **ScratchResourceManager**: 管理临时资源（未来功能）
- **CommandBuffer**: 接收编码的计算通道命令
- **Context**: 提供全局上下文信息
- **RuntimeEffectDictionary**: 管理运行时着色器效果（传递给子任务）

## 设计模式与设计决策

### 工厂方法模式 (Factory Method)

使用静态 `Make()` 方法而非公开构造函数：
- 隐藏构造细节，保证对象初始化的一致性
- 返回智能指针，明确所有权语义
- 方便未来扩展工厂逻辑（如验证、优化等）

### 组合模式 (Composite Pattern)

通过 `fChildTasks` 支持任务嵌套：
- 每个调度组可关联前置子任务
- 递归处理资源准备和命令录制
- 形成任务树结构，支持复杂依赖

### 延迟执行 (Deferred Execution)

任务创建时不执行计算，仅存储调度组：
- 资源准备和命令录制分离
- 允许任务图优化（重排序、合并、剔除）
- 支持跨多个任务的资源共享

### 跨度合并优化

动态分段计算通道的设计决策：
- **问题**: 每个 `DispatchGroup` 单独编码会产生大量小通道，增加开销
- **解决方案**: 将无子任务的连续调度组合并到一个通道
- **权衡**: 略微增加录制复杂度，但显著减少运行时编码器切换

### 空指针语义

`fChildTasks` 中的空指针表示无前置任务：
- 简化数组管理（无需额外标志）
- 自然支持丢弃机制（重置为空）
- 避免虚拟 NOP 任务对象的开销

### 小数组优化

`STArray<1, ...>` 类型定义：
- 大部分计算任务只包含一个调度组
- 栈上分配避免堆开销
- 超过 1 个元素时自动扩展到堆

## 性能考量

### 计算通道合并

- **减少编码器开销**: 多个调度组使用同一编码器，降低驱动层开销
- **批量提交**: GPU 可能更有效地调度批量计算工作
- **减少同步点**: 连续调度组间无显式同步，GPU 可优化执行

### 子任务灵活性

- **按需插入非计算任务**: 在计算间插入渲染或拷贝操作，支持复杂管线
- **依赖管理**: 子任务可确保数据就绪（如上传纹理、清空缓冲区）
- **避免全局同步**: 局部依赖替代全局屏障，减少 GPU 空闲

### 资源准备提前化

- **一次性准备**: `prepareResources()` 一次性实例化所有资源
- **错误提前检测**: 资源分配失败在命令录制前发现，避免部分录制
- **内存规划**: 资源提供者可统筹分配策略

### 丢弃机制

- **空任务快速返回**: 空调度组列表立即返回 `kDiscard`
- **子任务剪枝**: 丢弃的子任务置空，不占用执行时间
- **内存释放**: 智能指针自动释放丢弃的子任务资源

### 内存布局

- **紧凑数组**: 使用 `TArray` 而非链表，缓存友好
- **移动语义**: 调度组列表通过移动转移，避免拷贝
- **智能指针开销**: 每个子任务一个引用计数，但多数为空指针

## 相关文件

### 计算系统核心

- `src/gpu/graphite/compute/DispatchGroup.h`: 调度组封装
- `src/gpu/graphite/compute/ComputeStep.h`: 计算步骤抽象
- `src/gpu/graphite/ComputePipeline.h`: 计算管线对象

### 任务系统

- `src/gpu/graphite/task/Task.h`: 任务基类
- `src/gpu/graphite/task/DrawTask.h`: 绘制任务
- `src/gpu/graphite/task/RenderPassTask.h`: 渲染通道任务
- `src/gpu/graphite/task/CopyTask.h`: 拷贝任务
- `src/gpu/graphite/task/TaskList.h`: 任务列表容器

### 资源与命令

- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区
- `src/gpu/graphite/ResourceProvider.h`: 资源提供者
- `src/gpu/graphite/ScratchResourceManager.h`: 临时资源管理器
- `src/gpu/graphite/TextureProxy.h`: 纹理代理
- `src/gpu/graphite/Sampler.h`: 采样器

### 上下文与字典

- `src/gpu/graphite/Context.h`: 全局上下文
- `src/gpu/graphite/RuntimeEffectDictionary.h`: 运行时效果字典
