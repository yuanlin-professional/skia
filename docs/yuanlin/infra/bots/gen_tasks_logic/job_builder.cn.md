# Job Builder - CI 任务作业构建器

> 源文件: `infra/bots/gen_tasks_logic/job_builder.go`

## 概述

`job_builder.go` 实现了 Skia CI 任务系统的作业（Job）构建器。`jobBuilder` 结构体负责解析作业名称、创建子任务、上传 CIPD 资产到 CAS，以及根据作业角色（编译、测试、性能测试等）分派到具体的任务生成函数。

## 架构位置

位于 `infra/bots/gen_tasks_logic/` 包中，是任务生成管线的中间层。位于 `builder`（顶层协调器）和 `TaskBuilder`（具体任务配置）之间。

## 主要类与结构体

- **`jobBuilder`**: 作业构建器
  - 嵌入 `*builder`: 顶层构建器引用
  - 嵌入 `Parts`: 作业名称解析后的键值对
  - `Name string`: 作业名称
  - `Spec *specs.JobSpec`: 作业规格

## 公共 API 函数

- **`newJobBuilder(b, name)`**: 创建 jobBuilder，解析作业名称
- **`priority(p float64)`**: 设置作业优先级
- **`trigger(trigger string)`**: 设置触发条件
- **`addTask(name, fn)`**: 创建子任务并添加到作业
- **`uploadCIPDAssetToCAS(asset)`**: 将 CIPD 资产上传到 CAS
- **`genTasksForJob()`**: 根据作业类型生成所需任务
- **`finish()`**: 设置触发策略并注册作业

## 内部实现细节

1. **`addTask`**: 创建 TaskBuilder、执行配置函数、调用 AddTaskCallback、注册任务，并智能管理作业的依赖集合（移除被新任务间接依赖的旧任务）
2. **`genTasksForJob`**: 大型分派函数，按优先级顺序匹配：
   - Bundle Recipes / Build Task Drivers
   - CIPD 资产隔离
   - RecreateSKPs / InfraTests
   - Housekeepers（多种类型）
   - Build / BuildStats / CodeSize
   - Test（含 WasmGMTests 变体）
   - Canary（G3/Android/Chromium/Flutter）
   - Puppeteer / Perf / BazelBuild / BazelTest
3. **`finish`**: 根据频率设置触发策略（Nightly/Weekly/OnDemand/AnyBranch）

## 依赖关系

- `go.skia.org/infra/task_scheduler/go/specs`: 任务调度器规格定义
- 同包: `builder`, `TaskBuilder`, `Parts`

## 设计模式与设计决策

- 构建器模式: 链式配置作业属性
- 分派模式: `genTasksForJob` 根据名称特征分派到不同的生成逻辑
- 依赖优化: `addTask` 自动移除冗余的直接依赖

## 性能考量

任务生成是一次性操作，无运行时性能考量。

## 相关文件

- `infra/bots/gen_tasks_logic/task_builder.go`: 子任务构建器
- `infra/bots/gen_tasks_logic/gen_tasks_logic.go`: 顶层逻辑和 builder 定义
- `infra/bots/gen_tasks_logic/schema.go`: 名称解析 schema
