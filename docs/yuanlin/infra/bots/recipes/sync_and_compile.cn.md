# 同步与编译 Recipe (sync_and_compile)

> 源文件: `infra/bots/recipes/sync_and_compile.py`

## 概述

此 recipe 负责完整的代码检出和编译流程，适用于需要从头获取完整 Skia 代码库的构建任务。与 `compile.py`（假设代码已通过 CAS 获取）不同，此 recipe 通过 `bot_update` 或 `git` 进行代码同步，支持 `NoDEPS`（无 DEPS 同步）和 `NoPatch`（无补丁应用）两种特殊模式。它是 Skia CI 中编译阶段的核心 recipe 之一。

## 架构位置

该 recipe 位于 Skia CI 构建流水线的编译阶段，是需要完整代码检出的构建任务的入口：

- **适用场景**: NoDEPS 构建、NoPatch 构建（如 CodeSize 差异计算的基准构建）
- **上游**: 任务调度器触发
- **下游**: 编译产物通过 `copy_build_products` 输出到 Swarming 目录供后续任务使用
- **关联**: `compile.py` 处理代码已就绪的普通编译场景

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表，包含 build、checkout、gitiles 等 |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，执行以下主要流程：

1. **确定检出模式**:
   - `NoDEPS` 模式: 不使用 bot_update，直接 git 检出（跳过 DEPS 同步）
   - `NoPatch` 模式: 使用 bot_update 但跳过补丁应用；对于 CI 构建，通过 gitiles 查找父提交作为基准版本
   - 标准模式: 正常 bot_update 检出

2. **NoPatch 路径修正**: 将 Skia 仓库从 `k/skia` 复制到 `skia`，使路径与普通 Build 任务一致（避免 CodeSize 差异中的虚假 delta）

3. **编译**: 调用 `api.build` 执行编译，将产物复制到 Swarming 输出目录

4. **清理**: 在 Windows 平台上运行进程清理脚本

### `GenTests(api)`

生成三个测试用例：
- `Build-Win10-Clang-x86_64-Release-NoDEPS` -- Windows NoDEPS 构建
- `Build-Debian10-Clang-arm-Release-NoPatch` -- Debian NoPatch CI 构建
- `Build-Debian10-Clang-arm-Release-NoPatch (tryjob)` -- NoPatch trybot 构建

## 内部实现细节

- **NoPatch 父提交查找**: 通过 `api.gitiles.log` 获取当前 revision 的 git log，提取 `parents[0]` 作为基准版本。这允许 CodeSize 任务比较当前提交与父提交的二进制大小差异
- **路径一致性维护**: `bot_update` 将检出放在 `start_dir/k/skia`，但普通 Build 任务的路径是 `start_dir/skia`。为了使 CodeSize 差异比较不受路径变化影响（调试字符串中可能包含相对路径），需要手动复制到一致的位置
- **内联 Python 脚本**: 使用 `copytree.py` 脚本而非 `api.file.copytree`，因为后者不支持 `dirs_exist_ok` 参数
- **NoPatch 输出目录**: 使用 `cache_dir/work/skia/out/...` 路径，与普通 Build 任务的输出路径对齐
- **Windows 进程清理**: 编译后清理遗留的 Windows 进程（如 cl.exe、link.exe），防止影响后续任务

## 依赖关系

- **build** -- 编译模块，执行实际的 GN 配置和 Ninja 构建
- **checkout** -- 代码检出模块，封装 bot_update 和 git 操作
- **infra** -- 基础设施资源（包含 `copytree.py` 脚本）
- **run** -- 步骤执行和失败检查
- **vars** -- 构建变量管理
- **depot_tools/gitiles** -- Gitiles API 模块，用于查询 Git 提交历史
- **recipe_engine/context** -- 执行上下文
- **recipe_engine/file** -- 文件操作
- **recipe_engine/json** -- JSON 处理
- **recipe_engine/path** -- 路径操作
- **recipe_engine/platform** -- 平台检测
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/step** -- 步骤执行

## 设计模式与设计决策

- **构建器名称驱动**: 通过构建器名称中的 `NoDEPS`、`NoPatch` 标记来确定检出策略，这是 Skia CI 的命名约定
- **路径对齐策略**: 为了保证 CodeSize 差异比较的准确性，强制保持与普通 Build 任务相同的目录布局
- **Gitiles 集成**: 使用 Gitiles REST API 查找父提交，而非在本地 Git 仓库中操作，这在某些受限环境中更可靠
- **try/finally 资源清理**: 确保 Windows 进程清理在编译失败时也能执行

## 性能考量

- 完整的 bot_update 检出比 CAS 方式慢得多，因此此 recipe 仅用于必须进行完整检出的场景
- NoPatch 构建中的文件复制步骤（从 `k/skia` 到 `skia`）增加了额外的 I/O 开销
- 在非 NoPatch 模式下编译输出直接放在检出根目录下，减少路径长度
- NoPatch 模式使用 `cache_dir` 路径存放输出，利用构建缓存加速增量编译

## 相关文件

- `infra/bots/recipes/compile.py` -- 普通编译 recipe（代码已通过 CAS 获取）
- `infra/bots/recipe_modules/build/` -- 编译模块
- `infra/bots/recipe_modules/checkout/` -- 代码检出模块
- `infra/bots/recipe_modules/infra/resources/copytree.py` -- 目录复制脚本
- `infra/bots/recipe_modules/build/resources/cleanup_win_processes.py` -- Windows 进程清理脚本
