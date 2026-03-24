# run_gn_to_bp - GN 到 Android.bp 转换任务驱动

> 源文件: `infra/bots/task_drivers/run_gn_to_bp/run_gn_to_bp.go`

## 概述

`run_gn_to_bp` 是一个 Go 语言编写的任务驱动程序,用于在 Skia 的 CI 环境中自动运行 `gn_to_bp.py` 脚本,将 GN 构建系统的配置转换为 Android 构建系统所需的 `Android.bp` 格式。该程序先获取 GN 工具,然后执行转换脚本。

## 架构位置

属于 Skia 基础设施中的任务驱动(Task Driver)层,是 Swarming 任务调度系统的可执行入口之一,负责 Android 平台构建文件的自动生成。

## 主要类与结构体

无独立的结构体定义。使用 Skia infra 库提供的 `td`(Task Driver)和 `exec` 包。

## 公共 API 函数

- **`main()`**: 程序入口。解析以下命令行标志:
  - `--project_id`: Google Cloud 项目 ID
  - `--task_id`: 任务 ID
  - `--task_name`: 任务名称
  - `--o`: JSON 输出路径
  - `--local`: 是否本地运行
  - `--skia_checkout_root`: Skia checkout 根目录

## 内部实现细节

1. 通过 `td.StartRun` 初始化任务驱动上下文
2. 获取 Skia checkout 的绝对路径
3. 执行 `bin/fetch-gn` 获取 GN 工具
4. 运行 `python3 gn/gn_to_bp.py --gn <gn_path>` 完成转换

## 依赖关系

- `go.skia.org/infra/go/exec` - 命令执行
- `go.skia.org/infra/go/skerr` - 错误包装
- `go.skia.org/infra/task_driver/go/td` - 任务驱动框架

## 设计模式与设计决策

- **两阶段执行**: 先获取 GN 工具再执行转换,确保工具链完整
- **绝对路径**: 使用 `MustGetAbsolutePathOfFlag` 将相对路径转换为绝对路径,避免路径歧义

## 性能考量

作为 CI 任务,执行频率较低。GN 获取步骤可能涉及网络下载,是主要耗时环节。

## 相关文件

- `gn/gn_to_bp.py` - 实际执行转换的 Python 脚本
- `bin/fetch-gn` - GN 工具获取脚本
