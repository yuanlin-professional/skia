# Git Recipe Module API

> 源文件: `infra/bots/recipe_modules/git/api.py`

## 概述

此文件实现了 Skia `git` recipe 模块的核心 API 类 `GitApi`。该类继承自 `recipe_engine.recipe_api.RecipeApi`，提供了一个上下文管理器方法 `env()`，用于将 Git 可执行文件的路径添加到 `PATH` 环境变量中。此模块解决了在 Swarming 构建机器人上通过 CIPD 包分发的 Git 工具需要显式配置 PATH 的问题。

## 架构位置

`GitApi` 是 recipe 模块体系中的一个底层工具类，位于 Skia CI 的 recipe 模块层。当构建任务需要调用 Git 命令时，可以通过 `api.git.env()` 上下文管理器确保 Git 在 PATH 中可用。

- **层级**: recipe 模块 API 层
- **上游消费者**: 需要 Git 操作的各类 Skia recipe
- **下游依赖**: CIPD 部署的 `infra/git` 和 `infra/tools/git` 包

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `GitApi` | 类 | 继承 `RecipeApi`，提供 Git 环境配置功能 |

### `GitApi` 类

继承自 `recipe_api.RecipeApi`，是 recipe 引擎模块的标准 API 类。提供 `env()` 方法用于配置 Git 工具的路径。

## 公共 API 函数

### `GitApi.env()`

```python
def env(self):
```

返回一个上下文管理器，将 Git 目录和其 `bin` 子目录添加到 `PATH` 环境变量中。

- **返回值**: 上下文管理器对象（由 `self.m.env` 生成）
- **前置条件**: 需要 `infra/git` 和 `infra/tools/git` CIPD 包已安装在 `git` 相对路径下
- **PATH 构成**: `{start_dir}/git` + `{start_dir}/git/bin` + 原有 `%(PATH)s`

## 内部实现细节

- `git_dir` 指向 `start_dir/git`，即 CIPD 包的安装根目录
- `git_bin` 指向 `start_dir/git/bin`，包含 Git 可执行文件
- 使用 `self.m.path.pathsep` 进行跨平台路径分隔符拼接（Linux/Mac 用 `:`，Windows 用 `;`）
- `%(PATH)s` 占位符保留了原有的 PATH 值，确保新路径被追加到前面（优先级最高）
- 通过 `self.m.env` 返回环境变量上下文管理器，使得 PATH 修改仅在 `with` 块内有效

## 依赖关系

- **recipe_engine.recipe_api.RecipeApi** -- 基类，提供 recipe 模块的标准框架
- **self.m.path** -- `recipe_engine/path` 模块，用于路径操作
- **self.m.env** -- Skia `env` 模块，用于环境变量上下文管理

## 设计模式与设计决策

- **上下文管理器模式**: 使用 `with` 语句块控制 PATH 的作用域，避免全局污染环境变量
- **CIPD 集成**: 假设 Git 通过 CIPD 包分发，路径基于 CIPD 安装的标准位置推导
- **路径优先级**: 将 Git 路径放在 PATH 的最前面，确保使用 CIPD 安装的 Git 版本，而非系统默认版本

## 性能考量

此模块仅进行路径字符串拼接，不涉及文件系统操作或网络请求，性能开销极低。上下文管理器的创建和销毁也是轻量级操作。

## 相关文件

- `infra/bots/recipe_modules/git/__init__.py` -- 模块初始化文件，导出 `GitApi`
- `infra/bots/recipe_modules/git/examples/full.py` -- 使用示例
- `infra/bots/recipe_modules/env/` -- 环境变量管理模块
