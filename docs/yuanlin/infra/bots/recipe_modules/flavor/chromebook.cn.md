# chromebook.py - Chromebook 设备管理 Recipe Flavor

> 源文件:
> - `infra/bots/recipe_modules/flavor/chromebook.py`

## 概述

chromebook.py 实现了 Skia CI/CD 基础设施中专用于 Chromebook（Chrome OS）设备的管理 flavor。它继承自 `SSHFlavor`，配置了 Chrome OS 特定的目录结构，并添加了文件系统挂载和目录传输的处理逻辑。该模块是 Skia 在 Chromebook 设备上运行 GPU 测试的基础设施组件。

## 架构位置

```
recipe_modules/flavor/
├── default.py (DefaultFlavor 基类)
│   └── ssh.py (SSH 远程管理基类)
│       └── chromebook.py (Chromebook 特化)  <── 本模块
```

## 主要类与结构体

### `ChromebookFlavor`

- **继承**: `ssh.SSHFlavor`
- **成员变量**:
  - `chromeos_homedir`: Chrome OS 用户主目录 (`/home/chronos/user/`)
  - `device_dirs`: 设备目录配置（所有数据目录位于 `chromeos_homedir` 下）

### 设备目录布局

| 目录 | 路径 |
|------|------|
| bin_dir | `/home/chronos/user/bin` |
| dm_dir | `/home/chronos/user/dm_out` |
| perf_data_dir | `/home/chronos/user/perf` |
| resource_dir | `/home/chronos/user/resources` |
| images_dir | `/home/chronos/user/images` |
| skp_dir | `/home/chronos/user/skps` |
| svg_dir | `/home/chronos/user/svgs` |
| fonts_dir | `NOT_SUPPORTED` |
| texttraces_dir | `''` (空) |

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `install()` | 安装文件并重新挂载主目录为可执行 |
| `copy_directory_contents_to_device(host, device)` | 通过 SCP 递归复制目录到设备 |
| `copy_directory_contents_to_host(device, host)` | 通过 SCP 递归复制目录到主机 |

## 内部实现细节

### 可执行权限挂载

Chrome OS 默认将用户主目录挂载为 `noexec`（不可执行），需要重新挂载：

```python
self.ssh('remount %s as exec' % self.chromeos_homedir,
         'sudo', 'mount', '-i', '-o', 'remount,exec', '/home/chronos')
```

这是 `install()` 在调用父类安装逻辑后额外执行的关键步骤。

### SCP 目录传输

使用外部 Python 脚本 `scp.py` 执行递归 SCP 传输，通过传递 SSH 参数确保认证一致：

```python
cmd=['python3', script] + self._ssh_args + [src, dest]
```

这解决了 `SSHFlavor` 基类中 `copy_directory_contents_to_device/host` 的 TODO。

## 依赖关系

- **基类**: `ssh.SSHFlavor`（SSH 连接管理）
- **基类**: `default.DefaultFlavor`（`DeviceDirs` 数据结构）
- **外部脚本**: `scp.py`（目录递归 SCP 传输）
- **Recipe 框架**: `recipe_engine.recipe_api`

## 设计模式与设计决策

- **模板方法重写**: 重写 `install()` 添加挂载步骤，重写 `copy_directory_*` 实现目录传输
- **Chrome OS 适配**: 使用 `chronos` 用户目录（Chrome OS 的默认用户）
- **`sudo` 提权**: 文件系统重新挂载需要 `sudo` 权限
- **字体不支持**: `fonts_dir` 设为 `NOT_SUPPORTED`，表明 Chromebook 测试不涉及自定义字体
- **SCP 而非 rsync**: 使用 SCP 进行目录传输，虽然 rsync 可能更高效，但 SCP 更通用

## 性能考量

- SCP 递归传输相比单文件传输更高效，减少了连接建立的开销
- 文件系统重新挂载是一次性操作，不影响后续文件操作性能
- 继承了 `SSHFlavor` 的 SSH 连接复用和超时配置

## 相关文件

- `infra/bots/recipe_modules/flavor/ssh.py` - SSH 基类
- `infra/bots/recipe_modules/flavor/default.py` - DefaultFlavor 基类
- `infra/bots/recipe_modules/flavor/resources/scp.py` - SCP 传输脚本
- `infra/bots/recipe_modules/flavor/examples/full.py` - 测试用例
