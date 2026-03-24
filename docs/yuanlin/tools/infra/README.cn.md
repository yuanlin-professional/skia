# Skia 基础设施工具

## 概述

`tools/infra` 是 Skia 构建和持续集成基础设施的 Python 工具包。该模块提供了 Git 操作和 Go 语言环境管理的封装函数，被 Skia 的各种自动化脚本和构建流程使用。这是一个轻量级的实用工具库，简化了与 Skia 基础设施服务的交互。

## 目录结构

```
tools/infra/
├── __init__.py    # Python 包初始化
├── git.py         # Git 命令封装
└── go.py          # Go 语言环境管理
```

## 核心组件

### git.py

Git 命令行操作的 Python 封装：

```python
import tools.infra.git as git

# 执行 Git 命令并返回输出
output = git.git('log', '--oneline', '-5')
output = git.git('status')
output = git.git('diff', 'HEAD~1')
```

**跨平台支持：**
- Windows 系统使用 `git.bat`
- 其他系统使用 `git`

**实现细节：**
- 使用 `subprocess.check_output()` 执行命令
- 命令失败时抛出 `subprocess.CalledProcessError`
- 返回命令的标准输出内容

### go.py

Go 语言环境的检查、包管理和工具安装：

#### 环境检查

```python
import tools.infra.go as go

# 验证 Go 安装是否正确
go.check()
```

`check()` 函数验证以下条件：
1. `go` 可执行文件存在于 PATH 中
2. `GOPATH` 环境变量已设置
3. `$GOPATH/bin` 在 PATH 中

#### 包管理

| 函数 | 说明 |
|------|------|
| `get(pkg)` | 使用 `go get -u` 获取或更新指定包 |
| `mod_download(*pkgs)` | 使用 `go mod download` 下载模块依赖 |
| `install(pkg)` | 使用 `go install` 安装指定包 |
| `update_infra()` | 更新 Skia 基础设施代码库（go.skia.org/infra） |

```python
# 获取一个包
go.get('golang.org/x/tools/...')

# 更新 Skia 基础设施
go.update_infra()

# 安装一个工具
go.install('go.skia.org/infra/cmd/some-tool')

# 下载模块依赖
go.mod_download()
```

## 使用场景

### 自动化脚本

```python
from tools.infra import git, go

# 获取当前 Git 提交哈希
commit = git.git('rev-parse', 'HEAD')

# 确保 Go 环境就绪
go.check()

# 安装所需的 Go 工具
go.install('go.skia.org/infra/cmd/goldctl')
```

### CI/CD 流程

在 Skia 的持续集成系统中，这些工具用于：
- 检查仓库状态和版本信息
- 安装和更新构建依赖
- 管理 Go 语言工具链

## 与其他模块的关系

- **infra/bots/**: Skia 机器人任务脚本使用此模块
- **tools/skp/**: 网页回放脚本使用 Git 工具管理版本
- **go.skia.org/infra**: Skia 基础设施的 Go 代码仓库
- **bin/**: 各种二进制工具下载和管理脚本
