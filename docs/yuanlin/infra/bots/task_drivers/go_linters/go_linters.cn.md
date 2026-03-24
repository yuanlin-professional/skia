# go_linters

> 源文件: infra/bots/task_drivers/go_linters/go_linters.go

## 概述

`go_linters` 是一个 Skia CI/CQ 任务驱动程序，用于通过 Bazel 运行各种 Go 语言代码检查工具（linters）。该程序会执行 Go 代码格式化工具 `go fmt`，并通过 `git diff` 验证代码是否符合格式规范。如果发现任何格式错误或 Git 差异，任务将失败。这确保了提交到 Skia 仓库的 Go 代码都遵循统一的代码风格标准。

## 架构位置

该文件位于 Skia 持续集成基础设施的任务驱动层：

```
skia/
├── infra/
│   └── bots/
│       └── task_drivers/           # CI 任务驱动程序目录
│           ├── common/             # 通用任务驱动工具
│           └── go_linters/
│               └── go_linters.go   # Go 代码检查驱动程序
```

该程序作为 CI/CQ（持续集成/代码质量）检查的一部分运行，确保代码质量标准在合并前得到验证。

## 主要类与结构体

### 全局变量（命令行标志）

```go
var (
    gitPath   = flag.String("git_path", "", "Location of git binary to use for diffs.")
    projectId = flag.String("project_id", "", "ID of the Google Cloud project.")
    taskId    = flag.String("task_id", "", "ID of this task.")
    taskName  = flag.String("task_name", "", "Name of the task.")
    workdir   = flag.String("workdir", ".", "Working directory, the root directory of a full Skia checkout")
    local     = flag.Bool("local", false, "True if running locally (as opposed to on the CI/CQ)")
    output    = flag.String("o", "", "If provided, dump a JSON blob of step data to the given file. Prints to stdout if '-' is given.")
)
```

这些标志定义了程序运行所需的所有配置参数。

## 公共 API 函数

### main()

```go
func main()
```

主入口函数，执行以下流程：
1. 解析 Bazel 相关标志
2. 初始化任务驱动上下文
3. 验证必需参数（特别是 git 路径）
4. 转换为绝对路径
5. 在非本地环境创建临时 Git 仓库
6. 配置 Bazel 环境
7. 运行 Go 格式化工具
8. 检查 Git 差异
9. 清理 Bazel 缓存（如果磁盘空间不足）

### bazelRun()

```go
func bazelRun(ctx context.Context, skiaPath, label string, args ...string) error
```

使用 Bazelisk 运行指定的 Bazel 目标。

**参数**:
- `ctx`: 上下文对象
- `skiaPath`: Skia 仓库路径
- `label`: Bazel 标签（如 `//:go`）
- `args`: 额外的命令行参数

**功能**:
- 构建 bazelisk 命令
- 设置工作目录和环境
- 记录标准输出和标准错误
- 返回执行结果

### gitInit()

```go
func gitInit(ctx context.Context, gitPath, skiaPath string) error
```

创建临时 Git 仓库并建立基线。

**目的**: 在 CI 环境中，Swarming 不会复制 `.git` 目录，因此需要创建临时仓库来支持 `git diff` 操作。

**步骤**:
1. 执行 `git init` 初始化仓库
2. 执行 `git add .` 添加所有文件
3. 执行 `git commit -m "baseline commit"` 创建基线提交

### checkGitDiff()

```go
func checkGitDiff(ctx context.Context, gitPath, skiaPath string) error
```

运行 `git diff` 检查是否有未格式化的代码。

**验证逻辑**:
- 执行 `git diff --no-ext-diff`
- 如果输出非空，表示存在差异，返回错误
- 错误信息包含完整的差异内容

## 内部实现细节

### Bazel 配置

```go
opts := bazel.BazelOptions{
    CachePath: *bazelFlags.CacheDir,
}
if err := bazel.EnsureBazelRCFile(ctx, opts); err != nil {
    td.Fatal(ctx, err)
}
```

确保 Bazel 配置文件存在并正确设置缓存路径。Bazel 缓存放在较大的磁盘上，因为 GCE VM 的根磁盘只有 15 GB。

### Go 格式化执行

```go
if err := bazelRun(ctx, skiaPath, "//:go", append(*bazelFlags.AdditionalArgs, "--", "fmt", "./...")...); err != nil {
    td.Fatal(ctx, err)
}
```

执行命令等效于：
```bash
bazelisk run //:go -- fmt ./...
```

这会格式化 Skia 仓库中的所有 Go 代码。

### 磁盘空间管理

```go
if !*local {
    if err := common.BazelCleanIfLowDiskSpace(ctx, *bazelFlags.CacheDir, skiaPath, "bazelisk"); err != nil {
        td.Fatal(ctx, err)
    }
}
```

在 CI 环境中，如果磁盘空间不足，会清理 Bazel 缓存。这防止磁盘满导致的任务失败。

## 依赖关系

### 外部库依赖

```go
import (
    sk_exec "go.skia.org/infra/go/exec"                 // 命令执行
    "go.skia.org/infra/task_driver/go/lib/bazel"        // Bazel 集成
    "go.skia.org/infra/task_driver/go/lib/os_steps"     // 文件系统操作
    "go.skia.org/infra/task_driver/go/td"               // 任务驱动框架
    "go.skia.org/skia/infra/bots/task_drivers/common"   // 通用任务工具
)
```

### 系统依赖

- **Git**: 必需，用于差异检查
- **Bazelisk**: Bazel 版本管理器
- **Go 工具链**: 通过 Bazel 管理

### 数据流

```
命令行参数 → main()
    ↓
路径解析和验证
    ↓
gitInit() → 创建临时 Git 仓库（仅 CI 环境）
    ↓
bazelRun("//:go", "fmt", "./...") → 格式化代码
    ↓
checkGitDiff() → 验证无差异
    ↓
BazelCleanIfLowDiskSpace() → 清理缓存（如需要）
```

## 设计模式与设计决策

### 任务驱动框架集成

```go
ctx := td.StartRun(projectId, taskId, taskName, output, local)
defer td.EndRun(ctx)
```

使用 Skia 的任务驱动框架提供：
- 结构化的步骤报告
- 统一的错误处理
- JSON 格式的步骤数据导出

### 本地与 CI 环境分离

程序通过 `local` 标志区分运行环境：

**本地环境**:
- 假设存在 `.git` 目录
- 跳过磁盘清理

**CI 环境**:
- 创建临时 Git 仓库
- 执行磁盘空间管理

### 命令包装器模式

`bazelRun` 函数封装了所有 Bazel 命令执行：
- 统一的日志记录
- 一致的错误处理
- 标准化的命令构建

### 失败快速原则

使用 `td.Fatal(ctx, err)` 在任何错误时立即终止：
- 减少无效计算
- 快速反馈给开发者
- 节省 CI 资源

## 性能考量

### Bazel 缓存优化

```go
CachePath: *bazelFlags.CacheDir,
```

将 Bazel 缓存放在大容量磁盘上：
- 默认的主目录（根磁盘）只有 15 GB
- 缓存可以显著加速后续构建
- 避免重复下载依赖

### 条件性磁盘清理

仅在磁盘空间不足时清理缓存：
- 保留热缓存提高性能
- 避免不必要的清理开销
- 平衡空间和速度

### Git 操作优化

```go
Args: []string{"diff", "--no-ext-diff"}
```

使用 `--no-ext-diff` 标志：
- 禁用外部差异工具
- 加快差异计算
- 确保输出格式一致

### 命令执行配置

```go
InheritEnv: true,  // 需要确保 bazelisk 在 PATH 中
```

继承环境变量确保能找到 bazelisk，同时：
```go
InheritEnv: false,  // Git 命令，隔离环境
```

Git 命令不继承环境，避免本地 Git 配置干扰。

## 相关文件

### Skia 基础设施文件

- **/infra/bots/task_drivers/common/bazel.go**: Bazel 通用工具
- **/infra/bots/task_drivers/common/**: 其他通用任务驱动工具
- **/.bazelrc**: Bazel 配置文件
- **/bazel/buildrc**: 构建配置

### Go 代码文件

- **/infra/**: Skia 基础设施 Go 代码
- **/tools/**: 工具相关 Go 代码
- **各个子目录的 *.go 文件**: 被检查的目标文件

### 相关任务驱动

- **check_generated_files**: 检查生成的文件是否最新
- **bazel_build**: 执行 Bazel 构建
- **run_unittests**: 运行单元测试

### CI/CQ 集成

该任务通常作为 CQ（Code Quality）检查的一部分：

```
代码提交 → CQ 触发
    ↓
go_linters (本程序)
    ↓
其他检查（测试、构建等）
    ↓
所有检查通过 → 允许合并
```

这确保所有提交的 Go 代码都符合项目的格式标准，维护代码库的一致性和可读性。
