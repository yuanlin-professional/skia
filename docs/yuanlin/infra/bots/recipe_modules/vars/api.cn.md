# Vars Recipe Module API

> 源文件: `infra/bots/recipe_modules/vars/api.py`

## 概述

`api.py` 实现了 `SkiaVarsApi`，是 Skia CI 配方系统的核心变量管理模块。它解析构建器名称、设置工作目录、配置环境变量、检测 trybot 状态，并提供 Swarming 运行时信息访问。

## 架构位置

位于 `infra/bots/recipe_modules/vars/` 目录，是所有 Skia 配方的基础依赖。其他模块通过 `api.vars` 访问构建变量。

## 主要类与结构体

- **`SkiaVarsApi`** (recipe_api.RecipeApi): 变量管理 API

## 公共 API 函数

- **`setup()`**: 初始化所有构建变量
- **`is_linux`** (属性): 是否为 Linux 平台
- **`swarming_bot_id`** (属性): Swarming bot ID（延迟获取）
- **`swarming_task_id`** (属性): Swarming 任务 ID（延迟获取）
- **`getenv(name, var)`**: 获取环境变量值

## 内部实现细节

1. **Kitchen 兼容**: 移除 Kitchen 添加的 "k" 目录前缀
2. **目录结构**:
   - `workdir`: 起始目录
   - `build_dir`: workdir/build
   - `cache_dir`: workdir/cache
   - `swarming_out_dir`: workdir/<swarm_out_dir>
   - `tmp_dir`: start_dir/tmp
3. **构建器解析**: 通过 `builder_name_schema.DictForBuilderName` 解析构建器名称
4. **配置确定**: Housekeeper 角色默认 Release，其他使用构建器配置
5. **Windows x86_64 特殊处理**: 配置名附加 `_x64`
6. **Extra tokens**: 解析 extra_config，`SK_` 前缀的作为单一 token
7. **Trybot 检测**: 通过 patch_issue/patch_set/patch_ref 判断
8. **环境变量**: 通过调用 `get_env_var.py` 脚本获取

## 依赖关系

- `builder_name_schema`: 构建器名称解析
- `depot_tools/bot_update`: repo_resource 路径
- `recipe_engine` 标准模块

## 设计模式与设计决策

- 延迟初始化: swarming_bot_id/task_id 仅在首次访问时获取
- 集中配置: 所有构建变量在 `setup()` 中一次性初始化
- 平台检测基于构建器名称而非运行时环境

## 性能考量

- 变量初始化在 setup() 中一次性完成
- Swarming ID 使用延迟获取避免不必要的步骤执行

## 相关文件

- `infra/bots/recipe_modules/vars/__init__.py`: 模块初始化
- `infra/bots/recipe_modules/vars/examples/full.py`: 测试示例
- `infra/bots/recipe_modules/builder_name_schema/`: 名称解析模块
