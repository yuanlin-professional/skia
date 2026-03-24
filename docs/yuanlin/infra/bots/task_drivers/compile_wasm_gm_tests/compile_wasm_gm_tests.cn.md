# compile_wasm_gm_tests

> 源文件: infra/bots/task_drivers/compile_wasm_gm_tests/compile_wasm_gm_tests.go

## 概述

`compile_wasm_gm_tests` 是一个 Skia 持续集成任务驱动程序，负责将 GM 测试编译为 WebAssembly (WASM) 格式。该程序使用 Docker 容器和 Emscripten 工具链来执行编译任务，并将编译后的 WASM 和 JavaScript 文件输出到指定目录。这是 Skia 测试基础设施的重要组成部分，用于支持在浏览器环境中运行图形测试。

## 架构位置

该文件位于 Skia 持续集成基础设施的任务驱动层：

```
skia/
├── infra/
│   └── bots/
│       └── task_drivers/         # CI 任务驱动程序目录
│           └── compile_wasm_gm_tests/
│               └── compile_wasm_gm_tests.go  # WASM GM 测试编译驱动
```

该程序作为 Swarming 任务执行，属于 Skia 构建和测试流水线的一部分。它与其他任务驱动程序协同工作，支持跨平台的图形测试流程。

## 主要类与结构体

### 常量定义

```go
const dockerImage = "gcr.io/skia-public/canvaskit-emsdk:3.1.26_v2"
const innerBuildScript = "/SRC/infra/canvaskit/build_gmtests.sh"
```

- **dockerImage**: 指定使用的 Docker 镜像，包含 Emscripten SDK 3.1.26 版本
- **innerBuildScript**: 容器内部执行的构建脚本路径

### 命令行标志

程序使用 Go `flag` 包定义多个命令行参数：

- **outPath**: 编译后 WASM/JS 代码的输出目录
- **projectID**: Google Cloud 项目 ID
- **skiaPath**: Skia 代码仓库根目录路径
- **taskID**: 任务 ID，用于追踪和日志记录
- **taskName**: 任务名称
- **workPath**: 临时文件存储目录（如 Docker 构建文件）
- **local**: 是否在本地运行（与在 CI 机器上运行相对）
- **outputSteps**: 步骤数据输出文件路径（JSON 格式）

## 公共 API 函数

### main()

```go
func main()
```

主入口函数，负责：
1. 解析命令行参数并初始化任务驱动上下文
2. 创建必要的输出和工作目录
3. 设置 Docker 环境和身份验证
4. 在 Docker 容器中执行编译脚本
5. 提取编译输出到目标目录

### setupDocker()

```go
func setupDocker(ctx context.Context, isLocal bool) (*docker.Docker, error)
```

配置 Docker 环境：
- 创建用于访问 Google Container Registry 的令牌源
- 初始化具有适当权限的 Docker 客户端
- 返回配置好的 Docker 实例供后续使用

**参数**:
- `ctx`: 上下文对象，包含任务步骤信息
- `isLocal`: 标识是本地运行还是 CI 环境运行

**返回值**:
- Docker 实例和可能的错误

### extractOutput()

```go
func extractOutput(ctx context.Context, workDir, outAbsPath string) error
```

从工作目录中提取编译产物：
- 扫描工作目录中的所有文件
- 筛选包含 "wasm_gm_tests" 的文件名
- 将匹配的文件移动到输出目录

**参数**:
- `ctx`: 任务执行上下文
- `workDir`: Docker 容器的输出目录
- `outAbsPath`: 最终输出目录的绝对路径

## 内部实现细节

### Docker 容器执行流程

1. **卷挂载配置**:
```go
volumes := []string{skiaAbsPath + ":/SRC", workAbsPath + ":/OUT"}
```
将主机的 Skia 源码目录挂载到容器的 `/SRC`，工作目录挂载到 `/OUT`

2. **命令执行**:
```go
command := []string{innerBuildScript}
```
容器内执行 `/SRC/infra/canvaskit/build_gmtests.sh` 脚本

3. **文件提取**:
使用 `os.Rename` 移动文件而非复制，提高性能

### 错误处理机制

程序在多个关键点使用 `td.Fatal(ctx, err)` 进行错误处理：
- 目录创建失败
- Docker 设置失败
- 容器运行失败
- 输出提取失败

所有错误都会导致任务立即终止并记录详细信息。

### 身份验证流程

使用 `auth_steps.Init()` 创建令牌源：
```go
ts, err := auth_steps.Init(ctx, isLocal, auth.ScopeUserinfoEmail, storage.ScopeReadOnly)
```

支持的权限范围：
- `auth.ScopeUserinfoEmail`: 用户信息访问
- `storage.ScopeReadOnly`: Google Cloud Storage 只读访问

## 依赖关系

### 外部依赖

```go
import (
    "cloud.google.com/go/storage"              // Google Cloud Storage SDK
    "go.skia.org/infra/go/auth"               // Skia 身份验证库
    "go.skia.org/infra/go/skerr"              // Skia 错误处理
    "go.skia.org/infra/task_driver/go/lib/auth_steps"   // 任务驱动身份验证
    "go.skia.org/infra/task_driver/go/lib/docker"       // Docker 集成
    "go.skia.org/infra/task_driver/go/lib/os_steps"     // 操作系统操作
    "go.skia.org/infra/task_driver/go/td"               // 任务驱动框架
)
```

### 系统依赖

- **Docker**: 需要 Docker 守护进程运行
- **Google Cloud Registry**: 拉取 Emscripten Docker 镜像
- **build_gmtests.sh**: 实际的编译脚本（位于 `/infra/canvaskit/` 目录）

### 数据流

```
命令行参数 → main()
    ↓
创建目录 (MkdirAll)
    ↓
setupDocker() → 身份验证 → Docker 实例
    ↓
Docker.Run() → 容器执行 build_gmtests.sh
    ↓
extractOutput() → 移动 WASM/JS 文件到输出目录
```

## 设计模式与设计决策

### 任务驱动模式

使用 Skia 的 `task_driver` 框架：
```go
ctx := td.StartRun(projectID, taskID, taskName, outputSteps, local)
defer td.EndRun(ctx)
```

这种模式提供：
- 统一的步骤跟踪和日志记录
- 结构化的错误报告
- JSON 格式的步骤数据输出

### 容器化构建

使用 Docker 容器隔离编译环境的优势：
- **环境一致性**: 确保本地和 CI 环境使用相同的工具链版本
- **依赖管理**: 所有 Emscripten 依赖包含在镜像中
- **可重现性**: 固定的镜像版本保证构建可重现

### 延迟清理模式

```go
defer func() { _ = doc.Cleanup(ctx) }()
```

使用 `defer` 确保无论成功或失败都清理 Docker 资源。

### 绝对路径策略

```go
outAbsPath := td.MustGetAbsolutePathOfFlag(ctx, *outPath, "out_path")
```

所有路径都转换为绝对路径，避免 Docker 容器和主机之间的路径混淆问题。

## 性能考量

### 文件移动 vs 复制

```go
if err := os.Rename(oldFile, newFile); err != nil {
    return td.FailStep(ctx, skerr.Wrapf(err, "copying %s to %s", oldFile, newFile))
}
```

使用 `os.Rename` 而非文件复制，在同一文件系统上移动文件时几乎是瞬时的。

### Docker 镜像缓存

Docker 镜像 `gcr.io/skia-public/canvaskit-emsdk:3.1.26_v2` 会被本地缓存，避免每次任务都重新下载几百 MB 的镜像。

### 选择性文件提取

```go
if strings.Contains(name, "wasm_gm_tests") {
    // 只处理相关文件
}
```

仅提取匹配特定模式的文件，减少不必要的文件操作。

### 并行性考虑

该任务本身不执行并行操作，但在 Swarming 集群中可以与其他任务并行运行。Docker 容器内的编译过程可能利用多核 CPU。

## 相关文件

- **/infra/canvaskit/build_gmtests.sh**: 实际的 WASM 编译脚本
- **/infra/bots/task_drivers/common/**: 通用任务驱动工具
- **/tools/**: Skia 工具目录，包含其他构建辅助工具
- **Docker 镜像定义**: gcr.io/skia-public/canvaskit-emsdk 的构建文件
- **/gm/**: GM（Golden Master）测试源文件目录
- **/modules/canvaskit/**: CanvasKit 模块相关文件

### 相关任务驱动

- **compile_wasm_gm_tests**: 当前程序
- **test_wasm_gm_tests**: 运行编译后的 WASM 测试
- **perf_puppeteer_canvaskit**: CanvasKit 性能测试
- **upload_wasm_results**: 上传测试结果到 Gold

### 工作流集成

```
compile_wasm_gm_tests (本程序)
    ↓ 产生 WASM/JS 文件
test_wasm_gm_tests
    ↓ 生成测试结果
upload_wasm_results
    ↓ 上传到 Skia Gold
```

该任务是 Skia WASM 测试流水线的第一步，为后续的测试执行和结果分析提供编译产物。
