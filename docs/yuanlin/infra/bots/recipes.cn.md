# Recipes - LUCI 配方引擎引导脚本

> 源文件: `infra/bots/recipes.py`

## 概述

`recipes.py` 是 LUCI 配方引擎（recipe engine）的引导脚本，负责克隆和启动配方引擎工具。它解析 `recipes.cfg` 配置文件以确定配方引擎的版本和位置，然后检出对应版本并通过 `vpython3` 执行配方引擎主程序。此文件是从 chromium 仓库复制的标准引导脚本，不应手动修改。

## 架构位置

位于 `infra/bots/` 目录，是 Skia CI 配方系统的入口点。所有配方测试和执行都通过此脚本启动。

## 主要类与结构体

- **`EngineDep`** (namedtuple): 配方引擎依赖描述
  - `url`: 引擎仓库 URL
  - `revision`: Git commit hash
  - `branch`: 分支引用
- **`MalformedRecipesCfg`** (Exception): recipes.cfg 解析异常

## 公共 API 函数

- **`parse(repo_root, recipes_cfg_path)`**: 解析 recipes.cfg 文件，返回 (EngineDep, recipes_path)
- **`parse_args(argv)`**: 提取引擎覆盖路径和 --package 选项
- **`checkout_engine(engine_path, repo_root, recipes_cfg_path)`**: 检出配方引擎仓库
- **`main()`**: 主入口，执行完整的引导流程

## 内部实现细节

1. **Shell 技巧**: 文件开头的 `''''exec python3 -u -- "$0" ${1+"$@"} # '''` 在 sh 中触发 exec，在 Python 中是无操作字符串
2. **recipes.cfg 解析**: 支持 API 版本 2，提取 recipe_engine 依赖的 URL/revision/branch
3. **引擎检出** (`checkout_engine`):
   - 支持 file:// URL 直接使用本地路径
   - 使用 `git init` + `git fetch` + `git reset --hard` 模式
   - 处理 `index.lock` 残留文件
   - 执行 `git clean -qxf` 清理旧的 .pyc 文件
4. **执行引擎**: 通过 `vpython3` 运行 `recipe_engine/main.py`
5. **Windows 兼容**: 使用 `subprocess.call` + 信号忽略代替 `os.execvp`
6. **调试器支持**: 通过 `RECIPE_DEBUGGER` 环境变量选择不同的 vpython spec

## 依赖关系

- 外部工具: `git`, `cipd`, `vpython3`
- 配置文件: `infra/config/recipes.cfg`
- Python 标准库: `argparse`, `errno`, `json`, `logging`, `os`, `shutil`, `subprocess`, `sys`

## 设计模式与设计决策

- 自引导模式: 脚本自身检出并启动其管理的配方引擎
- 版本锁定: 通过 recipes.cfg 中的 commit hash 精确锁定引擎版本
- Unix exec 模式: 在 Unix 上使用 `os.execvp` 替换当前进程，避免额外的进程开销
- 标准化: 此文件是 LUCI 标准引导脚本，通过 autoroller 更新

## 性能考量

- 使用 `--quiet` 标志减少 git fetch 输出
- `git diff --quiet` 快速检查是否需要重置
- 避免不必要的网络操作（先检查本地 commit 是否存在）

## 相关文件

- `infra/config/recipes.cfg`: 配方引擎版本配置
- `infra/bots/run_recipe.py`: 配方运行脚本
- `infra/bots/recipe_modules/`: 配方模块集合
