# Task - Graphite 任务基类

> 源文件: `src/gpu/graphite/task/Task.h`

## 概述

Task 是 Skia Graphite 渲染后端中所有 GPU 任务的抽象基类。它定义了 GPU 工作单元的标准生命周期接口，包括资源准备（`prepareResources`）和命令录制（`addCommands`）两个阶段。Task 继承自 `SkRefCnt`，使用引用计数管理生命周期。

在 Graphite 的录制-回放架构中，Recording 会收集一组 Task 对象，这些 Task 在提交时按序执行。Task 可以是渲染通道（RenderPass）、拷贝操作、计算任务等各种 GPU 工作。

## 架构位置

```
Graphite 录制-回放架构
  -> Recording (录制)
    -> TaskList (任务列表)
      -> Task (任务基类)
        +--> RenderPassTask
        +--> CopyTask
        +--> ComputeTask
        +--> UploadTask
        +--> ...
```

Task 是 Graphite 任务系统的根类型，所有具体的 GPU 工作都通过 Task 的子类实现。

## 主要类与结构体

### `Task`
- **基类**: `SkRefCnt`（引用计数）
- **职责**: 定义 GPU 任务的资源准备和命令录制接口

### `Task::ReplayTargetData`
- **fTarget** (`const Texture*`): 渲染目标纹理
- **fTranslation** (`SkIVector`): 平移偏移
- **fClip** (`SkIRect`): 裁剪区域
- **用途**: 在任务回放时提供渲染目标和变换信息

### `Task::Status` 枚举
- **kSuccess**: 任务步骤成功，回放时应再次执行
- **kDiscard**: 任务步骤成功但为一次性操作，应从任务列表中移除。从 `prepareResources` 返回时，`addCommands` 不会被调用；从 `addCommands` 返回时，已添加的命令仍会执行一次
- **kFail**: 任务失败，Recording 将被标记为无效

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `prepareResources(ResourceProvider*, ScratchResourceManager*, RuntimeEffectDictionary)` | 在 Recorder 阶段实例化和准备资源（纯虚） |
| `addCommands(Context*, CommandBuffer*, ReplayTargetData)` | 向命令缓冲区添加 GPU 命令（纯虚） |
| `visitPipelines(visitor)` | 遍历任务使用的所有图形管线（可选覆盖） |
| `visitProxies(visitor, readsOnly)` | 遍历任务使用的所有纹理代理（可选覆盖） |
| `dump(index, prefix)` | 调试输出任务信息（仅 SK_DUMP_TASKS 构建） |
| `getTaskName()` | 返回任务类型名称（仅调试构建） |

## 内部实现细节

### 两阶段执行模型
Task 的生命周期分为两个阶段：
1. **prepareResources**: 在 Recorder 上执行，负责实例化 GPU 资源（如纹理、管线状态对象）。此阶段可访问 ResourceProvider 和 ScratchResourceManager。
2. **addCommands**: 在 Context 上执行，负责向 CommandBuffer 录制实际的 GPU 命令。

### Status 的语义
- `kDiscard` 允许一次性任务（如纹理上传）在执行后自动从 Recording 中移除。如果任务需要条件性跳过但可重复执行，应返回 `kSuccess` 而非 `kDiscard`。
- `kFail` 会使整个 Recording 无效，是不可恢复的错误。

### 访问器的默认实现
`visitPipelines` 和 `visitProxies` 默认返回 `true`（表示继续遍历），假设任务不使用任何管线或代理。子类按需覆盖。

### 调试支持
在 `SK_DUMP_TASKS` 构建中，Task 额外包含 `fFlushToken` 成员和 `dump`/`getTaskName` 方法，用于调试时追踪和输出任务信息。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/core/SkPoint.h` / `SkRect.h` | ReplayTargetData 中的几何类型 |
| `src/gpu/Token.h` | flush token（调试用） |
| `src/gpu/graphite/DebugUtils.h` | 调试工具 |
| `src/gpu/graphite/Log.h` | 日志 |
| `src/gpu/graphite/RuntimeEffectDictionary.h` | 运行时效果字典 |

## 设计模式与设计决策

1. **模板方法模式**: Task 定义了固定的两阶段执行流程（prepareResources -> addCommands），具体行为由子类实现。

2. **引用计数管理**: 继承 SkRefCnt 使得 Task 可以被多个 Recording 共享和重复使用（通过 kSuccess 返回值支持回放）。

3. **Status 枚举替代布尔返回值**: 三值 Status 比简单的 bool 提供了更精细的控制，特别是 kDiscard 状态允许优化一次性操作的内存使用。

4. **访问器模式（Visitor）**: `visitPipelines` 和 `visitProxies` 使用函数对象（`std::function`）作为访问器，允许外部代码遍历任务的资源依赖而无需暴露内部结构。

## 性能考量

1. **虚函数开销**: 所有核心方法都是虚函数，这意味着每次调用都有间接跳转开销。但由于 Task 通常代表大粒度的 GPU 工作（如整个渲染通道），虚调用开销相对于 GPU 工作本身可以忽略。

2. **std::function 开销**: `visitPipelines` 和 `visitProxies` 使用 `std::function`，可能涉及堆分配。文档建议在 `prepareResources` 之后调用这些方法，此时任务图已清理，避免重复访问。

3. **资源准备与命令录制分离**: 两阶段模型允许批量准备资源后再批量录制命令，可能改善 CPU 缓存利用率和 GPU 管线效率。

## 相关文件

- `src/gpu/graphite/task/TaskList.h` - 管理 Task 列表
- `src/gpu/graphite/Recording.h` - 录制包含 Task 列表
- `src/gpu/graphite/CommandBuffer.h` - addCommands 的目标
- `src/gpu/graphite/ResourceProvider.h` - prepareResources 的资源提供者
- `src/gpu/graphite/ScratchResourceManager.h` - 临时资源管理
- `src/gpu/graphite/Context.h` - addCommands 的上下文
