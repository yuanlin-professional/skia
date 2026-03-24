# git.py - Git 命令封装模块

> 源文件: [tools/infra/git.py](../../tools/infra/git.py)

## 概述

此模块提供了一个简洁的 Python 封装函数，用于在 Skia 基础设施脚本中执行 Git 命令。它自动处理 Windows 平台上 Git 可执行文件的命名差异（`git.bat` vs `git`），并以子进程方式运行 Git 命令，返回命令输出。这是 Skia 工具基础设施包（`tools/infra`）的基础组件，被多种自动化脚本用于与 Git 仓库交互。

## 架构位置

该模块属于 Skia 工具基础设施包（`tools/infra/`），是一个最基础的辅助模块。它与 `go.py`（Go 工具封装）一起构成了 `tools/infra` 包的两个核心工具模块。该模块被 `tools/infra/` 目录下以及 Skia 代码库中任何需要执行 Git 操作的 Python 脚本所使用，提供跨平台的 Git 命令执行能力。

在 Skia 基础设施工具链中的位置：
```
tools/infra/
    __init__.py  (包标识)
    git.py       (本文件 - Git 封装)
    go.py        (Go 工具封装)
```

## 主要类与结构体

无类定义。包含以下模块级元素：

- **`GIT`**（`str` 常量）：Git 可执行文件名
  - Windows 平台（`sys.platform == 'win32'`）：`'git.bat'`
  - 其他平台：`'git'`

- **`git(*args)`** 函数：核心 Git 命令执行器

## 公共 API 函数

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `git(*args)` | `*args`: Git 子命令和参数（可变参数） | `bytes`: 命令标准输出 | 执行 Git 命令并返回输出 |

**使用示例**：
```python
from tools.infra import git

# 获取最近 5 条提交日志
output = git.git('log', '--oneline', '-5')

# 获取当前分支名
branch = git.git('rev-parse', '--abbrev-ref', 'HEAD')

# 获取文件状态
status = git.git('status', '--porcelain')
```

**异常行为**：
- 如果 Git 命令返回非零退出码，`subprocess.check_output` 会抛出 `subprocess.CalledProcessError` 异常
- 如果 Git 可执行文件不存在，会抛出 `FileNotFoundError` 异常

## 内部实现细节

1. **平台检测**：在模块加载时通过 `sys.platform == 'win32'` 检查当前平台。
2. **命令构建**：将 `GIT` 常量与传入的可变参数组合为列表 `[GIT] + list(args)`。
3. **命令执行**：调用 `subprocess.check_output()` 执行命令，捕获并返回标准输出。
4. **返回类型**：返回原始 `bytes` 对象（Python 3），调用者需根据需要解码。

## 依赖关系

- **Python 标准库**：
  - `subprocess`：子进程管理，提供 `check_output` 函数
  - `sys`：系统平台检测，提供 `platform` 属性
- **系统工具**：
  - POSIX 系统：`git` 可执行文件（通常位于 `/usr/bin/git`）
  - Windows 系统：`git.bat` 批处理文件（Git for Windows 安装目录）

## 设计模式与设计决策

- **平台适配模式**：Windows 上 Git 通常通过 `git.bat` 批处理文件调用（Git for Windows 的标准安装方式），模块在加载时一次性确定正确的可执行文件名。

- **最小化封装原则**：模块极度简洁（仅 19 行源码），仅解决两个问题：跨平台 Git 命令名和子进程调用的样板代码。不添加任何额外的抽象层。

- **异常传播策略**：不捕获 `check_output` 的异常，让调用者自行处理命令失败。这是"让错误早期暴露"的设计哲学。

- **可变参数接口**：使用 `*args` 提供自然的函数调用语法（`git.git('log', '-5')`），无需手动构建列表。

- **文档字符串**：函数包含简洁的文档字符串（`'''Run the given Git command, return the output.'''`），符合 Python 最佳实践。

## 性能考量

- 每次调用都创建一个新的子进程，这在频繁调用场景下有一定的进程创建开销（通常 5-10ms per call）。
- 对于典型的基础设施脚本使用场景（每次运行执行几十次 Git 命令），子进程开销完全可以接受。
- 命令输出缓存在内存中（`check_output` 的行为），对大输出可能消耗较多内存。
- 如需批量 Git 操作，调用者可考虑使用 `git log --format=...` 等方式减少调用次数。

## 相关文件

- `tools/infra/__init__.py`：包初始化文件，使此模块可被导入
- `tools/infra/go.py`：类似的 Go 工具封装模块，遵循相同的设计模式
- 使用此模块的各种 Skia 基础设施脚本
- `infra/bots/` 下的 CI/CD 脚本可能间接使用此模块
