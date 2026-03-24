# ssh.py - SSH 远程设备管理 Recipe Flavor

> 源文件:
> - `infra/bots/recipe_modules/flavor/ssh.py`

## 概述

ssh.py 实现了通过 SSH 连接管理远程设备的 Recipe Flavor 基类。它封装了 SSH 连接建立、密钥管理、远程命令执行和文件传输（SCP）等操作，为远程 Linux 设备上运行 Skia 测试提供了基础设施。该类必须被子类化以设置 `device_dirs`（如 `ChromebookFlavor`）。

## 架构位置

```
recipe_modules/flavor/
├── default.py (DefaultFlavor 基类)
│   └── ssh.py (SSH 远程管理基类)  <── 本模块
│       └── chromebook.py (Chromebook 特化)
```

作为中间抽象层，位于 `DefaultFlavor` 和具体设备 Flavor（如 Chromebook）之间。

## 主要类与结构体

### `SSHFlavor`

- **继承**: `default.DefaultFlavor`
- **成员变量**:
  - `_did_ssh_setup` (bool): SSH 是否已初始化
  - `_ssh_args` (list): SSH 连接参数
  - `_user_ip` (str): 远程用户@IP，默认 `root@variable_chromeos_device_hostname`

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `ssh(title, *cmd)` | 通过 SSH 在远程设备上执行命令 |
| `install()` | 安装测试所需文件到远程设备 |
| `step(name, cmd)` | 在远程设备上执行测试命令 |
| `create_clean_device_dir(path)` | 创建空的远程目录 |
| `read_file_on_device(path)` | 读取远程文件内容 |
| `remove_file_on_device(path)` | 删除远程文件 |
| `copy_file_to_device(host_path, device_path)` | 通过 SCP 推送文件 |
| `ensure_device_dir(path)` | 确保远程目录存在 |
| `scp_device_path(device_path)` | 生成 SCP 格式的远程路径 |
| `user_ip` (property) | 获取远程设备的 user@ip |

## 内部实现细节

### SSH 密钥管理

`_ssh_setup` 方法（懒初始化）：
1. 克隆 Chromium OS chromite 仓库到临时目录
2. 获取 `testing_rsa` 密钥文件
3. 设置密钥权限为 600
4. 配置 SSH 参数：30 秒连接超时、4 次重试、禁用密码认证、使用 Protocol 2、15 秒心跳、禁用主机密钥检查

### SSH 命令构建

```python
ssh_cmd = ['ssh', '-oConnectTimeout=15', '-oBatchMode=yes', '-t', '-t'] + \
    self._ssh_args + [self.user_ip] + list(cmd)
```

使用 `-t -t` 强制分配伪终端，确保远程命令的输出正确传输。

### 安装流程

1. 确保资源目录存在
2. 创建干净的 bin 目录
3. 推送可执行文件到设备
4. 设置可执行权限 (`chmod +x`)

### 文件操作

- 删除操作使用 `rm -f` 静默忽略不存在的文件
- 创建目录使用 `rm -rf` + `mkdir -p`
- 读取文件使用 `cat` + `raw_io.output` 捕获输出

## 依赖关系

- **Recipe 框架**: `recipe_engine.recipe_api`
- **基类**: `default.DefaultFlavor`
- **外部工具**: SSH 客户端、SCP
- **Chromium OS**: chromite 仓库（SSH 密钥来源）

## 设计模式与设计决策

- **模板方法模式**: 定义了远程设备操作的框架，子类提供 `device_dirs` 等具体配置
- **懒初始化**: SSH 配置在首次使用时才执行 chromite 克隆
- **默认 infra_step**: 所有 SSH 操作默认标记为基础设施步骤
- **未实现的方法**: `copy_directory_contents_to_device` 和 `copy_directory_contents_to_host` 标记为 TODO（待用 rsync 实现）
- **安全最佳实践**: 禁用主机密钥检查（测试环境安全性让位于自动化便捷性）

## 性能考量

- chromite 克隆操作仅在首次 SSH 调用时执行一次
- SSH 连接参数配置了 `ServerAliveInterval=15` 和 `ServerAliveCountMax=8`，总计 120 秒的连接保活窗口
- `ConnectionAttempts=4` 提供了连接重试能力
- SCP 传输直接使用 SSH 密钥，无需额外认证开销

## 相关文件

- `infra/bots/recipe_modules/flavor/default.py` - DefaultFlavor 基类
- `infra/bots/recipe_modules/flavor/chromebook.py` - Chromebook 子类
- `infra/bots/recipe_modules/flavor/android.py` - Android flavor（对比：使用 ADB 而非 SSH）
