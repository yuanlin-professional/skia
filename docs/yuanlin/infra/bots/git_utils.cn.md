# Git Utils - Git 操作工具库

> 源文件: `infra/bots/git_utils.py`

## 概述

`git_utils.py` 提供了用于 Skia CI/CD 流程的高级 Git 操作工具，包括本地 Git 配置管理、临时分支创建与自动提交上传、以及新仓库克隆与检出的上下文管理器。

## 架构位置

位于 `infra/bots/` 目录，是基础设施 Git 操作的高层封装。依赖 `utils.py` 的基础工具。

## 主要类与结构体

- **`GitLocalConfig`**: 上下文管理器，临时修改本地 Git 配置
  - 入口: 保存当前值并设置新值
  - 退出: 恢复原值或 unset
- **`GitBranch`**: 上下文管理器，管理临时 Git 分支的完整生命周期
  - 入口: hard reset、checkout main、创建新分支（跟踪 origin/main）
  - `commit_and_upload(use_commit_queue)`: 提交修改并通过 `git cl upload` 上传 CL
  - 退出: 上传 CL（如果无错误）、checkout 回 main、删除临时分支
- **`NewGitCheckout`**: 继承 `utils.tmp_dir`，在临时目录中创建新的 Git 检出
  - 支持从远程仓库克隆
  - 支持使用本地镜像加速初始克隆

## 公共 API 函数

- **`GitBranch.commit_and_upload(use_commit_queue)`**: 提交并上传到 Gerrit，返回 issue URL
- **`NewGitCheckout.root`**: 返回检出的根目录路径

## 内部实现细节

1. **`GitLocalConfig`**: 使用 `git config --local` 操作，支持键不存在的情况
2. **`GitBranch.commit_and_upload`**:
   - 使用 `git cl upload -f --bypass-hooks --bypass-watchlists`
   - 支持 patch set 编号递增
   - 支持 commit queue 和 CC 列表
   - 从 `git cl issue` 输出中通过正则提取 issue URL
3. **`NewGitCheckout`**:
   - 可选的本地镜像：先从本地路径克隆，再将 remote 切换到远程 URL
   - 执行 `git remote update` 和 `git reset --hard origin/main` 确保同步

## 依赖关系

- `infra/bots/utils.py`: `tmp_dir` 基类
- Python 标准库: `os`, `re`, `shutil`, `subprocess`, `tempfile`
- 外部工具: `git`, `git cl` (depot_tools)

## 设计模式与设计决策

- 上下文管理器模式: 确保 Git 状态在异常时正确恢复
- GitBranch 的 `__exit__` 使用 try/finally 确保分支清理
- NewGitCheckout 的本地镜像加速减少网络依赖
- 分离关注点: GitLocalConfig 管理配置，GitBranch 管理分支和上传

## 性能考量

- 本地镜像优化: `NewGitCheckout` 支持从本地路径克隆以减少网络传输
- `bypass-hooks` 和 `bypass-watchlists` 跳过不必要的上传前检查

## 相关文件

- `infra/bots/utils.py`: 基础工具库（`tmp_dir` 等）
- `infra/bots/check_deps.py`: 使用 Git 工具的检查脚本
