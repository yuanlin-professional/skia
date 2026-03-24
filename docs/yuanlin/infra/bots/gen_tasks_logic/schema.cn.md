# Schema - 任务/作业名称解析 Schema

> 源文件: `infra/bots/gen_tasks_logic/schema.go`

## 概述

`schema.go` 实现了 Skia CI 系统的任务和作业名称解析逻辑。它定义了 `Parts` 类型（名称组件的键值对映射）及其丰富的查询方法，以及 `JobNameSchema` 结构体用于从 JSON 文件加载名称模式并解析/构造作业名称。

## 架构位置

位于 `infra/bots/gen_tasks_logic/` 包中，是名称解析的基础设施。所有任务配置逻辑都通过 `Parts` 的方法查询作业属性。

## 主要类与结构体

- **`Parts`** (map[string]string): 作业名称的键值对表示
- **`schema`**: JSON schema 子结构
  - `Keys`, `OptionalKeys`, `RecurseRoles`: 名称组成定义
- **`JobNameSchema`**: 作业名称 schema
  - `Schema map[string]*schema`: 按角色索引的 schema 映射
  - `Sep string`: 名称分隔符

## 公共 API 函数

### Parts 方法
- **精确匹配**: `Equal`, `Role`, `Os`, `Compiler`, `Model`, `Frequency`, `CPU`, `GPU`, `Arch`, `ExtraConfig`, `NoExtraConfig`
- **正则匹配**: `MatchPart`, `MatchRole`, `MatchOs`, `MatchCompiler`, `MatchModel`, `MatchCpu`, `MatchGpu`, `MatchArch`, `MatchBazelHost`, `MatchExtraConfig`
- **状态查询**: `Debug`, `Release`, `IsLinux`, `IsWindows`, `IsMac`
- **Bazel 部件**: `BazelBuildParts`, `BazelTestParts`
- **工具方法**: `Project`

### JobNameSchema 方法
- **`ParseJobName(name)`**: 解析作业名称为 Parts
- **`MakeJobName(parts)`**: 从 Parts 构造作业名称

## 内部实现细节

1. **`ExtraConfig`**: 将 extra_config 按 `_` 分割，但 `SK_` 前缀视为单一配置项
2. **`MatchExtraConfig`**: 类似 ExtraConfig 但使用正则匹配
3. **`IsLinux`**: 匹配 Debian/Ubuntu/on_rpi 以及 Housekeeper/Canary/Upload 角色
4. **`ParseJobName`**: 递归解析支持 `RecurseRoles`（嵌套角色），如 Upload-Test-...
5. **`MakeJobName`**: 按 Keys + OptionalKeys 顺序构造，跳过空值的可选键

## 依赖关系

- 标准库: `encoding/json`, `fmt`, `log`, `os`, `regexp`, `strings`

## 设计模式与设计决策

- 流式查询API: `Parts` 的方法支持变参模式 `Role("Build", "Test")`
- 精确/正则双模式: Equal 系列用于已知值匹配，Match 系列用于模式匹配
- Schema 驱动: 名称格式由 JSON 文件定义，支持灵活的名称方案

## 性能考量

- 正则表达式使用 `regexp.MustCompile` 按需编译（每次调用创建新编译器）
- Parts 的查询方法频繁调用，map 查找为 O(1)

## 相关文件

- `infra/bots/recipe_modules/builder_name_schema/builder_name_schema.json`: 名称 schema JSON
- `infra/bots/gen_tasks_logic/job_builder.go`: 使用 Parts 查询
- `infra/bots/gen_tasks_logic/task_builder.go`: 使用 Parts 查询
