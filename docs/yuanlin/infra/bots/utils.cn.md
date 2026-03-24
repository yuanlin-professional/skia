# Utils - Skia 基础设施通用工具库

> 源文件: `infra/bots/utils.py`

## 概述

`utils.py` 是 Skia CI/CD 基础设施的核心通用工具库，提供临时目录管理、目录切换、Git 操作辅助、目录递归删除等功能。它被多个基础设施脚本和配方模块广泛使用。

## 架构位置

位于 `infra/bots/` 目录，是基础设施工具链的基础层。被 `test_utils.py`、`zip_utils_test.py`、`check_deps.py`、`git_utils.py` 等多个文件依赖。

## 主要类与结构体

- **`print_timings`**: 上下文管理器，打印任务开始/结束时间和耗时
- **`tmp_dir`**: 上下文管理器，创建临时目录并在退出时清理
  - `name` 属性: 返回临时目录路径
- **`chdir`**: 上下文管理器，切换到指定目录并在退出时恢复
- **`git_branch`**: 上下文管理器，创建临时 Git 分支
  - 入口: stash 本地修改，fetch origin，创建跟踪 origin/main 的临时分支
  - 退出: hard reset，恢复原分支，pop stash，删除临时分支

## 公共 API 函数

- **`git_clone(repo_url, dest_dir)`**: 克隆 Git 仓库
- **`RemoveDirectory(*path)`**: 递归删除目录（处理 Windows 只读文件问题）

## 内部实现细节

1. **平台检测**: 使用 `sys.platform` 判断 Windows（`gclient.bat` vs `gclient`）
2. **GIT 路径**: 通过 `which git` 获取 Git 可执行文件完整路径
3. **`RemoveDirectory`**:
   - Windows: 使用 `cmd.exe /c rd /q /s`，最多重试 3 次（处理防病毒/索引锁定）
   - Unix: 递归遍历目录树，先 chmod 使目录可写，再删除
   - 处理符号链接和 Windows `ENOENT` 错误

## 依赖关系

- Python 标准库: `datetime`, `errno`, `os`, `shutil`, `sys`, `subprocess`, `tempfile`, `time`, `uuid`

## 设计模式与设计决策

- 上下文管理器模式: 确保资源（临时目录、Git 状态）在异常情况下正确清理
- Windows 兼容性: `RemoveDirectory` 处理 Windows 特有的只读文件和锁定问题
- 重试机制: Windows 目录删除使用 3 次重试，应对系统锁定

## 性能考量

- `RemoveDirectory` 在 Windows 上可能因重试而耗时（每次重试等待 3 秒）
- `tmp_dir` 使用系统 `tempfile.mkdtemp` 确保快速创建

## 相关文件

- `infra/bots/git_utils.py`: 更高级的 Git 操作工具
- `infra/bots/test_utils.py`: 测试辅助工具
- `infra/bots/zip_utils.py`: 压缩工具
