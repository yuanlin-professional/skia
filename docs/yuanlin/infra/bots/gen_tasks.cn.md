# Gen Tasks - 任务生成入口

> 源文件: `infra/bots/gen_tasks.go`

## 概述

`gen_tasks.go` 是 Skia CI 任务生成系统的入口点，调用 `gen_tasks_logic.GenTasks` 函数生成 `tasks.json` 文件。该文件定义了所有 CI/CD 任务的配置。

## 架构位置

位于 `infra/bots/` 目录，是任务生成管线的最顶层入口。实际逻辑在 `gen_tasks_logic` 包中实现。

## 主要类与结构体

无。

## 公共 API 函数

- `main()`: 调用 `gen_tasks_logic.GenTasks(nil)` 生成任务配置

## 内部实现细节

传入 `nil` 表示使用默认配置（Skia 仓库自身的配置）。其他仓库可以传入自定义 `Config` 对象。

## 依赖关系

- `go.skia.org/skia/infra/bots/gen_tasks_logic`: 任务生成核心逻辑

## 设计模式与设计决策

- 极简入口模式：将所有逻辑委托给独立包，使入口文件保持最小化
- 支持被其他仓库导入和自定义

## 性能考量

无。单次运行脚本。

## 相关文件

- `infra/bots/gen_tasks_logic/`: 任务生成核心逻辑包
- `infra/bots/tasks.json`: 生成的任务配置文件
