# tools.go - Go 工具依赖声明文件

> 源文件:
> - `tools.go`

## 概述

`tools.go` 是 Skia 项目根目录下的一个 Go 语言文件，用于确保间接使用的 Go 模块依赖被正确记录在 `go.mod` 文件中。这是 Go 社区中常见的"工具依赖"模式（tools dependency pattern），通过 build tag 约束确保该文件不会在正常构建中被编译，仅用于依赖管理。

## 架构位置

```
Skia 项目根目录
├── go.mod (Go 模块依赖声明)
├── tools.go (间接依赖导入)  <── 本文件
└── infra/bots/ (实际使用这些依赖的构建脚本)
```

该文件在 Go 模块系统中充当依赖锚点，确保 `go mod tidy` 不会移除实际需要但未直接导入的依赖。

## 主要类与结构体

无。本文件仅包含 `import` 声明。

## 公共 API 函数

无。本文件不定义任何函数或导出符号。

## 内部实现细节

### Build Tag 约束

```go
//go:build tools
// +build tools
```

使用 `tools` build tag 确保该文件仅在明确指定 `-tags tools` 时参与编译。两行分别是新旧两种 build tag 语法，保持向后兼容。

### 导入的依赖

| 导入路径 | 用途 |
|----------|------|
| `go.skia.org/infra/go/ds` | Google Cloud Datastore 客户端（传递依赖于 `cloud.google.com/go/datastore`）|
| `go.skia.org/infra/go/firestore` | Firestore 客户端 |
| `go.chromium.org/luci` | Chromium LUCI CI 系统 |
| `github.com/vektra/mockery/v2` | Mock 代码生成工具 |

### 为什么需要这个文件

Go 模块系统只会跟踪代码中直接导入的依赖。对于以下情况的依赖会被 `go mod tidy` 自动清除：
- 通过 `go run` 或 `go install` 使用的 CLI 工具
- 在外部脚本（如 `build_task_drivers.sh`）中构建的包
- 作为 `main` 包无法被直接导入的工具

### 具体场景说明

文件中的注释解释了一个特定的依赖链问题：Skia 的构建流程会编译 `@org_skia_go_infra//infra/bots/task_drivers/canary/canary.go`（在 `build_task_drivers.sh` 中），该文件间接依赖 `cloud.google.com/go/datastore`。然而，由于 `canary.go` 所在的包是一个 `main` 包，Go 语言不允许其他包直接导入它。因此，需要通过导入 `go.skia.org/infra/go/ds`（它同样依赖 `cloud.google.com/go/datastore`）来间接锚定这个传递依赖。

### `package main` 声明

该文件声明为 `package main`，与 Skia 项目根目录的 Go 包保持一致。由于使用了 `tools` build tag，它在正常编译时不会与其他 `main` 包冲突。

## 依赖关系

- `go.skia.org/infra` - Skia 基础设施 Go 库
- `go.chromium.org/luci` - Chromium LUCI 持续集成框架
- `github.com/vektra/mockery/v2` - Go 接口 mock 生成器

## 设计模式与设计决策

- **工具依赖模式**: 这是 Go 社区在 golang/go#25922 中讨论并推荐的标准做法
- **空导入（blank import）**: 使用 `_` 前缀导入，仅为了副作用（触发依赖追踪）
- **双格式 build tag**: 同时使用新旧两种 build constraint 语法，确保在所有 Go 版本下都能正确解析

## 性能考量

本文件不参与正常构建，无性能影响。

## 相关文件

- `go.mod` - Go 模块定义文件
- `go.sum` - Go 模块校验和
- `infra/bots/task_drivers/` - 使用这些依赖的任务驱动程序
- `build_task_drivers.sh` - 构建任务驱动程序的脚本
