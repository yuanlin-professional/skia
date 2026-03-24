# 基础设施测试 Recipe (infra)

> 源文件: `infra/bots/recipes/infra.py`

## 概述

此 recipe 运行 Skia 基础设施的自动化测试（infra tests），验证 Skia CI/CD 基础设施代码本身的正确性。它在检出的仓库中初始化 Git 环境，配置 Go 开发环境，然后执行 `infra/bots/infra_tests.py` 测试脚本。该 recipe 支持 Skia 主仓库和 lottie-ci 仓库。

## 架构位置

该 recipe 是 Skia CI 基础设施自测体系的核心组件：

- **职责**: 测试 recipe、任务驱动器、Go 工具等基础设施代码
- **触发**: 作为 Housekeeper 任务由任务调度器在每次提交后触发
- **测试对象**: `infra/bots/` 目录下的基础设施代码

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块：infra、context、path、properties、step、vars |

## 公共 API 函数

### `git_init(api, repo_root, env)`

在指定目录中初始化 Git 仓库（init + add + commit），因为某些基础设施测试假设运行在 Git 仓库内部。

- **参数**: `repo_root` -- 仓库根目录, `env` -- 环境变量字典

### `RunSteps(api)`

Recipe 入口，执行以下流程：
1. 从仓库 URL 提取仓库名称（去除 `.git` 后缀）
2. 合并默认环境和 Go 环境变量（PATH 变量特殊合并）
3. 在仓库目录和（如非 skia 仓库时）skia 目录中初始化 Git
4. 在配置好的环境中运行 `infra_tests.py`
5. 在 Windows 上最多重试 3 次（因文件删除的竞态条件导致的不稳定性）

### `GenTests(api)`

生成两个测试用例：
- `infra_tests` -- Skia 仓库的基础设施测试
- `infra_tests_lottie_ci` -- lottie-ci 仓库的基础设施测试

## 内部实现细节

- **Git 初始化**: 基础设施测试可能调用 `git log`、`git describe` 等命令，需要在有效的 Git 仓库中运行。通过 `git init` + `git add .` + `git commit` 创建一个最小的 Git 仓库
- **环境变量合并**: Go 环境和默认环境的 PATH 都包含 `%(PATH)s` 占位符，合并时通过字符串替换链接两者
- **多仓库支持**: 当处理非 skia 仓库（如 lottie-ci）时，同时在 skia 目录初始化 Git，因为基础设施测试可能引用 skia 仓库
- **Windows 重试**: Windows 上文件操作的竞态条件导致测试不稳定，通过最多 3 次重试来缓解

## 依赖关系

- **infra** -- 基础设施模块（提供 `go_env` 和资源路径）
- **vars** -- 构建变量（提供 `default_env`）
- **recipe_engine/context** -- 执行上下文（cwd、env）
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/step** -- 步骤执行

## 设计模式与设计决策

- **自测试**: 基础设施代码测试自身，确保 recipe 和工具变更不会破坏 CI 流水线
- **环境隔离**: 通过显式配置完整的环境变量集合（Go 环境 + 默认环境）确保测试环境一致
- **PATH 合并策略**: PATH 通过 `%(PATH)s` 占位符机制逐级合并，其他环境变量直接覆盖
- **容错重试**: Windows 平台上的重试机制是实用主义的解决方案，而非根治竞态条件

## 性能考量

- Git 初始化（`git add .`）在大型仓库中可能有一定耗时
- 基础设施测试本身运行时间取决于测试覆盖范围
- Windows 上最多 3 次重试可能延长总运行时间

## 相关文件

- `infra/bots/infra_tests.py` -- 基础设施测试入口脚本
- `infra/bots/recipe_modules/infra/` -- 基础设施工具模块
- `infra/bots/recipe_modules/vars/` -- 构建变量模块
