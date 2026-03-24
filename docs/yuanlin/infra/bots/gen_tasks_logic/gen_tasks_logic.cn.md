# Gen Tasks Logic - CI 任务生成核心逻辑

> 源文件: `infra/bots/gen_tasks_logic/gen_tasks_logic.go`

## 概述

`gen_tasks_logic.go` 是 Skia CI 任务生成系统的核心文件，定义了所有 CI 常量（CAS 规格名称、操作系统版本、机器类型等）、`Config` 配置结构体、`builder` 顶层协调器，以及各种具体的任务生成方法（编译、测试、性能测试、Housekeeper、Bazel 构建等）。这是整个任务生成管线中最大的文件（约 2400 行）。

## 架构位置

位于 `infra/bots/gen_tasks_logic/` 包中，是任务生成系统的中枢。定义了全局常量、配置结构和具体的任务模板。

## 主要类与结构体

- **`Config`**: 全局配置结构体
  - `AssetsDir`, `BuilderNameSchemaFile`: 资源路径
  - `GoldHashesURL`, `GsBucketGm`, `GsBucketNano`: Gold/GCS 配置
  - `InternalHardwareLabel`: 内部设备 ID 函数
  - `NoUpload`, `PathToSkia`, `Pool`, `Project`: 项目设置
  - 多个 `ServiceAccount*` 字段: 各类服务账号
  - `SwarmDimensions`, `AddTaskCallback`: 自定义维度和回调
- **`builder`**: 顶层构建器
  - 嵌入 `*specs.TasksCfgBuilder`
  - `cfg *Config`, `jobNameSchema *JobNameSchema`
  - 资产版本缓存

## 公共 API 函数

- **`GenTasks(cfg *Config)`**: 主入口，生成完整的 tasks.json
- 大量任务生成方法: `compile()`, `dm()`, `perf()`, `bazelBuild()`, `bazelTest()` 等

## 内部实现细节

1. **常量系统**: 定义了 ~50 个 CAS 规格名、OS 版本、机器类型等常量
2. **缓存系统**: Git、Go、工作目录、ccache、Docker 等命名缓存
3. **CIPD 包管理**: `CIPD_PKG_LUCI_AUTH`, `CIPD_PKGS_GOLDCTL` 等
4. **ISOLATE_ASSET_MAPPING**: 定义 8 种资产（skimage, skp, svg 等）的隔离配置
5. **任务生成流程**: GenTasks -> 解析所有作业名称 -> 为每个作业调用 genTasksForJob -> finish
6. **维度计算**: `linuxGceDimensions`, `macModelDimensions` 等辅助函数
7. **编译任务**: 处理 Clang、GCC、MSVC、Emscripten 等多种编译器
8. **测试任务**: DM 和 Nanobench 的参数配置

## 依赖关系

- `go.skia.org/infra/go/cas/rbe`: CAS/RBE 配置
- `go.skia.org/infra/go/cipd`: CIPD 包管理
- `go.skia.org/infra/task_scheduler/go/specs`: 任务调度器规格
- `go.skia.org/skia/bazel/device_specific_configs`: Bazel 设备配置
- 标准库: `encoding/json`, `fmt`, `log`, `os`, `regexp`, `sort`, `strings`, `time`

## 设计模式与设计决策

- 声明式任务定义: 通过配置常量和条件逻辑描述任务
- 可扩展性: Config 支持回调函数和自定义维度，允许外部仓库复用
- 版本管理: OS 版本、SKP 版本等通过常量集中管理
- 任务去重: 同名任务只生成一次

## 性能考量

- 任务生成是离线操作，优化目标是生成的 tasks.json 的正确性
- 使用资产版本缓存避免重复读取 VERSION 文件

## 相关文件

- `infra/bots/gen_tasks_logic/job_builder.go`: 作业构建器
- `infra/bots/gen_tasks_logic/task_builder.go`: 任务构建器
- `infra/bots/gen_tasks_logic/schema.go`: 名称 schema
- `infra/bots/gen_tasks_logic/dm_flags.go`: DM 测试标志
- `infra/bots/gen_tasks_logic/nano_flags.go`: Nanobench 标志
- `infra/bots/gen_tasks_logic/compile_cas.go`: 编译 CAS 规格
