# Infra Module 测试示例

> 源文件: `infra/bots/recipe_modules/infra/examples/full.py`

## 概述

`full.py` 是 Infra 配方模块的测试示例，验证 Go 环境配置后可以正常执行步骤。

## 架构位置

位于 `infra/bots/recipe_modules/infra/examples/` 目录。

## 主要类与结构体

无。

## 公共 API 函数

- `RunSteps(api)`: 设置 vars 并在 Go 环境中执行 echo 命令
- `GenTests(api)`: 生成 Housekeeper-PerCommit-InfraTests 测试场景

## 内部实现细节

使用 `with api.context(env=api.infra.go_env)` 设置 Go 环境变量。

## 依赖关系

- `infra`, `recipe_engine/context`, `recipe_engine/file`, `recipe_engine/path`, `recipe_engine/properties`, `recipe_engine/step`, `run`, `vars`

## 设计模式与设计决策

LUCI 配方测试标准模式。

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/infra/api.py`: 被测试的 API
