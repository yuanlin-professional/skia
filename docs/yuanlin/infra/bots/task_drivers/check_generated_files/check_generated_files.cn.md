# check_generated_files

> 源文件: infra/bots/task_drivers/check_generated_files/check_generated_files.go

## 概述

`check_generated_files` 是一个 Skia CI/CQ 任务驱动程序，用于验证代码库中的生成文件是否是最新的。该程序通过 Bazel 运行各种代码生成工具（如依赖解析器、接口生成器、SkSL 编译器等），然后使用 `git diff` 检查是否有任何文件被修改。如果发现差异，意味着生成的文件与源代码不同步，任务将失败并提示开发者重新生成文件。这确保了提交的代码包含所有最新的生成文件。

## 架构位置

```
skia/
└── infra/
    └── bots/
        └── task_drivers/
            ├── common/                          # 通用工具
            └── check_generated_files/
                └── check_generated_files.go     # 生成文件检查驱动（本文件）
```

## 主要类与结构体

### 命令行标志

```go
var (
    gitPath   = flag.String("git_path", "", "Location of git binary to use for diffs.")
    projectId = flag.String("project_id", "", "ID of the Google Cloud project.")
    taskId    = flag.String("task_id", "", "ID of this task.")
    taskName  = flag.String("task_name", "", "Name of the task.")
    workdir   = flag.String("workdir", ".", "Working directory, the root directory of a full Skia checkout")
    local     = flag.Bool("local", false, "True if running locally (as opposed to on the CI/CQ)")
    output    = flag.String("o", "", "If provided, dump a JSON blob of step data to the given file.")
)
```

## 公共 API 函数

### main()

```go
func main()
```

主函数协调整个检查流程：
1. 解析 Bazel 标志和参数
2. 初始化任务驱动上下文
3. 验证必需参数（git 路径）
4. 在 CI 环境创建临时 Git 仓库（建立基线）
5. 配置 Bazel 环境
6. 按顺序运行所有代码生成工具
7. 运行 Gazelle（Go Bazel 目标生成）和 Buildifier（格式化）
8. 使用 git diff 检查是否有变更
9. 清理 Bazel 缓存（如果磁盘空间不足）

### bazelRun()

```go
func bazelRun(ctx context.Context, skiaPath, label string, args ...string) error
```

使用 Bazelisk 运行指定的 Bazel 目标。

**功能**:
- 构建完整的命令行
- 设置工作目录和环境变量继承
- 记录标准输出和标准错误
- 返回执行结果

### gitInit()

```go
func gitInit(ctx context.Context, gitPath, skiaPath string) error
```

创建临时 Git 仓库并建立基线提交。

**执行步骤**:
1. `git init`: 初始化仓库
2. `git add .`: 添加所有文件
3. `git commit -m "baseline commit"`: 创建基线提交

**目的**: CI 环境中 Swarming 不复制 `.git` 目录，因此需要临时仓库来支持 git diff 操作。

### generateGNIFiles()

```go
func generateGNIFiles(ctx context.Context, skiaPath string) error
```

从 BUILD.bazel 文件重新生成 .gni 文件，实现 Bazel 和 GN 构建系统之间的互操作。

**实现**:
- 使用 `make -C bazel generate_gni_rbe`
- 不通过 `bazel run` 运行，因为 exporter_tool 内部调用 Bazel，会导致死锁

### gazelle()

```go
func gazelle(ctx context.Context, skiaPath string) error
```

运行 Gazelle 工具生成/更新 BUILD.bazel 文件中的 Go 目标。

**实现**:
- 使用 `make -C bazel generate_go`
- 自动发现 Go 包并生成 Bazel 目标

### checkGitDiff()

```go
func checkGitDiff(ctx context.Context, gitPath, skiaPath string) error
```

运行 git diff 并验证结果为空。

**验证**:
- 执行 `git diff --no-ext-diff`
- 如果输出非空，返回错误（包含完整差异）
- 空输出表示所有生成文件都是最新的

## 内部实现细节

### 代码生成工具序列

程序按顺序运行以下工具：

1. **依赖解析器**:
```go
bazelRun(ctx, skiaPath, "//bazel/deps_parser", *bazelFlags.AdditionalArgs...)
```

2. **GL 接口生成器**:
```go
bazelRun(ctx, skiaPath, "//tools/ganesh/gl/interface:generate_gl_interfaces", ...)
```

3. **SkSL 编译器**（8 个目标）:
```go
skslTests := []string{
    "compile_hlsl_tests",
    "compile_glsl_tests",
    "compile_glsl_nosettings_tests",
    "compile_metal_tests",
    "compile_skrp_tests",
    "compile_stage_tests",
    "compile_spirv_tests",
    "compile_wgsl_tests",
}
for _, label := range skslTests {
    bazelRun(ctx, skiaPath, "//tools/skslc:"+label, skslFlags...)
}
```

4. **Workarounds 生成器**:
```go
bazelRun(ctx, skiaPath, "//tools:generate_workarounds", ...)
```

5. **SkSL 压缩工具**（2 个目标）:
```go
bazelRun(ctx, skiaPath, "//tools/sksl-minify:minify_srcs", skslFlags...)
bazelRun(ctx, skiaPath, "//tools/sksl-minify:minify_tests", skslFlags...)
```

6. **GNI 文件生成**:
```go
generateGNIFiles(ctx, skiaPath)
```

7. **Gazelle（Go 目标生成）**:
```go
gazelle(ctx, skiaPath)
```

8. **Buildifier（Bazel 文件格式化）**:
```go
bazelRun(ctx, skiaPath, "//:buildifier", ...)
```

9. **Go 代码生成**:
```go
bazelRun(ctx, skiaPath, "//:go", append(*bazelFlags.AdditionalArgs, "--", "generate", "./...")...)
```

### SkSL 编译配置

```go
skslFlags := append([]string{"--config=compile_sksl"}, *bazelFlags.AdditionalArgs...)
```

使用专门的 `compile_sksl` 配置来编译 SkSL 着色器到各种目标语言（HLSL、GLSL、Metal、SPIR-V、WGSL）。

### 错误处理策略

任何步骤失败都会立即终止任务：
```go
if err := bazelRun(ctx, skiaPath, label, args...); err != nil {
    td.Fatal(ctx, err)
}
```

这确保问题快速暴露，避免后续步骤基于不完整的输出运行。

## 依赖关系

### 外部库依赖

```go
import (
    sk_exec "go.skia.org/infra/go/exec"              // 命令执行
    "go.skia.org/infra/task_driver/go/lib/bazel"     // Bazel 集成
    "go.skia.org/infra/task_driver/go/lib/os_steps"  // 文件系统操作
    "go.skia.org/infra/task_driver/go/td"            // 任务驱动框架
    "go.skia.org/skia/infra/bots/task_drivers/common"// 通用工具
)
```

### 系统依赖

- **Git**: 必需，用于差异检查
- **Bazelisk**: Bazel 版本管理器
- **Make**: 用于运行 GNI 生成和 Gazelle
- **Go 工具链**: 用于 Go 代码生成

### 生成工具依赖

- **//bazel/deps_parser**: 依赖解析工具
- **//tools/ganesh/gl/interface:generate_gl_interfaces**: OpenGL 接口生成器
- **//tools/skslc**: SkSL 编译器
- **//tools:generate_workarounds**: 驱动 workarounds 生成器
- **//tools/sksl-minify**: SkSL 压缩工具
- **Gazelle**: Go Bazel 目标生成器
- **Buildifier**: Bazel 文件格式化工具

### 数据流

```
命令行参数 → 解析
    ↓
gitInit() → 创建基线（仅 CI）
    ↓
bazelRun("//bazel/deps_parser") → 生成依赖文件
    ↓
bazelRun("//tools/ganesh/gl/interface:generate_gl_interfaces") → 生成 GL 接口
    ↓
for each SkSL 目标:
    bazelRun("//tools/skslc:compile_*_tests") → 编译着色器
    ↓
bazelRun("//tools:generate_workarounds") → 生成 workarounds
    ↓
bazelRun("//tools/sksl-minify:minify_*") → 压缩 SkSL
    ↓
generateGNIFiles() → 生成 GNI 文件
    ↓
gazelle() → 生成 Go Bazel 目标
    ↓
bazelRun("//:buildifier") → 格式化 Bazel 文件
    ↓
bazelRun("//:go", "generate", "./...") → Go 代码生成
    ↓
checkGitDiff() → 验证无差异
    ↓
BazelCleanIfLowDiskSpace() → 清理缓存（如需要）
```

## 设计模式与设计决策

### 顺序执行

所有生成步骤顺序执行，而非并行：
- 某些步骤有依赖关系（如 GNI 生成依赖 Bazel 目标）
- 简化错误诊断
- 避免文件竞争条件

### 失败快速原则

```go
if err != nil {
    td.Fatal(ctx, err)
}
```

任何错误立即终止，好处：
- 减少无效计算
- 快速反馈
- 节省 CI 资源

### 配置驱动行为

SkSL 编译使用专门配置：
```go
skslFlags := append([]string{"--config=compile_sksl"}, ...)
```

这允许：
- 针对编译任务优化设置
- 统一配置管理
- 便于调整和维护

### 两阶段 Git 设置

1. 创建基线（gitInit）
2. 检查差异（checkGitDiff）

这种分离允许在基线和检查之间插入任意生成步骤。

### 工具隔离

GNI 生成和 Gazelle 不通过 `bazel run`：
```go
runCmd := &sk_exec.Command{
    Name: "make",
    Args: []string{"-C", "bazel", "generate_gni_rbe"},
    ...
}
```

**原因**: 这些工具内部调用 Bazel，使用 `bazel run` 会导致死锁（Bazel 不支持嵌套调用）。

## 性能考量

### Bazel 缓存利用

所有工具通过 Bazel 运行，利用其缓存：
- 未变更的生成器不重新构建
- 未变更的输入不重新生成
- 显著加速重复运行

### 磁盘空间管理

```go
common.BazelCleanIfLowDiskSpace(ctx, *bazelFlags.CacheDir, skiaPath, "bazelisk")
```

任务完成后检查并清理缓存，防止磁盘满导致后续任务失败。

### SkSL 编译优化

```go
skslFlags := append([]string{"--config=compile_sksl"}, ...)
```

专用配置可能包含：
- 优化的编译器标志
- 并行编译设置
- 缓存策略调整

### 顺序 vs 并行

虽然当前实现是顺序的，但 Bazel 内部会并行化独立任务（如不同的 SkSL 目标）。

## 相关文件

### 生成的文件

- **bazel/deps.bzl**: 依赖定义（由 deps_parser 生成）
- **src/gpu/ganesh/gl/GrGLInterface.cpp**: GL 接口实现（自动生成）
- **src/sksl/generated/**: SkSL 编译输出
- **src/sksl/sksl_*.minified.sksl**: 压缩后的 SkSL
- **各种 .gni 文件**: GN 构建定义（从 BUILD.bazel 导出）
- **BUILD.bazel 文件**: Gazelle 生成/更新的 Go 目标

### 生成工具源码

- **bazel/deps_parser/**: 依赖解析器实现
- **tools/ganesh/gl/interface/**: GL 接口生成器
- **tools/skslc/**: SkSL 编译器
- **tools/generate_workarounds.cpp**: Workarounds 生成器
- **tools/sksl-minify/**: SkSL 压缩工具

### 构建配置

- **//bazel/buildrc**: Bazel 构建配置
  - `compile_sksl`: SkSL 编译配置
- **.bazelrc**: 用户 Bazel 配置
- **bazel/Makefile**: GNI 生成和 Gazelle 目标

### CI 配置

- **infra/bots/tasks.json**: 定义 check_generated_files 任务
- **infra/bots/jobs.json**: CQ 作业配置

### 相关任务驱动

- **go_linters**: Go 代码检查（可能也验证 go generate）
- **bazel_build**: 执行实际构建
- **run_unittests**: 运行测试

### 开发工作流

开发者修改源文件后应运行：
```bash
# 本地重新生成所有文件
make -C bazel generate_all
# 或者
bazelisk run //tools:regenerate_all
```

CQ 运行 `check_generated_files` 验证开发者已经这样做了。如果失败，CQ 会提示：
```
Generated files are out of sync. Please run:
  make -C bazel generate_all
and commit the changes.
```

该任务是 Skia 代码质量保证的关键环节，确保生成代码和源代码始终保持同步，避免构建错误和运行时问题。
