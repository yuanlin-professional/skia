# gen_tasks_logic - 任务生成核心逻辑

## 概述

`gen_tasks_logic/` 目录包含用 Go 语言编写的任务生成核心逻辑，负责根据配置文件和预定义规则生成 `tasks.json` 文件。这是 Skia CI/CD 任务调度的核心引擎。

## 目录结构

```
gen_tasks_logic/
├── gen_tasks_logic.go   # 主逻辑：任务定义、规则匹配、DAG 生成
├── job_builder.go       # 作业构建器：定义作业与任务的关联
├── task_builder.go      # 任务构建器：定义单个任务的属性
├── compile_cas.go       # CAS（Content Addressable Storage）编译配置
├── dm_flags.go          # DM（Drawing Manager）测试标志定义
├── nano_flags.go        # Nanobench 性能测试标志定义
└── schema.go            # 数据结构定义
```

## 关键文件

### gen_tasks_logic.go

主文件，包含：
- 常量定义：CAS 配置名称、操作系统版本、机器类型、输出目录等
- `GenTasks()` 函数：任务生成的入口点
- 各类任务的生成函数（编译、测试、性能评测、维护等）
- 平台和配置的匹配逻辑

重要常量：
- CAS 配置：`CAS_COMPILE`、`CAS_TEST`、`CAS_PERF`、`CAS_RECIPES` 等
- 操作系统：`DEFAULT_OS_LINUX_GCE`（Ubuntu 24.04）、`DEFAULT_OS_MAC`（Mac 15.7）等
- 机器类型：`MACHINE_TYPE_SMALL`（2核）、`MACHINE_TYPE_MEDIUM`（16核）、`MACHINE_TYPE_LARGE`（64核）

### job_builder.go

提供作业构建的抽象层，将配置文件中定义的作业名称映射为具体的任务链。

### task_builder.go

提供任务构建的抽象层，封装了任务的属性设置，包括维度（dimensions）、CIPD 包、环境变量等。

### dm_flags.go

定义 DM（Skia 的绘图测试管理器）在不同平台和配置下使用的命令行标志。根据构建器名称中的关键字（如 GPU 类型、操作系统等）确定哪些测试应该运行或跳过。

### nano_flags.go

类似于 `dm_flags.go`，但针对 Nanobench（性能基准测试工具），定义在不同配置下的性能测试标志。

### compile_cas.go

定义编译任务的 CAS 输入配置，指定哪些文件需要传输到编译机器。

## 工作流程

```
cfg.json + jobs.json
        │
        ▼
   gen_tasks.go（入口）
        │
        ▼
   GenTasks()（gen_tasks_logic.go）
        │
        ├── 解析配置
        ├── 遍历 jobs.json 中的每个作业
        ├── 根据作业名称匹配生成规则
        ├── 构建任务 DAG
        └── 输出 tasks.json
```

## 依赖关系

- `go.skia.org/infra/go/cas/rbe` - RBE CAS 集成
- `go.skia.org/infra/go/cipd` - CIPD 包管理
- `go.skia.org/infra/task_scheduler/go/specs` - 任务调度器规范定义
- `go.skia.org/skia/bazel/device_specific_configs` - 设备特定配置

## 相关文档与参考

- 父目录 `infra/bots/README.md` 中关于任务和作业的说明
- [Task Scheduler specs 包](https://pkg.go.dev/go.skia.org/infra/task_scheduler/go/specs)
