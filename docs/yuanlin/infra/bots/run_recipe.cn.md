# Run Recipe - 配方执行脚本

> 源文件: `infra/bots/run_recipe.py`

## 概述

`run_recipe.py` 是 Skia CI 系统的配方（recipe）执行入口脚本。它通过 `kitchen` 工具在 Swarming 环境中运行 LUCI 配方，配置了已知的 Gerrit 主机列表和日志输出端点。

## 架构位置

位于 `infra/bots/` 目录，是 CI 任务运行时的引导脚本。被 Swarming 任务直接调用，负责启动 kitchen cook 流程。

## 主要类与结构体

无类定义。

## 公共 API 函数

- 命令行接口: `python run_recipe.py <unknown> <recipe_name> <properties_json> <luci_project>`

## 内部实现细节

1. 构造 `kitchen cook` 命令，参数包括：
   - `--checkout-dir recipe_bundle`: 配方检出目录
   - `--mode swarming`: Swarming 运行模式
   - `--luci-system-account system`: LUCI 系统账号
   - `--cache-dir cache` / `--temp-dir tmp`: 缓存和临时目录
   - `--known-gerrit-host`: 9 个已知 Gerrit 主机（Google 内部源码服务器）
   - `--recipe`: 从 `sys.argv[2]` 获取配方名称
   - `--properties`: 从 `sys.argv[3]` 获取 JSON 属性
   - `--logdog-annotation-url`: 使用 SWARMING_TASK_ID 构建日志 URL
2. 使用 `subprocess.check_call` 执行命令

## 依赖关系

- 运行时依赖: `kitchen` 可执行文件（位于当前工作目录）
- 环境变量: `SWARMING_TASK_ID`
- Python 标准库: `os`, `subprocess`, `sys`

## 设计模式与设计决策

- 薄封装模式: 仅构造和执行 kitchen 命令
- LogDog 集成: 使用 LUCI 项目和 Swarming 任务 ID 构建日志 URL
- 已知 Gerrit 主机硬编码，简化配置管理

## 性能考量

无特殊性能考量，一次性执行脚本。

## 相关文件

- `infra/bots/recipes.py`: 配方引擎引导脚本
- `infra/bots/recipe_modules/`: 配方模块集合
