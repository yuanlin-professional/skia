# Checkout Recipe Module API

> 源文件: `infra/bots/recipe_modules/checkout/api.py`

## 概述

`api.py` 实现了 `CheckoutApi` 配方模块，提供两种代码检出策略：纯 Git 检出（无 DEPS）和 bot_update 检出（含依赖同步）。它处理了 trybot 补丁应用、gclient 配置、跨仓库补丁等复杂场景。

## 架构位置

位于 `infra/bots/recipe_modules/checkout/` 目录，是所有需要源码的配方任务的基础模块。

## 主要类与结构体

- **`CheckoutApi`** (recipe_api.RecipeApi): 代码检出 API

## 公共 API 函数

- **`default_checkout_root`** (属性): 默认检出根目录 (cache/work)
- **`assert_git_is_from_cipd()`**: 验证 Git 来自 CIPD
- **`git(checkout_root)`**: 纯 Git 检出（无 DEPS 同步）
- **`bot_update(checkout_root, gclient_cache, skip_patch, override_revision)`**: bot_update 完整检出

## 内部实现细节

1. **`git` 方法**:
   - 克隆仓库到 checkout_root/skia
   - trybot 时: fetch patch_ref -> checkout FETCH_HEAD -> rebase
2. **`bot_update` 方法**:
   - 配置 gclient: 设置缓存目录、主仓库、解决方案
   - 处理跨仓库补丁: 从 patch_repo 提取 patch_root
   - 清理旧的 `.gclient_entries` 文件
   - 构造 `patch_refs` 格式: `repo@revision:patch_ref`
   - 调用 `bot_update.ensure_checkout`，启用 topic 下载
   - 返回 got_revision

## 依赖关系

- `depot_tools/bot_update`, `depot_tools/gclient`, `depot_tools/git`, `depot_tools/tryserver`
- `recipe_engine/context`, `recipe_engine/file`, `recipe_engine/path`, `recipe_engine/properties`, `recipe_engine/step`
- `run`, `vars`

## 设计模式与设计决策

- 双模式检出: git（快速，无依赖）vs bot_update（完整，含依赖）
- CIPD Git 验证: 确保使用 CIPD 提供的 Git 版本而非系统 Git
- Topic 下载: 通过 `download_topics=True` 同步关联的 Gerrit 变更
- `patch=True` 始终设置，避免步骤名称中出现误导性的 "without patch"

## 性能考量

- 使用 gclient 缓存减少网络传输
- 持久化检出（`default_checkout_root` 在缓存目录）减少增量同步时间

## 相关文件

- `infra/bots/recipe_modules/checkout/__init__.py`: 模块初始化
- `infra/bots/recipe_modules/checkout/examples/full.py`: 测试示例
