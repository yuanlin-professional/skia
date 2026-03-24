# format_jobs_json -- jobs.json 格式化工具

> 源文件: `infra/bots/format_jobs_json/format_jobs_json.go`

## 概述

此 Go 程序用于重新格式化 Skia CI/CD 基础设施中的 `jobs.json` 文件。它将文件中的作业（job）条目按名称排序，并清理冗余的 `"cq_config": null` 字段以保持文件紧凑可读。`jobs.json` 定义了 Skia 任务调度器（Task Scheduler）中所有可用的构建/测试作业及其 CQ（Commit Queue）配置。

## 架构位置

该工具是 Skia 基础设施构建配置管理的辅助工具，位于 `infra/bots/` 目录下。它直接操作 `infra/bots/jobs.json` 文件，该文件是 Skia 任务调度系统的核心配置之一。

- **层级**: 基础设施工具层
- **关联配置**: `infra/bots/jobs.json`（任务调度器作业定义）
- **依赖服务**: Skia 任务调度器（Task Scheduler）

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `job` | struct | 表示 `jobs.json` 中的单个作业条目，包含 `Name` 和 `CqConfig` 字段 |
| `jobSlice` | type | `[]*job` 的类型别名，实现了 `sort.Interface` 用于按名称排序 |

### `job` 结构体

```go
type job struct {
    Name     string                      `json:"name"`
    CqConfig *specs.CommitQueueJobConfig `json:"cq_config"`
}
```

- `Name`: 作业名称，如 `Build-Debian10-Clang-x86_64-Release`
- `CqConfig`: CQ 配置指针，`nil` 表示不参与 CQ，空对象 `{}` 表示参与 CQ

### `jobSlice` 类型

实现 `sort.Interface` 的三个方法：`Less`、`Len`、`Swap`，按作业名称的字典序排序。

## 公共 API 函数

### `main()`

程序入口。读取 `jobs.json` 文件，调用 `updateJobsJSON` 进行格式化处理，然后将结果写回原文件。

### `findJobsJSON() string`

查找 `jobs.json` 文件的绝对路径。首先尝试基于当前源文件位置推导（使用 `runtime.Caller`），失败则回退到假设从仓库根目录运行。

### `updateJobsJSON(oldJobsContents []byte) ([]byte, error)`

核心处理函数，执行以下操作：
1. 将 JSON 反序列化为 `[]*job` 切片
2. 按名称排序
3. 重新序列化为带缩进的 JSON
4. 使用正则表达式清理 `"cq_config": null` 字段

## 内部实现细节

- **排序实现**: 使用标准库 `sort.Sort` 对 `jobSlice` 排序，复杂度为 O(n log n)
- **JSON 格式化**: 使用 `json.MarshalIndent` 生成带 2 空格缩进的 JSON
- **null 清理**: 通过正则表达式 `(?m)\{\n\s*"name":\s*"(\S+)",\n\s*"cq_config":\s*null\n\s*}` 匹配并替换带有 `null` cq_config 的条目为紧凑的单行格式 `{"name": "$1"}`
- **不使用 omitempty 的原因**: Go 的 `omitempty` 标签会同时省略 `"cq_config": {}` (空对象)，而空对象在语义上表示"应参与 CQ"，需要保留
- **文件定位策略**: 使用 `runtime.Caller(0)` 获取源文件路径，据此推导 `jobs.json` 位置，这使得程序可以从任意工作目录运行

## 依赖关系

- **标准库**: `encoding/json`, `os`, `path/filepath`, `regexp`, `runtime`, `sort`
- **外部库**:
  - `go.skia.org/infra/go/skerr` -- Skia 基础设施错误包装库
  - `go.skia.org/infra/task_scheduler/go/specs` -- 任务调度器规格定义，提供 `CommitQueueJobConfig` 类型

## 设计模式与设计决策

- **就地修改**: 读取文件后直接写回同一路径，适合作为预提交钩子或格式化工具使用
- **幂等操作**: 多次运行产生相同结果，已排序和格式化的文件再次处理不会变化
- **紧凑与可读的平衡**: 无 CQ 配置的作业使用单行格式以减少文件长度，有 CQ 配置的保留多行格式以便阅读
- **正则表达式后处理**: 由于 Go 的 JSON 编解码器不支持所需的精确输出格式，采用正则替换作为后处理步骤

## 性能考量

- 该工具处理的 `jobs.json` 文件通常在数千行左右，排序和正则替换的性能完全可以接受
- 使用 `os.ReadFile` 和 `os.WriteFile` 一次性读写整个文件，避免流式处理的复杂性
- 正则表达式预编译 (`regexp.MustCompile`) 确保只编译一次

## 相关文件

- `infra/bots/jobs.json` -- 被格式化的目标文件
- `infra/bots/task_drivers/` -- 任务驱动器目录
- `go.skia.org/infra/task_scheduler/go/specs` -- 任务调度器规格定义
