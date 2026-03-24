# Task Builder - CI 任务构建器

> 源文件: `infra/bots/gen_tasks_logic/task_builder.go`

## 概述

`task_builder.go` 实现了 Skia CI 系统的核心任务构建器 `TaskBuilder`。它提供了丰富的 API 用于配置任务的各个方面：CIPD 包、CAS 规格、命令、维度、超时、缓存、环境变量、依赖关系等。同时包含了工具链配置的高层辅助方法（Bazel、CMake、Git、Go、Docker 等）。

## 架构位置

位于 `infra/bots/gen_tasks_logic/` 包中，是任务配置的直接操作层。被 `jobBuilder.addTask` 创建和使用。

## 主要类与结构体

- **`TaskBuilder`**: 任务构建器
  - 嵌入 `*jobBuilder`: 父作业引用
  - 嵌入 `Parts`: 名称组件
  - `Name string`: 任务名称
  - `Spec *specs.TaskSpec`: 任务规格
  - `recipeProperties map[string]string`: 配方属性
- **`uploadAssetCASCfg`**: CIPD 到 CAS 上传配置
  - `alwaysIsolate`, `uploadTaskName`, `path`

## 公共 API 函数

### 基础配置
- `attempts(a int)`, `cache(...)`, `cmd(...)`, `dimension(...)`, `expiration(e)`, `idempotent()`, `cas(casSpec)`, `env(key, value)`, `envPrefixes(key, values)`, `addToPATH(loc)`, `output(paths)`, `serviceAccount(sa)`, `timeout(t)`, `dep(tasks)`, `cipd(pkgs)`, `cipdFromDEPS(pkgName)`

### 工具链
- `usesBazel(hostOSArch)`, `usesCCache()`, `usesCMake()`, `usesGit()`, `usesGo()`, `usesDocker()`

### 资产管理
- `asset(assets)`, `assetWithVersion(name, version)`, `useIsolatedAssets()`

## 内部实现细节

1. **去重逻辑**: `dimension`, `cipd`, `cache`, `dep`, `output`, `envPrefixes` 都检查重复项
2. **CIPD 冲突检测**: 同名不同定义的包会触发 `log.Fatal`
3. **`cipdFromDEPS`**: 从 DEPS 文件解析 CIPD 包版本
4. **`useIsolatedAssets`**: Android/iOS/ChromeOS 使用隔离资产而非直接 CIPD 下载
5. **`usesGo`**: 自动依赖 Git，添加 GOROOT/GOPATH/PATH
6. **`usesDocker`**: 配置 Docker HOME 目录和认证
7. **`shellsOutToBazel`**: 检测 Fontations/RustPNG/ICU4X 需要 Bazel

## 依赖关系

- `go.skia.org/infra/go/cipd`: CIPD 包定义
- `go.skia.org/infra/task_scheduler/go/specs`: 任务规格
- `go.skia.org/skia/infra/bots/deps`: DEPS 文件解析
- 同包: `jobBuilder`, `Parts`, 常量定义

## 设计模式与设计决策

- 构建器模式: 提供流式 API 配置任务的各个方面
- 防御性编程: 重复检测和冲突检测防止配置错误
- 平台感知: `usesBazel`, `usesCMake`, `usesGo` 根据目标平台选择正确的包
- 自动依赖: `usesGo` 自动引入 Git 依赖

## 性能考量

- `useIsolatedAssets` 决定是通过 CAS 还是 CIPD 获取资产，影响任务启动时间
- 去重逻辑避免重复的 CIPD 下载和 PATH 配置

## 相关文件

- `infra/bots/gen_tasks_logic/job_builder.go`: 创建 TaskBuilder 的作业构建器
- `infra/bots/gen_tasks_logic/dm_flags.go`: DM 标志生成（挂在 TaskBuilder 上）
- `infra/bots/gen_tasks_logic/nano_flags.go`: Nanobench 标志生成
