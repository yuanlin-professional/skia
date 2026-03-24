# Git Recipe Module 完整使用示例

> 源文件: `infra/bots/recipe_modules/git/examples/full.py`

## 概述

此文件是 `git` recipe 模块的完整使用示例（example recipe），用于演示如何使用 `api.git.env()` 上下文管理器来配置 Git 环境。它同时也作为 recipe 引擎的集成测试用例，验证模块在不同平台上的正确行为。该示例展示了在使用和不使用 `git.env()` 上下文管理器两种情况下执行 Git 命令的区别。

## 架构位置

此文件位于 recipe 模块的 `examples/` 目录中，遵循 recipe 引擎对模块示例的标准约定。recipe 引擎会自动发现并运行 `examples/` 下的测试 recipe，用于验证模块功能的正确性。

- **层级**: recipe 模块测试/示例层
- **目的**: 验证 `git` 模块的 `env()` 功能在各平台上正常工作

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 声明依赖 `git`、`recipe_engine/platform`、`recipe_engine/step` |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口函数，执行两个步骤：
1. **步骤 '1'**: 直接运行 `git status`（不使用 `git.env()`），此时依赖系统默认的 Git
2. **步骤 '2'**: 在 `api.git.env()` 上下文管理器内运行 `git status`，此时 CIPD 安装的 Git 已被添加到 PATH

### `GenTests(api)`

测试生成器函数，生成两个测试用例：
- `test`: 默认平台（Linux）下的测试
- `test-win`: Windows 64 位平台下的测试，验证路径分隔符等跨平台行为

## 内部实现细节

- `RunSteps` 中的步骤 '1' 和步骤 '2' 形成对比，说明 `env()` 上下文管理器的作用
- `GenTests` 使用 `api.platform('win', 64)` 模拟 Windows 平台，确保模块的路径拼接在 Windows 下使用 `;` 分隔符
- `cmd=['git', 'status']` 以列表形式传递命令，避免 shell 注入问题

## 依赖关系

- **git** -- 被测试的 `git` recipe 模块
- **recipe_engine/platform** -- 用于在测试中模拟不同操作系统平台
- **recipe_engine/step** -- 用于执行构建步骤（shell 命令）

## 设计模式与设计决策

- **示例即测试**: recipe 引擎的惯例是将 `examples/` 目录下的 recipe 同时作为功能演示和自动化测试
- **跨平台验证**: 通过 `api.platform('win', 64)` 在测试中显式覆盖 Windows 平台，确保路径分隔符等平台差异被正确处理
- **最小化示例**: 仅用两个步骤清晰展示了模块的核心功能，降低理解门槛

## 性能考量

此文件仅用于测试和演示目的，不在生产构建中执行，因此无性能方面的特殊考量。测试运行在模拟环境中，不涉及实际的 Git 命令执行。

## 相关文件

- `infra/bots/recipe_modules/git/__init__.py` -- 模块初始化文件
- `infra/bots/recipe_modules/git/api.py` -- 模块 API 实现
