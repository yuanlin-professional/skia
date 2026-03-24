# bazel_build

> 源文件: infra/bots/task_drivers/bazel_build/bazel_build.go

## 概述

`bazel_build` 是一个 Skia CI/CQ 任务驱动程序，用于执行单个 Bazel 构建目标。该程序封装了在 CI 机器上运行 Bazel 构建所需的所有设置工作，包括配置缓存、管理磁盘空间、执行构建以及可选地复制构建输出到指定目录。它使用 Bazelisk（Bazel 版本管理器）来确保使用正确的 Bazel 版本，并支持通过 `--config` 参数选择预定义的构建配置。

## 架构位置

```
skia/
└── infra/
    └── bots/
        └── task_drivers/
            ├── common/            # 通用 Bazel 工具
            └── bazel_build/
                └── bazel_build.go # Bazel 构建任务驱动（本文件）
```

该程序与其他 Bazel 相关任务驱动（如 `check_generated_files`、`go_linters`）共享通用基础设施。

## 主要类与结构体

### 全局变量（命令行标志）

```go
var (
    projectId      = flag.String("project_id", "", "ID of the Google Cloud project.")
    taskId         = flag.String("task_id", "", "ID of this task.")
    taskName       = flag.String("task_name", "", "Name of the task.")
    workdir        = flag.String("workdir", ".", "Working directory in which the build will be performed.")
    outPath        = flag.String("out_path", "", "Directory into which to copy the //bazel-bin subdirectories...")
    savedOutputDir = infra_common.NewMultiStringFlag("saved_output_dir", nil, `//bazel-bin subdirectories to copy...`)
    local          = flag.Bool("local", false, "True if running locally (as opposed to on the CI/CQ)")
    output         = flag.String("o", "", "If provided, dump a JSON blob of step data...")
)
```

### Bazel 标志（来自 common 包）

```go
bazelFlags := common.MakeBazelFlags(common.MakeBazelFlagsOpts{
    Label:          true,   // --label
    Config:         true,   // --config
    AdditionalArgs: true,   // 其他参数
})
```

这些标志定义：
- **label**: Bazel 构建目标（如 `//src/skia:skia`）
- **config**: 构建配置（对应 `//bazel/buildrc` 中的配置）
- **cache_dir**: Bazel 缓存路径
- **additional_args**: 传递给 Bazel 的额外参数

## 公共 API 函数

### main()

```go
func main()
```

主入口函数，执行以下流程：
1. 创建 Bazel 标志并解析参数
2. 初始化任务驱动上下文
3. 验证参数（outPath 和 savedOutputDir 的组合）
4. 解析为绝对路径
5. 创建 Bazel 实例并配置缓存
6. 注册清理钩子（shutdown 和磁盘空间管理）
7. 执行 Bazel 构建
8. 复制输出（如果指定）

### copyBazelBinSubdirs()

```go
func copyBazelBinSubdirs(ctx context.Context, checkoutDir string, bazelBinSubdirs []string, destinationDir string) error
```

复制 Bazel 构建输出到目标目录。

**参数**:
- `checkoutDir`: Skia 代码检出目录
- `bazelBinSubdirs`: 要复制的 `bazel-bin` 子目录列表
- `destinationDir`: 目标目录

**功能**:
- 使用 `filepath.WalkDir` 遍历源目录树
- 保留目录结构
- 复制所有文件
- 处理符号链接和权限问题

## 内部实现细节

### Bazel 缓存配置

```go
opts := bazel.BazelOptions{
    CachePath: *bazelFlags.CacheDir,
}
bzl, err := bazel.New(ctx, checkoutPath, "", opts)
```

**缓存位置选择**:
GCE VM 的根磁盘只有 15 GB，因此缓存放在更大的磁盘上（通常是挂载的工作磁盘）。这避免了 "磁盘已满" 错误。

### 构建命令构造

```go
args := append([]string{*bazelFlags.Label, fmt.Sprintf("--config=%s", *bazelFlags.Config)}, *bazelFlags.AdditionalArgs...)
if _, err := bzl.Do(ctx, "build", args...); err != nil {
    td.Fatal(ctx, err)
}
```

示例命令：
```bash
bazelisk build //src/skia:skia --config=linux_x64 --compilation_mode=opt
```

### 清理流程

```go
defer func() {
    if !*local {
        cleanErr := common.BazelCleanIfLowDiskSpace(ctx, *bazelFlags.CacheDir, checkoutPath, "bazelisk")
        if _, err := bzl.Do(ctx, "shutdown"); err != nil {
            td.Fatal(ctx, err)
        }
        if cleanErr != nil {
            td.Fatal(ctx, cleanErr)
        }
    }
}()
```

**清理顺序**:
1. 检查磁盘空间并可选地清理缓存
2. 执行 `bazel shutdown` 停止 Bazel 服务器
3. 如果清理失败，报告错误

这确保即使构建失败，资源也被正确释放。

### 文件复制实现

```go
return filepath.WalkDir(srcDir, func(path string, d fs.DirEntry, err error) error {
    if err != nil {
        return skerr.Wrap(err)  // 传播错误
    }
    relPath, err := filepath.Rel(srcDir, path)
    dstPath := filepath.Join(dstDir, relPath)

    if d.IsDir() {
        return skerr.Wrap(os_steps.MkdirAll(ctx, dstPath))
    }
    return skerr.Wrap(os_steps.CopyFile(ctx, path, dstPath))
})
```

**特性**:
- 保留目录结构
- 处理嵌套目录
- 错误包装以提供上下文
- 使用 `os_steps` 进行步骤跟踪

## 依赖关系

### 外部库依赖

```go
import (
    infra_common "go.skia.org/infra/go/common"          // 通用基础设施工具
    "go.skia.org/infra/go/skerr"                        // 错误处理
    "go.skia.org/infra/task_driver/go/lib/bazel"        // Bazel 集成
    "go.skia.org/infra/task_driver/go/lib/os_steps"     // 文件系统操作
    "go.skia.org/infra/task_driver/go/td"               // 任务驱动框架
    "go.skia.org/skia/infra/bots/task_drivers/common"   // Bazel 通用工具
)
```

### 系统依赖

- **Bazelisk**: Bazel 版本管理器，必须在 PATH 中
- **Bazel**: 通过 Bazelisk 自动下载
- **磁盘空间**: 构建缓存可能需要几 GB

### Bazel 配置文件

- **//bazel/buildrc**: 预定义的构建配置
- **.bazelrc**: 用户 Bazel 配置（由程序生成）

### 数据流

```
命令行参数
    ↓
解析和验证
    ↓
bazel.New() → 创建 Bazel 实例
    ↓
bzl.Do("build", args) → 执行构建
    ↓
copyBazelBinSubdirs() → 复制输出（可选）
    ↓
BazelCleanIfLowDiskSpace() → 清理缓存（如需要）
    ↓
bzl.Do("shutdown") → 停止 Bazel 服务器
```

## 设计模式与设计决策

### 延迟清理模式

```go
defer func() {
    // 清理逻辑
}()
```

使用 `defer` 确保：
- 无论构建成功或失败都执行清理
- 资源泄漏被最小化
- Bazel 服务器不会孤立运行

### 错误优先级

```go
cleanErr := common.BazelCleanIfLowDiskSpace(...)
if _, err := bzl.Do(ctx, "shutdown"); err != nil {
    td.Fatal(ctx, err)  // shutdown 错误优先
}
if cleanErr != nil {
    td.Fatal(ctx, cleanErr)  // 然后报告清理错误
}
```

`shutdown` 错误优先于清理错误，因为孤立的 Bazel 服务器可能导致更严重的问题。

### 配置驱动构建

```go
fmt.Sprintf("--config=%s", *bazelFlags.Config)
```

所有构建配置（编译器、优化级别、目标平台）通过配置名称选择，而非命令行参数堆叠。这：
- 简化命令行
- 集中配置管理
- 允许配置继承和组合

### 条件性输出复制

```go
if outputPath != "" {
    if err := copyBazelBinSubdirs(...); err != nil {
        td.Fatal(ctx, err)
    }
}
```

只在需要时复制输出，避免不必要的文件操作。

### 多子目录支持

```go
savedOutputDir = infra_common.NewMultiStringFlag(...)
```

允许复制多个 `bazel-bin` 子目录：
```bash
--saved_output_dir tests --saved_output_dir tools
```

这支持复杂的构建产物收集需求。

## 性能考量

### Bazel 缓存

```go
CachePath: *bazelFlags.CacheDir,
```

**缓存优势**:
- 避免重复编译
- 增量构建速度提升 10-100 倍
- 跨任务共享缓存（如果使用远程缓存）

**缓存权衡**:
- 需要额外磁盘空间（2-10 GB）
- 需要定期清理以避免磁盘满

### 磁盘空间管理

```go
common.BazelCleanIfLowDiskSpace(ctx, *bazelFlags.CacheDir, checkoutPath, "bazelisk")
```

自动检测磁盘空间：
- 如果低于阈值，清理缓存
- 如果足够，保留缓存以加速后续构建
- 平衡速度和空间

### 文件复制优化

```go
os_steps.CopyFile(ctx, path, dstPath)
```

使用 `os_steps.CopyFile` 而非 `io.Copy`：
- 在支持的平台使用 `copy_file_range`（零拷贝）
- 保留文件元数据（时间戳、权限）
- 提供步骤跟踪

### Bazel Shutdown

```go
bzl.Do(ctx, "shutdown")
```

显式停止 Bazel 服务器：
- 释放内存（Bazel 服务器可能占用 1-2 GB）
- 释放文件句柄
- 避免后台进程积累

## 相关文件

### Skia Bazel 配置

- **//bazel/buildrc**: 构建配置定义
  - `linux_x64`: Linux 64 位构建
  - `macos_arm64`: macOS ARM 构建
  - `wasm`: WebAssembly 构建
  - 等等

- **.bazelversion**: 指定 Bazel 版本
- **WORKSPACE**: Bazel 工作空间定义
- **MODULE.bazel**: Bazel 模块定义（新版）

### 通用工具

- **infra/bots/task_drivers/common/bazel.go**: Bazel 标志定义
- **infra/bots/task_drivers/common/disk_space.go**: 磁盘空间管理

### 相关任务驱动

- **check_generated_files**: 验证生成的文件
- **go_linters**: Go 代码检查
- **run_unittests**: 运行单元测试

### CI 配置

- **infra/bots/tasks.json**: 定义使用该驱动的任务
- **infra/bots/jobs.json**: 定义 CI 作业

### 使用示例

在 CI 中，该程序可能这样调用：

```bash
bazel_build \
  --project_id skia-public \
  --task_id 12345abcde \
  --task_name "Build-Linux-Clang-x86_64-Release" \
  --workdir /mnt/pd0/workspace \
  --label //src/skia:skia \
  --config linux_x64 \
  --cache_dir /mnt/pd0/bazel_cache \
  --out_path /mnt/pd0/out \
  --saved_output_dir skia
```

这将构建 `//src/skia:skia` 目标，使用 `linux_x64` 配置，并将 `bazel-bin/skia/` 目录的内容复制到 `/mnt/pd0/out/skia/`。

该程序是 Skia 向 Bazel 构建系统迁移的核心组件，提供了在 CI 环境中可靠运行 Bazel 构建的统一接口。
